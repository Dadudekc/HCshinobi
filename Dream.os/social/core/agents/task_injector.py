"""
Agent responsible for watching an input file and injecting new tasks into the task list.
"""
import logging
import os
import sys
import json
import time
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    # Need TaskStatus for setting default
    from agents.task_executor_agent import TaskStatus 
except ImportError:
     logger.warning("Could not import TaskStatus relatively.")
     class TaskStatus: PENDING = "PENDING"

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = "TaskInjectorAgent"
DEFAULT_INPUT_FILE = "run/input_tasks.jsonl"

class TaskInjector:
    """Watches an input file and injects tasks into the shared task list."""

    def __init__(self,
                 task_list_path: str,
                 input_task_file_path: str = DEFAULT_INPUT_FILE,
                 task_list_lock: Optional[threading.Lock] = None):
        """
        Initializes the task injector.

        Args:
            task_list_path: Path to the main task list JSON file.
            input_task_file_path: Path to the JSON Lines file to watch for new tasks.
            task_list_lock: The shared lock for accessing task_list.json.
        """
        self.agent_name = AGENT_NAME # For logging purposes
        self.task_list_path = os.path.abspath(task_list_path)
        self.input_task_file_path = os.path.abspath(input_task_file_path)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Require the shared lock
        if task_list_lock is None:
             raise ValueError("TaskInjector requires a shared task_list_lock.")
        self._lock = task_list_lock

        # Ensure input file directory exists
        try:
            os.makedirs(os.path.dirname(self.input_task_file_path), exist_ok=True)
        except IOError as e:
            logger.error(f"Failed to create directory for input task file {self.input_task_file_path}: {e}")
            # Continue initialization, but run_cycle will likely fail

        logger.info(f"{self.agent_name} initialized. Watching input file: {self.input_task_file_path}")

    # --- Use Task List Load/Save Logic (Copied/Adapted - Needs Refactor) ---
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Loads tasks from the JSON file using the shared lock."""
        # Duplicated - Needs refactor
        with self._lock:
            # Check if task list exists *inside* the lock
            if not os.path.exists(self.task_list_path):
                 logger.warning(f"Task list file not found at {self.task_list_path} during load by {self.agent_name}.")
                 return [] # Return empty list if file doesn't exist
            try:
                with open(self.task_list_path, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                if not isinstance(tasks, list):
                    logger.error(f"Invalid format in task list file {self.task_list_path}. Expected list.")
                    return []
                return tasks
            except FileNotFoundError:
                 # Should be caught by exists check, but handle anyway
                 logger.warning(f"Task list file vanished between check and open: {self.task_list_path}")
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
        """Saves the task list back to the JSON file using the shared lock."""
        # Duplicated - Needs refactor
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

    def _validate_and_prepare_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validates basic structure and sets defaults for an incoming task."""
        if not isinstance(task_data, dict):
             logger.warning("Invalid task format received (not a dict): skipping.")
             return None
        
        if "action" not in task_data:
             logger.warning(f"Invalid task format received (missing 'action'): {task_data}. Skipping.")
             return None
        
        # Assign defaults
        if "task_id" not in task_data:
             task_data["task_id"] = f"injected_{uuid.uuid4().hex[:8]}"
             logger.debug(f"Assigned new task_id: {task_data['task_id']}")
             
        if "status" not in task_data:
             task_data["status"] = TaskStatus.PENDING
             
        if "priority" not in task_data:
             task_data["priority"] = 50 # Default priority for injected tasks
             
        task_data.setdefault("params", {})
        task_data.setdefault("depends_on", [])
        task_data.setdefault("retry_count", 0)
        task_data.setdefault("repair_attempts", 0)
        task_data["injected_at"] = datetime.now().isoformat()

        return task_data

    def run_cycle(self):
        """Checks the input file, processes valid tasks, and clears the file."""
        if not os.path.exists(self.input_task_file_path):
            # logger.debug(f"Input file not found: {self.input_task_file_path}")
            return # Nothing to do

        logger.info(f"Detected input task file: {self.input_task_file_path}. Processing...")
        newly_injected_tasks = []
        processed_lines = 0
        invalid_lines = 0
        
        try:
            # Read all lines first
            with open(self.input_task_file_path, 'r', encoding='utf-8') as infile:
                lines_to_process = infile.readlines()
            
            if not lines_to_process:
                 logger.warning(f"Input task file {self.input_task_file_path} was empty.")
            else:
                for line in lines_to_process:
                    processed_lines += 1
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue # Skip empty lines and comments
                    try:
                        task_data = json.loads(line)
                        prepared_task = self._validate_and_prepare_task(task_data)
                        if prepared_task:
                            newly_injected_tasks.append(prepared_task)
                        else:
                             invalid_lines += 1
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in input file line: {line}")
                        invalid_lines += 1
                    except Exception as e:
                         logger.error(f"Error processing line from input file: {line} - {e}")
                         invalid_lines += 1
            
            # Inject valid tasks into the main list
            if newly_injected_tasks:
                logger.info(f"Attempting to inject {len(newly_injected_tasks)} new tasks...")
                current_tasks = self._load_tasks()
                current_tasks.extend(newly_injected_tasks)
                if self._save_tasks(current_tasks):
                     logger.info(f"Successfully injected {len(newly_injected_tasks)} tasks into {self.task_list_path}.")
                else:
                     logger.error("Failed to save task list after injection!")
            else:
                 logger.info("No valid tasks found to inject from input file.")

            # Clear the input file by deleting it (safest way to avoid reprocessing)
            try:
                os.remove(self.input_task_file_path)
                logger.info(f"Processed and removed input file: {self.input_task_file_path}")
            except OSError as e:
                logger.error(f"Failed to remove processed input file {self.input_task_file_path}: {e}. Manual removal needed.")
        
        except IOError as e:
            logger.error(f"Error reading input task file {self.input_task_file_path}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error during task injection cycle: {e}", exc_info=True)

    # --- Background Thread Methods --- 
    def _run_loop(self):
        """The main loop for the injector thread."""
        logger.info(f"{self.agent_name} background thread started.")
        while not self._stop_event.is_set():
            try:
                self.run_cycle()
            except Exception as e:
                 logger.error(f"Critical error in {self.agent_name} run loop: {e}", exc_info=True)
            # Check relatively frequently
            time.sleep(3)
        logger.info(f"{self.agent_name} background thread stopped.")

    def start(self):
        """Starts the file watching loop in a separate thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"{self.agent_name} is already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"{self.agent_name}Loop", daemon=True)
        self._thread.start()
        logger.info(f"{self.agent_name} started background thread.")

    def stop(self):
        """Signals the background thread to stop and waits for it."""
        if self._thread is None or not self._thread.is_alive():
            logger.info(f"{self.agent_name} is not running.")
            return

        logger.info(f"Stopping {self.agent_name} background thread...")
        self._stop_event.set()
        self._thread.join(timeout=5) # Shorter timeout for injector
        if self._thread.is_alive():
             logger.warning(f"{self.agent_name} background thread did not stop gracefully.")
        else:
             logger.info(f"{self.agent_name} background thread stopped successfully.")
        self._thread = None

# ========= USAGE BLOCK START ==========
# Minimal block for structure check
if __name__ == "__main__":
    print(f">>> Running module: {__file__} (Basic Checks)")
    dummy_task_file = "./temp_injector_main_tasks.json"
    dummy_input_file = "./temp_injector_input.jsonl"

    # Initial task list
    initial_tasks = [
        {"task_id": "existing1", "status": "COMPLETED", "action": "A"}
    ]
    # Tasks to inject
    tasks_to_inject = [
        {"action": "INJECTED_ACTION_1", "params": {"x": 1}}, # Missing ID, status, etc.
        {"task_id": "injected2", "action": "INJECTED_ACTION_2", "priority": 5}
    ]

    test_lock = threading.Lock()

    try:
        # Setup initial files
        with open(dummy_task_file, 'w') as f: json.dump(initial_tasks, f)
        with open(dummy_input_file, 'w') as f:
            for task in tasks_to_inject: f.write(json.dumps(task) + '\n')
            f.write("  \n") # Empty line
            f.write("# This is a comment\n")
            f.write("{"invalid json"\n") # Invalid line
        print(f"Created dummy task file: {dummy_task_file}")
        print(f"Created dummy input file: {dummy_input_file}")

        print("\n>>> Instantiating TaskInjector...")
        injector = TaskInjector(task_list_path=dummy_task_file,
                                input_task_file_path=dummy_input_file,
                                task_list_lock=test_lock)
        print(">>> Injector instantiated.")

        print("\n>>> Running one cycle...")
        injector.run_cycle()
        print(">>> Cycle finished.")

        print("\n>>> Checking updated task file...")
        with open(dummy_task_file, 'r') as f: updated_tasks = json.load(f)
        print(json.dumps(updated_tasks, indent=2))
        assert len(updated_tasks) == 3 # existing1 + injected1 + injected2
        injected_task1 = next(t for t in updated_tasks if t["action"] == "INJECTED_ACTION_1")
        assert injected_task1["status"] == "PENDING"
        assert injected_task1["priority"] == 50
        assert "task_id" in injected_task1
        injected_task2 = next(t for t in updated_tasks if t["task_id"] == "injected2")
        assert injected_task2["status"] == "PENDING"
        assert injected_task2["priority"] == 5
        print(">>> Main task list updated correctly.")

        print("\n>>> Checking if input file was removed...")
        assert not os.path.exists(dummy_input_file)
        print(">>> Input file removed as expected.")

    except Exception as e:
        print(f"ERROR in usage block: {e}", file=sys.stderr)
        raise
    finally:
        # Cleanup
        if os.path.exists(dummy_task_file): os.remove(dummy_task_file)
        if os.path.exists(dummy_input_file): os.remove(dummy_input_file)
        print("Cleaned up dummy files.")

    print(f">>> Module {__file__} basic checks complete.")
    sys.exit(0)

# ========= USAGE BLOCK END ==========