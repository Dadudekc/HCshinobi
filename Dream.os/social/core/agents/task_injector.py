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
# Target agent for injected tasks (could be configurable)
DEFAULT_INJECTION_TARGET = "TaskExecutorAgent"

class TaskInjector:
    """Watches an input file and injects tasks via AgentBus messages."""

    def __init__(self,
                 agent_bus: AgentBus, # Requires AgentBus now
                 input_task_file_path: str = DEFAULT_INPUT_FILE):
        """
        Initializes the task injector.

        Args:
            agent_bus: The central AgentBus instance.
            input_task_file_path: Path to the JSON Lines file to watch for new tasks.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus # Store the bus instance
        self.input_task_file_path = os.path.abspath(input_task_file_path)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Lock is no longer needed as we don't write to task_list.json directly
        # self._lock = task_list_lock 

        # Ensure input file directory exists
        try:
            os.makedirs(os.path.dirname(self.input_task_file_path), exist_ok=True)
        except IOError as e:
            logger.error(f"Failed to create directory for input task file {self.input_task_file_path}: {e}")
            # Continue initialization, but run_cycle will likely fail

        # Register this agent (optional, but good practice)
        self.bus.register_agent(self.agent_name, capabilities=["task_injection"])

        logger.info(f"{self.agent_name} initialized. Watching input file: {self.input_task_file_path}")

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
        """Checks the input file, processes valid tasks, and sends INJECT_TASK messages."""
        if not os.path.exists(self.input_task_file_path):
            return # Nothing to do

        logger.info(f"Detected input task file: {self.input_task_file_path}. Processing...")
        injected_count = 0
        processed_lines = 0
        invalid_lines = 0
        lines_to_process = []
        
        try:
            # Read all lines first
            with open(self.input_task_file_path, 'r', encoding='utf-8') as infile:
                lines_to_process = infile.readlines()
        except Exception as e:
            logger.error(f"Error reading input file {self.input_task_file_path}: {e}")
            # Decide whether to delete the file if unreadable
            return
            
        if not lines_to_process:
                logger.warning(f"Input task file {self.input_task_file_path} was empty.")
        else:
            for line in lines_to_process:
                processed_lines += 1
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    task_data = json.loads(line)
                    # Validate and prepare (sets defaults like ID, status)
                    prepared_task = self._validate_and_prepare_task(task_data)
                    if prepared_task:
                        # Send message to inject the task
                        logger.debug(f"Sending INJECT_TASK message for task: {prepared_task.get('task_id')}")
                        self.bus.send_message(
                            sender=self.agent_name,
                            recipient=DEFAULT_INJECTION_TARGET, # Target the executor
                            message_type="INJECT_TASK",
                            payload=prepared_task # Send the whole task dict
                        )
                        injected_count += 1
                    else:
                            invalid_lines += 1
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in input file line: {line}")
                    invalid_lines += 1
                except Exception as e:
                        logger.error(f"Error processing line from input file: {line} - {e}")
                        invalid_lines += 1
        
        logger.info(f"Processed {processed_lines} lines from input file. Injected {injected_count} tasks. Invalid lines: {invalid_lines}.")

        # Clear the input file by deleting it
        try:
            os.remove(self.input_task_file_path)
            logger.info(f"Processed and removed input file: {self.input_task_file_path}")
        except OSError as e:
            logger.error(f"Failed to remove processed input file {self.input_task_file_path}: {e}")

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

    # Add shutdown method
    def shutdown(self):
        logger.info(f"Shutting down {self.agent_name}...")
        self.stop() # Stop the background thread if running
        # Unregister?
        # self.bus.deregister_agent(self.agent_name)
        logger.info(f"{self.agent_name} shutdown complete.")

# ========= USAGE BLOCK START ==========
# Minimal block for structure check
if __name__ == "__main__":
    print(f">>> Running module: {__file__} (Basic Checks)")
    # Note: This usage block doesn't fully demonstrate the AgentBus interaction
    dummy_task_file = "./temp_injector_task_list.json"
    dummy_input_file = "./temp_injector_input.jsonl"
    test_lock = threading.Lock()

    # Create dummy files for testing
    try:
        with open(dummy_task_file, 'w') as f: json.dump([], f)
        with open(dummy_input_file, 'w') as f:
            f.write('{"action": "TEST_ACTION_1"}\n')
            f.write('invalid json line\n')
            f.write('{"action": "TEST_ACTION_2", "params": {"x": 1}}\n')

        print("\n>>> Instantiating TaskInjector...")
        # Needs a dummy AgentBus for the refactored version
        class DummyBusForInjector:
            def register_agent(self, *args, **kwargs): print(f"[DummyBus] Registered: {args[0]}")
            def send_message(self, **kwargs):
                print(f"[DummyBus] Sending message: {kwargs.get('message_type')} to {kwargs.get('recipient')}")
                print(f"    Payload: {kwargs.get('payload')}")
        
        injector = TaskInjector(agent_bus=DummyBusForInjector(),
                                input_task_file_path=dummy_input_file)
        print(">>> Injector instantiated.")

        print("\n>>> Running injection cycle...")
        injector.run_cycle()
        print(">>> Injection cycle finished.")

        # Verify input file was removed
        if not os.path.exists(dummy_input_file):
            print(">>> Input file successfully removed after processing.")
        else:
            print("!!! Input file was NOT removed after processing.")

    except Exception as e:
        print(f"\n!!! Error during usage block execution: {e}")
    finally:
        # Clean up dummy files
        if os.path.exists(dummy_task_file): os.remove(dummy_task_file)
        if os.path.exists(dummy_input_file): os.remove(dummy_input_file)
        print("\n>>> Usage block cleanup complete.")

# ========= USAGE BLOCK END ==========