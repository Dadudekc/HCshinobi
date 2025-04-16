#!/usr/bin/env python
import argparse
import json
import logging
import os
import sys
import time
import datetime

# --- Adjust Python path to find top-level modules ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..', '..')) # Go up two levels: D:\Dream.os
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT) # Add workspace root to the beginning of the path

# --- Basic Logging Setup ---
# Set level based on debug needs, format can be added
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') 
logger = logging.getLogger("AgentEntrypoint")

# --- Define Paths Robustly from Workspace Root ---
AGENT_COORD_DIR = os.path.join(WORKSPACE_ROOT, '_agent_coordination')
SHARED_MAILBOX_DIR = os.path.join(AGENT_COORD_DIR, 'shared_mailboxes')
MASTER_TASK_LIST_PATH = os.path.join(WORKSPACE_ROOT, 'master_task_list.json') 

# --- Constants ---
MAX_MAILBOXES = 8
POLL_INTERVAL = 5
MAX_IDLE_DURATION = 3600
# AGENT_HEARTBEAT_INTERVAL = 60 # Not currently used, can be removed or implemented later

# --- Module Imports ---
logging.debug(f"DEBUG_IMPORT: sys.path right before core import = {sys.path}") # Log path here
from agents.core.agent_command_handler import CommandHandler # Restore original import

# --- REMOVING Absolute Path Import Test Block --- 
# try:
#     ...
# except Exception as e:
#      ...
#      sys.exit(1)
# --- End REMOVED Absolute Path Import Test Block ---

# Ensure this import still works (it uses _agent_coordination which should be findable)
from _agent_coordination.utils.onboarding_message_injector import inject_initial_onboarding_message 

# --- Placeholder Implementations (if needed) ---
class PlaceholderFilesystem:
    def exists(self, path): return os.path.exists(path)
    def read_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}") 
    def list_dir(self, path): return os.listdir(path)
    def write_file(self, path, content):
        # Basic atomic write using temp file
        temp_path = path + ".tmpwrite"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f: f.write(content)
            os.replace(temp_path, path)
        except Exception as e:
             logger.error(f"Filesystem write error to {path}: {e}")
             if os.path.exists(temp_path):
                 try: os.remove(temp_path) # Cleanup temp file on error
                 except: pass 
             raise # Re-raise the original exception

class PlaceholderMemory:
    def __init__(self): self._data = {}
    def set(self, key, value): self._data[key] = value
    def get(self, key, default=None): return self._data.get(key, default)

# --- Function Definitions ---

def claim_shared_mailbox(agent_id: str) -> str | None:
    """ Placeholder function: Attempts to claim an available shared mailbox.
        In a real system, this needs file locking or a more robust atomic mechanism.
    """
    logger.info(f"[{agent_id}] Attempting to claim a shared mailbox...")
    logger.debug(f"DEBUG_PATH: Checking mailboxes in SHARED_MAILBOX_DIR = {SHARED_MAILBOX_DIR}") # Debug Log
    for i in range(1, MAX_MAILBOXES + 1):
        mailbox_path = os.path.join(SHARED_MAILBOX_DIR, f"mailbox_{i}.json")
        logger.debug(f"DEBUG_PATH: Checking mailbox path: {mailbox_path}") # Debug Log
        try:
            # Simplified check: Try to read status. Real check needs atomicity.
            mailbox_data = {}
            if os.path.exists(mailbox_path):
                 # Read content carefully
                 with open(mailbox_path, "r", encoding='utf-8') as f:
                    try: 
                        content = f.read()
                        if content.strip():
                             mailbox_data = json.loads(content) 
                        else: # File exists but is empty
                             mailbox_data = {} # Treat as available
                    except json.JSONDecodeError: 
                         logger.warning(f"[{agent_id}] Mailbox {mailbox_path} has invalid JSON. Treating as available.")
                         mailbox_data = {} # Treat as available
            
            # If file doesn't exist or is empty/invalid JSON, mailbox_data remains {}
            
            # Check status only if mailbox_data is a dictionary
            if isinstance(mailbox_data, dict) and mailbox_data.get("status") != "online":
                logger.info(f"[{agent_id}] Attempting claim on {mailbox_path}...")
                # Claim it - THIS IS NOT ATOMIC, FOR DEMO ONLY
                claim_data = {
                    "status": "online",
                    "assigned_agent_id": agent_id,
                    "last_seen_utc": datetime.datetime.utcnow().isoformat(),
                    "messages": mailbox_data.get("messages", []), # Preserve existing messages if they existed
                    "processed_message_ids": mailbox_data.get("processed_message_ids", [])
                }
                temp_path = mailbox_path + ".claim.tmp"
                with open(temp_path, "w", encoding='utf-8') as f:
                    json.dump(claim_data, f, indent=2)
                os.replace(temp_path, mailbox_path)
                logger.info(f"[{agent_id}] Successfully claimed mailbox: {mailbox_path}")
                return mailbox_path # Return the path of the claimed mailbox
            elif isinstance(mailbox_data, dict):
                logger.debug(f"[{agent_id}] Mailbox {mailbox_path} already claimed by {mailbox_data.get('assigned_agent_id')}.")
            else:
                # This should ideally not be reached if parsing treats invalid/empty as {}
                logger.error(f"[{agent_id}] Mailbox {mailbox_path} read resulted in non-dict data type: {type(mailbox_data)}. Skipping claim attempt.")

        except Exception as e:
            # Catch errors during file access or processing for a specific mailbox
            logger.error(f"[{agent_id}] Error checking/claiming mailbox {mailbox_path}: {e}", exc_info=True)
            continue # Try the next one
            
    logger.error(f"[{agent_id}] Failed to claim any available shared mailbox after checking all {MAX_MAILBOXES}.")
    return None

def release_shared_mailbox(mailbox_path: str, agent_id: str):
    """ Placeholder: Releases the mailbox by setting status to offline. Needs atomicity.
    """
    logger.info(f"[{agent_id}] Releasing mailbox: {mailbox_path}")
    try:
        mailbox_data = {}
        if os.path.exists(mailbox_path):
             with open(mailbox_path, "r", encoding='utf-8') as f:
                try: mailbox_data = json.load(f) 
                except json.JSONDecodeError: 
                     logger.warning(f"[{agent_id}] Could not parse JSON in {mailbox_path} during release. Proceeding cautiously.")
                     mailbox_data = {} # Assume we might still need to write offline status

        # Only release if currently assigned to this agent OR if structure is broken (assume intent to release)
        if not isinstance(mailbox_data, dict) or mailbox_data.get("assigned_agent_id") == agent_id:
            if not isinstance(mailbox_data, dict):
                 logger.warning(f"[{agent_id}] Overwriting potentially invalid structure in {mailbox_path} to release.")
                 
            release_data = {
                "status": "offline",
                "assigned_agent_id": None,
                "last_seen_utc": datetime.datetime.utcnow().isoformat(),
                "messages": mailbox_data.get("messages", []) if isinstance(mailbox_data, dict) else [], 
                "processed_message_ids": mailbox_data.get("processed_message_ids", []) if isinstance(mailbox_data, dict) else []
            }
            temp_path = mailbox_path + ".release.tmp"
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump(release_data, f, indent=2)
            os.replace(temp_path, mailbox_path)
            logger.info(f"[{agent_id}] Mailbox {mailbox_path} updated to offline status.")
        else:
             logger.warning(f"[{agent_id}] Attempted to release mailbox {mailbox_path} not assigned to this agent (Current: {mailbox_data.get('assigned_agent_id')}). No changes made.")
    except Exception as e:
        logger.error(f"[{agent_id}] Error releasing mailbox {mailbox_path}: {e}", exc_info=True)

def process_mailbox_messages(mailbox_path: str, agent_id: str, command_handler: CommandHandler) -> bool:
    """ Reads mailbox, processes new messages, updates processed list. Needs atomicity.
    Returns True if any new messages were processed, False otherwise.
    """
    logger.debug(f"[{agent_id}] Checking mailbox {mailbox_path} for messages...")
    processed_new_message = False # Flag to track if we actually processed something new
    try:
        # --- Read Phase (Needs Lock) ---
        mailbox_data = {}
        if os.path.exists(mailbox_path):
            with open(mailbox_path, "r", encoding='utf-8') as f:
                try: 
                    # --- Debug Log: Check structure after reading ---
                    raw_content = f.read()
                    logger.debug(f"[{agent_id}] DEBUG_PROCESS: Read raw content from {mailbox_path} (length: {len(raw_content)}). Sample: {raw_content[:100]}...")
                    if raw_content.strip():
                        mailbox_data = json.loads(raw_content) 
                        logger.debug(f"[{agent_id}] DEBUG_PROCESS: Loaded data type: {type(mailbox_data).__name__}")
                        if isinstance(mailbox_data, dict):
                             logger.debug(f"[{agent_id}] DEBUG_PROCESS: Loaded dict keys: {list(mailbox_data.keys())}")
                        else:
                             logger.debug(f"[{agent_id}] DEBUG_PROCESS: Loaded non-dict content sample: {str(mailbox_data)[:100]}...")
                    else:
                         mailbox_data = {} # Treat empty file as empty dict for processing consistency
                         logger.debug(f"[{agent_id}] DEBUG_PROCESS: Mailbox file was empty or whitespace only.")
                    # --- End Debug Log ---
                except json.JSONDecodeError: 
                    logger.error(f"[{agent_id}] Mailbox {mailbox_path} has invalid JSON. Skipping processing run.")
                    return False
        else:
             logger.warning(f"[{agent_id}] Mailbox file {mailbox_path} disappeared. Cannot process.")
             return False

        if not isinstance(mailbox_data, dict):
             logger.error(f"[{agent_id}] Mailbox {mailbox_path} structure invalid (not a dict). Skipping processing run.")
             return False
             
        # Check if still assigned
        if mailbox_data.get("assigned_agent_id") != agent_id:
            logger.warning(f"[{agent_id}] Lost claim on mailbox {mailbox_path}. Stopping processing for this cycle.")
            return False 
            
        messages = mailbox_data.get("messages", [])
        processed_ids = set(mailbox_data.get("processed_message_ids", []))
        newly_processed_ids = []

        if not isinstance(messages, list):
            logger.error(f"[{agent_id}] Mailbox {mailbox_path} 'messages' field is not a list. Resetting to empty list.")
            messages = [] # Attempt to recover by resetting messages
            # Force write back later even if no messages processed?
            
        # --- Process Phase ---
        # Iterate over a copy of messages in case handler modifies the list?
        for i, message in enumerate(list(messages)): # Iterate copy
            if not isinstance(message, dict):
                 logger.warning(f"[{agent_id}] Skipping invalid message item (not a dict) at index {i} in {mailbox_path}.")
                 continue
                 
            # Generate a fallback ID if missing, ensuring it's somewhat unique
            message_id = message.get("message_id", f"msg_{i}_{int(time.time()*1000)}") 
            
            if message_id not in processed_ids:
                logger.info(f"[{agent_id}] Processing message {message_id} from {mailbox_path}")
                command = message.get("command")
                params = message.get("params", {})
                sender = message.get("sender", "Unknown")
                
                if not command:
                     logger.error(f"[{agent_id}] Message {message_id} missing 'command'. Skipping.")
                     newly_processed_ids.append(message_id) # Mark as processed to avoid re-processing bad msg
                     continue
                     
                logger.info(f"[{agent_id}] Dispatching command: '{command}' from sender '{sender}'")
                
                # === Dispatch to CommandHandler ===
                result = command_handler.handle_command(command, params)
                logger.info(f"[{agent_id}] Command '{command}' (ID: {message_id}) result: {result}")
                
                # Simple success check - adjust based on handle_command's return structure
                if result and isinstance(result, dict) and result.get("status") == "success":
                    newly_processed_ids.append(message_id)
                    processed_new_message = True # Mark activity
                    logger.info(f"[{agent_id}] Marked message {message_id} as processed.")
                else:
                    logger.error(f"[{agent_id}] Command '{command}' (ID: {message_id}) failed processing or returned non-success status. Result: {result}. Message will be retried next cycle.")
                    # Consider adding failure count or moving to error queue here
            else:
                logger.debug(f"[{agent_id}] Skipping already processed message {message_id}.")

        # --- Write Phase (Needs Lock) ---
        if newly_processed_ids:
            logger.info(f"[{agent_id}] Updating processed message IDs in {mailbox_path}")
            # Create the final list ensuring uniqueness (though set union should handle it)
            final_processed_ids = list(processed_ids.union(newly_processed_ids))
            
            # Read current data again just before writing to minimize race conditions
            current_data = {} 
            try:
                with open(mailbox_path, "r", encoding='utf-8') as f: 
                    current_data = json.load(f)
                if not isinstance(current_data, dict):
                     logger.error(f"[{agent_id}] Mailbox {mailbox_path} structure became invalid before writing processed IDs. Attempting overwrite.")
                     current_data = {} # Fallback to overwrite
            except Exception as read_err:
                 logger.error(f"[{agent_id}] Failed to re-read mailbox before writing processed IDs: {read_err}. Attempting overwrite.")
                 current_data = {} # Fallback to overwrite
                
            # Update only processed IDs & heartbeat, keep other fields as they were (unless overwritten)
            current_data["processed_message_ids"] = final_processed_ids
            current_data["last_seen_utc"] = datetime.datetime.utcnow().isoformat()
            # Ensure other core fields exist if we fell back to overwrite
            current_data.setdefault("status", "online")
            current_data.setdefault("assigned_agent_id", agent_id)
            current_data.setdefault("messages", messages) # Use potentially modified messages list
            
            temp_path = mailbox_path + ".proc.tmp"
            with open(temp_path, "w", encoding='utf-8') as f:
                json.dump(current_data, f, indent=2)
            os.replace(temp_path, mailbox_path)
            logger.info(f"[{agent_id}] Mailbox {mailbox_path} updated with {len(newly_processed_ids)} newly processed IDs.")
        else:
             # Update heartbeat even if no messages processed
             current_data = {} 
             try:
                 with open(mailbox_path, "r", encoding='utf-8') as f: 
                    current_data = json.load(f)
                 # Check if still assigned and is a dict before heartbeat update
                 if isinstance(current_data, dict) and current_data.get("assigned_agent_id") == agent_id:
                     current_data["last_seen_utc"] = datetime.datetime.utcnow().isoformat()
                     temp_path = mailbox_path + ".heartbeat.tmp"
                     with open(temp_path, "w", encoding='utf-8') as f:
                         json.dump(current_data, f, indent=2)
                     os.replace(temp_path, mailbox_path)
                     logger.debug(f"[{agent_id}] Updated heartbeat in {mailbox_path}")
                 elif not isinstance(current_data, dict):
                     logger.warning(f"[{agent_id}] Cannot update heartbeat, mailbox structure invalid: {mailbox_path}")
                 # else: not assigned anymore, don't update heartbeat
             except Exception as hb_err:
                 logger.error(f"[{agent_id}] Failed to update heartbeat for {mailbox_path}: {hb_err}")
                 
    except Exception as e:
        logger.error(f"[{agent_id}] Unhandled error during mailbox processing loop for {mailbox_path}: {e}", exc_info=True)
        
    return processed_new_message # Return the activity flag

# --- Task List Functions ---

def _read_master_task_list(filesystem) -> list:
    """Safely reads and parses the master task list."""
    try:
        # Add debug log for path
        logger.debug(f"DEBUG_PATH: Reading task list from MASTER_TASK_LIST_PATH = {MASTER_TASK_LIST_PATH}")
        content = filesystem.read_file(MASTER_TASK_LIST_PATH)
        if content:
            task_list_data = json.loads(content)
            if isinstance(task_list_data, list):
                 return task_list_data
            else:
                 logger.error(f"Master task list file does not contain a JSON list: {MASTER_TASK_LIST_PATH}")
                 return []
        else:
            logger.warning(f"Master task list file is empty: {MASTER_TASK_LIST_PATH}")
            return []
    except FileNotFoundError:
        logger.error(f"Master task list file not found at: {MASTER_TASK_LIST_PATH}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding master task list JSON from {MASTER_TASK_LIST_PATH}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading master task list {MASTER_TASK_LIST_PATH}: {e}", exc_info=True)
        return []

def _write_master_task_list(task_list: list, filesystem) -> bool:
    """Safely writes the task list back to the file."""
    try:
        # Add debug log for path
        logger.debug(f"DEBUG_PATH: Writing task list to MASTER_TASK_LIST_PATH = {MASTER_TASK_LIST_PATH}")
        # Assume filesystem.write_file handles atomicity (e.g., write-to-temp, rename)
        filesystem.write_file(MASTER_TASK_LIST_PATH, json.dumps(task_list, indent=2))
        logger.debug(f"Successfully wrote updated task list to {MASTER_TASK_LIST_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to write master task list {MASTER_TASK_LIST_PATH}: {e}", exc_info=True)
        return False

def find_and_execute_task_from_list(agent_id: str, specialization: str, command_handler, memory, filesystem) -> bool:
    """Finds, claims, executes, and updates a task from the master list.
    Returns True if a task was found and attempted, False otherwise.
    """
    logger.debug(f"[{agent_id}] Scanning master task list...")
    task_list = _read_master_task_list(filesystem)
    if not task_list: # Handles empty list or read errors
        logger.info(f"[{agent_id}] No tasks found in master list or error reading list.")
        return False # No tasks to process
        
    claimable_task_index = -1
    claimed_task = None

    # --- Task Identification Logic (Priority Order) ---
    # 1. Directly assigned to this agent
    for i, task in enumerate(task_list):
        # Check if task is a dictionary before accessing keys
        if isinstance(task, dict) and task.get("status") == "PENDING" and \
           (task.get("target_agent") == agent_id or task.get("assigned_to") == agent_id):
            claimable_task_index = i
            logger.info(f"[{agent_id}] Found potential task (Directly Assigned): {task.get('id', '[no_id]')}")
            break
        elif not isinstance(task, dict):
             logger.warning(f"[{agent_id}] Skipping invalid item (not a dict) at index {i} in task list.")

    # 2. Unassigned and matches specialization (case-insensitive description check)
    if claimable_task_index == -1:
        for i, task in enumerate(task_list):
             if isinstance(task, dict) and task.get("status") == "PENDING" and \
               (not task.get("assigned_to") and not task.get("target_agent")) and \
               specialization.lower() in task.get("description", "").lower():
                 claimable_task_index = i
                 logger.info(f"[{agent_id}] Found potential task (Specialization Match): {task.get('id', '[no_id]')}")
                 break

    # 3. Unassigned general task (could refine this definition later)
    if claimable_task_index == -1:
         for i, task in enumerate(task_list):
            if isinstance(task, dict) and task.get("status") == "PENDING" and \
               (not task.get("assigned_to") and not task.get("target_agent")):
                 # Basic check - could add filtering for 'generic' tags etc.
                 claimable_task_index = i
                 logger.info(f"[{agent_id}] Found potential task (General Unassigned): {task.get('id', '[no_id]')}")
                 break

    if claimable_task_index == -1:
        logger.info(f"[{agent_id}] No suitable PENDING tasks found in master list.")
        return False # No actionable task found
        
    # --- Atomic Claim Attempt ---
    # Re-read the list immediately before modification for atomicity
    task_id_to_claim = task_list[claimable_task_index].get('id', '[no_id]') # Get ID before re-read
    logger.info(f"[{agent_id}] Attempting to claim task index {claimable_task_index} (ID: {task_id_to_claim})")
    current_task_list = _read_master_task_list(filesystem)
    # Check if list could be read and index is still valid
    if not current_task_list or claimable_task_index >= len(current_task_list):
        logger.warning(f"[{agent_id}] Task list changed or read error occurred before claim for task {task_id_to_claim}. Aborting claim.")
        return False # Indicate no task was processed this cycle
        
    task_to_claim = current_task_list[claimable_task_index]
    
    # Verify task is still a dictionary and PENDING (critical check for atomicity)
    if not isinstance(task_to_claim, dict) or task_to_claim.get("status") != "PENDING":
        logger.warning(f"[{agent_id}] Task {task_id_to_claim} is no longer claimable (Status: '{task_to_claim.get('status')}' or invalid structure). Aborting claim.")
        return False # Indicate no task was processed this cycle
        
    # Modify the task in memory
    task_to_claim["status"] = "IN_PROGRESS"
    task_to_claim["assigned_to"] = agent_id
    claimed_task = task_to_claim # Keep a copy for execution
    task_id = claimed_task.get('id', '[no_id]') # Use ID from claimed task dict
    
    # Write the entire list back
    if _write_master_task_list(current_task_list, filesystem):
        logger.info(f"[{agent_id}] Successfully claimed task {task_id}.")
        
        # --- Execute Task --- 
        execution_success = execute_task(claimed_task, command_handler, memory, filesystem)
        
        # --- Update Task Status --- 
        final_status = "COMPLETED" if execution_success else "FAILED"
        logger.info(f"[{agent_id}] Task {task_id} execution result: {'Success' if execution_success else 'Failure'}. Updating status to {final_status}.")
        update_task_status(task_id, final_status, agent_id, filesystem)
        
        return True # Task was found and processed
    else:
        logger.error(f"[{agent_id}] Failed to write updated task list during claim for task {task_id}. Task not executed.")
        # Should we try to revert the in-memory status if write fails?
        return False # Indicate task processing failed

def execute_task(task_data: dict, command_handler, memory, filesystem) -> bool:
    """ Placeholder function to simulate task execution.
        In a real system, this would dispatch to command-specific logic.
    """
    task_id = task_data.get('id', '[no_id]')
    command = task_data.get('command', '[no_command]')
    params = task_data.get('params', {})
    logger.info(f"[{command_handler.agent_id}] == EXECUTING TASK (Placeholder) ==")
    logger.info(f"[{command_handler.agent_id}] Task ID: {task_id}")
    logger.info(f"[{command_handler.agent_id}] Command: {command}")
    logger.info(f"[{command_handler.agent_id}] Params: {params}")
    
    # Simulate execution success/failure (e.g., based on command type or randomly)
    # For now, always simulate success
    simulated_success = True 
    
    logger.info(f"[{command_handler.agent_id}] == TASK EXECUTION SIMULATION COMPLETE (Result: {'Success' if simulated_success else 'Failure'}) ==")
    return simulated_success

def update_task_status(task_id: str, new_status: str, agent_id: str, filesystem):
    """ Atomically updates the status of a specific task in the master list. """
    logger.debug(f"[{agent_id}] Attempting to update status for task {task_id} to {new_status}.")
    current_task_list = _read_master_task_list(filesystem)
    if not current_task_list: # Checks for None or empty list
        logger.error(f"[{agent_id}] Cannot update task status for {task_id}: Failed to read task list or list is empty.")
        return False
        
    task_found = False
    for task in current_task_list:
        # Check if task is a dict and ID matches
        if isinstance(task, dict) and task.get("id") == task_id:
            # Sanity check - ensure agent updating is the one assigned
            current_assignee = task.get('assigned_to')
            if current_assignee != agent_id:
                 logger.warning(f"[{agent_id}] Attempting to update status of task {task_id} currently assigned to '{current_assignee}'. Allowing update.")
                 # Decide policy: allow update anyway, or reject?
                 
            logger.info(f"[{agent_id}] Updating task {task_id} status from '{task.get('status')}' to '{new_status}'.")
            task["status"] = new_status
            # Optional: Clear assignee if COMPLETED or FAILED?
            # if new_status in ["COMPLETED", "FAILED"]:
            #     task["assigned_to"] = None
            task_found = True
            break
            
    if not task_found:
        logger.error(f"[{agent_id}] Cannot update task status: Task ID {task_id} not found in list.")
        return False
        
    if _write_master_task_list(current_task_list, filesystem):
        logger.debug(f"[{agent_id}] Successfully updated status for task {task_id}.")
        return True
    else:
        logger.error(f"[{agent_id}] Failed to write task list after updating status for task {task_id}.")
        return False

def main_agent_loop(agent_id: str, specialization: str):
    """ Main operational loop for the agent. Prioritizes tasks from master list.
        Includes idle timeout mechanism.
    """
    logger.info(f"--- Starting Agent {agent_id} (Specialization: {specialization}) ---")
    
    # --- Claim Mailbox ---
    claimed_mailbox_path = claim_shared_mailbox(agent_id)
    if not claimed_mailbox_path:
        logger.critical(f"[{agent_id}] Agent startup failed: Could not claim a mailbox. Exiting.")
        return 1 # Exit with error code
        
    # --- Inject Onboarding Message --- 
    logger.info(f"[{agent_id}] Mailbox claimed. Injecting initial onboarding message...")
    # Use the utility function directly
    from _agent_coordination.utils.onboarding_message_injector import inject_initial_onboarding_message # Re-import here just in case
    injection_success = inject_initial_onboarding_message(claimed_mailbox_path, agent_id)
    if not injection_success:
        logger.critical(f"[{agent_id}] FAILED to inject initial onboarding message into {claimed_mailbox_path}. Proceeding, but onboarding may fail.")
    else:
        logger.info(f"[{agent_id}] Onboarding message successfully injected into {claimed_mailbox_path}.")

    # --- Initialize Core Components ---
    filesystem = PlaceholderFilesystem()
    memory = PlaceholderMemory()
    command_handler = CommandHandler(
        agent_id=agent_id,
        specialization=specialization,
        filesystem=filesystem,
        memory=memory,
        logger=logging.getLogger(f"CommandHandler_{agent_id}")
    )
    
    logger.info(f"[{agent_id}] Initialization complete. Starting main operational loop (Task List Priority). Claimed Mailbox: {claimed_mailbox_path}")
    
    # --- Main Operational Loop ---
    last_activity_time = time.time() # Initialize activity timer
    try:
        while True:
            # 1. Check for External Termination Signal first
            if memory.get("terminate_signal"):
               reason = memory.get("terminate_reason", "Unknown")
               logger.info(f"[{agent_id}] Termination signal detected (Reason: {reason}). Shutting down main loop.")
               break
               
            activity_this_cycle = False
            
            # 2. Attempt to find and execute a task from the master list
            task_processed = find_and_execute_task_from_list(
                agent_id, specialization, command_handler, memory, filesystem
            )
            if task_processed:
                activity_this_cycle = True
            
            # 3. If no task was found/processed, check mailbox for commands
            processed_new_mailbox_message = False
            if not activity_this_cycle:
                 logger.debug(f"[{agent_id}] No task processed. Checking mailbox {claimed_mailbox_path} for commands...")
                 processed_new_mailbox_message = process_mailbox_messages(claimed_mailbox_path, agent_id, command_handler)
                 if processed_new_mailbox_message:
                     activity_this_cycle = True
                     
            # 4. Update Activity Timer or Check Idle Timeout
            if activity_this_cycle:
                last_activity_time = time.time() # Reset timer on activity
                logger.debug(f"[{agent_id}] Activity detected this cycle. Resetting idle timer.")
                # Short sleep after activity
                time.sleep(0.1)
            else:
                # No activity, check idle duration
                idle_duration = time.time() - last_activity_time
                logger.debug(f"[{agent_id}] No activity this cycle. Idle duration: {idle_duration:.2f} seconds.")
                if idle_duration > MAX_IDLE_DURATION:
                    logger.warning(f"[{agent_id}] Exceeded max idle duration ({MAX_IDLE_DURATION}s). Initiating self-termination.")
                    memory.set("terminate_signal", True)
                    memory.set("terminate_reason", "Idle timeout")
                    # No need to break here, the check at the top of the loop will catch it next iteration
                
                # Longer sleep when idle
                time.sleep(POLL_INTERVAL)
                 
    except KeyboardInterrupt:
        logger.info(f"[{agent_id}] Keyboard interrupt received. Shutting down gracefully.")
    except Exception as e:
         logger.critical(f"[{agent_id}] Critical error in main operational loop: {e}", exc_info=True)
    finally:
        # --- Release Mailbox on Exit ---
        # Ensure mailbox path was successfully claimed before trying to release
        if claimed_mailbox_path:
             release_shared_mailbox(claimed_mailbox_path, agent_id)
        logger.info(f"--- Agent {agent_id} Finished ---")
        
    return 0 # Exit normally

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dream.OS Agent Entrypoint")
    parser.add_argument("--agent-id", required=True, help="Unique ID for this agent instance.")
    parser.add_argument("--specialization", default="generic", help="Specialization role for the agent.")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG level logging.") # Add debug flag
    args = parser.parse_args()

    # Set logging level based on flag
    log_level = logging.DEBUG if args.debug else logging.INFO
    # Reconfigure logging ONLY if not already configured (e.g. by basicConfig earlier)
    # This might require more sophisticated logging setup in a real app
    for handler in logging.root.handlers[:]: 
        logging.root.removeHandler(handler)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info(f"Logging level set to: {logging.getLevelName(log_level)}")

    # Ensure shared mailbox directory exists
    if not os.path.exists(SHARED_MAILBOX_DIR):
        try:
            os.makedirs(SHARED_MAILBOX_DIR)
            logger.info(f"Created shared mailbox directory: {SHARED_MAILBOX_DIR}")
        except OSError as e:
             logger.critical(f"Failed to create shared mailbox directory {SHARED_MAILBOX_DIR}: {e}")
             sys.exit(1)
        
    # Start the main agent loop
    exit_code = main_agent_loop(args.agent_id, args.specialization)
    sys.exit(exit_code) 