import os
import sys
import json
import datetime
import copy

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # core/memory
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Constants ---
RUNTIME_DIR = os.path.join(project_root, 'runtime')
STATE_FILE_NAME = 'supervisor_state.json'
STATE_FILE_PATH = os.path.join(RUNTIME_DIR, STATE_FILE_NAME)

# --- Helper Functions ---
def _get_default_state():
    """Returns the default structure for a new state file."""
    return {
        "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "current_focus": {
            "purpose": "Initialization",
            "context_snippet": "System starting up.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        },
        "active_goals": [], # List of strings or dicts describing goals
        "agent_states": {}, # Dict mapping agent_id -> {status: str, active_task_id: str}
        "task_assignments": {}, # Dict mapping task_id -> {agent_id: str, status: str}
        "system_notes": [] # General supervisor notes or observations
    }

def _ensure_runtime_dir():
    """Creates the runtime directory if it doesn't exist."""
    if not os.path.exists(RUNTIME_DIR):
        try:
            os.makedirs(RUNTIME_DIR)
            print(f"[SupervisorMemory Info] Created runtime directory: {RUNTIME_DIR}")
        except OSError as e:
            print(f"[SupervisorMemory Error ❌] Failed to create runtime directory {RUNTIME_DIR}: {e}")
            raise # Re-raise if directory creation fails critically

# --- Core State Management Functions ---

def load_state() -> dict:
    """Loads the supervisor state from supervisor_state.json."""
    _ensure_runtime_dir()
    try:
        if not os.path.exists(STATE_FILE_PATH):
            print(f"[SupervisorMemory Info] State file not found at {STATE_FILE_PATH}. Creating default state.")
            default_state = _get_default_state()
            save_state(default_state) # Save the default state immediately
            return default_state
            
        with open(STATE_FILE_PATH, 'r', encoding='utf-8') as f:
            state = json.load(f)
        # print(f"[SupervisorMemory ✅] Loaded state from {STATE_FILE_PATH}") # Can be noisy
        return state
    except json.JSONDecodeError as e:
        print(f"[SupervisorMemory Error ❌] Failed to parse state file {STATE_FILE_PATH}: {e}. Returning default state.")
        return _get_default_state()
    except Exception as e:
        print(f"[SupervisorMemory Error ❌] Failed to load state from {STATE_FILE_PATH}: {e}. Returning default state.")
        return _get_default_state()

def save_state(state_data: dict):
    """Saves the provided state data to supervisor_state.json atomically."""
    _ensure_runtime_dir()
    # Add/update the last_updated timestamp automatically
    state_data['last_updated'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    temp_file_path = STATE_FILE_PATH + '.tmp'
    try:
        # Write to a temporary file first
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2) # Use indent for readability
        
        # Atomically rename the temporary file to the final file
        os.replace(temp_file_path, STATE_FILE_PATH)
        # print(f"[SupervisorMemory ✅] Saved state to {STATE_FILE_PATH}") # Can be noisy
        return True
    except Exception as e:
        print(f"[SupervisorMemory Error ❌] Failed to save state to {STATE_FILE_PATH}: {e}")
        # Attempt to clean up the temp file if it exists
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError:
                pass # Ignore cleanup errors
        return False

def update_state(changes: dict):
    """Loads the current state, applies changes, and saves it back."""
    current_state = load_state()
    # Use deep copy to avoid modifying the loaded state directly if update fails
    updated_state = copy.deepcopy(current_state)
    
    # Simple dictionary update (could be replaced with deep merge logic if needed)
    updated_state.update(changes)
    
    return save_state(updated_state)

def get_active_tasks() -> dict:
    """Retrieves the task_assignments dictionary from the current state."""
    state = load_state()
    return state.get('task_assignments', {})

def log_current_focus(purpose_str: str, context_snippet: str):
    """Updates the 'current_focus' field in the supervisor state."""
    focus_update = {
        "current_focus": {
            "purpose": purpose_str,
            "context_snippet": context_snippet,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }
    return update_state(focus_update)

# --- Example Usage (for testing if run directly) ---
if __name__ == "__main__":
    print("--- Testing Supervisor Memory --- (runtime/supervisor_state.json)")

    # 1. Initial Load (might create default)
    print("\n1. Loading initial state...")
    initial_state = load_state()
    print(f"   Initial state loaded (or created):\n{json.dumps(initial_state, indent=2)}")

    # 2. Log Focus
    print("\n2. Logging current focus...")
    log_success = log_current_focus("Testing Memory Module", "Running __main__ block.")
    if log_success:
        print("   Logged focus successfully.")
        updated_state_after_focus = load_state()
        print(f"   New focus: {updated_state_after_focus.get('current_focus')}")
    else:
        print("   Failed to log focus.")

    # 3. Update State (example: add a goal and agent state)
    print("\n3. Updating state with new goal and agent status...")
    update_changes = {
        "active_goals": ["Fully test supervisor memory"],
        "agent_states": {"SocialAgent": {"status": "idle", "active_task_id": None}}
    }
    update_success = update_state(update_changes)
    if update_success:
        print("   State updated successfully.")
        state_after_update = load_state()
        print(f"   New goals: {state_after_update.get('active_goals')}")
        print(f"   New agent states: {state_after_update.get('agent_states')}")
    else:
        print("   Failed to update state.")

    # 4. Get Active Tasks (might be empty initially)
    print("\n4. Getting active tasks...")
    active_tasks = get_active_tasks()
    print(f"   Current task assignments: {active_tasks}")

    print("\n--- Test Complete --- Check runtime/supervisor_state.json") 