# Agent1/supervisor_tools/process_inbox.py

import os
import json
import yaml
import logging
import time
import shutil
from pathlib import Path
from datetime import datetime
import uuid
import re # Added for parsing result files

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SupervisorInboxProcessor")

# --- Configuration ---
# Assuming this script is run relative to the project root or paths are adjusted
AGENT1_DIR = Path("_agent_coordination/Agent1") # Adjusted Path
INBOX_DIR = AGENT1_DIR / "inbox"
PROCESSED_DIR = AGENT1_DIR / "inbox_processed"
ERROR_DIR = AGENT1_DIR / "inbox_errors"
OUTBOX_DIR = AGENT1_DIR / "outbox" # Added for monitoring results
OUTBOX_PROCESSED_DIR = AGENT1_DIR / "outbox_processed" # Added
OUTBOX_ERROR_DIR = AGENT1_DIR / "outbox_errors" # Added
LOG_DIR = AGENT1_DIR / "logs"
REFLECTION_LOG_FILE = LOG_DIR / "reflection_log.md"
AGENT_DIRS_ROOT = Path("_agent_coordination") # Base for finding other agents
REFLECTION_AGENT = "Agent2" # Designate Agent 2 for reflections

# Ensure directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_ERROR_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- Task Injection Functionality (NEW) ---
def generate_task_id(prefix="TASK"):
    """Generates a unique task ID."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    short_uuid = str(uuid.uuid4().hex)[:6]
    return f"{prefix}-{timestamp}-{short_uuid}"

def inject_task(target_agent: str, task_data: dict):
    """Injects a task file (JSON) into the target agent's inbox."""
    if "task_id" not in task_data:
        logger.error(f"Task data missing 'task_id' for injection into {target_agent}. Aborting.")
        return False
    
    task_id = task_data["task_id"]
    target_inbox = AGENT_DIRS_ROOT / target_agent / "inbox"
    task_file_path = target_inbox / f"{task_id}.json"

    try:
        target_inbox.mkdir(parents=True, exist_ok=True) # Ensure inbox exists
        with open(task_file_path, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, indent=2)
        logger.info(f"Successfully injected task '{task_id}' into {target_agent}'s inbox: {task_file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to inject task '{task_id}' into {target_agent}'s inbox: {e}", exc_info=True)
        return False

# --- Reflection Log Functionality ---
def log_reflection_trigger(alert_details, reflection_task_id):
    """Appends a 'TRIGGERED' entry to the reflection log, including the task ID."""
    entry_id = f"RFL-LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{alert_details.get('message_id', 'unknown')[:8]}"
    timestamp = datetime.now().isoformat() + "Z"

    log_entry = f"""---
**Entry ID:** {entry_id}
**Timestamp:** {timestamp}
**Alert ID:** {alert_details.get('message_id', 'N/A')}
**Violated Rule:** {alert_details.get('rule_id', 'Unknown')}
**Violating Agent:** {alert_details.get('violating_agent', 'Unknown')}
**Status:** TRIGGERED
**Details:** Alert received. Initiating reflection task for {REFLECTION_AGENT}.
**Reflection Task ID:** {reflection_task_id}
**Reflection Outcome:** (Pending)
---
"""
    try:
        with open(REFLECTION_LOG_FILE, 'a', encoding='utf-8') as f:
             # Add header if file is new/empty
            if REFLECTION_LOG_FILE.stat().st_size == 0:
                f.write("# Reflection Log\n\nTracks rule violations and triggered reflections.\n\n")
            f.write("\n" + log_entry)
        logger.info(f"Logged reflection trigger to {REFLECTION_LOG_FILE} for Alert ID: {alert_details.get('message_id')} (Task: {reflection_task_id})")
        return True
    except Exception as e:
        logger.error(f"Failed to write to reflection log {REFLECTION_LOG_FILE}: {e}")
        return False

def update_reflection_log_outcome(reflection_task_id, outcome_status, outcome_summary):
    """Finds a reflection log entry by task ID and updates its outcome."""
    if not REFLECTION_LOG_FILE.exists():
        logger.error(f"Reflection log file not found: {REFLECTION_LOG_FILE}")
        return False

    try:
        content = REFLECTION_LOG_FILE.read_text(encoding='utf-8')
        # Regex to find the specific entry and update status/outcome
        # This assumes the basic structure remains consistent
        pattern = re.compile(
            rf"(\*\*Entry ID:\*\* .*?\n.*?\*\*Reflection Task ID:\*\* {re.escape(reflection_task_id)}\n)(\*\*Status:\*\* TRIGGERED)(\n\*\*Reflection Outcome:\*\* \(Pending\))",
            re.MULTILINE | re.DOTALL
        )
        
        update_timestamp = datetime.now().isoformat() + "Z"
        new_status_line = f"**Status:** {outcome_status}"
        new_outcome_line = f"**Reflection Outcome:** {outcome_summary} (Updated: {update_timestamp})"
        
        updated_content, num_replacements = pattern.subn(
            rf"\1{new_status_line}\n{new_outcome_line}",
            content
        )

        if num_replacements > 0:
            REFLECTION_LOG_FILE.write_text(updated_content, encoding='utf-8')
            logger.info(f"Updated reflection log for Task ID: {reflection_task_id} with status: {outcome_status}")
            return True
        else:
            logger.warning(f"Could not find pending reflection log entry for Task ID: {reflection_task_id}")
            return False # Entry not found or already updated
    except Exception as e:
        logger.error(f"Failed to update reflection log outcome for Task ID {reflection_task_id}: {e}")
        return False

# --- Message Processing Functions ---
def process_rule_alert(message_path, message_data):
    """Processes messages with type 'rule_alert'. Logs violation and injects reflection task."""
    logger.info(f"Processing Rule Alert: {message_data.get('message_id', 'Unknown ID')}")
    
    # Extract details
    alert_details = {
        "message_id": message_data.get('message_id'),
        "timestamp": message_data.get('timestamp'),
        "source_agent": message_data.get('source_agent'),
        "violating_agent": message_data.get('violating_agent'),
        "halt_reason": message_data.get('halt_reason'),
        # Attempt to get rule ID from standard field or infer if needed
        "rule_id": message_data.get('rule_id', message_data.get('rule_ref', 'Unknown')), 
        "context": message_data.get('message', '')
    }

    # Generate Reflection Task
    reflection_task_id = generate_task_id(prefix="REFLECT")
    reflection_task_data = {
        "task_id": reflection_task_id,
        "type": "reflection_request",
        "timestamp": datetime.now().isoformat() + "Z",
        "priority": 2, # Make reflection reasonably high priority
        "details": {
            "alert_id": alert_details["message_id"],
            "violating_agent": alert_details["violating_agent"],
            "violated_rule": alert_details["rule_id"],
            "alert_context": alert_details["context"],
            "request": f"Analyze the circumstances of alert {alert_details['message_id']} regarding agent {alert_details['violating_agent']} and rule {alert_details['rule_id']}. Consult the rulebook. Generate a reflection report suggesting potential causes, fixes, or rule clarifications. Place report ({reflection_task_id}-reflection.md) in Agent1/outbox."
        }
    }

    # --- >>> Implementing coord-002 <<< ---
    # 1. Log the trigger event (including the reflection task ID)
    logged = log_reflection_trigger(alert_details, reflection_task_id)
    
    # 2. Inject the reflection task into the designated agent's inbox
    injected = inject_task(REFLECTION_AGENT, reflection_task_data)
    
    # Return success only if both logging and injection worked
    return logged and injected

def process_other_message(message_path, message_data):
    """Placeholder for processing other message types."""
    logger.info(f"Processing Other Message ({message_data.get('type', 'Unknown Type')}): {message_data.get('message_id', 'Unknown ID')}")
    # Add logic here for handling status updates, task results, etc.
    return True # Indicate successful processing

def process_inbox_file(message_path: Path):
    """Reads, parses, and routes a message file for processing."""
    try:
        logger.debug(f"Attempting to process message: {message_path.name}")
        content = message_path.read_text(encoding='utf-8')
        
        # Determine format (JSON or YAML) - Assume JSON for now based on examples
        if message_path.suffix.lower() == '.json':
            data = json.loads(content)
        # elif message_path.suffix.lower() in ['.yaml', '.yml']:
        #     data = yaml.safe_load(content)
        else:
            logger.warning(f"Skipping non-JSON file: {message_path.name}")
            # Move to an 'unknown_format' dir? For now, leave it.
            return False # Not processed
        
        message_type = data.get("type", "unknown").lower()
        processed = False
        if message_type == "rule_alert":
            processed = process_rule_alert(message_path, data)
        # Add elif for other message types here
        # elif message_type == "task_result":
        #     processed = process_task_result(message_path, data)
        else:
            processed = process_other_message(message_path, data)
        
        return processed

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in message file {message_path.name}: {e}")
        return False # Processing failed
    except Exception as e:
        logger.error(f"Error processing message file {message_path.name}: {e}", exc_info=True)
        return False # Processing failed

# --- Result Processing Functions (NEW) ---
def parse_result_file(result_path: Path) -> dict | None:
    """Parses the simple KEY: Value format used in Agent 2's results."""
    try:
        content = result_path.read_text(encoding='utf-8')
        result_data = {}
        header_part = content.split("\n---\n", 1)[0] # Get only lines before separator
        for line in header_part.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                result_data[key.strip()] = value.strip()
        # Optionally extract report content if needed later
        # if "\n---\n" in content:
        #     result_data["report_content"] = content.split("\n---\n", 1)[1].strip()
        return result_data
    except Exception as e:
        logger.error(f"Error parsing result file {result_path.name}: {e}")
        return None

def process_reflection_result(result_path: Path):
    """Handles reflection results placed in the supervisor outbox."""
    logger.info(f"Processing reflection result file: {result_path.name}")
    result_data = parse_result_file(result_path)
    if not result_data:
        return False # Parsing failed
    
    task_id = result_data.get("TASK_ID")
    status = result_data.get("STATUS", "Unknown")
    summary = result_data.get("RESULT_SUMMARY", "(No summary provided)")
    
    if not task_id:
        logger.error(f"Result file {result_path.name} is missing TASK_ID.")
        return False
        
    # Update the reflection log
    log_status = "COMPLETED" if status == "Done" else "ERROR_REPORTED"
    outcome_updated = update_reflection_log_outcome(task_id, log_status, summary)
    
    # Further actions based on result (e.g., create proposal, notify human) - TODO
    if status == "Error":
         logger.warning(f"Reflection task {task_id} reported an error: {summary}")
    elif status == "Done":
         logger.info(f"Reflection task {task_id} completed. Outcome: {summary}")
         # TODO: Trigger proposal generation if report suggests rule change?
         
    return outcome_updated # Return True if log was updated

# --- File Processing Dispatchers ---
def process_outbox_file(result_path: Path):
    """Identifies and routes result files from the supervisor outbox."""
    # Basic routing based on task ID prefix for now
    filename = result_path.name
    processed = False
    if filename.startswith("result_REFLECT-"):
        processed = process_reflection_result(result_path)
    # Add elif for other result types (e.g., from Writer, Overseer)
    else:
        logger.info(f"Ignoring non-reflection result file in outbox: {filename}")
        processed = True # Ignore but consider processed to move it
        
    return processed

# --- Main Loop --- #
def main_loop(poll_interval=10):
    """Continuously scans inbox and outbox, processing messages and results."""
    logger.info(f"Starting Supervisor Processor. Watching Inbox: {INBOX_DIR}, Outbox: {OUTBOX_DIR}")
    if not INBOX_DIR.is_dir() or not OUTBOX_DIR.is_dir():
        logger.error(f"Inbox ({INBOX_DIR}) or Outbox ({OUTBOX_DIR}) directory not found. Exiting.")
        return

    while True:
        inbox_processed_count = 0
        outbox_processed_count = 0
        
        # --- Process Inbox --- 
        logger.debug("Scanning inbox...")
        try:
            for item in INBOX_DIR.iterdir():
                if item.is_file():
                    success = process_inbox_file(item) # Use the renamed function
                    target_dir = PROCESSED_DIR if success else ERROR_DIR
                    try:
                        shutil.move(str(item), str(target_dir / item.name))
                        logger.debug(f"Moved inbox file {item.name} to {target_dir.name}")
                        inbox_processed_count += 1
                    except Exception as move_e:
                        logger.error(f"Failed to move inbox file {item.name}: {move_e}")
        except Exception as loop_e:
            logger.error(f"Error during inbox scan: {loop_e}", exc_info=True)
            
        # --- Process Outbox --- 
        logger.debug("Scanning outbox...")
        try:
            for item in OUTBOX_DIR.iterdir():
                if item.is_file():
                    success = process_outbox_file(item)
                    target_dir = OUTBOX_PROCESSED_DIR if success else OUTBOX_ERROR_DIR
                    try:
                        shutil.move(str(item), str(target_dir / item.name))
                        logger.debug(f"Moved outbox file {item.name} to {target_dir.name}")
                        outbox_processed_count += 1
                    except Exception as move_e:
                        logger.error(f"Failed to move outbox file {item.name}: {move_e}")
        except Exception as loop_e:
            logger.error(f"Error during outbox scan: {loop_e}", exc_info=True)

        # --- Sleep --- 
        if inbox_processed_count == 0 and outbox_processed_count == 0:
             logger.debug(f"No new messages/results found. Sleeping for {poll_interval} seconds.")
        time.sleep(poll_interval)

if __name__ == "__main__":
    # TODO: Add argument parsing for poll interval, directories, etc. if needed
    main_loop() 