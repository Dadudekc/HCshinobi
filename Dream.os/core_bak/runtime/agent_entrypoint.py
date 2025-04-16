import json
import argparse
import time
import uuid
import logging
import sys
import os
import random
import signal
from pathlib import Path
from datetime import datetime, timezone

# --- Attempt to import the specific Agent class --- 
# TODO: Make the agent class import dynamic or configurable
# For now, assuming CursorControlAgent is the one we want
# Adjust the path based on actual project structure if this agent moves
AGENT_CLASS = None
try:
    # Assumes this script is in _agent_coordination/runtime/
    # and the agent is in _agent_coordination/agents/
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agents.cursor_control_agent import CursorControlAgent
    AGENT_CLASS = CursorControlAgent
    print(f"Successfully imported agent class: {AGENT_CLASS.__name__}")
except ImportError as e:
    print(f"Error: Could not import agent class (tried CursorControlAgent). Ensure it's accessible. {e}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred during agent class import: {e}")
    sys.exit(1)

# --- Configuration ---
SHARED_MAILBOX_DIR = Path(__file__).parent.parent / "shared_mailboxes"
NUM_MAILBOXES = 8
HEARTBEAT_INTERVAL_SECONDS = 30 # How often to update last_seen_utc
POLL_INTERVAL_SECONDS = 3 # How often to check for new messages
CLAIM_RETRY_DELAY_MAX_SECONDS = 1.5 # Max random delay before retrying claim

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
        # TODO: Add FileHandler if persistent logs per agent are needed
    ]
)
logger = logging.getLogger("AgentEntrypoint")

# --- Safe JSON I/O Functions (Embedded) ---
def load_json_safe(file_path: Path, default=None):
    """Safely load JSON from a file, handling errors."""
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}")
        return default
    except json.JSONDecodeError:
        logger.error(f"JSON decode error in file: {file_path}. Returning default.")
        # Consider backing up the corrupted file here
        return default
    except Exception as e:
        logger.error(f"Unexpected error loading JSON from {file_path}: {e}", exc_info=True)
        return default

def write_json_safe(file_path: Path, data: dict):
    """Safely write JSON data to a file using a temporary file and rename."""
    temp_file_path = file_path.with_suffix(f".{uuid.uuid4()}.tmp")
    try:
        with temp_file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        # Atomic rename (on most POSIX systems and Windows)
        os.replace(temp_file_path, file_path)
        return True
    except Exception as e:
        logger.error(f"Error writing JSON safely to {file_path}: {e}", exc_info=True)
        # Attempt to clean up the temporary file if it exists
        if temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except OSError:
                pass
        return False

# --- Mailbox Interaction ---
def claim_mailbox(agent_id: str) -> Path | None:
    """Attempt to claim an available shared mailbox."""
    mailbox_indices = list(range(1, NUM_MAILBOXES + 1))
    random.shuffle(mailbox_indices) # Reduce likelihood of simultaneous attempts on mailbox_1

    for i in mailbox_indices:
        mailbox_path = SHARED_MAILBOX_DIR / f"mailbox_{i}.json"
        logger.info(f"Attempting to claim {mailbox_path.name}...")

        # Read current state
        mailbox_data = load_json_safe(mailbox_path)
        if not mailbox_data:
            logger.error(f"Could not read or parse {mailbox_path.name}. Skipping.")
            continue

        if mailbox_data.get("status") == "offline" or mailbox_data.get("assigned_agent_id") is None:
            logger.info(f"{mailbox_path.name} appears available. Attempting atomic write...")
            mailbox_data["status"] = "online"
            mailbox_data["assigned_agent_id"] = agent_id
            mailbox_data["last_seen_utc"] = datetime.now(timezone.utc).isoformat()
            mailbox_data["messages"] = mailbox_data.get("messages", []) # Ensure lists exist
            mailbox_data["processed_message_ids"] = mailbox_data.get("processed_message_ids", [])

            # Attempt to write back
            if write_json_safe(mailbox_path, mailbox_data):
                # Verify our write stuck (read back)
                time.sleep(0.1) # Small delay for filesystem
                verify_data = load_json_safe(mailbox_path)
                if verify_data and verify_data.get("assigned_agent_id") == agent_id:
                    logger.info(f"Successfully claimed {mailbox_path.name} for agent {agent_id}.")
                    return mailbox_path
                else:
                    logger.warning(f"Claimed {mailbox_path.name}, but verification failed (another agent might have claimed simultaneously). Rolling back attempt.")
                    # Attempt to roll back (best effort)
                    if verify_data: # Only rollback if we read something valid
                        verify_data["status"] = "offline"
                        verify_data["assigned_agent_id"] = None
                        write_json_safe(mailbox_path, verify_data) # Write back original agent's data if possible
            else:
                logger.error(f"Failed to write claim to {mailbox_path.name}.")
        else:
            logger.debug(f"{mailbox_path.name} is already assigned to {mailbox_data.get('assigned_agent_id')} with status {mailbox_data.get('status')}. Skipping.")

        # Random delay before trying next mailbox
        time.sleep(random.uniform(0.1, CLAIM_RETRY_DELAY_MAX_SECONDS))

    logger.error(f"Agent {agent_id} could not claim any of the {NUM_MAILBOXES} mailboxes.")
    return None

def release_mailbox(mailbox_path: Path, agent_id: str):
    """Release the claimed mailbox."""
    logger.info(f"Releasing mailbox {mailbox_path.name} for agent {agent_id}...")
    mailbox_data = load_json_safe(mailbox_path)
    if mailbox_data:
        if mailbox_data.get("assigned_agent_id") == agent_id:
            mailbox_data["status"] = "offline"
            mailbox_data["assigned_agent_id"] = None
            # Optionally clear messages or leave them?
            # mailbox_data["messages"] = []
            # mailbox_data["processed_message_ids"] = []
            if write_json_safe(mailbox_path, mailbox_data):
                logger.info(f"Successfully released {mailbox_path.name}.")
            else:
                logger.error(f"Failed to write release state to {mailbox_path.name}.")
        else:
            logger.warning(f"Tried to release {mailbox_path.name}, but it seems assigned to another agent ({mailbox_data.get('assigned_agent_id')}). Doing nothing.")
    else:
        logger.error(f"Could not read {mailbox_path.name} during release attempt.")

# --- Main Agent Loop ---
def run_agent_loop(agent_id: str, mailbox_path: Path, agent_instance):
    """Main loop for monitoring mailbox and processing messages."""
    logger.info(f"Agent {agent_id} starting main loop for {mailbox_path.name}.")
    last_heartbeat_time = time.monotonic()
    running = True

    while running:
        try:
            current_time = time.monotonic()
            heartbeat_due = (current_time - last_heartbeat_time) >= HEARTBEAT_INTERVAL_SECONDS

            # Read mailbox state
            mailbox_data = load_json_safe(mailbox_path)
            if not mailbox_data or mailbox_data.get("assigned_agent_id") != agent_id:
                logger.error(f"Lost claim on {mailbox_path.name} or mailbox unreadable. Shutting down.")
                running = False
                continue

            processed_ids = set(mailbox_data.get("processed_message_ids", []))
            messages_to_process = []
            needs_write = False

            # Check for new messages
            for msg in mailbox_data.get("messages", [])[:]: # Iterate over a copy for potential removal
                msg_id = msg.get("message_id")
                if not msg_id:
                    logger.warning(f"Found message without ID in {mailbox_path.name}, skipping: {msg.get('command')}")
                    # Optionally remove malformed message here? Requires careful list handling
                    continue
                
                if msg_id not in processed_ids:
                    messages_to_process.append(msg)

            if messages_to_process:
                logger.info(f"Found {len(messages_to_process)} new message(s). Processing...")
                mailbox_data["status"] = "busy"
                mailbox_data["last_seen_utc"] = datetime.now(timezone.utc).isoformat()
                write_json_safe(mailbox_path, mailbox_data) # Update status to busy before processing
                needs_write = False # Reset flag as we just wrote

                for msg in messages_to_process:
                    msg_id = msg["message_id"]
                    command = msg.get("command")
                    params = msg.get("params", {})
                    logger.info(f"Processing message {msg_id}: Command='{command}'")

                    handler = agent_instance.command_handlers.get(command)
                    if handler:
                        try:
                            # Execute the handler
                            # Pass the full message payload for context (like original_task_id if present)
                            success = handler(msg) 
                            logger.info(f"Handler for command '{command}' (msg {msg_id}) returned: {success}")
                            # TODO: Decide if message should be removed or just marked processed
                            # mailbox_data["messages"].remove(msg) # Example removal
                        except Exception as e:
                            logger.error(f"Error executing handler for command '{command}' (msg {msg_id}): {e}", exc_info=True)
                            # TODO: Add error details to message or separate log?
                    else:
                        logger.warning(f"No handler found for command '{command}' (msg {msg_id}). Marking as processed.")

                    # Mark as processed regardless of handler success/failure to avoid loops
                    processed_ids.add(msg_id)
                    mailbox_data["processed_message_ids"] = list(processed_ids)
                    needs_write = True

                # Update status back after processing batch
                mailbox_data["status"] = "online" # Or "idle"?
                needs_write = True

            elif heartbeat_due:
                logger.debug(f"Sending heartbeat for {agent_id}...")
                mailbox_data["status"] = mailbox_data.get("status", "online") # Keep current status if not busy
                needs_write = True

            # Write back if changes were made or heartbeat is due
            if needs_write:
                mailbox_data["last_seen_utc"] = datetime.now(timezone.utc).isoformat()
                if write_json_safe(mailbox_path, mailbox_data):
                     if heartbeat_due: last_heartbeat_time = current_time
                else:
                    logger.error("Failed to write updated mailbox state. Retrying next cycle.")

            # Wait before next poll
            time.sleep(POLL_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Shutting down loop...")
            running = False
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            # Potentially add a longer sleep here to prevent rapid error loops
            time.sleep(POLL_INTERVAL_SECONDS * 5)

    logger.info(f"Agent {agent_id} loop finished.")

# --- Signal Handling for Graceful Shutdown ---
claimed_mailbox_path = None
agent_id_global = None

def handle_signal(signum, frame):
    logger.warning(f"Received signal {signum}. Initiating graceful shutdown for agent {agent_id_global}...")
    if claimed_mailbox_path and agent_id_global:
        release_mailbox(claimed_mailbox_path, agent_id_global)
    sys.exit(0)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Autonomous agent entrypoint using shared mailboxes.")
    parser.add_argument("--agent-id", required=True, help="Unique identifier for this agent instance.")
    # TODO: Add arguments for agent class, task list path, etc. if needed by the agent
    args = parser.parse_args()

    agent_id_global = args.agent_id
    logger.info(f"--- Initializing Agent: {agent_id_global} ---")

    if not SHARED_MAILBOX_DIR.is_dir():
        logger.error(f"Shared mailbox directory not found: {SHARED_MAILBOX_DIR}")
        sys.exit(1)

    # Attempt to claim a mailbox
    claimed_mailbox_path = claim_mailbox(agent_id_global)

    if not claimed_mailbox_path:
        logger.error(f"Agent {agent_id_global} failed to claim a mailbox. Exiting.")
        sys.exit(1)

    # Instantiate the agent class
    # TODO: Pass necessary config (like task_list_path if needed) to the agent constructor
    try:
        agent_instance = AGENT_CLASS(mailbox_root_dir=SHARED_MAILBOX_DIR.parent) # Pass root above shared?
        logger.info(f"Instantiated agent logic class: {type(agent_instance).__name__}")
    except Exception as e:
        logger.error(f"Failed to instantiate agent class {AGENT_CLASS.__name__}: {e}", exc_info=True)
        # Release mailbox before exiting if instantiation fails
        release_mailbox(claimed_mailbox_path, agent_id_global)
        sys.exit(1)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal) # Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal) # Termination signal

    try:
        # Run the main loop
        run_agent_loop(agent_id_global, claimed_mailbox_path, agent_instance)
    except Exception as e:
        # Catch any unexpected errors escaping the loop
        logger.error(f"Fatal error during agent execution: {e}", exc_info=True)
    finally:
        # Final attempt to release mailbox upon exit
        logger.info("Ensuring mailbox is released...")
        release_mailbox(claimed_mailbox_path, agent_id_global)
        logger.info(f"--- Agent {agent_id_global} Finished ---") 