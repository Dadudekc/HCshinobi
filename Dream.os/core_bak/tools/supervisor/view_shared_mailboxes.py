import json
import argparse
import time
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# --- Configuration ---
SHARED_MAILBOX_DIR = Path(__file__).parent.parent / "shared_mailboxes"
NUM_MAILBOXES = 8
DEFAULT_STALE_THRESHOLD_MINUTES = 5
DEFAULT_WATCH_INTERVAL_SECONDS = 5

# --- Safe JSON I/O Function (Embedded) ---
def load_json_safe(file_path: Path, default=None):
    """Safely load JSON from a file, handling errors."""
    try:
        with file_path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # This is expected if a mailbox file hasn't been created yet, treat as offline
        return default
    except json.JSONDecodeError:
        print(f"⚠️ Error: JSON decode error in file: {file_path}. Treating as invalid.", file=sys.stderr)
        return {"mailbox_id": file_path.stem, "status": "ERROR_INVALID_JSON"} # Return error status
    except Exception as e:
        print(f"⚠️ Error: Unexpected error loading JSON from {file_path}: {e}", file=sys.stderr)
        return {"mailbox_id": file_path.stem, "status": "ERROR_READING"} # Return error status

# --- Helper Functions ---
def parse_utc_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse ISO 8601 UTC timestamp string."""
    if not timestamp_str:
        return None
    try:
        # Handle potential Z suffix and different precision levels
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'
        return datetime.fromisoformat(timestamp_str).astimezone(timezone.utc)
    except ValueError:
        print(f"⚠️ Warning: Could not parse timestamp: {timestamp_str}", file=sys.stderr)
        return None

def format_time_delta(delta: timedelta) -> str:
    """Format timedelta into a human-readable string."""
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s ago"
    else:
        return f"{seconds // 3600}h {(seconds % 3600) // 60}m ago"

# --- Display Function ---
def display_mailbox_status(stale_threshold: timedelta):
    """Fetch status from all mailboxes and display them."""
    print("--- Shared Mailbox Status ---")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Stale Threshold: {stale_threshold.total_seconds() / 60:.1f} mins)")
    print("=" * 80)
    print(f"{'Mailbox':<12} {'Agent ID':<25} {'Status':<15} {'Pending Msgs':<15} {'Last Seen':<20}")
    print("-" * 80)

    now_utc = datetime.now(timezone.utc)
    active_agents = 0
    total_pending_msgs = 0

    for i in range(1, NUM_MAILBOXES + 1):
        mailbox_path = SHARED_MAILBOX_DIR / f"mailbox_{i}.json"
        data = load_json_safe(mailbox_path, default={})

        mailbox_id = data.get("mailbox_id", f"mailbox_{i}")
        agent_id = data.get("assigned_agent_id", "-")
        status = data.get("status", "offline")
        messages = data.get("messages", [])
        pending_msg_count = len(messages)
        last_seen_str = data.get("last_seen_utc", "-")
        last_seen_dt = parse_utc_timestamp(last_seen_str)

        stale = False
        time_ago_str = "-"
        if last_seen_dt:
            delta = now_utc - last_seen_dt
            time_ago_str = format_time_delta(delta)
            if status != "offline" and delta > stale_threshold:
                stale = True
                status += " (STALE!)"
        elif status != "offline": # Online but no valid timestamp?
             time_ago_str = "(No timestamp)"
             stale = True
             status += " (STALE!)"

        if status != "offline" and not status.startswith("ERROR"):
             active_agents += 1
        total_pending_msgs += pending_msg_count

        agent_id_str = agent_id if agent_id is not None else "-" # Ensure string for formatting

        # Basic color coding attempt (might not work on all terminals)
        color_start = '\033[91m' if stale else '\033[92m' if status == 'online' else '\033[93m' if status == 'busy' else '\033[0m'
        color_end = '\033[0m'

        print(f"{color_start}{mailbox_id:<12} {agent_id_str:<25} {status:<15} {pending_msg_count:<15} {time_ago_str:<20}{color_end}")

    print("=" * 80)
    print(f"Summary: {active_agents}/{NUM_MAILBOXES} Active Agents | {total_pending_msgs} Total Pending Messages")
    print("=" * 80)

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor the status of shared agent mailboxes.")
    parser.add_argument(
        "--stale-threshold",
        type=int,
        default=DEFAULT_STALE_THRESHOLD_MINUTES,
        help="Threshold in minutes after which an agent is considered stale."
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously monitor and refresh the status display."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_WATCH_INTERVAL_SECONDS,
        help="Refresh interval in seconds when using --watch."
    )
    parser.add_argument(
        "--mailbox-dir",
        default=str(SHARED_MAILBOX_DIR), # Use the configured default
        help="Path to the shared mailboxes directory."
    )

    args = parser.parse_args()

    # Use the parsed argument for the directory path
    mailbox_dir_path = Path(args.mailbox_dir).resolve()
    if not mailbox_dir_path.is_dir():
        print(f"❌ Error: Shared mailbox directory not found: {mailbox_dir_path}", file=sys.stderr)
        sys.exit(1)

    stale_delta = timedelta(minutes=args.stale_threshold)

    if args.watch:
        try:
            while True:
                # Clear screen (works on most terminals)
                print("\033[H\033[J", end="")
                display_mailbox_status(stale_delta)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nExiting watch mode.")
            sys.exit(0)
    else:
        display_mailbox_status(stale_delta) 