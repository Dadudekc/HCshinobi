"""
Agent responsible for monitoring task failures and injecting new diagnostic tasks.
"""
import logging
import os
import sys
import json
import time
import threading
import uuid # For generating unique task IDs
from datetime import datetime
from typing import Optional, Dict, Any, List

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from coordination.agent_bus import AgentBus, Message
    # Use TaskStatus constants for consistency
    from agents.task_executor_agent import TaskStatus 
except ImportError:
     logger.warning("Could not import AgentBus/TaskStatus relatively.")
     # Define dummy classes if needed
     class AgentBus: 
         def register_agent(self, *args, **kwargs): pass
         def send_message(self, *args, **kwargs): return "dummy_msg_id"
     class Message: pass
     class TaskStatus: 
        FAILED = "FAILED"; ERROR = "ERROR"; PENDING = "PENDING"; COMPLETED = "COMPLETED"

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = "PromptFeedbackLoopAgent"
DEFAULT_TASK_LIST_PATH = "task_list.json"
MAX_REPAIR_ATTEMPTS = 1 # Limit repair attempts per failed task

class PromptFeedbackLoopAgent:
    """Monitors for failed tasks via AgentBus messages and injects repair/diagnostic tasks."""

    def __init__(self, agent_bus: AgentBus, task_list_path: str = DEFAULT_TASK_LIST_PATH, task_list_lock: Optional[threading.Lock] = None):
        """
        Initializes the feedback loop agent.

        Args:
            agent_bus: The central AgentBus instance.
            task_list_path: Path to the JSON file containing the task list.
            task_list_lock: A shared threading.Lock() for task list access.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.task_list_path = os.path.abspath(task_list_path)
        self._lock = task_list_lock if task_list_lock else threading.Lock()

        # Ensure task list file exists (though TaskExecutorAgent likely creates it)
        if not os.path.exists(self.task_list_path):
            logger.warning(f"Task list file not found at {self.task_list_path} by {self.agent_name}. Attempting creation.")
            try:
                 os.makedirs(os.path.dirname(self.task_list_path), exist_ok=True)
                 with open(self.task_list_path, 'w') as f:
                     json.dump([], f)
            except IOError as e:
                logger.error(f"Failed to create task list file: {e}")
                # Agent might not be able to function

        # Register agent
        self.bus.register_agent(self.agent_name, capabilities=["feedback_loop", "task_injection"])
        
        # Register handler for relevant messages indicating failure
        # Option 1: Listen to messages directed to TaskExecutorAgent with failed status
        self.bus.register_handler("TaskExecutorAgent", self.handle_potential_failure)
        # Option 2: Listen for specific ERROR messages (might be less reliable for task status)
        self.bus.register_handler("ERROR", self.handle_potential_failure)
        # Option 3: Define and listen for a specific TASK_FAILED message type (ideal)
        # self.bus.register_handler("TASK_FAILED", self.handle_task_failure)
        
        logger.info(f"{self.agent_name} initialized. Listening for task failures on AgentBus.")

    # --- Use Task List Load/Save/Update Logic (Could be refactored to common utility) ---
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Loads tasks from the JSON file. Returns empty list on error."""
        # Duplicated from TaskExecutorAgent - Consider refactoring later
        with self._lock:
            try:
                with open(self.task_list_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                if not isinstance(tasks, list):
                    logger.error(f"Invalid format in task list file {self.task_list_path}. Expected list.")
                    return []
                return tasks
            except FileNotFoundError:
                 logger.warning(f"Task list file not found during load: {self.task_list_path}")
                 return []
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from task list file {self.task_list_path}: {e}")
                return []
            except IOError as e:
                logger.error(f"Error reading task list file {self.task_list_path}: {e}")
                return []
            except Exception as e:
                 logger.error(f"Unexpected error loading tasks: {e}", exc_info=True)
                 return []

    def _save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        """Saves the modified task list back to the JSON file."""
        # Duplicated from TaskExecutorAgent - Consider refactoring later
        with self._lock:
            temp_path = self.task_list_path + ".tmp"
            try:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, indent=2)
                os.replace(temp_path, self.task_list_path)
                return True
            except IOError as e:
                logger.error(f"Error writing task list file {self.task_list_path}: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error saving tasks: {e}", exc_info=True)
                 if os.path.exists(temp_path): 
                     try: os.remove(temp_path)
                     except OSError: pass
            return False

    def _mark_repair_triggered(self, tasks: List[Dict[str, Any]], task_id: str) -> bool:
        """Finds a task and marks it as having triggered a repair action."""
        found = False
        for task in tasks:
            if isinstance(task, dict) and task.get("task_id") == task_id:
                repair_attempts = task.get("repair_attempts", 0)
                task["repair_attempts"] = repair_attempts + 1
                # Using repair_attempts counter instead of a boolean flag
                task["last_updated"] = datetime.now().isoformat()
                logger.info(f"Marked task '{task_id}' as repair attempt #{task['repair_attempts']}.")
                found = True
                break
        if not found:
            logger.warning(f"Could not find task '{task_id}' to mark repair attempt.")
        return found

    def _create_diagnostic_task(self, failed_task: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a diagnostic task tailored to the type of failure."""
        original_task_id = failed_task.get("task_id", "unknown_original")
        original_action = failed_task.get("action")
        original_params = failed_task.get("params", {})
        failure_reason = f"Task failed with status {failed_task.get('status')}. Last response: {failed_task.get('last_response')}"
        
        new_task_id = f"repair_{original_task_id}_{uuid.uuid4().hex[:6]}"
        diag_commands = [
            f"echo \"[Agent Repair] Task {original_task_id} (Action: {original_action}) failed. Diagnosing...\"",
            f"echo \"Failure Reason: {failure_reason[:150]}...\""
        ]
        target_agent = "CursorControlAgent" # Default target
        diag_action = "RUN_TERMINAL_COMMAND" # Default action

        # --- Context-Specific Diagnostics ---
        if original_action == "RUN_TERMINAL_COMMAND":
            # Check CWD and list files
            diag_commands.append("pwd")
            diag_commands.append("ls -alh")
            # If original command might have logs, try to tail them (example)
            original_command = original_params.get("command", "")
            if "build" in original_command or ".py" in original_command:
                 # Very basic log file guessing - needs improvement
                 diag_commands.append("echo \"Attempting to check recent logs...\"" )
                 diag_commands.append("ls -lt *.log | head -n 5") # List recent log files
                 # diag_commands.append("tail -n 20 latest.log") # Requires knowing log name
        
        elif original_action == "OPEN_FILE":
            file_path = original_params.get("file_path")
            if file_path:
                # Check if file exists and its permissions
                diag_commands.append(f"echo \"Checking file status for: {file_path}\"" )
                diag_commands.append(f"ls -ld \"{file_path}\"" ) # Use quotes for paths with spaces
            else:
                 diag_commands.append("echo \"Original OPEN_FILE task missing file_path parameter.\"" )
                 diag_commands.append("pwd")
                 diag_commands.append("ls -alh")

        elif original_action in ["GET_EDITOR_CONTENT", "SET_EDITOR_CONTENT", "INSERT_EDITOR_TEXT", "FIND_ELEMENT", "ENSURE_CURSOR_FOCUSED"]:
             # Likely indicates an issue with Cursor interaction or the instance itself
             diag_commands.append("echo \"Checking Cursor process status...\"" )
             if sys.platform == "win32":
                 diag_commands.append("tasklist | findstr Cursor")
             else: # Linux/macOS
                 diag_commands.append("ps aux | grep -i [C]ursor") # [C] prevents grep finding itself
             # Could also inject a task to explicitly refocus?
             # diag_action = "ENSURE_CURSOR_FOCUSED" # Requires CursorControlAgent to handle this action

        else:
             # Default diagnostics for unknown actions
             diag_commands.append("echo \"Running default diagnostics (pwd, ls)...\"" )
             diag_commands.append("pwd")
             diag_commands.append("ls -alh")

        # Combine commands into a single string for shell execution
        full_diag_command = " && ".join(diag_commands)

        repair_task = {
            "task_id": new_task_id,
            "status": TaskStatus.PENDING,
            "task_type": f"diagnose_{original_action}_failure", # More specific type
            "action": diag_action, # Could be different if not RUN_TERMINAL_COMMAND
            "params": {
                "command": full_diag_command,
                "related_task_id": original_task_id,
                "failure_reason": failure_reason,
                "original_task_action": original_action,
                "original_task_params": original_params 
            },
            "depends_on": [original_task_id],
            "priority": 1, 
            "retry_count": 0,
            "repair_attempts": 0,
            "target_agent": target_agent
        }
        logger.info(f"Generated diagnostic task {new_task_id} for failed task {original_task_id} (Action: {original_action}).")
        return repair_task

    def _log_injection_event(self, failed_task_id: str, new_task_id: str):
         """Sends a log message to the AgentMonitorAgent (if available)."""
         log_payload = {
             "failed_task_id": failed_task_id,
             "new_task_id": new_task_id,
             "trigger_agent": self.agent_name
         }
         # Send to monitor or broadcast an event
         self.bus.send_message(
             sender=self.agent_name,
             recipient="AgentMonitorAgent", # Direct message to monitor
             message_type="SYSTEM_EVENT", 
             payload=log_payload,
             status="AUTO_REPAIR_TASK_CREATED"
         )

    # --- New Message Handler --- 
    def handle_potential_failure(self, message: Message):
        """Handles messages that might indicate a task failure."""
        # Check if message represents a failed task
        task_id = getattr(message, 'task_id', None)
        status = getattr(message, 'status', None)
        
        is_failure = status in [TaskStatus.FAILED, TaskStatus.ERROR]
        # If listening to TaskExecutorAgent, check recipient
        is_response_to_executor = message.recipient == "TaskExecutorAgent"

        # Determine if this message signals a failure we should act on
        # This logic might need refinement based on actual message flow
        if task_id and is_failure and is_response_to_executor:
             logger.info(f"Detected potential failure for task {task_id} via message {message.id} from {message.sender}.")
             self.trigger_repair_task_injection(task_id)
        elif message.type == "ERROR" and task_id: # Handle generic ERROR messages linked to a task
             logger.info(f"Detected potential failure for task {task_id} via generic ERROR message {message.id} from {message.sender}.")
             self.trigger_repair_task_injection(task_id)
        # Add handling for specific TASK_FAILED event type if implemented later
        # elif message.type == "TASK_FAILED":
        #    self.trigger_repair_task_injection(task_id)

    def trigger_repair_task_injection(self, failed_task_id: str):
        """Loads tasks, checks repair attempts, creates, and injects a diagnostic task."""
        tasks = self._load_tasks()
        if not tasks: 
            logger.error("Cannot trigger repair: Failed to load task list.")
            return

        failed_task = None
        for task in tasks:
             if isinstance(task, dict) and task.get("task_id") == failed_task_id:
                 failed_task = task
                 break
        
        if not failed_task:
            logger.warning(f"Cannot trigger repair: Failed task {failed_task_id} not found in list.")
            return

        # Check if max repair attempts exceeded
        repair_attempts = failed_task.get("repair_attempts", 0)
        if repair_attempts >= MAX_REPAIR_ATTEMPTS:
            logger.info(f"Skipping repair for task {failed_task_id}: Max repair attempts ({MAX_REPAIR_ATTEMPTS}) reached.")
            return

        # Create the diagnostic/repair task
        repair_task = self._create_diagnostic_task(failed_task)
        logger.info(f"Generated repair task {repair_task['task_id']} for failed task {failed_task_id}.")

        # Mark the original task as having triggered a repair
        marked = self._mark_repair_triggered(tasks, failed_task_id)
        
        # Add the new repair task to the list
        tasks.append(repair_task)

        # Save the updated task list
        if self._save_tasks(tasks):
            logger.info(f"Successfully injected repair task {repair_task['task_id']} into task list.")
            # Log the injection event separately? 
            self._log_injection_event(failed_task_id, repair_task['task_id'])
        else:
            logger.error(f"Failed to save task list after injecting repair task for {failed_task_id}.")

    # Add shutdown method if needed for cleanup
    def shutdown(self):
        logger.info(f"Shutting down {self.agent_name}...")
        # Unregister?
        # self.bus.deregister_agent(self.agent_name)
        logger.info(f"{self.agent_name} shutdown complete.")

# ========= USAGE BLOCK START ==========
# Minimal block, primarily for structure verification
if __name__ == "__main__":
    print(f">>> Running module: {__file__} (Basic Checks)")
    dummy_task_file = "./temp_feedback_loop_tasks.json"
    dummy_log_file = "./temp_monitor_agent_log_feedback.jsonl"

    # Sample tasks including a failed one
    sample_tasks = [
        {"task_id": "task_ok", "status": "COMPLETED", "action": "GET_EDITOR_CONTENT", "repair_attempts": 0},
        {"task_id": "task_fail_1", "status": "FAILED", "action": "RUN_TERMINAL_COMMAND", "params": {"command": "bad_cmd"}, "last_response": {"error": "Command failed"}, "repair_attempts": 0},
        {"task_id": "task_fail_2", "status": "ERROR", "action": "OTHER_ACTION", "repair_attempts": 1} # Already attempted repair
    ]

    # Dummy Monitor Agent to receive log messages
    logged_events = []
    class DummyMonitor:
        def handle_event_message(self, message):
             print(f"DummyMonitor received: {message.payload}")
             logged_events.append(message.payload)

    # Dummy Agent Bus
    class DummyBus:
        handlers = {}
        monitor = DummyMonitor()
        def register_agent(self, agent_name, *args, **kwargs): print(f"DummyBus: Registering {agent_name}")
        def register_handler(self, target, handler): self.handlers[target] = handler
        def send_message(self, sender, recipient, message_type, payload, status=None, **kwargs):
            print(f"DummyBus: Sending message from {sender} to {recipient} (Type: {message_type}, Status: {status})")
            if recipient == "AgentMonitorAgent":
                 # Simulate message delivery to monitor
                 class Msg: pass
                 m = Msg()
                 m.sender=sender; m.recipient=recipient; m.type=message_type; m.payload=payload; m.status=status
                 self.monitor.handle_event_message(m)
            return f"msg_{time.time()}"

    bus = DummyBus()
    try:
        with open(dummy_task_file, 'w') as f: json.dump(sample_tasks, f, indent=2)
        print(f"Created dummy task file: {dummy_task_file}")

        print("\n>>> Instantiating PromptFeedbackLoopAgent...")
        agent = PromptFeedbackLoopAgent(agent_bus=bus, task_list_path=dummy_task_file)
        print(">>> Agent instantiated.")

        print("\n>>> Running one cycle...")
        agent.run_cycle()
        print(">>> Cycle finished.")

        print("\n>>> Checking updated task file...")
        with open(dummy_task_file, 'r') as f: updated_tasks = json.load(f)
        print(json.dumps(updated_tasks, indent=2))

        # Assertions
        assert len(updated_tasks) == 4 # Original 3 + 1 new repair task
        original_failed_task = next(t for t in updated_tasks if t["task_id"] == "task_fail_1")
        assert original_failed_task.get("repair_attempts") == 1 # Marked as attempted
        original_error_task = next(t for t in updated_tasks if t["task_id"] == "task_fail_2")
        assert original_error_task.get("repair_attempts") == 1 # Unchanged as max attempts reached
        repair_task = next(t for t in updated_tasks if t["task_id"].startswith("repair_task_fail_1"))
        assert repair_task["status"] == "PENDING"
        assert repair_task["priority"] == 1
        assert repair_task["depends_on"] == ["task_fail_1"]
        print(">>> Task list updated correctly.")

        print("\n>>> Checking logged events...")
        print(json.dumps(logged_events, indent=2))
        assert len(logged_events) == 1
        assert logged_events[0]["failed_task_id"] == "task_fail_1"
        assert logged_events[0]["new_task_id"] == repair_task["task_id"]
        print(">>> Injection event logged correctly.")

    except Exception as e:
        print(f"ERROR in usage block: {e}", file=sys.stderr)
        raise
    finally:
        if os.path.exists(dummy_task_file):
             os.remove(dummy_task_file)
             print(f"Removed dummy task file: {dummy_task_file}")
        if os.path.exists(dummy_log_file):
             os.remove(dummy_log_file)
             # print(f"Removed dummy monitor log: {dummy_log_file}")

    print(f">>> Module {__file__} basic checks complete.")
    sys.exit(0)
# ========= USAGE BLOCK END ========== 