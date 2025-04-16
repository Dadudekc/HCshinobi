#!/usr/bin/env python
"""
Standalone tool to send a message JSON file to a target agent's mailbox.

Based on the requirements in _agent_coordination/SUPERVISOR_ONBOARDING.md (Capability 6).

Usage:
  python send_mailbox_message.py --recipient <AGENT_NAME> --sender <SENDER_NAME> --payload-json "{\"key\": \"value\"}" [--mailbox-root <PATH>]

Example:
  python tools/send_mailbox_message.py \
    --recipient CursorControlAgent \
    --sender SupervisorTool \
    --payload-json "{\"command\": \"resume_operation\", \"reason\": \"Manual reactivation via tool.\"}"
"""

import json
import os
import uuid
import argparse
import time
from pathlib import Path

# Assuming standard mailbox structure relative to this script or a specified root
DEFAULT_MAILBOX_ROOT = Path(__file__).parent.parent / "runtime" / "mailboxes"

def create_message_file(recipient: str, sender: str, payload: dict, mailbox_root: Path):
    """Creates a message file in the recipient's inbox."""
    try:
        agent_inbox = mailbox_root / recipient / "inbox"
        agent_inbox.mkdir(parents=True, exist_ok=True)

        message_id = str(uuid.uuid4())
        timestamp_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        message_filename = f"msg_{timestamp_utc}_{message_id}.json"
        message_path = agent_inbox / message_filename

        # Construct the message envelope
        message_content = {
            "message_id": message_id,
            "sender": sender,
            "recipient": recipient,
            "timestamp_created_utc": timestamp_utc,
            "payload": payload
        }

        with message_path.open("w", encoding="utf-8") as f:
            json.dump(message_content, f, indent=2)

        print(f"Successfully created message {message_id} for agent '{recipient}' in {message_path}")
        return True

    except Exception as e:
        print(f"Error creating message file for agent '{recipient}': {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send a message to an agent's mailbox.")
    parser.add_argument("--recipient", required=True, help="Name of the target agent.")
    parser.add_argument("--sender", required=True, help="Name of the sender (e.g., SupervisorTool, SystemOrchestrator).")
    parser.add_argument("--payload-json", required=True, help="Payload content as a JSON string.")
    parser.add_argument("--mailbox-root", default=str(DEFAULT_MAILBOX_ROOT.resolve()), help=f"Root directory for mailboxes (defaults to: {DEFAULT_MAILBOX_ROOT.resolve()})")

    args = parser.parse_args()

    try:
        payload_dict = json.loads(args.payload_json)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON provided for payload: {e}")
        exit(1)

    # Use resolved absolute path for mailbox root
    mailbox_root_path = Path(args.mailbox_root).resolve()

    # Add imports needed within the function if run as script
    from datetime import datetime, timezone

    if not create_message_file(args.recipient, args.sender, payload_dict, mailbox_root_path):
        exit(1) 