import json
import time
import os
import uuid
from pathlib import Path
import logging

# Configure logging
# Check if handlers are already configured to avoid duplicates if reloaded
if not logging.getLogger("TaskDispatcher").hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskDispatcher")

class TaskDispatcher:
    def __init__(self, task_list_path="task_list.json", check_interval=10, mailbox_root_dir="mailboxes"):
        """Initializes the TaskDispatcher."""
        self.task_list_path = Path(task_list_path).resolve()
        self.check_interval = check_interval
        # Define and ensure the root mailbox directory exists relative to task list
        self.mailbox_root = self.task_list_path.parent / mailbox_root_dir
        self.mailbox_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"TaskDispatcher initialized. Monitoring: {self.task_list_path}. Mailbox Root: {self.mailbox_root}")

    def _read_tasks(self):
        """Reads the task list from the JSON file."""
        try:
            if not self.task_list_path.exists():
                logger.warning(f"Task list not found at {self.task_list_path}, creating empty list.")
                self.task_list_path.write_text("[]", encoding="utf-8")
                return []
            
            with self.task_list_path.open("r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    # logger.debug(f"Task list file is empty: {self.task_list_path}")
                    return []
                tasks = json.loads(content)
                return tasks
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.task_list_path}: {e}. File content: '{content[:100]}...'")
            # Optional: Move corrupted file
            # corrupted_path = self.task_list_path.with_suffix(f".corrupted_{int(time.time())}.json")
            # try: 
            #     self.task_list_path.rename(corrupted_path)
            #     logger.info(f"Moved corrupted task list to {corrupted_path}")
            #     self.task_list_path.write_text("[]", encoding="utf-8") # Start fresh
            # except Exception as move_e:
            #     logger.error(f"Failed to move corrupted task list: {move_e}")
            return [] 
        except Exception as e:
            logger.error(f"Error reading task list {self.task_list_path}: {e}", exc_info=True)
            return []

    def _write_tasks(self, tasks):
        """Writes the updated task list back to the JSON file."""
        try:
            with self.task_list_path.open("w", encoding="utf-8") as f:
                json.dump(tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing task list {self.task_list_path}: {e}", exc_info=True)

    def _update_task_status(self, task_id, new_status, tasks=None, error_message=None):
        """Updates the status of a specific task in the list and writes back.
           Optionally takes the current task list to avoid re-reading.
        """
        updated = False
        save_needed = False
        if tasks is None:
             tasks = self._read_tasks()
             
        for task in tasks:
            if task.get("task_id") == task_id:
                if task.get("status") != new_status:
                    task["status"] = new_status
                    task["timestamp_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    if error_message:
                        task["error_message"] = error_message
                    elif "error_message" in task: # Clear previous error if status changes
                        del task["error_message"] 
                    updated = True
                    save_needed = True
                else:
                    updated = True # Task found, but status already correct
                break
                
        if save_needed:
            self._write_tasks(tasks)
        elif not updated:
             logger.warning(f"Could not find task {task_id} to update status to {new_status}")

        return updated # Return True if task was found, regardless of whether status changed

    def _dispatch_message_to_agent(self, target_agent: str, message_payload: dict):
        """Writes a message file to the target agent's inbox."""
        try:
            agent_inbox = self.mailbox_root / target_agent / "inbox"
            agent_inbox.mkdir(parents=True, exist_ok=True)
            
            message_id = str(uuid.uuid4())
            message_filename = f"msg_{message_id}.json"
            message_path = agent_inbox / message_filename

            # Add standard message envelope fields
            message_payload["message_id"] = message_id
            message_payload["sender_agent"] = "TaskDispatcher"
            message_payload["timestamp_dispatched"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            with message_path.open("w", encoding="utf-8") as f:
                json.dump(message_payload, f, indent=2)
            
            logger.info(f"Dispatched message {message_id} to agent '{target_agent}' inbox: {message_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to dispatch message to agent '{target_agent}': {e}", exc_info=True)
            return False

    def handle_task(self, task):
        """Handles a single task by dispatching a message to the target agent's mailbox."""
        task_id = task.get("task_id", "unknown_task")
        task_type = task.get("task_type", "unknown_type")
        params = task.get("params", {})
        target_agent = task.get("target_agent") # Expecting this to be set
        action_keyword = task.get("action") # The original suggested action keyword

        if not target_agent:
            logger.error(f"Task {task_id} missing 'target_agent'. Cannot dispatch. Marking as FAILED.")
            return False, "Missing target_agent"

        logger.info(f"Handling task {task_id} (Type: {task_type}, Target: {target_agent}) Params: {params}")

        # Construct the message payload for the target agent
        # This becomes the body of the message placed in the agent's mailbox
        message_payload = {
            "command": task_type, # Use task_type as the command for the target agent
            "original_task_id": task_id,
            "params": params,
            "action_keyword": action_keyword 
        }

        # --- Dispatch based on Task Type (using file-based mailbox) ---
        dispatch_successful = False
        # Define known task types that require dispatching
        dispatchable_task_types = [
            "resume_operation", 
            "generate_task", 
            "diagnose_loop", 
            "confirmation_check", 
            "context_reload", 
            "clarify_objective",
            "generic_recovery",
            # Add other known, non-recovery task types here
            # e.g., "run_script", "send_prompt_to_cursor"
        ]

        if task_type in dispatchable_task_types:
            logger.info(f"Dispatching task '{task_type}' message to agent '{target_agent}'")
            dispatch_successful = self._dispatch_message_to_agent(target_agent, message_payload)
        else:
            logger.warning(f"Unknown or non-dispatchable task type '{task_type}' for task {task_id}. Marking as FAILED.")
            return False, f"Unknown/Non-dispatchable task_type: {task_type}"
            
        # Return success based on dispatch attempt
        if dispatch_successful:
            logger.info(f"Successfully dispatched task {task_id} message to {target_agent}.")
            # Mark the task as COMPLETED in the task_list once dispatched.
            # The target agent is responsible for its own execution status/logging.
            return True, None 
        else:
            logger.error(f"Failed to dispatch task {task_id} message to {target_agent}. Marking as FAILED.")
            return False, f"Failed to dispatch message to agent {target_agent}"

    def process_pending_tasks(self):
        """Reads the task list, processes pending tasks, and updates statuses."""
        logger.debug("Checking for pending tasks...")
        tasks = self._read_tasks()
        if not tasks:
            # logger.debug("Task list is empty or unreadable.")
            return

        processed_ids = set()
        tasks_to_process = [task for task in tasks if task.get("status") == "PENDING"]

        if not tasks_to_process:
            # logger.debug("No pending tasks found.")
            return
            
        logger.info(f"Found {len(tasks_to_process)} pending task(s).")

        # We re-read the tasks inside the loop in case multiple dispatchers run
        # or to get the most recent status before processing. 
        # Alternatively, lock the file during processing.

        for task in tasks_to_process:
            task_id = task.get("task_id")
            if not task_id:
                 logger.warning(f"Skipping task with no ID: {task}")
                 continue
            if task_id in processed_ids: # Avoid potential duplicate processing within the same batch
                 continue

            logger.info(f"Attempting to process task: {task_id}")
            
            # --- Read tasks again and check status just before processing --- 
            current_tasks = self._read_tasks()
            current_task_state = next((t for t in current_tasks if t.get("task_id") == task_id), None)

            if not current_task_state:
                logger.warning(f"Task {task_id} disappeared before processing could start. Skipping.")
                continue
            if current_task_state.get("status") != "PENDING":
                logger.info(f"Task {task_id} status changed to {current_task_state.get('status')} before processing could start. Skipping.")
                continue
            # --- End Pre-check ---

            # Update status to PROCESSING immediately
            if not self._update_task_status(task_id, "PROCESSING", tasks=current_tasks):
                 logger.warning(f"Failed to update task {task_id} status to PROCESSING. Skipping. Another process might have grabbed it.")
                 continue # Skip if we couldn't update status

            try:
                success, error_msg = self.handle_task(current_task_state) # Pass the confirmed current state
                new_status = "COMPLETED" if success else "FAILED"
                # Update status based on handle_task outcome
                self._update_task_status(task_id, new_status, error_message=error_msg)
                logger.info(f"Task {task_id} finished dispatch with status: {new_status}")
                processed_ids.add(task_id)
            except Exception as e:
                logger.error(f"Critical error handling task {task_id}: {e}", exc_info=True)
                # Attempt to mark as FAILED
                self._update_task_status(task_id, "FAILED", error_message=str(e))
                processed_ids.add(task_id) 

        if processed_ids:
             logger.info(f"Finished processing batch. {len(processed_ids)} task(s) attempted.")
        
    def run(self):
        """Main loop to periodically check and process tasks."""
        logger.info("TaskDispatcher starting run loop.")
        try:
            while True:
                self.process_pending_tasks()
                # logger.debug(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("TaskDispatcher stopped by user.")
        except Exception as e:
            logger.error(f"TaskDispatcher encountered critical error in run loop: {e}", exc_info=True)

# Example instantiation (if run directly)
if __name__ == "__main__":
    # Determine project root relative to this script's location
    # Assumes script is in _agent_coordination/dispatchers/
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent # Go up two levels
    
    task_list_file = project_root / "task_list.json"
    mailbox_dir = project_root / "mailboxes"
    
    print(f"Project Root detected as: {project_root}")
    print(f"Task List Path: {task_list_file}")
    print(f"Mailbox Root Dir: {mailbox_dir}")

    # Ensure task list exists before starting
    if not task_list_file.is_file():
        print(f"WARNING: Task list {task_list_file} not found. Creating empty file.")
        task_list_file.parent.mkdir(parents=True, exist_ok=True) # Ensure parent dir exists
        task_list_file.write_text("[]", encoding="utf-8")
        
    dispatcher = TaskDispatcher(task_list_path=str(task_list_file), mailbox_root_dir=str(mailbox_dir))
    dispatcher.run() 