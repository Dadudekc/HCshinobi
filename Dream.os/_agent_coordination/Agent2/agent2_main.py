# Agent2/agent2_main.py

import os
import json
import logging
import time
import shutil
from pathlib import Path
from datetime import datetime
import re # Keep re for rulebook parsing

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Agent2")

# --- Configuration ---
AGENT_NAME = "Agent2"
AGENT_DIR = Path("_agent_coordination") / AGENT_NAME
INBOX_DIR = AGENT_DIR / "inbox"
OUTBOX_DIR = AGENT_DIR / "outbox"
PROCESSED_DIR = AGENT_DIR / "inbox_processed"
ERROR_DIR = AGENT_DIR / "inbox_errors"
SUPERVISOR_OUTBOX = Path("_agent_coordination/Agent1/outbox") # Where to put results
RULEBOOK_PATH = Path("_agent_coordination/Agent1/rulebook.md") # Location of rulebook
RESULT_FORMAT = ".json" # Standardizing output format

# Ensure directories exist
INBOX_DIR.mkdir(parents=True, exist_ok=True)
OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
ERROR_DIR.mkdir(parents=True, exist_ok=True)
SUPERVISOR_OUTBOX.mkdir(parents=True, exist_ok=True) # Ensure supervisor outbox exists

# --- Reflection Processing Functionality (NEW) ---
def read_rulebook(rule_id=None):
    """Reads the rulebook, optionally filtering for a specific rule ID."""
    try:
        content = RULEBOOK_PATH.read_text(encoding='utf-8')
        if rule_id:
            # Basic search for rule block - enhance parsing if needed
            rule_match = re.search(rf"### Rule \S+:.*?\n- \*\*ID:\*\* {re.escape(rule_id)}\n([\s\S]*?)(?:\n### |\Z)", content)
            return rule_match.group(0) if rule_match else f"Rule {rule_id} not found."
        return content
    except FileNotFoundError:
        logger.error(f"Rulebook not found at {RULEBOOK_PATH}")
        return "Error: Rulebook not found."
    except Exception as e:
        logger.error(f"Error reading rulebook: {e}")
        return f"Error reading rulebook: {e}"

def generate_reflection_report(task_data):
    """Analyzes alert details and generates a reflection report text."""
    details = task_data.get("details", {})
    alert_id = details.get("alert_id", "Unknown Alert")
    violating_agent = details.get("violating_agent", "Unknown Agent")
    violated_rule = details.get("violated_rule", "Unknown Rule")
    alert_context = details.get("alert_context", "No context provided.")
    
    logger.info(f"Generating reflection report for Task: {task_data.get('task_id')}, Alert: {alert_id}")
    
    # 1. Consult Rulebook
    rule_text = read_rulebook(violated_rule)
    
    # 2. Analyze Context (Simple analysis for now)
    analysis = f"Analysis of alert context suggests the agent [{violating_agent}] halted unexpectedly. "
    if "unnecessary" in alert_context.lower():
        analysis += "The alert explicitly mentions the halt might be unnecessary according to rules. "
    analysis += f"Rule {violated_rule} emphasizes continuous operation unless explicitly allowed. "
    
    # 3. Formulate Reflection / Suggestions
    suggestions = ""
    suggestions += "1. **Potential Cause:** Agent logic might lack proper error handling or state management, leading to unexpected termination instead of recovery or escalation.\n"
    suggestions += "2. **Potential Fix:** Review and enhance error handling in the violating agent. Ensure fallback mechanisms exist.\n"
    if "unnecessary" in alert_context.lower():
        suggestions += "3. **Rule Clarification:** Rule {violated_rule} seems clear, but perhaps agent onboarding needs to emphasize GEN-002 (Proactive Problem Solving) more strongly.\n"
    else:
        suggestions += "3. **Rule Clarification:** If the halt *was* necessary but triggered the alert, the monitoring logic or Rule {violated_rule} itself might need refinement to define acceptable halting conditions more precisely.\n"
        
    # 4. Construct Report
    report = f"""# Reflection Report: {task_data.get('task_id')}

**Alert ID:** {alert_id}
**Violating Agent:** {violating_agent}
**Violated Rule:** {violated_rule}
**Timestamp:** {datetime.now().isoformat() + "Z"}

## Alert Context Summary:
```
{alert_context}
```

## Relevant Rule ({violated_rule}):
```
{rule_text}
```

## Analysis:
{analysis}

## Suggestions / Potential Actions:
{suggestions}
"""
    return report

def write_result_to_supervisor_outbox(task_id, status, summary, report_content_md=None):
    """Writes the task result as JSON to Agent 1's outbox."""
    result_filename = f"result_{task_id}_from_{AGENT_NAME}_{datetime.now().strftime('%Y%m%d%H%M%S')}{RESULT_FORMAT}"
    result_path = SUPERVISOR_OUTBOX / result_filename
    
    # Construct JSON payload according to expected schema
    result_data = {
        "type": "reflection_result", # Explicit type
        "task_id": task_id,
        "status": status,
        "agent_name": AGENT_NAME,
        "timestamp": datetime.now().isoformat() + "Z",
        "result_summary": summary,
        "error_details": summary if status == "Error" else None, # Include summary as error detail if Error
        "report_markdown": report_content_md # Include full report optionally
    }
        
    try:
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2)
        logger.info(f"Wrote JSON result for task {task_id} to Supervisor outbox: {result_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write JSON result for task {task_id} to Supervisor outbox: {e}")
        return False

def process_reflection_request(message_path, message_data):
    """Handles tasks of type 'reflection_request'."""
    task_id = message_data.get("task_id", f"UNKNOWN_TASK_{message_path.stem}")
    logger.info(f"Processing Reflection Request Task: {task_id}")
    
    report_content_md = None # Initialize
    try:
        report_content_md = generate_reflection_report(message_data)
        summary = f"Generated reflection report for Alert {message_data.get('details', {}).get('alert_id', '?')} regarding Rule {message_data.get('details', {}).get('violated_rule', '?')}."
        success = write_result_to_supervisor_outbox(task_id, "Done", summary, report_content_md)
        return success
    except Exception as e:
        error_summary = f"Failed to generate reflection report: {e}"
        logger.error(f"Error processing reflection request {task_id}: {e}", exc_info=True)
        # Write error status to outbox as JSON
        write_result_to_supervisor_outbox(task_id, "Error", error_summary)
        return False # Indicate failure

# --- Generic Message Handling ---
def process_message_file(message_path: Path):
    """Reads, parses, and routes a message file for processing."""
    try:
        logger.debug(f"Agent 2 attempting to process message: {message_path.name}")
        content = message_path.read_text(encoding='utf-8')
        data = json.loads(content) # Assuming JSON task files
        
        message_type = data.get("type", "unknown").lower()
        processed = False
        if message_type == "reflection_request":
            processed = process_reflection_request(message_path, data)
        # Add elif for other task types Agent 2 might handle
        else:
            logger.warning(f"Agent 2 received unknown task type '{message_type}' in {message_path.name}")
            # Write basic status back?
            error_summary = f"Agent 2 cannot handle task type: {message_type}"
            write_result_to_supervisor_outbox(data.get('task_id', message_path.stem), "Error", error_summary)
            processed = False # Considered error for now
        
        return processed

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Agent 2 inbox file {message_path.name}: {e}")
        return False # Processing failed
    except Exception as e:
        logger.error(f"Error processing Agent 2 inbox file {message_path.name}: {e}", exc_info=True)
        return False # Processing failed

# --- Main Loop --- #
def agent2_main_loop(poll_interval=15):
    """Agent 2's main operational loop."""
    logger.info(f"Starting {AGENT_NAME}. Watching inbox: {INBOX_DIR}")
    while True:
        logger.debug("Agent 2 scanning inbox...")
        processed_a_file = False
        try:
            for item in INBOX_DIR.iterdir():
                if item.is_file() and item.suffix.lower() == '.json': # Only process .json
                    success = process_message_file(item)
                    target_dir = PROCESSED_DIR if success else ERROR_DIR
                    try:
                        shutil.move(str(item), str(target_dir / item.name))
                        logger.debug(f"Agent 2 moved {item.name} to {target_dir.name}")
                        processed_a_file = True
                    except Exception as move_e:
                        logger.error(f"Agent 2 failed to move file {item.name}: {move_e}")
                elif item.is_file():
                     logger.warning(f"Agent 2 found non-JSON file in inbox: {item.name}. Ignoring.")
                     # Optionally move non-JSON files elsewhere
                     # shutil.move(str(item), str(ERROR_DIR / item.name))
        except Exception as loop_e:
            logger.error(f"Error during Agent 2 inbox scan: {loop_e}", exc_info=True)

        if not processed_a_file:
            logger.debug(f"Agent 2: No new messages. Sleeping for {poll_interval} seconds.")
        time.sleep(poll_interval)

if __name__ == "__main__":
    # Basic execution - can be enhanced with args
    agent2_main_loop() 