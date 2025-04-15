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
    """Monitors for failed tasks and injects repair/diagnostic tasks."""

    def __init__(self, agent_bus: AgentBus, task_list_path: str = DEFAULT_TASK_LIST_PATH):
        """
        Initializes the feedback loop agent.

        Args:
            agent_bus: The central AgentBus instance.
            task_list_path: Path to the JSON file containing the task list.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.task_list_path = os.path.abspath(task_list_path)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock() # Lock for task list access

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
        logger.info(f"{self.agent_name} initialized. Monitoring task list: {self.task_list_path}")

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
        """Generates a standard diagnostic task definition."""
        original_task_id = failed_task.get("task_id", "unknown_original")
        failure_reason = f"Task failed with status {failed_task.get('status')}. Last response: {failed_task.get('last_response')}"
        
        new_task_id = f"repair_{original_task_id}_{uuid.uuid4().hex[:6]}"
        
        # Basic diagnostic command - could be made more context-aware
        diag_command = (
            f"echo \"[Agent Repair] Task {original_task_id} failed. Reviewing environment...\" && "
            f"echo \"Failure Reason: {failure_reason[:100]}...\" && " # Limit reason length
            f"pwd && "
            f"ls -alh"
            # Future: Add commands to get logs, check resource usage, etc.
        )

        repair_task = {
            "task_id": new_task_id,
            "status": TaskStatus.PENDING,
            "task_type": "diagnose_task_failure", # Categorize the task
            "action": "RUN_TERMINAL_COMMAND",
            "params": {
                "command": diag_command,
                "related_task_id": original_task_id,
                "failure_reason": failure_reason,
                # Include original task details for context?
                "original_task_action": failed_task.get("action"),
                "original_task_params": failed_task.get("params") 
            },
            "depends_on": [original_task_id], # Ensure original task is no longer PENDING/DISPATCHED
            "priority": 1, # High priority for repair tasks
            "retry_count": 0,
            "repair_attempts": 0, # Initialize for the repair task itself
            "target_agent": "CursorControlAgent" # Assuming terminal diagnostics for now
        }
        logger.info(f"Generated diagnostic task {new_task_id} for failed task {original_task_id}.")
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

    def run_cycle(self):
        """Checks for failed tasks and injects repair tasks."""
        logger.debug(f"{self.agent_name} checking for failed tasks...")
        tasks = self._load_tasks()
        if not tasks:
            return
        
        tasks_to_add = []
        tasks_updated = False

        for task in tasks:
            if not isinstance(task, dict): continue

            task_id = task.get("task_id")
            status = task.get("status")
            repair_attempts = task.get("repair_attempts", 0)

            # Check if task failed and hasn't exceeded repair attempts
            if status in [TaskStatus.FAILED, TaskStatus.ERROR] and repair_attempts < MAX_REPAIR_ATTEMPTS:
                 logger.warning(f"Detected failed task '{task_id}' with status '{status}'. Attempting repair injection (Attempt {repair_attempts + 1}).")
                 
                 # Generate the repair task
                 new_task = self._create_diagnostic_task(task)
                 tasks_to_add.append(new_task)
                 
                 # Mark the original task as having triggered a repair
                 if self._mark_repair_triggered(tasks, task_id):
                     tasks_updated = True
                 
                 # Log the injection event
                 self._log_injection_event(task_id, new_task["task_id"])

        # Add new tasks and save if changes were made
        if tasks_to_add:
             tasks.extend(tasks_to_add)
             tasks_updated = True # Need to save the combined list
        
        if tasks_updated:
            if not self._save_tasks(tasks):
                logger.error("Failed to save task list after injecting repair tasks!")

        logger.debug(f"{self.agent_name} finished failure check cycle.")

    # --- Background Thread Methods (Copied from TaskExecutorAgent) ---
    def _run_loop(self):
        """The main loop for the agent thread."""
        logger.info(f"{self.agent_name} background thread started.")
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                 logger.error(f"Critical error in {self.agent_name} run loop: {e}", exc_info=True)
            # Adjust sleep time as needed - check less frequently than executor?
            time.sleep(15) # Check for failures every 15 seconds
        logger.info(f"{self.agent_name} background thread stopped.")

    def start(self):
        """Starts the agent's task monitoring loop in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"{self.agent_name} is already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"{self.agent_name}Loop", daemon=True)
        self._thread.start()
        logger.info(f"{self.agent_name} started background thread.")

    def stop(self):
        """Signals the agent's background thread to stop and waits for it."""
        if self._thread is None or not self._thread.is_alive():
            logger.info(f"{self.agent_name} is not running.")
            return

        logger.info(f"Stopping {self.agent_name} background thread...")
        self._stop_event.set()
        self._thread.join(timeout=10)
        if self._thread.is_alive():
             logger.warning(f"{self.agent_name} background thread did not stop gracefully.")
        else:
             logger.info(f"{self.agent_name} background thread stopped successfully.")
        self._thread = None

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