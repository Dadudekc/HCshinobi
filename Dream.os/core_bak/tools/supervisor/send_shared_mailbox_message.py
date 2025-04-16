import json
import argparse
import time
import uuid
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# --- Configuration ---
DEFAULT_SHARED_MAILBOX_DIR = Path(__file__).parent.parent / "shared_mailboxes"
NUM_MAILBOXES = 8

# --- Safe JSON I/O Functions (Embedded) ---
def load_json_safe(file_path: Path, default=None):
    """Safely load JSON from a file, handling errors."""
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Warning: File not found: {file_path}", file=sys.stderr)
        return default
    except json.JSONDecodeError:
        print(f"⚠️ Error: JSON decode error in file: {file_path}. Returning default.", file=sys.stderr)
        return default
    except Exception as e:
        print(f"⚠️ Error: Unexpected error loading JSON from {file_path}: {e}", file=sys.stderr)
        return default

def write_json_safe(file_path: Path, data: dict):
    """Safely write JSON data to a file using a temporary file and rename."""
    temp_file_path = file_path.with_suffix(f".{uuid.uuid4()}.tmp")
    try:
        with temp_file_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file_path, file_path)
        return True
    except Exception as e:
        print(f"❌ Error writing JSON safely to {file_path}: {e}", file=sys.stderr)
        if temp_file_path.exists():
            try: temp_file_path.unlink()
            except OSError: pass
        return False

# --- Core Logic ---
def find_agent_mailbox(agent_id: str, mailbox_dir: Path) -> Path | None:
    """Scan mailboxes to find the one assigned to the target agent."""
    for i in range(1, NUM_MAILBOXES + 1):
        mailbox_path = mailbox_dir / f"mailbox_{i}.json"
        data = load_json_safe(mailbox_path)
        if data and data.get("assigned_agent_id") == agent_id:
            return mailbox_path
    return None

def inject_message(
    agent_id: str,
    command: str,
    params: dict,
    mailbox_dir: Path,
    sender_id: str = "SupervisorCLI",
    dry_run: bool = False,
    show_summary: bool = False
) -> bool:
    """Injects a message into the target agent's claimed mailbox."""

    target_mailbox_path = find_agent_mailbox(agent_id, mailbox_dir)

    if not target_mailbox_path:
        print(f"❌ Error: Agent '{agent_id}' does not appear to be assigned to any mailbox in {mailbox_dir}.", file=sys.stderr)
        return False

    # Read the current state of the target mailbox
    mailbox_data = load_json_safe(target_mailbox_path)
    if not mailbox_data:
        print(f"❌ Error: Could not read target mailbox file: {target_mailbox_path}", file=sys.stderr)
        return False

    # Validate agent assignment and status
    current_assigned_agent = mailbox_data.get("assigned_agent_id")
    if current_assigned_agent != agent_id:
        # This should ideally not happen if find_agent_mailbox worked, but double-check
        print(f"❌ Error: Mailbox {target_mailbox_path.name} is assigned to '{current_assigned_agent}', not '{agent_id}'. Race condition?", file=sys.stderr)
        return False
    
    current_status = mailbox_data.get("status", "unknown")
    if current_status == "offline" or current_status.startswith("ERROR"):
         print(f"❌ Error: Target agent '{agent_id}' in mailbox {target_mailbox_path.name} has status '{current_status}'. Cannot inject message.", file=sys.stderr)
         return False
    elif current_status != "online" and current_status != "idle" and current_status != "busy":
         print(f"⚠️ Warning: Target agent '{agent_id}' status is '{current_status}'. Proceeding, but agent might not process immediately.", file=sys.stderr)

    # Construct the new message
    new_message = {
        "message_id": str(uuid.uuid4()),
        "command": command,
        "params": params,
        "sender_agent_id": sender_id,
        "timestamp_sent_utc": datetime.now(timezone.utc).isoformat()
    }

    if dry_run:
        print("--- Dry Run --- Would inject the following message:")
        print(json.dumps(new_message, indent=2))
        print(f"Target Mailbox: {target_mailbox_path}")
        return True # Indicate success for dry run

    # Append the message
    if "messages" not in mailbox_data:
        mailbox_data["messages"] = []
    mailbox_data["messages"].append(new_message)

    # Write back safely
    print(f"Injecting message into {target_mailbox_path.name} for agent '{agent_id}'...")
    if write_json_safe(target_mailbox_path, mailbox_data):
        print("✅ Message injected successfully.")
        if show_summary:
            print("--- Injected Message Summary ---")
            print(json.dumps(new_message, indent=2))
            print(f"Target Mailbox: {target_mailbox_path}")
        return True
    else:
        print(f"❌ Error: Failed to write updated mailbox file: {target_mailbox_path}", file=sys.stderr)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inject a message into a shared agent mailbox.")
    parser.add_argument("--agent-id", required=True, help="Unique identifier of the target agent.")
    parser.add_argument("--command", required=True, help="The command the agent should handle.")
    parser.add_argument("--params-json", default="{}", help="JSON string or path to JSON file (prefixed with '@') for the command parameters.")
    parser.add_argument("--summary", action="store_true", help="Print a confirmation summary after injection.")
    parser.add_argument("--dry-run", action="store_true", help="Print the message that would be injected but do not modify files.")
    parser.add_argument("--mailbox-dir", default=str(DEFAULT_SHARED_MAILBOX_DIR), help="Path to the shared mailboxes directory.")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to inject the message.")
    parser.add_argument("--sender-id", default="SupervisorCLI", help="Identifier for the sender of this message.")

    args = parser.parse_args()

    mailbox_dir_path = Path(args.mailbox_dir).resolve()
    if not mailbox_dir_path.is_dir():
        print(f"❌ Error: Shared mailbox directory not found: {mailbox_dir_path}", file=sys.stderr)
        sys.exit(1)

    # Parse params
    params_data = {}
    if args.params_json:
        param_input = args.params_json
        if param_input.startswith('@'):
            param_file_path = Path(param_input[1:])
            if not param_file_path.is_file():
                print(f"❌ Error: Parameter file not found: {param_file_path}", file=sys.stderr)
                sys.exit(1)
            print(f"Loading parameters from file: {param_file_path}")
            params_data = load_json_safe(param_file_path, default=None)
            if params_data is None:
                 print(f"❌ Error: Failed to load or parse parameter file: {param_file_path}", file=sys.stderr)
                 sys.exit(1)
        else:
            try:
                params_data = json.loads(param_input)
            except json.JSONDecodeError as e:
                print(f"❌ Error: Invalid JSON string provided for --params-json: {e}", file=sys.stderr)
                sys.exit(1)

    # Inject message N times
    success_count = 0
    failure_count = 0
    for i in range(args.repeat):
        if args.repeat > 1:
            print(f"\n--- Injection {i+1}/{args.repeat} ---")
        
        success = inject_message(
            agent_id=args.agent_id,
            command=args.command,
            params=params_data,
            mailbox_dir=mailbox_dir_path,
            sender_id=args.sender_id,
            dry_run=args.dry_run,
            show_summary=args.summary
        )
        
        if success:
            success_count += 1
        else:
            failure_count += 1
        
        if args.repeat > 1 and i < args.repeat - 1:
            time.sleep(0.1) # Small delay between repeats

    print("\n--- Injection Complete ---")
    print(f"Total Injections Attempted: {args.repeat}")
    print(f"Successful: {success_count}")
    print(f"Failed:     {failure_count}")

    if failure_count > 0:
        sys.exit(1) # Exit with error code if any injections failed 