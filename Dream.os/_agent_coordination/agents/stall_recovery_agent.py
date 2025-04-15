import time
import json
from pathlib import Path
# Assuming task_utils is importable from parent dir
try:
    from .._agent_coordination.task_utils import read_tasks
except ImportError:
    try:
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from _agent_coordination.task_utils import read_tasks
    except ImportError as e:
        print(f"Error: Could not import read_tasks from task_utils. Task list check disabled. {e}")
        # Define a dummy function
        def read_tasks(*args, **kwargs):
            print("Warning: read_tasks dummy used.")
            return None # Indicate failure/inability to check

from tools.project_context_producer import produce_project_context
import logging # Added logging
# Potential future imports: mailbox_utils, config, logging

# Configure logging
logger = logging.getLogger("StallRecoveryAgent")
if not logger.hasHandlers():
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class StallRecoveryAgent:
    def __init__(self, project_root=".", log_file_path="logs/agent_ChatCommander.log", check_interval=60, task_list_path="task_list.json"):
        """
        Initializes the StallRecoveryAgent.

        Args:
            project_root (str): The root directory of the project.
            log_file_path (str): Path to the log file to monitor.
            check_interval (int): Interval in seconds to check for stalls.
            task_list_path (str): Path to the main task list file.
        """
        self.project_root = Path(project_root).resolve()
        self.log_file_path = self.project_root / log_file_path 
        self.task_list_path = self.project_root / task_list_path # Store task list path
        self.check_interval = check_interval
        self.last_log_size = 0 # To detect changes/stalls based on log activity
        # Get initial size on startup
        try:
            if self.log_file_path.exists():
                self.last_log_size = self.log_file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Could not get initial log file size for {self.log_file_path}: {e}")
            
        logger.info(f"StallRecoveryAgent initialized. Monitoring: {self.log_file_path}. Task List: {self.task_list_path}")

    def _is_system_busy(self) -> bool:
        """Checks if there are active tasks in the task list."""
        tasks = read_tasks(self.task_list_path)
        if tasks is None: # Handle read failure
            logger.warning("Could not read task list to check busy status. Assuming not busy.")
            return False 
        
        for task in tasks:
            status = task.get("status", "").upper()
            if status in ["PENDING", "PROCESSING"]:
                logger.debug(f"System busy: Task {task.get('task_id')} is {status}.")
                return True
        logger.debug("System not busy: No PENDING or PROCESSING tasks found.")
        return False

    def check_for_stall(self):
        """
        Checks the monitored log file for signs of a stall, but only if the system
        doesn't appear busy based on the task list.
        """
        try:
            current_log_size = self.log_file_path.stat().st_size
            log_unchanged = (current_log_size == self.last_log_size and current_log_size > 0)
            
            if log_unchanged:
                logger.debug(f"Log file size unchanged ({self.log_file_path}). Checking system busy status...")
                if not self._is_system_busy():
                    logger.warning(f"Potential stall detected: Log file size hasn't changed AND no active tasks found.")
                    # Read last N lines/chars for context analysis
                    try:
                        with self.log_file_path.open('r', encoding='utf-8') as f:
                            # Efficiently get last ~10k chars (adjust as needed)
                            f.seek(max(0, current_log_size - 10000)) 
                            log_tail = f.read() 
                        return log_tail # Return the tail for context production
                    except Exception as read_e:
                         logger.error(f"Error reading log tail for stall analysis: {read_e}")
                         return None # Cannot analyze if read fails
                else:
                     logger.info("Log file size unchanged, but system is busy with tasks. No stall declared.")
                     # Update last_log_size even if busy, so next check uses current size
                     self.last_log_size = current_log_size 
                     return None
            else:
                # Log changed size (optional, can be verbose)
                # logger.debug(f"Log file size changed: {self.last_log_size} -> {current_log_size}")
                pass
                
            # Always update size if it changed or if we didn't declare stall despite no change
            self.last_log_size = current_log_size
            return None 
        except FileNotFoundError:
            # Don't treat missing log file as a stall unless persistent
            logger.warning(f"Monitored log file not found: {self.log_file_path}")
            self.last_log_size = 0
            return None
        except Exception as e:
            logger.error(f"Error checking log file for stall: {e}", exc_info=True)
            return None

    def log_stall_event(self, context: dict, recovery_dispatched: bool):
        """Logs the details of a detected stall event to a JSON file."""
        log_path = self.project_root / "logs" / "stall_events.log" # Using .log extension for consistency
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stall_category": context.get("stall_category", "UNKNOWN"),
            "relevant_files": context.get("relevant_files", []),
            "suggested_action_keyword": context.get("suggested_action_keyword", "N/A"),
            "recovery_dispatched": recovery_dispatched,
            "recovery_task_id": context.get("recovery_task_id", None) # Add task_id if available
        }
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True) # Ensure logs directory exists
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[StallRecovery] Failed to log stall event: {e}")

    def dispatch_recovery_task(self, context: dict):
        """Generates and appends a recovery task to task_list.json with dynamic parameters."""
        task_list_path = self.project_root / "task_list.json"
        stall_category = context.get("stall_category", "UNCATEGORIZED")
        task_id = f"recovery_{stall_category.lower()}_{int(time.time())}"
        
        # Determine task_type and base params based on category
        task_type = "generic_recovery"
        params = {
            "stall_category": stall_category,
            "relevant_files": context.get("relevant_files", [])[:3], # Limit for brevity in task
            "recovery_intent": context.get("suggested_action_keyword", "Perform general diagnostics.")
        }
        target_agent = "CursorControlAgent" # Default target

        if stall_category == "NO_INPUT":
            task_type = "resume_operation"
            params["instruction_hint"] = "Check editor state or task list for next action."
        elif stall_category == "NEEDS_TASKS":
            task_type = "generate_task"
            params["instruction_hint"] = "Review project goals and define the next logical task."
        elif stall_category == "LOOP_BREAK":
            task_type = "diagnose_loop"
            params["instruction_hint"] = "Analyze recent actions/logs for repetitive patterns and suggest a fix."
        elif stall_category == "AWAIT_CONFIRM":
            task_type = "confirmation_check"
            params["instruction_hint"] = "Analyze state for safety, proceed if clear, otherwise summarize confirmation needed."
            # Potentially target a Supervisor agent here later
        elif stall_category == "MISSING_CONTEXT":
            task_type = "context_reload"
            params["instruction_hint"] = "Attempt to reload relevant context files or project state."
        elif stall_category == "UNCLEAR_OBJECTIVE":
            task_type = "clarify_objective"
            params["instruction_hint"] = "Review high-level goals or request clarification."
        # Add more specific types and params as needed

        new_task = {
            "task_id": task_id,
            "status": "PENDING",
            "task_type": task_type, # Added task type
            "action": context.get("suggested_action_keyword", "Perform general diagnostics."), 
            "params": params,  # Now includes dynamic params
            "target_agent": target_agent, # Still default, but defined
            "timestamp_created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        try:
            if not task_list_path.exists():
                task_list_path.write_text("[]", encoding="utf-8")
            with open(task_list_path, "r+", encoding="utf-8") as f:
                tasks = json.load(f)
                tasks.append(new_task)
                f.seek(0)
                json.dump(tasks, f, indent=2)
                f.truncate()
            print(f"[StallRecovery] Recovery task added: {task_id}")
            return task_id # Return the ID for logging
        except Exception as e:
            print(f"[StallRecovery] Failed to dispatch recovery task: {e}")
            return None

    def attempt_recovery(self, log_snippet):
        """
        Uses the context bridge utility to analyze the situation, log the event,
        and dispatch a recovery task.
        """
        print("Attempting stall recovery...")
        context = produce_project_context(log_snippet, str(self.project_root), return_dict=True)
        recovery_dispatched = False
        dispatched_task_id = None

        if context:
            print("--- Stall Context ---")
            print(f"Category: {context['stall_category']}")
            print(f"Suggested Keyword: {context['suggested_action_keyword']}")
            print(f"Relevant Files: {context['relevant_files']}")
            print("---------------------")

            # Dispatch recovery task
            dispatched_task_id = self.dispatch_recovery_task(context)
            if dispatched_task_id:
                recovery_dispatched = True
                context["recovery_task_id"] = dispatched_task_id # Add for logging

            # Log the event regardless of dispatch success, but note if dispatched
            self.log_stall_event(context, recovery_dispatched)

            # Placeholder print statements (can be removed later)
            if context['stall_category'] == "AWAIT_CONFIRM":
                print("Action: Analyze context and potentially send confirmation request.")
            elif context['stall_category'] == "NO_INPUT":
                 print("Action: Check task queue or generate next task.")
            # Add logic for other categories...
            else:
                 print("Action: Perform general diagnostics or escalate.")
        else:
            print("Failed to generate stall context.")
            # Log minimal failure event
            self.log_stall_event({"stall_category": "CONTEXT_FAILURE"}, False)


    def run(self):
        """
        Main loop for the agent to periodically check for stalls.
        """
        print("StallRecoveryAgent running...")
        try:
            while True:
                log_tail_for_analysis = self.check_for_stall()
                if log_tail_for_analysis:
                    self.attempt_recovery(log_tail_for_analysis)
                
                # Wait before next check
                time.sleep(self.check_interval) 
        except KeyboardInterrupt:
            print("StallRecoveryAgent stopped by user.")
        except Exception as e:
            print(f"StallRecoveryAgent encountered an error: {e}")

# Example instantiation and run (if executed directly)
if __name__ == "__main__":
    # Assumes running from the workspace root where logs/ and tools/ exist
    recovery_agent = StallRecoveryAgent(project_root=".") 
    recovery_agent.run() 