"""Memory engine for governance and logging."""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from dreamforge.core import config

def log_event(event_type: str, source: str, details: Dict[str, Any]) -> None:
    """Log an event to the governance memory."""
    event = {
        "type": event_type,
        "source": source,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    
    _store_event(event)
    
def _store_event(event: Dict[str, Any]) -> None:
    """Store an event in the governance log."""
    log_file = os.path.join(config.LOGS_DIR, "governance.log")
    try:
        with open(log_file, 'a') as f:
            json.dump(event, f)
            f.write('\n')
    except Exception as e:
        print(f"Error storing event: {e}")
        
def get_events(event_type: Optional[str] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get events from the governance log."""
    log_file = os.path.join(config.LOGS_DIR, "governance.log")
    events = []
    
    try:
        if not os.path.exists(log_file):
            return events
            
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if _event_matches(event, event_type, source):
                        events.append(event)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading events: {e}")
        
    return events
    
def _event_matches(event: Dict[str, Any], event_type: Optional[str], source: Optional[str]) -> bool:
    """Check if an event matches the filter criteria."""
    if event_type and event.get('type') != event_type:
        return False
    if source and event.get('source') != source:
        return False
    return True
    
def clear_events() -> None:
    """Clear all events from the governance log."""
    log_file = os.path.join(config.LOGS_DIR, "governance.log")
    try:
        if os.path.exists(log_file):
            os.remove(log_file)
    except Exception as e:
        print(f"Error clearing events: {e}") 