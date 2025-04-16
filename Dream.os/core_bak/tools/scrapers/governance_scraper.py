import os
import json
import glob
import re
from datetime import datetime, timezone, timedelta

# Configuration
# Define paths relative to project root (assuming script is run from root or core/)
if os.path.basename(os.path.dirname(__file__)) == 'core':
     PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
else:
     PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__)) # Assume run from root if not in core/

RUNTIME_DIR_NAME = "runtime"
ANALYSIS_DIR_NAME = "analysis"

RUNTIME_DIR = os.path.join(PROJECT_ROOT, RUNTIME_DIR_NAME)
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, ANALYSIS_DIR_NAME)

# Updated paths using the new structure
GOVERNANCE_LOG_FILE = os.path.join(RUNTIME_DIR, "governance_memory.jsonl")
RULEBOOK_PATH = os.path.join(RUNTIME_DIR, "rulebook.md")
PROPOSAL_FILE = os.path.join(ANALYSIS_DIR, "rulebook_update_proposals.md")
REFLECTION_LOG_PATTERN = os.path.join(RUNTIME_DIR, "*", "reflection", "reflection_log.md") # Scan within runtime

# How far back to look for recent items in summaries
RECENT_HOURS = 72
MAX_LOG_LINES = 20 # Max governance log lines to include
MAX_REFLECTIONS = 10 # Max reflection entries to include
MAX_PROPOSALS = 10   # Max proposals to include

def load_recent_governance_events(max_lines=MAX_LOG_LINES):
    """Loads the last N events from the governance log."""
    events = []
    if not os.path.exists(GOVERNANCE_LOG_FILE):
        return events
    try:
        with open(GOVERNANCE_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Take the last max_lines
        recent_lines = lines[-max_lines:]
        for line in recent_lines:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"[GS] Warning: Skipping invalid JSON line in governance log.")
        return events
    except Exception as e:
        print(f"[GS] Error loading governance log: {e}")
        return []

def load_recent_reflections(max_reflections=MAX_REFLECTIONS):
    """Loads recent reflection entries from all agent reflection logs."""
    reflections = []
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(hours=RECENT_HOURS)

    reflection_files = glob.glob(REFLECTION_LOG_PATTERN)
    for log_file in reflection_files:
        try:
            agent_id = os.path.basename(os.path.dirname(os.path.dirname(log_file)))
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            # Split into entries based on '---'
            entries = content.split('---')
            for entry in entries:
                if not entry.strip(): continue
                # Attempt to parse timestamp and check recency
                ts_match = re.search(r'\*\*Reflection Timestamp:\*\*\s*(.*?)(?:Z)?\n', entry, re.IGNORECASE)
                entry_time = None
                if ts_match:
                    try:
                        entry_time = datetime.fromisoformat(ts_match.group(1).strip().replace('Z', '+00:00'))
                        if not entry_time.tzinfo: entry_time = entry_time.replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass # Ignore entries with unparseable timestamps

                # Add if recent (or if timestamp parsing failed, include anyway up to limit)
                if entry_time is None or entry_time >= time_limit:
                    # Extract key info for summary (simplified)
                    alert_id_match = re.search(r'\*\*Alert ID:\*\*\s*(.*?)\n', entry, re.IGNORECASE)
                    disposition_match = re.search(r'\*\*Disposition:\*\*\s*(.*?)\n', entry, re.IGNORECASE)
                    justification_match = re.search(r'\*\*Justification:\*\*\s*(.*?)\n', entry, re.IGNORECASE)

                    reflections.append({
                        "agent_id": agent_id,
                        "timestamp": ts_match.group(1).strip() if ts_match else "Unknown",
                        "alert_id": alert_id_match.group(1).strip() if alert_id_match else "Unknown",
                        "disposition": disposition_match.group(1).strip() if disposition_match else "Unknown",
                        "justification": justification_match.group(1).strip() if justification_match else "N/A",
                    })
        except Exception as e:
            print(f"[GS] Warning: Failed to read or parse reflection log {log_file}: {e}")

    # Sort by timestamp (best effort, string sort if format varies) and take most recent
    try:
        reflections.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception:
        pass # Ignore sorting errors if timestamps are inconsistent

    return reflections[:max_reflections]

def load_proposals(status_filter="Proposed", max_proposals=MAX_PROPOSALS):
    """Loads proposals from the proposal file, optionally filtering by status."""
    proposals = []
    if not os.path.exists(PROPOSAL_FILE):
        return proposals
    try:
        with open(PROPOSAL_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        proposal_regex = re.compile(r"(## Proposal ID:.*?)(?=^## Proposal ID:|^\Z)", re.DOTALL | re.MULTILINE)
        status_regex = re.compile(r"\*\*Status:\*\*\s*(.*?)\n", re.IGNORECASE)
        id_regex = re.compile(r"## Proposal ID:\s*(.*?)\n")
        type_regex = re.compile(r"\*\*Type:\*\*\s*(.*?)\n", re.IGNORECASE)
        rationale_regex = re.compile(r"\*\*Rationale:\*\*\s*(.*?)(?=\n\*\*|$)", re.DOTALL | re.IGNORECASE)

        for match in proposal_regex.finditer(content):
            proposal_block = match.group(1).strip()
            status_match = status_regex.search(proposal_block)
            status = status_match.group(1).strip() if status_match else "Unknown"

            if status_filter is None or status.lower() == status_filter.lower():
                id_match = id_regex.search(proposal_block)
                type_match = type_regex.search(proposal_block)
                rationale_match = rationale_regex.search(proposal_block)
                rationale_text = rationale_match.group(1).strip().replace('\n', ' ') if rationale_match else "N/A"
                proposals.append({
                    "id": id_match.group(1).strip() if id_match else "Unknown",
                    "status": status,
                    "type": type_match.group(1).strip() if type_match else "Unknown",
                    "rationale": rationale_text[:150] + ("..." if len(rationale_text) > 150 else "") # Snippet for prompt
                })
        return proposals[-max_proposals:]
    except Exception as e:
        print(f"[GS] Error loading proposals: {e}")
        return []

def get_rulebook_summary():
    """Returns a string summary of the rulebook status."""
    if not os.path.exists(RULEBOOK_PATH):
        return "- Rulebook file not found."
    try:
        with open(RULEBOOK_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        # Simple count of rule definitions (adjust regex if format changes)
        rule_count = len(re.findall(r'^### Rule:', content, re.MULTILINE))
        general_rule_count = len(re.findall(r'^### Rule \d+:', content, re.MULTILINE))
        # Count applied rules more reliably
        applied_rule_count = content.count("# --- AUTO-APPLIED RULE ---")
        return f"- Rulebook Status: Contains approx. {rule_count + general_rule_count} core rules and {applied_rule_count} auto-applied rules."
    except Exception as e:
        print(f"[GS] Error reading rulebook: {e}")
        return "- Error reading rulebook."

def generate_governance_data():
    """Generates a dictionary containing the raw governance state data."""
    print("\n[📊] Gathering Governance State Data...")

    data = {
        "rulebook_summary": get_rulebook_summary(),
        "open_proposals": load_proposals(status_filter="Proposed"),
        "recent_reflections": load_recent_reflections(),
        "recent_events": load_recent_governance_events(),
        # Pass config values needed by template
        "recent_hours": RECENT_HOURS,
        "max_log_lines": MAX_LOG_LINES
    }

    print("[🏁] Governance Data Gathered.")
    # print(json.dumps(data, indent=2)) # Optional: Debug print
    return data

# --- Example Usage (Updated path for temp file) --- 
if __name__ == "__main__":
    governance_data = generate_governance_data()
    print("\n--- Gathered Data --- ")
    # Print keys and number of items for verification
    for key, value in governance_data.items():
        if isinstance(value, list):
            print(f"- {key}: {len(value)} items")
        else:
            print(f"- {key}: Provided")

    # Save data to a temporary file for template engine test
    temp_data_file = os.path.join(ANALYSIS_DIR_NAME, "temp_governance_data.json") # Place in analysis dir
    try:
        os.makedirs(os.path.dirname(temp_data_file), exist_ok=True)
        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(governance_data, f, indent=2) # Use indent for readability if needed
        print(f"\n[💾] Governance data saved to {temp_data_file}")
    except Exception as e:
        print(f"\n[❌] Failed to save temporary data file: {e}")

    # Example of how dispatcher would use it (requires template engine)
    # from template_engine import render_template # Assuming this exists
    # try:
    #     prompt = render_template("chatgpt_governance.md.j2", governance_data)
    #     print("\n--- Rendered Prompt Snippet ---")
    #     print(prompt[:500] + "...")
    # except Exception as e:
    #     print(f"\nError rendering template: {e}") 