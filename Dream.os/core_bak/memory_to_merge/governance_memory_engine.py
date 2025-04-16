import os
import sys
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Configuration / Path Setup
# Assume this file is in core/memory/
CORE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = CORE_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"
GOVERNANCE_LOG_FILE = RUNTIME_DIR / "governance_memory.jsonl"
_SOURCE_ID = "GovernanceEngine"

# Ensure runtime directory exists on import (or first use)
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

def log_event(event_type: str, agent_source: str, details: dict):
    """Logs a structured governance event to the central log file.

    Args:
        event_type (str): The type of event (e.g., 'PROPOSAL_CREATED', 'REFLECTION_LOGGED', 'ENGINE_INFO').
        agent_source (str): The ID of the agent or system component generating the event (e.g., 'MetaArchitect', 'GovernanceEngine').
        details (dict): A dictionary containing event-specific information.
    """
    try:
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        event_id = f"event-{timestamp.split('T')[0].replace('-', '')}-{uuid.uuid4().hex[:6]}"

        event_data = {
            "event_id": event_id,
            "timestamp": timestamp,
            "event_type": event_type.upper(),
            "agent_source": agent_source,
            "details": details
        }

        # Ensure directory exists just before write, although it should exist from import
        GOVERNANCE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(GOVERNANCE_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event_data) + '\n')

        # Minimal print to console for confirmation, primary record is the file.
        # Avoid printing the log_event call itself for internal messages to prevent noise.
        if agent_source != _SOURCE_ID:
            # Use standard print or integrate with central logger if available later
            print(f"  [💾 GME] Logged event: {event_id} ({event_type}) by {agent_source}")
        return True

    except Exception as e:
        # Fallback to print for critical logging failure
        print(f"[CRITICAL - GME] Failed to write event to {GOVERNANCE_LOG_FILE}: {e}", file=sys.stderr)
        try:
            details_str = json.dumps(details) # Attempt to serialize details for error message
        except Exception:
            details_str = str(details)
        print(f"  Event Data Attempted: {{'event_type': '{event_type}', 'agent_source': '{agent_source}', 'details': {details_str}}}...", file=sys.stderr)
        return False

# --- Example Usage (for testing purposes) ---
if __name__ == "__main__":
    # Add project root to path for potential imports in details if needed for testing
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    print(f"Writing governance logs to: {GOVERNANCE_LOG_FILE}")

    log_event("ENGINE_INFO", _SOURCE_ID, {"message": "Testing Governance Memory Engine Logging..."})

    # Example 1: Proposal Creation
    log_event(
        event_type="PROPOSAL_CREATED",
        agent_source="MetaArchitect",
        details={
            "proposal_id": "ARCH-RULE-20250414-XYZ1",
            "origin_reflection_id": "alert-manual-test-001",
            "disposition": "DISAGREE_RULE",
            "target_rule_id": "UnknownRule",
            "reason": "Rule ambiguous based on reflection."
        }
    )

    # Example 2: Reflection Logged
    log_event(
        event_type="REFLECTION_LOGGED",
        agent_source="Agent2", # The agent who performed the reflection
        details={
            "reflection_timestamp": "2025-04-14T06:15:00.123Z", # From reflection log
            "alert_id": "alert-manual-test-001",
            "disposition": "DISAGREE_RULE",
            "justification": "Rule appears ambiguous or unclear based on reason provided."
        }
    )

    # Example 3: Human Decision
    log_event(
        event_type="PROPOSAL_ACCEPTED",
        agent_source="HumanInterface", # Or specific user ID
        details={
            "proposal_id": "ARCH-RULE-20250414-XYZ1",
            "decision_maker": "Victor",
            "comments": "Accepting proposal to clarify Rule GEN-001 ambiguity."
        }
    )

    log_event("ENGINE_INFO", _SOURCE_ID, {"message": f"Test complete. Check log file: {GOVERNANCE_LOG_FILE}"}) 