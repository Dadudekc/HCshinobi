import json
import logging
import os
import portalocker
import time
from typing import Optional, Dict, Any, Literal
from ..agent_bus import AgentBus, Message  # Assuming AgentBus is in core

logger = logging.getLogger(__name__)

DEFAULT_UPDATE_TARGET = "TaskExecutorAgent" # Or AgentMonitorAgent? Needs decision.
MSG_TYPE_TASK_UPDATE = "TASK_STATUS_UPDATE"

class TaskStatusUpdater:
    """Handles updating task status, prioritizing AgentBus with file fallback."""

    def __init__(self, agent_bus: Optional[AgentBus], task_list_path: str, lock: portalocker.Lock):
        """
        Initializes the updater.

        Args:
            agent_bus: The AgentBus instance. Can be None if bus is unavailable.
            task_list_path: The absolute path to the master task list JSON file.
            lock: A shared portalocker.Lock instance for accessing the task list file.
        """
        self.agent_bus = agent_bus
        self.task_list_path = task_list_path
        self.lock = lock
        self.agent_name = "TaskStatusUpdaterUtil" # Name for sending bus messages

    def update_task_status(
        self,
        task_id: str,
        status: Literal["COMPLETED", "FAILED"],
        result_summary: Optional[str] = None,
        error_details: Optional[str] = None,
        originating_agent: Optional[str] = None # Agent reporting the status
    ) -> bool:
        """
        Updates the status of a task. Prioritizes sending an event via AgentBus,
        falls back to direct file modification if the bus is unavailable or fails.

        Args:
            task_id: The ID of the task to update.
            status: The new status ('COMPLETED' or 'FAILED').
            result_summary: A brief summary of the result (for COMPLETED).
            error_details: Details about the failure (for FAILED).
            originating_agent: The name of the agent reporting this status update.

        Returns:
            True if the update was successfully sent via bus or written to file, False otherwise.
        """
        logger.info(f"Attempting to update task {task_id} to status {status}")
        bus_success = False

        # 1. Attempt to send via AgentBus
        if self.agent_bus:
            payload = {
                "task_id": task_id,
                "status": status,
                "result_summary": result_summary,
                "error_details": error_details,
                "reporting_agent": originating_agent or self.agent_name
            }
            try:
                # Send to a central handler like TaskExecutorAgent or AgentMonitorAgent
                self.agent_bus.send_message(
                    sender=originating_agent or self.agent_name,
                    recipient=DEFAULT_UPDATE_TARGET,
                    message_type=MSG_TYPE_TASK_UPDATE,
                    payload=payload
                )
                logger.info(f"Sent task update event for {task_id} via AgentBus.")
                bus_success = True
                # If bus succeeds, we assume the recipient handles the file write.
                # If the requirement is for *this* utility to *ensure* the write,
                # we might need a response mechanism or always do the file write.
                # For now, assume bus dispatch is sufficient if successful.
                return True
            except Exception as e:
                logger.warning(f"Failed to send task update event for {task_id} via AgentBus: {e}. Falling back to file write.", exc_info=True)
                bus_success = False

        # 2. Fallback: Direct file modification (if bus failed or unavailable)
        if not bus_success:
            logger.info(f"Updating task {task_id} status directly in file: {self.task_list_path}")
            try:
                # Use retry logic for locking as file might be temporarily busy
                max_retries = 5
                retry_delay = 0.2 # seconds
                for attempt in range(max_retries):
                    try:
                        with self.lock: # Acquire exclusive lock
                            if not os.path.exists(self.task_list_path):
                                logger.error(f"Task list file not found at: {self.task_list_path}")
                                return False

                            with open(self.task_list_path, 'r+', encoding='utf-8') as f:
                                try:
                                    tasks = json.load(f)
                                except json.JSONDecodeError:
                                     logger.error(f"Failed to decode JSON from task list: {self.task_list_path}", exc_info=True)
                                     # Consider handling: overwrite with empty list? return False?
                                     # For now, return False to indicate failure.
                                     return False

                                task_found = False
                                for task in tasks:
                                    if task.get("task_id") == task_id:
                                        task["status"] = status
                                        if status == "COMPLETED" and result_summary:
                                            task["result_summary"] = result_summary
                                        elif status == "FAILED" and error_details:
                                            task["error_details"] = error_details
                                        # Optionally add timestamp_completed_utc?
                                        task_found = True
                                        logger.info(f"Updated task {task_id} status in list object.")
                                        break

                                if not task_found:
                                    logger.warning(f"Task ID {task_id} not found in {self.task_list_path} for status update.")
                                    # Still return True as the operation 'succeeded' in terms of file access?
                                    # Or False because the intended task wasn't updated? Let's return False.
                                    return False

                                # Write the changes back
                                f.seek(0) # Go to the beginning of the file
                                json.dump(tasks, f, indent=2)
                                f.truncate() # Remove any trailing old data
                                logger.info(f"Successfully wrote updated task list to {self.task_list_path}")
                                return True # File write successful

                    except portalocker.LockException:
                         logger.warning(f"Could not acquire lock on {self.task_list_path} (Attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                         time.sleep(retry_delay)
                    except FileNotFoundError:
                        logger.error(f"Task list file disappeared during operation: {self.task_list_path}")
                        return False
                    except Exception as e:
                        logger.error(f"Error during direct file update for task {task_id}: {e}", exc_info=True)
                        return False # Indicate failure

                logger.error(f"Failed to acquire lock on {self.task_list_path} after {max_retries} attempts.")
                return False # Failed to acquire lock

            except Exception as e:
                logger.error(f"Unexpected error setting up file update for task {task_id}: {e}", exc_info=True)
                return False # Indicate failure
        
        return False # Should not be reached if logic is correct

# Example Usage (for testing purposes, not intended for direct run)
if __name__ == "__main__":
    # This block requires setting up dummy bus, lock, and task file
    print("TaskStatusUpdater utility module. Not intended for direct execution.")

    # Dummy setup
    class DummyBus:
        def send_message(self, sender, recipient, message_type, payload):
            print(f"[DummyBus] Send: From={sender}, To={recipient}, Type={message_type}, Payload={payload}")
            # Simulate failure sometimes?
            # raise ConnectionError("Bus unavailable simulation")

    dummy_task_file = "dummy_task_list_updater.json"
    dummy_lock_file = dummy_task_file + ".lock"

    # Ensure clean start for dummy file
    if os.path.exists(dummy_task_file):
        os.remove(dummy_task_file)
    if os.path.exists(dummy_lock_file):
         os.remove(dummy_lock_file) # Remove stale lock file if present

    # Create dummy task list
    initial_tasks = [{"task_id": "task-123", "status": "IN_PROGRESS", "description": "Test task"}]
    with open(dummy_task_file, 'w') as f:
        json.dump(initial_tasks, f, indent=2)

    # Create lock object (using a separate lock file for portalocker)
    lock = portalocker.Lock(dummy_lock_file, fail_when_locked=True, flags=portalocker.LOCK_EX)
    
    print(f"\n--- Testing Updater (Bus Available) ---")
    updater_with_bus = TaskStatusUpdater(agent_bus=DummyBus(), task_list_path=dummy_task_file, lock=lock)
    updater_with_bus.update_task_status("task-123", "COMPLETED", result_summary="Finished successfully.", originating_agent="TestAgent1")

    print(f"\n--- Testing Updater (Bus Unavailable - Fallback) ---")
    updater_no_bus = TaskStatusUpdater(agent_bus=None, task_list_path=dummy_task_file, lock=lock)
    updater_no_bus.update_task_status("task-123", "FAILED", error_details="Something went wrong.", originating_agent="TestAgent2")

    print(f"\n--- Verifying File Content ({dummy_task_file}) ---")
    try:
         with open(dummy_task_file, 'r') as f:
              print(f.read())
    except Exception as e:
        print(f"Error reading dummy file: {e}")
        
    # Clean up dummy files
    # os.remove(dummy_task_file)
    # os.remove(dummy_lock_file) 