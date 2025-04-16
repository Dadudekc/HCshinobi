import argparse
import json
import os
import sys
from datetime import datetime

# --- Add project root to sys.path ---
# This assumes the script is in tools/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Core Service Import ---
try:
    from core.memory.supervisor_memory import load_state
except ImportError as e:
    print(f"[StateViewer Error ❌] Failed to import supervisor_memory: {e}")
    print("Please ensure core/memory/supervisor_memory.py exists and is accessible.")
    sys.exit(1)

# --- Formatting Functions ---
def print_raw_json(state):
    """Prints the raw state dictionary as JSON."""
    print(json.dumps(state, indent=2))

def print_focus(state):
    """Prints the current_focus block prettily."""
    focus = state.get('current_focus', {})
    print("--- Current Focus ---")
    print(f"  Purpose: {focus.get('purpose', 'N/A')}")
    print(f"  Context: {focus.get('context_snippet', 'N/A')}")
    print(f"  Timestamp: {focus.get('timestamp', 'N/A')}")
    print("---------------------")

def print_summary(state):
    """Prints a human-readable summary of the state."""
    print(f"--- Supervisor State Summary (Last Updated: {state.get('last_updated', 'N/A')}) ---")

    # Focus
    focus = state.get('current_focus', {})
    print("\n[Current Focus]")
    print(f"  Purpose: {focus.get('purpose', 'N/A')}")
    print(f"  Context: {focus.get('context_snippet', 'N/A')}")

    # Goals
    goals = state.get('active_goals', [])
    print("\n[Active Goals]")
    if goals:
        for i, goal in enumerate(goals):
            print(f"  {i+1}. {goal}")
    else:
        print("  (No active goals)")

    # Agent States
    agent_states = state.get('agent_states', {})
    print("\n[Agent States]")
    if agent_states:
        # Basic table formatting
        print("  {:<15} {:<15} {:<20}".format('Agent ID', 'Status', 'Active Task ID'))
        print("  " + "-"*50)
        for agent_id, data in agent_states.items():
            status = data.get('status', 'N/A')
            task_id = data.get('active_task_id', 'None')
            print("  {:<15} {:<15} {:<20}".format(agent_id, status, str(task_id)))
    else:
        print("  (No agent states tracked)")

    # Task Assignments
    task_assignments = state.get('task_assignments', {})
    print("\n[Task Assignments]")
    if task_assignments:
        # Basic table formatting
        print("  {:<20} {:<15} {:<15}".format('Task ID', 'Agent ID', 'Status'))
        print("  " + "-"*50)
        for task_id, data in task_assignments.items():
            agent_id = data.get('agent_id', 'N/A')
            status = data.get('status', 'N/A')
            print("  {:<20} {:<15} {:<15}".format(task_id, agent_id, status))
    else:
        print("  (No task assignments tracked)")

    # System Notes
    notes = state.get('system_notes', [])
    print("\n[System Notes]")
    if notes:
        for i, note in enumerate(notes):
            print(f"  - {note}")
    else:
        print("  (No system notes)")

    print("\n-------------------------------------------------------------")

# --- Main Execution ---
def main():
    parser = argparse.ArgumentParser(description="View the Dream.OS Supervisor state.")
    parser.add_argument("--json", action="store_true", help="Output the raw state as JSON.")
    parser.add_argument("--focus", action="store_true", help="Output only the current focus block.")
    parser.add_argument("--summary", action="store_true", help="Output a human-readable summary (default behavior if no other flag set).")

    args = parser.parse_args()

    # Determine display mode
    display_mode = 'summary' # Default
    if args.json:
        display_mode = 'json'
    elif args.focus:
        display_mode = 'focus'
    # If no flags were set, argparse defaults summary to False unless we handle it
    # If only specific flags are false, it implies summary is desired.
    if not args.json and not args.focus and not args.summary:
        display_mode = 'summary' # Explicitly set default if no flags provided

    # Load the state
    state = load_state()
    if not state:
        print("[StateViewer Error ❌] Failed to load state. Exiting.")
        sys.exit(1)

    # Print based on determined mode
    if display_mode == 'json':
        print_raw_json(state)
    elif display_mode == 'focus':
        print_focus(state)
    else: # Default to summary
         print_summary(state)

if __name__ == "__main__":
    main() 