import os
import sys
import re
import json
import time
from datetime import datetime, timezone
from pathlib import Path # Use pathlib

# Determine project root assuming this file is in _agent_coordination/tools/
SCRIPT_DIR = Path(__file__).parent
AGENT_COORDINATION_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = AGENT_COORDINATION_DIR.parent

# Add project root to sys.path if not already present
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the governance logger from core/memory
try:
    from core.memory.governance_memory_engine import log_event
    gme_import_ok = True
except ImportError as e:
    print(f"[GCR] Error importing governance_memory_engine: {e}")
    gme_import_ok = False
    def log_event(*args, **kwargs): # Dummy function if import fails
        print("[GCR] FAKE log_event called (GME import failed)")

# Configuration
AGENT_ID = "gpt_command_router"
# Define paths using pathlib relative to project root
ANALYSIS_DIR = PROJECT_ROOT / "analysis"
RUNTIME_DIR = PROJECT_ROOT / "runtime" # Use runtime directory

# Ensure directories exist
ANALYSIS_DIR.mkdir(exist_ok=True)
RUNTIME_DIR.mkdir(exist_ok=True)

# Check for response in runtime first, then analysis as fallback?
# For now, assume response is generated elsewhere and placed in runtime
GPT_RESPONSE_FILE = RUNTIME_DIR / "latest_gpt_response.txt"
PROPOSAL_FILE = PROJECT_ROOT / "docs" / "rulebook_update_proposals.md" # Assume proposals moved to docs

# --- Regex Patterns for Commands ---
# Captures: 1=Command (ACCEPT/REJECT), 2=Proposal ID, 3=(Optional) Reason
COMMAND_REGEX = re.compile(r"\b(ACCEPT|REJECT)\s+proposal\s+([\w-]+)(?:\s+because\s+(.*))?", re.IGNORECASE)

# Regex to find a specific proposal block by ID
PROPOSAL_BLOCK_REGEX = r"(## Proposal ID:\s*{proposal_id}\s*.*?)(?=^## Proposal ID:|^\Z)"

def read_gpt_response():
    """Reads the content of the latest GPT response file."""
    if not GPT_RESPONSE_FILE.exists(): # Use Path object method
        print(f"[{AGENT_ID}] Error: GPT response file not found: {GPT_RESPONSE_FILE}")
        return None
    try:
        return GPT_RESPONSE_FILE.read_text(encoding='utf-8') # Use Path object method
    except Exception as e:
        print(f"[{AGENT_ID}] Error reading GPT response file {GPT_RESPONSE_FILE}: {e}")
        return None

def parse_commands(response_text):
    """Parses the response text to find ACCEPT/REJECT commands."""
    commands = []
    if not response_text:
        return commands

    for match in COMMAND_REGEX.finditer(response_text):
        command = match.group(1).upper()
        proposal_id = match.group(2)
        reason = match.group(3).strip() if match.group(3) else None
        commands.append({
            "command": command,
            "proposal_id": proposal_id,
            "reason": reason
        })
        print(f"[{AGENT_ID}] Parsed command: {command} proposal {proposal_id}" + (f" (Reason: {reason[:50]}...)" if reason else ""))

    if not commands:
        log_event(
            event_type="GPT_RESPONSE_NO_COMMANDS",
            agent_source=AGENT_ID,
            details={
                "reason": "No structured commands found in LLM response.",
                "response_file": str(GPT_RESPONSE_FILE),
                "full_response_snippet": response_text[:500] + ("..." if len(response_text) > 500 else "")
            }
        )

    return commands

def update_proposal_status(proposal_id, new_status, reason=None):
    """Updates the status of a specific proposal in the proposals file."""
    print(f"[{AGENT_ID}] Attempting to update status for proposal {proposal_id} to {new_status}...")
    if not PROPOSAL_FILE.exists():
        print(f"[{AGENT_ID}] Error: Proposal file not found: {PROPOSAL_FILE}. Cannot update status.")
        return False

    try:
        content = PROPOSAL_FILE.read_text(encoding='utf-8')

        # Dynamically create regex for the specific proposal block
        block_regex = re.compile(PROPOSAL_BLOCK_REGEX.format(proposal_id=re.escape(proposal_id)), re.DOTALL | re.MULTILINE)
        match = block_regex.search(content)

        if not match:
            print(f"[{AGENT_ID}] Error: Proposal ID {proposal_id} not found in {PROPOSAL_FILE}.")
            return False

        proposal_block = match.group(1)
        start_index = match.start(1)
        end_index = match.end(1)

        # Find the status line and update it
        status_line_regex = re.compile(r"(\*\*Status:\*\*\s*)(.*?)\n", re.IGNORECASE)
        updated_block, num_replacements = status_line_regex.subn(f"\g<1>{new_status}\n", proposal_block)

        if num_replacements == 0:
            print(f"[{AGENT_ID}] Warning: Could not find '**Status:**' line in proposal block for {proposal_id}. Cannot update.")
            return False

        # Add reason if provided
        if reason:
            updated_block = updated_block.rstrip() + f"\n**Decision Rationale:** {reason}"
            if not updated_block.strip().endswith("---"):
                updated_block = updated_block.strip() + "\n---"
            updated_block += "\n"

        new_content = content[:start_index] + updated_block + content[end_index:]

        # Rewrite the file
        PROPOSAL_FILE.write_text(new_content, encoding='utf-8')

        print(f"[{AGENT_ID}] Successfully updated status for proposal {proposal_id} to {new_status}.")
        return True

    except Exception as e:
        print(f"[{AGENT_ID}] Error updating proposal file {PROPOSAL_FILE}: {e}")
        return False

def execute_command(command_data):
    """Executes a parsed command."""
    command = command_data['command']
    proposal_id = command_data['proposal_id']
    reason = command_data.get('reason')

    new_status = "Unknown"
    log_event_type = "COMMAND_EXECUTED" # Default

    if command == "ACCEPT":
        new_status = "Accepted"
        log_event_type = "PROPOSAL_ACCEPTED"
    elif command == "REJECT":
        new_status = "Rejected"
        log_event_type = "PROPOSAL_REJECTED"
    else:
        print(f"[{AGENT_ID}] Warning: Unsupported command '{command}'. Skipping.")
        return

    # Update the proposal file
    success = update_proposal_status(proposal_id, new_status, reason)

    # Log the outcome to governance memory
    if success:
        log_event(
            event_type=log_event_type,
            agent_source="ChatGPT via " + AGENT_ID, # Indicate source
            details={
                "proposal_id": proposal_id,
                "decision_source": "ChatGPT",
                "reason": reason if reason else "N/A"
            }
        )
    else:
        log_event(
            event_type="COMMAND_EXECUTION_FAILED",
            agent_source=AGENT_ID,
            details={
                "command": command,
                "proposal_id": proposal_id,
                "reason": f"Failed to update status in {PROPOSAL_FILE}"
            }
        )

def main():
    if not gme_import_ok:
        print(f"[{AGENT_ID}] Cannot proceed due to missing governance_memory_engine import. Exiting.")
        sys.exit(1)
    print(f"\n[🤖] Starting {AGENT_ID}...")

    response_text = read_gpt_response()
    if not response_text:
        print(f"[{AGENT_ID}] No response found or error reading file. Exiting.")
        return

    print(f"[{AGENT_ID}] Processing response (length: {len(response_text)} chars)...")
    commands = parse_commands(response_text)

    if not commands:
        print(f"[{AGENT_ID}] No actionable commands extracted.")
    else:
        print(f"[{AGENT_ID}] Executing {len(commands)} parsed command(s)...")
        for cmd_data in commands:
            execute_command(cmd_data)
            time.sleep(0.5) # Small delay between actions

    print(f"[🏁] {AGENT_ID} finished.")

if __name__ == "__main__":
    main() 