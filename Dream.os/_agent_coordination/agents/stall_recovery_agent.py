import time
import json
from pathlib import Path
from tools.project_context_producer import produce_project_context
# Potential future imports: mailbox_utils, config, logging

class StallRecoveryAgent:
    def __init__(self, project_root=".", log_file_path="logs/agent_ChatCommander.log", check_interval=60):
        """
        Initializes the StallRecoveryAgent.

        Args:
            project_root (str): The root directory of the project.
            log_file_path (str): Path to the log file to monitor.
            check_interval (int): Interval in seconds to check for stalls.
        """
        self.project_root = Path(project_root).resolve()
        self.log_file_path = self.project_root / log_file_path 
        self.check_interval = check_interval
        self.last_log_size = 0 # To detect changes/stalls based on log activity
        print(f"StallRecoveryAgent initialized. Monitoring: {self.log_file_path}")

    def check_for_stall(self):
        """
        Checks the monitored log file for signs of a stall.
        Placeholder: Currently checks if the log file hasn't changed size.
        Needs more sophisticated logic (e.g., parsing last lines, checking timestamps).
        """
        try:
            current_log_size = self.log_file_path.stat().st_size
            if current_log_size == self.last_log_size and current_log_size > 0:
                print(f"Potential stall detected: Log file size hasn't changed ({self.log_file_path})")
                # Read last N lines/chars for context analysis
                with self.log_file_path.open('r', encoding='utf-8') as f:
                    # Efficiently get last ~10k chars (adjust as needed)
                    f.seek(max(0, current_log_size - 10000)) 
                    log_tail = f.read() 
                return log_tail # Return the tail for context production
            self.last_log_size = current_log_size
            return None 
        except FileNotFoundError:
            print(f"Warning: Log file not found: {self.log_file_path}")
            self.last_log_size = 0
            return None
        except Exception as e:
            print(f"Error checking log file: {e}")
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
        """Generates and appends a recovery task to task_list.json."""
        task_list_path = self.project_root / "task_list.json"
        task_id = f"recovery_{context['stall_category'].lower()}_{int(time.time())}"
        new_task = {
            "task_id": task_id,
            "status": "PENDING",
            # Using suggested_action_keyword as per user spec, might need refinement later
            "action": context.get("suggested_action_keyword", "Perform general diagnostics."), 
            "params": {},  # Add dynamic params based on category if needed
            "target_agent": "CursorControlAgent", # Or determine dynamically?
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