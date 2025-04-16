"""
Agent responsible for reading tasks from a list, dispatching them to appropriate agents
via the AgentBus, and potentially monitoring their status.
"""
import logging
import os
import sys
import json
import time
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
utils_dir = os.path.join(parent_dir, 'utils') # Path to core/utils
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
if utils_dir not in sys.path:
    sys.path.append(utils_dir) # Add utils dir for TaskStatusUpdater import

try:
    from coordination.agent_bus import AgentBus, Message
    # Import the new utility
    from task_status_updater import TaskStatusUpdater
except ImportError as e:
     logger.warning(f"Could not import relatively: {e}. Assuming execution context provides modules.")
     # Define dummy classes if needed for standalone script execution
     class AgentBus:
         def register_agent(self, *args, **kwargs): pass
         def send_message(self, *args, **kwargs): return "dummy_msg_id"
         def register_handler(self, *args, **kwargs): pass
     class Message:
         sender = "DummySender"
         status = "SUCCESS"
         payload = {}
         task_id = "dummy-task-id"
         id = "dummy-msg_id"
     class TaskStatusUpdater:
         def __init__(self, *args, **kwargs): pass
         def update_task_status(self, *args, **kwargs): 
             print("[DummyTaskStatusUpdater] Update called with:", args, kwargs)
             return True

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = "TaskExecutorAgent"
DEFAULT_TASK_LIST_PATH = "task_list.json"
# Define known task statuses
class TaskStatus:
    PENDING = "PENDING"
    INVALID = "INVALID"
    DISPATCHED = "DISPATCHED"
    DISPATCH_FAILED = "DISPATCH_FAILED"
    RUNNING = "RUNNING" # Set by target agent
    COMPLETED = "COMPLETED" # Set by target agent via response/update
    FAILED = "FAILED" # Set by target agent via response/update
    ERROR = "ERROR" # Set by target agent via response/update
    UNKNOWN = "UNKNOWN" # Added for normalization

class TaskExecutorAgent:
    """Reads tasks from a file and dispatches them via the AgentBus."""

    def __init__(self, agent_bus: AgentBus, task_status_updater: TaskStatusUpdater, task_list_path: str = DEFAULT_TASK_LIST_PATH, task_list_lock: Optional[threading.Lock] = None):
        """
        Initializes the task executor.

        Args:
            agent_bus: The central AgentBus instance.
            task_status_updater: The utility for updating task statuses.
            task_list_path: Path to the JSON file containing the task list.
            task_list_lock: A threading.Lock() object for synchronizing access to task_list.json
                          (primarily for reading tasks to dispatch, status updates handled by updater).
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        self.status_updater = task_status_updater # Store the updater instance
        self.task_list_path = os.path.abspath(task_list_path)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Lock mainly used for reading now
        self._lock = task_list_lock if task_list_lock else threading.Lock()

        # Ensure task list file exists (read-only check initially)
        if not os.path.exists(self.task_list_path):
            logger.warning(f"Task list file not found at {self.task_list_path}, creating an empty one.")
            try:
                 # Create directory if it doesn't exist
                 os.makedirs(os.path.dirname(self.task_list_path), exist_ok=True)
                 with open(self.task_list_path, 'w') as f:
                     json.dump([], f)
            except IOError as e:
                logger.error(f"Failed to create task list file: {e}")
                raise

        # Register agent
        self.bus.register_agent(self.agent_name, capabilities=["task_execution", "task_status_handling"])
        # Register handler for messages directed to this agent (e.g., responses)
        self.bus.register_handler(self.agent_name, self.handle_response)
        # Register handler for TASK_STATUS_UPDATE messages if this agent should handle them
        # (Alternatively, AgentMonitorAgent could handle these based on DEFAULT_UPDATE_TARGET)
        # self.bus.register_handler(MSG_TYPE_TASK_UPDATE, self.handle_direct_status_update)

        logger.info(f"{self.agent_name} initialized. Monitoring task list: {self.task_list_path}")

    def _normalize_status(self, agent_status: Optional[str]) -> str:
        """Maps agent response status to standardized task status."""
        if not agent_status:
            return TaskStatus.UNKNOWN # Or FAILED?
        status_upper = agent_status.upper()
        # Map more specific errors to FAILED or ERROR
        return {
            "SUCCESS": TaskStatus.COMPLETED,
            "FAILED": TaskStatus.FAILED,
            "ERROR": TaskStatus.ERROR,
            "EXECUTION_ERROR": TaskStatus.ERROR,
            "BAD_REQUEST": TaskStatus.FAILED,
            "UNKNOWN_ACTION": TaskStatus.FAILED,
            "COMPLETED": TaskStatus.COMPLETED, # Handle cases where status is already correct
            "INVALID_STATE": TaskStatus.FAILED,
            "TIMEOUT": TaskStatus.FAILED,
            # Add mappings for other potential agent statuses
        }.get(status_upper, TaskStatus.UNKNOWN) # Default if status is not explicitly mapped

    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Loads tasks from the JSON file. Returns empty list on error."""
        # Use the shared lock passed to the updater if possible, or the internal one
        lock_to_use = self.status_updater.lock if hasattr(self.status_updater, 'lock') else self._lock
        with lock_to_use: # Use the appropriate lock
            try:
                with open(self.task_list_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                if not isinstance(tasks, list):
                    logger.error(f"Invalid format in task list file {self.task_list_path}. Expected a list, got {type(tasks).__name__}.")
                    return []
                # Validate basic task structure?
                return tasks
            except FileNotFoundError:
                 logger.error(f"Task list file vanished: {self.task_list_path}")
                 return []
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from task list file {self.task_list_path}: {e}")
                # Optionally attempt to recover or backup the bad file
                return []
            except IOError as e:
                logger.error(f"Error reading task list file {self.task_list_path}: {e}")
                return []
            except Exception as e:
                 logger.error(f"Unexpected error loading tasks: {e}", exc_info=True)
                 return []

    def handle_response(self, message: Message):
        """Handles response messages received from other agents by using the TaskStatusUpdater."""
        logger.debug(f"{self.agent_name} received response message: Type={message.type}, Sender={message.sender}, Status={message.status}, TaskID={getattr(message, 'task_id', 'N/A')}")

        task_id = getattr(message, 'task_id', None)
        if not task_id:
            logger.warning(f"Received response message from {message.sender} without a task_id. Cannot update task status. Msg ID: {message.id}")
            return

        # Normalize the status received from the agent
        final_task_status = self._normalize_status(message.status)
        if final_task_status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.ERROR]:
            logger.warning(f"Received response for task {task_id} with unhandled status '{message.status}'. Not updating final task status.")
            # Optionally, update with an 'intermediate' status?
            return

        # Extract result or error details from the payload
        result_summary = None
        error_details = None
        if final_task_status == TaskStatus.COMPLETED:
            # Try to find a meaningful summary in the payload
            result_summary = str(message.payload) # Default to string representation
            if isinstance(message.payload, dict):
                result_summary = message.payload.get('summary', message.payload.get('result', str(message.payload)))
        elif final_task_status in [TaskStatus.FAILED, TaskStatus.ERROR]:
             if isinstance(message.payload, dict):
                error_details = message.payload.get('error', message.payload.get('error_details', str(message.payload)))
             else:
                 error_details = str(message.payload) # Store whatever payload came back

        # Use the TaskStatusUpdater
        success = self.status_updater.update_task_status(
            task_id=task_id,
            status=final_task_status,
            result_summary=result_summary,
            error_details=error_details,
            originating_agent=message.sender # Attribute the update to the agent that sent the response
        )

        if not success:
            logger.error(f"TaskStatusUpdater failed to update status for task '{task_id}' from agent {message.sender}. Check updater logs.")
        else:
             logger.info(f"TaskStatusUpdater successfully processed status update for task '{task_id}' to {final_task_status}.")

    def _check_dependencies(self, task_to_check: Dict[str, Any], all_tasks_map: Dict[str, Dict[str, Any]]) -> bool:
        """Checks if all dependencies for a given task are met (status is COMPLETED)."""
        dependencies = task_to_check.get("depends_on", [])
        if not dependencies:
            return True # No dependencies
        
        for dep_id in dependencies:
            dep_task = all_tasks_map.get(dep_id)
            if not dep_task:
                logger.warning(f"Task '{task_to_check.get('task_id')}' has unmet dependency: Task '{dep_id}' not found.")
                # Treat missing dependency as unmet for safety
                return False
            if dep_task.get("status") != TaskStatus.COMPLETED:
                 logger.debug(f"Task '{task_to_check.get('task_id')}' dependency '{dep_id}' not met (Status: {dep_task.get('status')}).")
                 return False # Dependency not complete
        
        logger.debug(f"All dependencies met for task '{task_to_check.get('task_id')}'.")
        return True

    def run_cycle(self):
        """Loads tasks, sorts by priority, checks dependencies, finds pending ones, and dispatches them."""
        logger.debug(f"{self.agent_name} starting run cycle...")
        tasks = self._load_tasks()
        if not tasks:
            return

        # Create a map for quick dependency lookup
        tasks_map = {task.get("task_id"): task for task in tasks if isinstance(task, dict) and task.get("task_id")}

        # Sort tasks by priority (lower number = higher priority), PENDING first
        def sort_key(task):
            if not isinstance(task, dict):
                return (float('inf'), float('inf')) # Invalid tasks last
            status = task.get("status", TaskStatus.PENDING).upper()
            priority = task.get("priority", 99) # Default priority if missing
            # Sort PENDING tasks by priority, then other statuses
            status_order = 0 if status == TaskStatus.PENDING else 1
            return (status_order, priority)

        sorted_tasks = sorted(tasks, key=sort_key)

        tasks_updated = False
        for i, task in enumerate(sorted_tasks):
            if not isinstance(task, dict):
                 logger.warning(f"Skipping invalid entry in task list (index {i}, original list): Not a dictionary.")
                 continue

            task_id = task.get("task_id")
            status = task.get("status", TaskStatus.PENDING).upper()
            action = task.get("action") or task.get("command")
            params = task.get("params", {})
            target_agent = task.get("target_agent")
            required_capability = task.get("capability")
            retry_count = task.get("retry_count", 0)

            if status == TaskStatus.PENDING:
                if not task_id or not action:
                     logger.error(f"Skipping invalid PENDING task (missing id or action): {task}")
                     if task_id:
                          if self.status_updater.update_task_status(task_id, TaskStatus.INVALID):
                              tasks_updated = True
                     continue
                
                # --- Dependency Check --- #
                if not self._check_dependencies(task, tasks_map):
                    logger.debug(f"Skipping task '{task_id}' due to unmet dependencies.")
                    continue # Skip this task for now

                # --- Retry Logic (Placeholder/Increment) --- #
                # Increment retry count on dispatch attempt (even if it fails to send)
                # More complex retry logic (e.g., exponential backoff, based on failure type)
                # would likely live in the response handling or a dedicated retry mechanism.
                task["retry_count"] = retry_count + 1 
                tasks_updated = True # Mark for save because retry_count changed
                logger.debug(f"Attempting dispatch for task '{task_id}', attempt #{task['retry_count']}.")

                # --- Dispatch Logic (Remains the same) --- #
                recipient = None
                if target_agent:
                    recipient = target_agent
                elif required_capability:
                    # TODO: Implement capability lookup via AgentBus - RESOLVED
                    # Use the new AgentBus method
                    recipient = self.bus.find_first_agent_by_capability(required_capability)
                    if not recipient:
                        # if required_capability == "cursor_control": # Old hardcoded logic
                        #      recipient = "CursorControlAgent"
                        # else:
                        logger.warning(f"Cannot dispatch task '{task_id}': No registered agent found for capability '{required_capability}'")
                        # Use the updater to mark as failed
                        if not self.status_updater.update_task_status(task_id, TaskStatus.DISPATCH_FAILED):
                            logger.error(f"Failed to update task {task_id} status to DISPATCH_FAILED")
                        # tasks_updated = True # Status update handles persistence?
                        continue
                elif action in ["GET_EDITOR_CONTENT", "RUN_TERMINAL_COMMAND", "GET_TERMINAL_OUTPUT", "OPEN_FILE", "INSERT_TEXT", "FIND_ELEMENT"]:
                     recipient = "CursorControlAgent"
                else:
                    logger.error(f"Cannot dispatch task '{task_id}': No target agent/capability, and action '{action}' unknown.")
                    self.status_updater.update_task_status(task_id, TaskStatus.DISPATCH_FAILED)
                    tasks_updated = True
                    continue

                # --- Send Message --- #
                message_payload = {"action": action, "params": params}
                # TODO: Determine message_type more dynamically - Use action as default
                # message_type = "CURSOR_COMMAND" if recipient == "CursorControlAgent" else "GENERIC_TASK"
                # Use the action itself as the message type by default.
                # Agents should register handlers for the actions they support.
                message_type = action 

                logger.info(f"Dispatching task '{task_id}' (Action: {action}, Type: {message_type}) to agent '{recipient}'")
                sent_msg_id = self.bus.send_message(
                    sender=self.agent_name,
                    recipient=recipient,
                    message_type=message_type,
                    payload=message_payload,
                    task_id=task_id # Include task_id
                )

                if sent_msg_id:
                    self.status_updater.update_task_status(task_id, TaskStatus.DISPATCHED)
                else:
                    logger.error(f"Failed to send message for task '{task_id}' to agent '{recipient}'")
                    self.status_updater.update_task_status(task_id, TaskStatus.DISPATCH_FAILED)
                # tasks_updated is already True due to retry_count increment

        # Save changes if any task status or retry_count was updated
        if tasks_updated:
            if not self.status_updater.update_task_status(task_id, TaskStatus.DISPATCHED):
                 logger.error("Failed to save updated task list!")

        logger.debug(f"{self.agent_name} run cycle finished.")

    def _run_loop(self):
        """The main loop for the agent thread."""
        logger.info(f"{self.agent_name} background thread started.")
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                 logger.error(f"Critical error in {self.agent_name} run loop: {e}", exc_info=True)
            # Wait before the next cycle
            time.sleep(5) # Check for new tasks every 5 seconds (adjust as needed)
        logger.info(f"{self.agent_name} background thread stopped.")

    def start(self):
        """Starts the agent's task processing loop in a separate thread."""
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
        self._thread.join(timeout=10) # Wait for thread to finish
        if self._thread.is_alive():
             logger.warning(f"{self.agent_name} background thread did not stop gracefully after 10s.")
        else:
             logger.info(f"{self.agent_name} background thread stopped successfully.")
        self._thread = None

# ========= USAGE BLOCK START ==========
# Minimal block, full testing requires AgentBus and other agents running.
if __name__ == "__main__":
    print(f">>> Running module: {__file__} (Basic Checks)")
    # Create a dummy task list for basic check
    dummy_task_file = "./temp_executor_tasks.json"
    dummy_tasks = [
        {"task_id": "task1", "status": "PENDING", "action": "GET_EDITOR_CONTENT"},
        {"task_id": "task2", "status": "PENDING", "action": "RUN_TERMINAL_COMMAND", "params": {"command": "ls -l"}, "target_agent": "CursorControlAgent"},
        {"task_id": "task3", "status": "DISPATCHED", "action": "OTHER"}
    ]
    try:
        with open(dummy_task_file, 'w') as f:
            json.dump(dummy_tasks, f, indent=2)
        print(f"Created dummy task file: {dummy_task_file}")

        # Basic instantiation check (requires a dummy AgentBus)
        class DummyBus:
            def register_agent(self, *args, **kwargs): print(f"DummyBus: Registering {args[0]}")
            def send_message(self, *args, **kwargs): print(f"DummyBus: Sending message {kwargs.get('payload')} to {kwargs.get('recipient')}"); return f"msg_{time.time()}"

        print("\n>>> Instantiating TaskExecutorAgent with DummyBus...")
        bus = DummyBus()
        executor = TaskExecutorAgent(agent_bus=bus, task_list_path=dummy_task_file)
        print(">>> Executor instantiated.")

        print("\n>>> Running one cycle...")
        executor.run_cycle()
        print(">>> Cycle finished.")

        print("\n>>> Checking updated task file...")
        with open(dummy_task_file, 'r') as f:
             updated_tasks = json.load(f)
        print(json.dumps(updated_tasks, indent=2))
        # Check if task1 and task2 status changed to DISPATCHED
        assert updated_tasks[0].get("status") == "DISPATCHED"
        assert updated_tasks[1].get("status") == "DISPATCHED"
        assert updated_tasks[2].get("status") == "DISPATCHED" # Status should remain unchanged
        print(">>> Task statuses updated as expected in file.")

    except Exception as e:
        print(f"ERROR in usage block: {e}", file=sys.stderr)
    finally:
        if os.path.exists(dummy_task_file):
             os.remove(dummy_task_file)
             print(f"Removed dummy task file: {dummy_task_file}")

    print(f">>> Module {filename} basic checks complete.")
    sys.exit(0)
# ========= USAGE BLOCK END ========== 