import argparse
from pathlib import Path
import logging
import json # Changed from yaml
import yaml # Keep yaml for potentially reading old formats?

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupervisorMailboxValidator")

# --- Configuration ---
# Adjust COORD_DIR if your structure is different
COORD_DIR = Path("_agent_coordination") 
EXPECTED_DIRS = ["inbox", "outbox"]
EXPECTED_FORMAT = ".json" # Standardizing on JSON

# Define basic required keys per message type (can be expanded)
# Using simplified keys for now - needs refinement based on actual usage
BASE_REQUIRED_KEYS = ["type", "timestamp"] # Keys required in ALL messages
TASK_REQUIRED_KEYS = BASE_REQUIRED_KEYS + ["task_id", "details"] # For inbox tasks
RESULT_REQUIRED_KEYS = BASE_REQUIRED_KEYS + ["task_id", "status", "agent_name"] # For outbox results
ALERT_REQUIRED_KEYS = BASE_REQUIRED_KEYS + ["message_id", "source_agent"] # For inbox alerts

# --- Functions ---
def validate_message_file(file_path: Path, agent_name: str) -> tuple[int, int]:
    """Validates a single message file (JSON) against basic required keys based on type."""
    errors = 0
    warnings = 0
    required_keys = BASE_REQUIRED_KEYS # Default
    file_type = "Unknown"

    logger.debug(f"[{agent_name}] Validating file: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            logger.error(f"[{agent_name}] Message file is not a valid dictionary: {file_path.name}")
            return 1, 0 # 1 error, 0 warnings
        
        file_type = data.get("type", "unknown").lower()
        
        # Determine required keys based on type
        if file_type == "task" or file_type.endswith("_request"): # e.g., task, reflection_request
            required_keys = TASK_REQUIRED_KEYS
        elif file_type == "task_result" or file_type.endswith("_result") or file_type == "report": # e.g., task_result, reflection_result
            required_keys = RESULT_REQUIRED_KEYS
        elif file_type.endswith("_alert") or file_type == "issue_report":
            required_keys = ALERT_REQUIRED_KEYS
        else:
             logger.warning(f"[{agent_name}] Unknown message type '{file_type}' in {file_path.name}. Using base key check.")
             warnings += 1
             # Fallback to ensure message/task ID exists if possible
             id_key = "task_id" if "task_id" in data else ("message_id" if "message_id" in data else None)
             if id_key:
                 required_keys = BASE_REQUIRED_KEYS + [id_key]
             else:
                  logger.error(f"[{agent_name}] Unknown message type '{file_type}' AND missing task_id/message_id in {file_path.name}.")
                  errors += 1 # Critical if no ID

        # Check for required keys
        missing_keys = [key for key in required_keys if key not in data]
        if missing_keys:
            # Log missing keys as errors for now, could be warnings for non-critical keys later
            logger.error(f"[{agent_name}] Message file ({file_type}) missing required keys ({', '.join(missing_keys)}): {file_path.name}")
            errors += len(missing_keys)
        else:
             logger.debug(f"[{agent_name}] Required keys check passed for {file_path.name} ({file_type})")
            
    except json.JSONDecodeError as e:
        logger.error(f"[{agent_name}] Invalid JSON format in message file {file_path.name}: {e}")
        errors += 1
    except Exception as e:
        logger.error(f"[{agent_name}] Error reading/processing message file {file_path.name}: {e}")
        errors += 1
        
    return errors, warnings

def validate_agent_mailbox(agent_name: str) -> tuple[int, int]:
    """Validates the mailbox structure and message file formats for an agent."""
    agent_dir = COORD_DIR / agent_name
    total_errors = 0
    total_warnings = 0

    if not agent_dir.is_dir():
        logger.warning(f"[{agent_name}] Agent directory not found: {agent_dir}")
        return 0, 1 # Count as 1 warning

    logger.info(f"Validating mailbox for: {agent_name}")

    for subdir_name in EXPECTED_DIRS: # Check both inbox and outbox
        subdir_path = agent_dir / subdir_name
        if not subdir_path.is_dir():
            logger.error(f"[{agent_name}] Missing expected directory: {subdir_path}")
            total_errors += 1
            continue # Skip checking files if dir missing
            
        # Validate message files within the directory
        for item in subdir_path.iterdir():
            if item.is_file():
                if item.name.lower().endswith(EXPECTED_FORMAT):
                    err, warn = validate_message_file(item, agent_name)
                    total_errors += err
                    total_warnings += warn
                else:
                    # Log unexpected file formats as warnings
                    logger.warning(f"[{agent_name}] Found file with unexpected format in {subdir_name}: {item.name}")
                    total_warnings += 1
            # Ignore subdirectories within inbox/outbox for now

    if total_errors == 0 and total_warnings == 0:
         logger.info(f"[{agent_name}] Mailbox validation passed.")
    else:
         logger.warning(f"[{agent_name}] Mailbox validation finished with {total_errors} errors and {total_warnings} warnings.")

    return total_errors, total_warnings

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate agent mailbox structures and formats (expecting JSON)." + # Updated desc
                                     f" Checks for required keys based on message 'type'.")
    parser.add_argument("agents", nargs='*' , help="Specific agent names to validate (validates all agents found in coordination dir if none provided).")
    args = parser.parse_args()

    logger.info("--- Supervisor: Validating Agent Mailboxes (JSON Format) ---")
    overall_errors = 0
    overall_warnings = 0

    if not COORD_DIR.is_dir():
        logger.error(f"Coordination directory not found: {COORD_DIR}")
        exit(1)

    if args.agents:
        agents_to_validate = args.agents
    else:
        # Find all subdirectories in coordination dir as potential agents
        agents_to_validate = [d.name for d in COORD_DIR.iterdir() if d.is_dir()]
        logger.info(f"No specific agents provided, found: {', '.join(agents_to_validate)}")

    logger.info(f"Validating agents: {', '.join(agents_to_validate)}")

    for agent in agents_to_validate:
        err, warn = validate_agent_mailbox(agent)
        overall_errors += err
        overall_warnings += warn

    logger.info("--- Mailbox Validation Complete ---")
    if overall_errors > 0 or overall_warnings > 0:
        logger.warning(f"Validation finished with Total Errors: {overall_errors}, Total Warnings: {overall_warnings}")
    else:
        logger.info("All validated mailboxes passed checks.")

    if overall_errors > 0:
        exit(1) # Exit with error code if validation errors occurred
    else:
        exit(0) 