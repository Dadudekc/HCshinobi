import os
import sys
import json

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tools/
project_root = os.path.abspath(os.path.join(script_dir, '..')) 
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Import Governance Logger ---
try:
    from core.memory.governance_memory_engine import log_event
except ImportError:
    # Fallback dummy logger
    def log_event(event_type, source, details):
        print(f"[Dummy Logger - ChatCursorBridge] Event: {event_type}, Source: {source}, Details: {details}")
        return False
# ------------------------------

# Define source for logging
_SOURCE = "ChatCursorBridge"

def write_to_cursor_input(text: str):
    """Writes the given text to the designated input file for Cursor."""
    path = "temp/cursor_input.txt"
    log_context = {"path": path}
    try:
        # Ensure the temp directory exists (though created separately, good practice)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        # print(f"[Bridge 📤] Prompt written to {path}")
        log_event("BRIDGE_WRITE_SUCCESS", _SOURCE, {**log_context, "message": "Prompt written to input file"})
        return True
    except Exception as e:
        # print(f"[Bridge Error ❌] Failed to write to {path}: {e}")
        log_event("BRIDGE_WRITE_ERROR", _SOURCE, {**log_context, "error": "Failed to write to input file", "details": str(e)})
        return False

def read_from_cursor_output():
    """Reads and parses JSON from the designated output file written by Cursor."""
    path = "temp/cursor_output.json"
    log_context = {"path": path}
    if not os.path.exists(path):
        # print(f"[Bridge ⏳] Waiting for output at {path}...") # This indicates waiting, maybe not an event?
        log_event("BRIDGE_READ_WAITING", _SOURCE, {**log_context, "message": "Output file not found yet"})
        return None # Return None if file doesn't exist
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = json.load(f)
        # print(f"[Bridge 📥] Parsed JSON from {path}")
        log_event("BRIDGE_READ_SUCCESS", _SOURCE, {**log_context, "message": "Parsed JSON from output file"})
        # Optional: Delete or archive the file after reading?
        # os.remove(path)
        return content
    except json.JSONDecodeError as e:
        # print(f"[Bridge Error ❌] Failed to parse JSON from {path}: {e}")
        log_event("BRIDGE_READ_ERROR", _SOURCE, {**log_context, "error": "Failed to parse JSON from output file", "details": str(e)})
        return None
    except Exception as e:
        # print(f"[Bridge Error ❌] Error reading {path}: {e}")
        log_event("BRIDGE_READ_ERROR", _SOURCE, {**log_context, "error": "Error reading output file", "details": str(e)})
        return None 