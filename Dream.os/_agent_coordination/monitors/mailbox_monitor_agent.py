# _agent_coordination/monitors/mailbox_monitor_agent.py

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os
import sys
# import fcntl # fcntl is Unix-specific
import portalocker # Use portalocker for cross-platform file locking
from typing import List, Dict, Optional # Add typing

# --- Path Setup ---
# Assumes this file is in _agent_coordination/monitors/
SCRIPT_DIR = Path(__file__).parent
AGENT_COORDINATION_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENT_COORDINATION_DIR.parent

# Add project root to sys.path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# ------------------

# Use the central logger setup from _agent_coordination
try:
    from _agent_coordination.core.utils.logging import get_logger
    logger = get_logger(__name__, component="MailboxMonitorAgent")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MailboxMonitorAgent [fallback]")
    logger.warning("Could not import central logger. Using basic config.")

# --- Configuration ---
AGENT_ID = "agent_mailbox_monitor"
MAILBOX_DIR = AGENT_COORDINATION_DIR / "mailboxes"
SUPERVISOR_MAILBOX_FILE = MAILBOX_DIR / "supervisor_mailbox.json"
TASK_LIST_FILE = PROJECT_ROOT / "runtime" / "task_list.json"
CHECK_INTERVAL_SECONDS = 5

# Ensure directories exist on import
MAILBOX_DIR.mkdir(parents=True, exist_ok=True)
TASK_LIST_FILE.parent.mkdir(parents=True, exist_ok=True)

# --- Cross-Platform File Locking Utilities (using portalocker) ---
def acquire_lock(file_path):
    """Acquires an exclusive lock on the file using portalocker."""
    try:
        # Open in append mode (doesn't truncate), create if not exists
        lock_file = open(file_path, 'a') 
        portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)
        logger.debug(f"Acquired lock for {file_path}")
        return lock_file # Return the file handle
    except portalocker.exceptions.LockException:
        logger.warning(f"Could not acquire lock for {file_path}, already locked.")
        if 'lock_file' in locals():
             lock_file.close() # Close if opened but lock failed
        return None
    except Exception as e:
        logger.error(f"Error acquiring lock for {file_path}: {e}", exc_info=True)
        if 'lock_file' in locals():
            lock_file.close()
        return None

def release_lock(lock_file):
    """Releases the lock and closes the file handle."""
    if lock_file:
        try:
            portalocker.unlock(lock_file)
            lock_file.close()
            logger.debug(f"Released lock for {lock_file.name}")
        except Exception as e:
            logger.error(f"Error releasing lock for {lock_file.name}: {e}", exc_info=True)
            # Ensure file is closed even if unlock fails
            if not lock_file.closed:
                lock_file.close()

# --- Mailbox Processing Logic ---
class MailboxMonitorAgent:

    def __init__(self):
        self.running = False
        logger.info(f"[{AGENT_ID}] Initialized.")

    def _read_mailbox(self) -> List[Dict]:
        """Safely reads the mailbox file using portalocker."""
        if not SUPERVISOR_MAILBOX_FILE.exists():
            return []
        
        lock_file = acquire_lock(SUPERVISOR_MAILBOX_FILE)
        if not lock_file:
             return [] # Could not get lock, try again later

        try:
            # Lock acquired, now read the actual content
            # Re-open in read mode (or seek to beginning if needed)
            with open(SUPERVISOR_MAILBOX_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return []
                mailbox = json.loads(content)
                return mailbox if isinstance(mailbox, list) else []
        except json.JSONDecodeError:
            logger.error(f"Mailbox file {SUPERVISOR_MAILBOX_FILE} contains invalid JSON.")
            return []
        except Exception as e:
            logger.error(f"Error reading mailbox file {SUPERVISOR_MAILBOX_FILE}: {e}", exc_info=True)
            return []
        finally:
            release_lock(lock_file)

    def _write_mailbox(self, mailbox_data: List[Dict]) -> bool:
        """Safely writes the updated mailbox data back to the file using portalocker."""
        lock_file = acquire_lock(SUPERVISOR_MAILBOX_FILE)
        if not lock_file:
            return False

        try:
            # Lock acquired, now write the content (this will overwrite)
            with open(SUPERVISOR_MAILBOX_FILE, 'w', encoding='utf-8') as f:
                # Need to seek to beginning if opened in append mode before locking
                # f.seek(0)
                # f.truncate() # Clear file before writing new content
                json.dump(mailbox_data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error writing mailbox file {SUPERVISOR_MAILBOX_FILE}: {e}", exc_info=True)
            return False
        finally:
            release_lock(lock_file)

    def _add_task_to_list(self, task_data: Dict) -> bool:
        """Safely adds a new task to the main task list file using portalocker."""
        lock_file = acquire_lock(TASK_LIST_FILE)
        if not lock_file:
            return False
        
        task_list = [] # Initialize task_list
        try:
            # Re-open in read mode to get current content
            if TASK_LIST_FILE.exists() and TASK_LIST_FILE.stat().st_size > 0:
                 with open(TASK_LIST_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    task_list = json.loads(content) if content.strip() else []
                    if not isinstance(task_list, list):
                        logger.error(f"Task list file {TASK_LIST_FILE} is not a valid JSON list. Overwriting.")
                        task_list = []
            else:
                task_list = [] # Ensure it's a list if file empty or doesn't exist

            # Add the new task
            task_list.append(task_data)

            # Re-open in write mode to save
            with open(TASK_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(task_list, f, indent=2)
                
            logger.info(f"Added task {task_data.get('task_id')} to {TASK_LIST_FILE}.")
            return True
        except json.JSONDecodeError:
            logger.error(f"Task list file {TASK_LIST_FILE} contains invalid JSON. Cannot add task.")
            return False
        except Exception as e:
            logger.error(f"Error updating task list file {TASK_LIST_FILE}: {e}", exc_info=True)
            return False
        finally:
            release_lock(lock_file)

    def _process_unread_messages(self):
        """Reads mailbox, processes unread messages, updates mailbox and task list."""
        mailbox = self._read_mailbox()
        if not mailbox:
            return # Nothing to process or error reading

        updated = False
        processed_indices = [] # Track indices to update
        mailbox_copy = mailbox[:] # Work on a copy to modify status

        for i, message in enumerate(mailbox_copy):
            if isinstance(message, dict) and message.get("status") == "unread":
                message_id = message.get("message_id", "unknown_msg")
                logger.info(f"Processing unread message: {message_id}")
                
                # 1. Validate and transform payload into task
                task_data = self._transform_message_to_task(message)
                
                if task_data:
                    # 2. Add task to task_list.json
                    if self._add_task_to_list(task_data):
                        # 3. Mark mailbox message as processed in the copy
                        message["status"] = "processed"
                        message.pop("error", None) # Remove previous error if reprocessing
                        logger.info(f"Successfully processed message {message_id} and added task {task_data['task_id']}.")
                        updated = True
                    else:
                        # Failed to add task, mark message as failed in the copy
                        message["status"] = "failed"
                        message["error"] = "Failed to add task to task_list.json"
                        logger.error(f"Failed to add task for message {message_id}. Marked message as failed.")
                        updated = True # Still updated the status
                else:
                    # Transformation failed, mark message as failed in the copy
                    message["status"] = "failed"
                    message["error"] = "Failed to transform message payload into valid task data."
                    logger.error(f"Failed to transform message {message_id}. Marked message as failed.")
                    updated = True # Still updated the status

        # Rewrite the mailbox file only if changes were made
        if updated:
            self._write_mailbox(mailbox_copy)

    def _transform_message_to_task(self, message: Dict) -> Optional[Dict]:
        """Transforms a mailbox message into a task list entry dictionary."""
        try:
            payload = message.get("payload", {})
            task_type = payload.get("task_type")
            params = payload.get("params", {})
            target_agent = message.get("target_agent")
            message_id = message.get("message_id", uuid.uuid4().hex[:8]) # Fallback ID

            if not task_type:
                logger.warning(f"Message {message_id} missing 'task_type' in payload.")
                return None

            # Generate task_id based on message
            # Ensure task_type part is safe for filename/id use
            safe_task_type = "".join(c if c.isalnum() else '_' for c in task_type)[:15]
            task_id = f"mailbox_{safe_task_type}_{message_id[:8]}"

            task_entry = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "PENDING",
                "params": params,
                "target_agent": target_agent, # Can be None/"broadcast" if dispatcher handles routing
                "source": "supervisor_mailbox",
                "source_message_id": message.get("message_id"),
                "timestamp_created": datetime.now(timezone.utc).isoformat() + "Z",
                "origin_sender": message.get("sender")
            }
            return task_entry
        except Exception as e:
            logger.error(f"Error transforming message {message.get('message_id')} to task: {e}", exc_info=True)
            return None

    async def run(self):
        """Main loop for the MailboxMonitorAgent."""
        self.running = True
        logger.info(f"[{AGENT_ID}] Starting run loop (checking every {CHECK_INTERVAL_SECONDS}s)...")
        while self.running:
            try:
                logger.debug(f"Checking {SUPERVISOR_MAILBOX_FILE}...")
                self._process_unread_messages()
            except Exception as e:
                logger.error(f"[{AGENT_ID}] Error in main loop: {e}", exc_info=True)
            
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
        logger.info(f"[{AGENT_ID}] Run loop stopped.")

    def stop(self):
        """Stops the agent's run loop."""
        logger.info(f"[{AGENT_ID}] Received stop signal.")
        self.running = False

# --- Example Usage --- 
async def main():
    # Example: Add a dummy message to the mailbox for testing
    MAILBOX_DIR.mkdir(exist_ok=True)
    test_message = {
        "message_id": f"test_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "sender": "test_script",
        "target_agent": "DummyAgent",
        "message_type": "directive",
        "payload": {
            "task_type": "test_task",
            "params": {"data": "example payload"}
        },
        "status": "unread"
    }
    # Write initial mailbox if it doesn't exist or is empty
    # Use locking here as well for safety in test setup
    lock = acquire_lock(SUPERVISOR_MAILBOX_FILE)
    mailbox_content = []
    try:
        if lock:
            if SUPERVISOR_MAILBOX_FILE.exists() and SUPERVISOR_MAILBOX_FILE.stat().st_size > 0:
                 try:
                      with open(SUPERVISOR_MAILBOX_FILE, 'r') as f:
                           mailbox_content = json.load(f)
                           if not isinstance(mailbox_content, list):
                                mailbox_content = []
                 except json.JSONDecodeError:
                      mailbox_content = [] # Start fresh if corrupted
            
            # Check if test message already exists (simple check)
            if not any(m.get("message_id") == test_message["message_id"] for m in mailbox_content):
                mailbox_content.append(test_message)
                with open(SUPERVISOR_MAILBOX_FILE, 'w') as f:
                    json.dump(mailbox_content, f, indent=2)
                logger.info(f"Added/updated test message in mailbox: {SUPERVISOR_MAILBOX_FILE}")
            else:
                logger.info("Test message already exists in mailbox.")
    finally:
         if lock:
              release_lock(lock)

    agent = MailboxMonitorAgent()
    try:
        await agent.run()
    except KeyboardInterrupt:
        agent.stop()
    finally:
        agent.stop() # Ensure stop is called

if __name__ == "__main__":
    print(f"Running Mailbox Monitor Agent directly (for testing). Press Ctrl+C to stop.")
    print(f"Monitoring mailbox: {SUPERVISOR_MAILBOX_FILE}")
    print(f"Adding tasks to: {TASK_LIST_FILE}")
    try:
        import portalocker # Check if installed
        asyncio.run(main())
    except ImportError:
        print("\nPlease install portalocker: pip install portalocker")
    except KeyboardInterrupt:
        print("\nMailbox Monitor Agent stopped by user.") 