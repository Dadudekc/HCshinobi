import json
import os
import logging
import datetime

# Configure a logger for this utility module
logger = logging.getLogger(__name__)

# Define the standard empty/initial mailbox structure
DEFAULT_MAILBOX_STRUCTURE = lambda agent_id: {
    "status": "online", # Assume claimed if injecting
    "assigned_agent_id": agent_id,
    "last_seen_utc": datetime.datetime.utcnow().isoformat(),
    "messages": [],
    "processed_message_ids": []
}

def inject_initial_onboarding_message(mailbox_path: str, agent_id: str, template_path: str = "user_prompts/agent_activation_template.txt") -> bool:
    """
    Injects the standard initial onboarding message into the specified mailbox file,
    ensuring the file maintains the correct object structure.

    Args:
        mailbox_path: The full path to the target shared mailbox JSON file.
        agent_id: The ID of the agent claiming the mailbox.
        template_path: The relative path (from workspace root) to the activation template.

    Returns:
        True if injection was successful, False otherwise.
    """
    onboarding_msg = {
        "message_id": f"onboarding_{agent_id}_{int(datetime.datetime.utcnow().timestamp())}", # Add unique ID
        "sender": "AgentBootstrap",
        "timestamp_utc": datetime.datetime.utcnow().isoformat(),
        "command": "initial_onboarding",
        "params": {
            "prompt_template_path": template_path
        }
    }

    logger.info(f"[{agent_id}] Attempting to inject onboarding message into: {mailbox_path}")

    # --- Read and Load Phase --- 
    mailbox_data = {}
    needs_initialization = False
    try:
        if os.path.exists(mailbox_path):
            with open(mailbox_path, "r", encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    try:
                        loaded_data = json.loads(content)
                        if isinstance(loaded_data, dict):
                            mailbox_data = loaded_data
                            logger.debug(f"[{agent_id}] Loaded existing mailbox object from {mailbox_path}")
                        else:
                            logger.warning(f"[{agent_id}] Mailbox {mailbox_path} contained non-object data ({type(loaded_data).__name__}). Re-initializing structure.")
                            needs_initialization = True
                    except json.JSONDecodeError:
                        logger.warning(f"[{agent_id}] Mailbox {mailbox_path} contained invalid JSON. Re-initializing structure.")
                        needs_initialization = True
                else:
                    logger.info(f"[{agent_id}] Mailbox {mailbox_path} was empty. Initializing structure.")
                    needs_initialization = True
        else:
             logger.info(f"[{agent_id}] Mailbox file {mailbox_path} not found. Initializing structure.")
             needs_initialization = True
            
        if needs_initialization:
            mailbox_data = DEFAULT_MAILBOX_STRUCTURE(agent_id)
            # Ensure basic fields are present if we loaded partial data before deciding to re-init
            mailbox_data.setdefault("status", "online")
            mailbox_data.setdefault("assigned_agent_id", agent_id)
            mailbox_data.setdefault("last_seen_utc", datetime.datetime.utcnow().isoformat())
            mailbox_data.setdefault("messages", [])
            mailbox_data.setdefault("processed_message_ids", [])
        else:
             # Ensure essential lists exist if loaded object was missing them
             if not isinstance(mailbox_data.get("messages"), list):
                 logger.warning(f"[{agent_id}] Existing mailbox object missing/invalid 'messages' list. Resetting.")
                 mailbox_data["messages"] = []
             if not isinstance(mailbox_data.get("processed_message_ids"), list):
                 logger.warning(f"[{agent_id}] Existing mailbox object missing/invalid 'processed_message_ids' list. Resetting.")
                 mailbox_data["processed_message_ids"] = []
                
    except Exception as e:
        logger.error(f"[{agent_id}] Error reading/preparing mailbox {mailbox_path} before injection: {e}", exc_info=True)
        return False # Indicate failure

    # --- Modify Phase --- 
    # Append onboarding message to the messages list within the object
    try:
        # Ensure messages is actually a list before appending
        if not isinstance(mailbox_data.get("messages"), list):
             logger.error(f"[{agent_id}] Internal error: mailbox_data['messages'] is not a list before append. Aborting injection.")
             return False
            
        mailbox_data["messages"].append(onboarding_msg)
        # Update status fields as we are interacting
        mailbox_data["status"] = "online" # Ensure it's marked online
        mailbox_data["assigned_agent_id"] = agent_id
        mailbox_data["last_seen_utc"] = datetime.datetime.utcnow().isoformat()
        logger.debug(f"[{agent_id}] Appended onboarding message to in-memory mailbox object.")
    except Exception as e:
        logger.error(f"[{agent_id}] Error modifying mailbox data in memory: {e}", exc_info=True)
        return False

    # --- Write Phase (Atomic) --- 
    temp_mailbox_path = mailbox_path + ".inject.tmp"
    try:
        # Ensure parent directory exists
        mailbox_dir = os.path.dirname(mailbox_path)
        if mailbox_dir and not os.path.exists(mailbox_dir):
            os.makedirs(mailbox_dir)
            logger.info(f"[{agent_id}] Created directory for mailbox: {mailbox_dir}")
           
        # --- Debug Log: Check structure before writing ---
        if isinstance(mailbox_data, dict):
            logger.debug(f"[{agent_id}] DEBUG_INJECT: Writing OBJECT to {temp_mailbox_path}. Keys: {list(mailbox_data.keys())}")
        else:
            logger.debug(f"[{agent_id}] DEBUG_INJECT: Writing NON-OBJECT ({type(mailbox_data).__name__}) to {temp_mailbox_path}")
        # --- End Debug Log ---
            
        with open(temp_mailbox_path, "w", encoding='utf-8') as f:
            json.dump(mailbox_data, f, indent=2)
        os.replace(temp_mailbox_path, mailbox_path)
        logger.info(f"[{agent_id}] Successfully injected onboarding message into {mailbox_path} (object structure maintained).")
        return True
    except Exception as e:
        logger.error(f"[{agent_id}] Failed to write updated mailbox object to {mailbox_path}: {e}", exc_info=True)
        if os.path.exists(temp_mailbox_path):
            try: os.remove(temp_mailbox_path)
            except Exception as cleanup_err: logger.error(f"[{agent_id}] Failed to remove temp file {temp_mailbox_path}: {cleanup_err}")
        return False

# Example usage (if run directly for testing)
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     # Ensure paths are correct relative to where you run this
#     # Adjust mailbox number and paths as needed for testing
#     test_mailbox = '../_agent_coordination/shared_mailboxes/mailbox_8.json' 
#     test_agent_id = 'TestAgent001'
#     print(f"Testing injection into: {os.path.abspath(test_mailbox)}")
#     success = inject_initial_onboarding_message(test_mailbox, test_agent_id)
#     print(f"Test injection successful: {success}") 