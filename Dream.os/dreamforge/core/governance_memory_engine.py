import os
import json
import uuid
from datetime import datetime, timezone
import sys # Added for path correction

# Configuration
RUNTIME_DIR_NAME = "runtime"
# PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
# Corrected path: Go up two levels from dreamforge/core/ to get project root
script_dir = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, '..', '..'))

GOVERNANCE_LOG_FILE = os.path.join(PROJECT_ROOT, RUNTIME_DIR_NAME, "governance_memory.jsonl")
_SOURCE_ID = "GovernanceEngine"

def log_event(event_type: str, data: dict, source: str = _SOURCE_ID) -> bool:
    """
    Log an event to the governance memory system.
    
    Args:
        event_type (str): Type of event being logged
        data (dict): Event data/payload
        source (str): Source system/component generating the event
        
    Returns:
        bool: True if logging succeeded, False otherwise
    """
    try:
        # Ensure runtime directory exists
        os.makedirs(os.path.dirname(GOVERNANCE_LOG_FILE), exist_ok=True)
        
        event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "source": source,
            "data": data
        }
        
        with open(GOVERNANCE_LOG_FILE, "a") as f:
            json.dump(event, f)
            f.write("\n")
        return True
        
    except Exception as e:
        print(f"Error logging event: {e}", file=sys.stderr)
        return False

def get_events(event_type: str = None, source: str = None, limit: int = 100) -> list:
    """
    Retrieve events from the governance memory system.
    
    Args:
        event_type (str, optional): Filter by event type
        source (str, optional): Filter by source
        limit (int): Maximum number of events to return
        
    Returns:
        list: List of matching events
    """
    try:
        if not os.path.exists(GOVERNANCE_LOG_FILE):
            return []
            
        events = []
        with open(GOVERNANCE_LOG_FILE, "r") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event_type and event["type"] != event_type:
                        continue
                    if source and event["source"] != source:
                        continue
                    events.append(event)
                    if len(events) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
                    
        return events
        
    except Exception as e:
        print(f"Error retrieving events: {e}", file=sys.stderr)
        return []

# ... (rest of governance_memory_engine.py remains the same) ... 