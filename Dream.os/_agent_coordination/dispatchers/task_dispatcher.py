import json
import time
import os
import uuid
from pathlib import Path
import logging

# Import shared task utilities
# Assuming task_utils.py is in the parent directory (_agent_coordination)
try:
    from ..task_utils import read_tasks, write_tasks, update_task_status
except ImportError:
    # Fallback for direct execution or different structure
    try:
        import sys
        # Add parent's parent to path (_agent_coordination)
        sys.path.append(str(Path(__file__).parent.parent))
        from task_utils import read_tasks, write_tasks, update_task_status
    except ImportError as e:
        print(f"FATAL: Could not import task utilities. TaskDispatcher cannot function. Error: {e}")
        # In a real scenario, might raise the error or exit
        # For this example, define dummies to allow structure check
        def read_tasks(*args, **kwargs): print("ERROR: read_tasks dummy"); return []
        def write_tasks(*args, **kwargs): print("ERROR: write_tasks dummy") 
        def update_task_status(*args, **kwargs): print("ERROR: update_task_status dummy"); return False

# Configure logging
if not logging.getLogger("TaskDispatcher").hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskDispatcher")

class TaskDispatcher:
    def __init__(self, task_list_path="task_list.json", check_interval=10, mailbox_root_dir="mailboxes"):
        """Initializes the TaskDispatcher."""
        # Ensure task_list_path is a Path object and resolved
        self.task_list_path = Path(task_list_path).resolve()
        self.check_interval = check_interval
        # Define and ensure the root mailbox directory exists relative to task list
        self.mailbox_root = self.task_list_path.parent / mailbox_root_dir
        self.mailbox_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"TaskDispatcher initialized. Monitoring: {self.task_list_path}. Mailbox Root: {self.mailbox_root}")

    # Removed local _read_tasks, _write_tasks, _update_task_status methods

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
        target_agent = task.get("target_agent") 
        action_keyword = task.get("action") 

        if not target_agent:
            logger.error(f"Task {task_id} missing 'target_agent'. Cannot dispatch. Marking as FAILED.")
            # Use imported utility to update status
            update_task_status(self.task_list_path, task_id, "FAILED", error_message="Missing target_agent")
            return False, "Missing target_agent"

        logger.info(f"Handling task {task_id} (Type: {task_type}, Target: {target_agent}) Params: {params}")

        message_payload = {
            "command": task_type, 
            "original_task_id": task_id,
            "params": params,
            "action_keyword": action_keyword 
        }

        dispatchable_task_types = [
            "resume_operation", "generate_task", "diagnose_loop", 
            "confirmation_check", "context_reload", "clarify_objective",
            "generic_recovery",
            # Add other known, non-recovery task types here
        ]

        dispatch_successful = False
        if task_type in dispatchable_task_types:
            logger.info(f"Dispatching task '{task_type}' message to agent '{target_agent}'")
            dispatch_successful = self._dispatch_message_to_agent(target_agent, message_payload)
        else:
            logger.warning(f"Unknown or non-dispatchable task type '{task_type}' for task {task_id}. Marking as FAILED.")
            # Use imported utility
            update_task_status(self.task_list_path, task_id, "FAILED", error_message=f"Unknown/Non-dispatchable task_type: {task_type}")
            return False, f"Unknown/Non-dispatchable task_type: {task_type}"
            
        if dispatch_successful:
            logger.info(f"Successfully dispatched task {task_id} message to {target_agent}.")
            # Mark as COMPLETED *after successful dispatch*
            # Use imported utility
            update_task_status(self.task_list_path, task_id, "COMPLETED", result_summary=f"Dispatched to {target_agent}")
            return True, None 
        else:
            logger.error(f"Failed to dispatch task {task_id} message to {target_agent}. Marking as FAILED.")
            # Use imported utility
            update_task_status(self.task_list_path, task_id, "FAILED", error_message=f"Failed to dispatch message to agent {target_agent}")
            return False, f"Failed to dispatch message to agent {target_agent}"

    def process_pending_tasks(self):
        """Reads the task list, processes pending tasks, and updates statuses."""
        logger.debug("Checking for pending tasks...")
        # Use imported utility
        tasks = read_tasks(self.task_list_path)
        if tasks is None or not tasks:
            return

        processed_ids = set()
        tasks_to_process = [task for task in tasks if task.get("status") == "PENDING"]

        if not tasks_to_process:
            return
            
        logger.info(f"Found {len(tasks_to_process)} pending task(s).")

        for task in tasks_to_process:
            task_id = task.get("task_id")
            if not task_id or task_id in processed_ids:
                 continue

            logger.info(f"Attempting to process task: {task_id}")
            
            # Re-read tasks and check status just before processing 
            # Use imported utility
            current_tasks_state = read_tasks(self.task_list_path)
            current_task = next((t for t in current_tasks_state if t.get("task_id") == task_id), None)

            if not current_task or current_task.get("status") != "PENDING":
                logger.info(f"Task {task_id} status changed or disappeared before processing. Skipping.")
                continue

            # Update status to PROCESSING immediately
            # Use imported utility
            if not update_task_status(self.task_list_path, task_id, "PROCESSING"):
                 logger.warning(f"Failed to update task {task_id} status to PROCESSING. Skipping.")
                 continue 

            try:
                # Call handle_task which now also updates to COMPLETED/FAILED on its own
                self.handle_task(current_task) 
                processed_ids.add(task_id)
            except Exception as e:
                logger.error(f"Critical error handling task {task_id}: {e}", exc_info=True)
                # Attempt to mark as FAILED using imported utility
                update_task_status(self.task_list_path, task_id, "FAILED", error_message=f"Critical error: {e}")
                processed_ids.add(task_id) 

        if processed_ids:
             logger.info(f"Finished processing batch. {len(processed_ids)} task(s) attempted.")
        
    def run(self):
        """Main loop to periodically check and process tasks."""
        logger.info("TaskDispatcher starting run loop.")
        try:
            while True:
                self.process_pending_tasks()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("TaskDispatcher stopped by user.")
        except Exception as e:
            logger.error(f"TaskDispatcher encountered critical error in run loop: {e}", exc_info=True)

# Example instantiation (if run directly)
if __name__ == "__main__":
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent 
    task_list_file = project_root / "task_list.json"
    mailbox_dir = project_root / "mailboxes"
    
    print(f"Project Root detected as: {project_root}")
    print(f"Task List Path: {task_list_file}")
    print(f"Mailbox Root Dir: {mailbox_dir}")

    if not task_list_file.is_file():
        print(f"WARNING: Task list {task_list_file} not found. Creating empty file.")
        task_list_file.parent.mkdir(parents=True, exist_ok=True)
        task_list_file.write_text("[]", encoding="utf-8")
        
    dispatcher = TaskDispatcher(task_list_path=str(task_list_file), mailbox_root_dir=str(mailbox_dir))
    dispatcher.run() 