import json
import time
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskDispatcher")

class TaskDispatcher:
    def __init__(self, task_list_path="task_list.json", check_interval=10):
        """Initializes the TaskDispatcher."""
        self.task_list_path = Path(task_list_path).resolve()
        self.check_interval = check_interval
        logger.info(f"TaskDispatcher initialized. Monitoring: {self.task_list_path}")

    def _read_tasks(self):
        """Reads the task list from the JSON file."""
        try:
            if not self.task_list_path.exists():
                logger.warning(f"Task list not found at {self.task_list_path}, creating empty list.")
                self.task_list_path.write_text("[]", encoding="utf-8")
                return []
            
            with self.task_list_path.open("r", encoding="utf-8") as f:
                # Handle empty file case
                content = f.read()
                if not content:
                    logger.warning(f"Task list file is empty: {self.task_list_path}")
                    return []
                tasks = json.loads(content)
                return tasks
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.task_list_path}: {e}")
            # Consider moving the corrupted file and starting fresh?
            return [] 
        except Exception as e:
            logger.error(f"Error reading task list {self.task_list_path}: {e}")
            return []

    def _write_tasks(self, tasks):
        """Writes the updated task list back to the JSON file."""
        try:
            with self.task_list_path.open("w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing task list {self.task_list_path}: {e}")

    def _update_task_status(self, task_id, new_status, tasks=None, error_message=None):
        """Updates the status of a specific task in the list and writes back.
           Optionally takes the current task list to avoid re-reading.
        """
        updated = False
        if tasks is None:
             tasks = self._read_tasks()
             
        for task in tasks:
            if task.get("task_id") == task_id:
                task["status"] = new_status
                task["timestamp_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                if error_message:
                    task["error_message"] = error_message
                updated = True
                break
                
        if updated:
            self._write_tasks(tasks)
        else:
             logger.warning(f"Could not find task {task_id} to update status to {new_status}")
        return updated

    def handle_task(self, task):
        """Handles a single task based on its type and parameters."""
        task_id = task.get("task_id", "unknown_task")
        task_type = task.get("task_type", "unknown_type")
        params = task.get("params", {})
        target_agent = task.get("target_agent", "default") # e.g., 'CursorControlAgent'

        logger.info(f"Handling task {task_id} (Type: {task_type}, Target: {target_agent}) Params: {params}")

        # --- Recovery Task Handling (from StallRecoveryAgent) ---
        if task_type == "resume_operation":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Send command/prompt to CursorControlAgent (or target_agent)
            # Example: mailbox_utils.send_message(target_agent, {'command': 'GET_EDITOR_CONTENT', 'params': params})
            pass 
        elif task_type == "generate_task":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Trigger a planning agent or log the need for manual intervention
            pass
        elif task_type == "diagnose_loop":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Send analysis request to CursorControlAgent or a diagnostic agent
            pass
        elif task_type == "confirmation_check":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Send analysis/request to Supervisor or CursorControlAgent
            pass
        elif task_type == "context_reload":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Trigger context reload mechanism in target agent
            pass
        elif task_type == "clarify_objective":
            logger.info(f"Dispatching '{task_type}': {params.get('instruction_hint')}")
            # Placeholder: Generate prompt asking for clarification, potentially target Supervisor
            pass
        elif task_type == "generic_recovery":
             logger.warning(f"Handling generic recovery task {task_id}. Action: {task.get('action')}. Consider defining a specific task_type.")
             # Placeholder: Basic diagnostic action?
             pass
        # --- Add handlers for other task types here ---    
        else:
            logger.warning(f"Unknown task type '{task_type}' for task {task_id}. Skipping.")
            # Mark as failed or requires manual intervention?
            # For now, we'll just update status to completed to avoid re-processing unknown types
            pass 
            
        # Simulate task completion for now
        return True, None # success, error_message

    def process_pending_tasks(self):
        """Reads the task list, processes pending tasks, and updates statuses."""
        logger.debug("Checking for pending tasks...")
        tasks = self._read_tasks()
        if not tasks:
            logger.debug("Task list is empty or unreadable.")
            return

        processed_count = 0
        pending_tasks = [task for task in tasks if task.get("status") == "PENDING"]

        if not pending_tasks:
            logger.debug("No pending tasks found.")
            return
            
        logger.info(f"Found {len(pending_tasks)} pending task(s).")

        # Create a copy to iterate over while modifying the original list implicitly via _update_task_status
        tasks_to_process = list(pending_tasks) 

        for task in tasks_to_process:
            task_id = task.get("task_id")
            if not task_id:
                 logger.warning(f"Skipping task with no ID: {task}")
                 continue
            
            logger.info(f"Processing task: {task_id}")
            # Update status to PROCESSING immediately to prevent reprocessing by other dispatchers (if any)
            if not self._update_task_status(task_id, "PROCESSING", tasks=tasks):
                 logger.warning(f"Failed to update task {task_id} status to PROCESSING. Skipping.")
                 continue # Skip if we couldn't update status

            try:
                success, error_msg = self.handle_task(task)
                new_status = "COMPLETED" if success else "FAILED"
                self._update_task_status(task_id, new_status, tasks=tasks, error_message=error_msg)
                logger.info(f"Task {task_id} finished with status: {new_status}")
                processed_count += 1
            except Exception as e:
                logger.error(f"Critical error handling task {task_id}: {e}", exc_info=True)
                self._update_task_status(task_id, "FAILED", tasks=tasks, error_message=str(e))
                processed_count += 1 # Count as processed (failed)

        if processed_count > 0:
             logger.info(f"Finished processing batch of {processed_count} task(s).")
        
    def run(self):
        """Main loop to periodically check and process tasks."""
        logger.info("TaskDispatcher starting run loop.")
        try:
            while True:
                self.process_pending_tasks()
                logger.debug(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("TaskDispatcher stopped by user.")
        except Exception as e:
            logger.error(f"TaskDispatcher encountered critical error in run loop: {e}", exc_info=True)

# Example instantiation (if run directly)
if __name__ == "__main__":
    # Assumes task_list.json is in the current working directory or project root
    # You might need to adjust the path based on where this script is run from
    project_root = Path(__file__).parent.parent.parent # Adjust based on actual nesting
    task_list_file = project_root / "task_list.json"
    
    if not task_list_file.exists():
        print(f"WARNING: Task list {task_list_file} not found. Creating empty file.")
        task_list_file.parent.mkdir(parents=True, exist_ok=True)
        task_list_file.write_text("[]", encoding="utf-8")
        
    dispatcher = TaskDispatcher(task_list_path=str(task_list_file))
    dispatcher.run() 