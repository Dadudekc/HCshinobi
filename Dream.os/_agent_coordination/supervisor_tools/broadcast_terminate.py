#!/usr/bin/env python
import argparse
import json
import logging
import os
import subprocess
import sys

# --- Setup ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_COORD_DIR = os.path.dirname(SCRIPT_DIR) # Assumes this script is in _agent_coordination/supervisor_tools
WORKSPACE_ROOT = os.path.dirname(AGENT_COORD_DIR)
SHARED_MAILBOX_DIR = os.path.join(AGENT_COORD_DIR, 'shared_mailboxes')
SEND_MSG_SCRIPT = os.path.join(AGENT_COORD_DIR, 'supervisor_tools', 'send_shared_mailbox_message.py')
MAX_MAILBOXES = 8

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BroadcastTerminate")

# Ensure send_shared_mailbox_message.py is executable and exists
if not os.path.exists(SEND_MSG_SCRIPT):
    logger.critical(f"Error: send_shared_mailbox_message.py not found at {SEND_MSG_SCRIPT}")
    sys.exit(1)

def get_active_agents() -> list[tuple[str, str]]:
    """Scans mailboxes and returns a list of (agent_id, mailbox_path) for active agents."""
    active_agents = []
    logger.info(f"Scanning mailboxes in {SHARED_MAILBOX_DIR}...")
    for i in range(1, MAX_MAILBOXES + 1):
        mailbox_path = os.path.join(SHARED_MAILBOX_DIR, f"mailbox_{i}.json")
        try:
            if os.path.exists(mailbox_path):
                with open(mailbox_path, "r", encoding='utf-8') as f:
                    try: 
                        data = json.load(f)
                        if isinstance(data, dict) and data.get("status") == "online":
                            agent_id = data.get("assigned_agent_id")
                            if agent_id:
                                logger.info(f"Found active agent {agent_id} in {mailbox_path}")
                                active_agents.append((agent_id, mailbox_path))
                            else:
                                 logger.warning(f"Mailbox {mailbox_path} is online but has no assigned_agent_id.")
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse JSON in {mailbox_path}. Skipping.")
        except Exception as e:
            logger.error(f"Error scanning mailbox {mailbox_path}: {e}")
    return active_agents

def send_terminate_command(agent_id: str, reason: str, delay: int):
    """Uses send_shared_mailbox_message.py to send the terminate command."""
    logger.info(f"Sending terminate command to Agent {agent_id} (Reason: '{reason}', Delay: {delay}s)")
    
    params = {"reason": reason, "delay_seconds": delay}
    params_json_str = json.dumps(params)
    
    command = [
        sys.executable, # Use the same python interpreter that's running this script
        SEND_MSG_SCRIPT,
        "--agent-id", agent_id,
        "--command", "terminate",
        "--params-json", params_json_str,
        "--sender", "SupervisorBroadcast"
    ]
    
    try:
        # Run the command
        result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=AGENT_COORD_DIR)
        
        if result.returncode == 0:
            logger.info(f"Successfully sent terminate command to {agent_id}.")
            logger.debug(f"Send script stdout:
{result.stdout}")
            return True
        else:
            logger.error(f"Failed to send terminate command to {agent_id}. Return code: {result.returncode}")
            logger.error(f"Send script stderr:
{result.stderr}")
            logger.error(f"Send script stdout:
{result.stdout}")
            return False
    except Exception as e:
        logger.error(f"Exception running send command for {agent_id}: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Broadcast terminate command to active Dream.OS agents.")
    parser.add_argument("-r", "--reason", default="Supervisor requested shutdown.", help="Reason for termination.")
    parser.add_argument("-d", "--delay", type=int, default=0, help="Delay in seconds before termination (agent implementation dependent).")
    parser.add_argument("--force", action="store_true", help="Attempt to send terminate even if no active agents found (e.g., for testing injection).")
    
    args = parser.parse_args()

    active_agents = get_active_agents()
    
    if not active_agents and not args.force:
        logger.info("No active agents found. No terminate commands sent.")
        sys.exit(0)
        
    if not active_agents and args.force:
        logger.warning("No active agents found, but --force specified. Attempting broadcast anyway (may fail if mailboxes don't exist).")
        # Synthesize target IDs if needed for testing, or maybe target all mailboxes?
        # For now, let's just try sending to potentially offline agents who might pick up later.
        target_agent_ids = [f"Agent_Force_Target_{i}" for i in range(1, MAX_MAILBOXES + 1)] # Example placeholder IDs
    else:
        target_agent_ids = [agent_id for agent_id, _ in active_agents]

    logger.info(f"Broadcasting terminate command to agents: {', '.join(target_agent_ids)}")
    
    success_count = 0
    failure_count = 0
    
    for agent_id in target_agent_ids:
        if send_terminate_command(agent_id, args.reason, args.delay):
            success_count += 1
        else:
            failure_count += 1
            
    logger.info("Broadcast complete.")
    logger.info(f"Successfully sent: {success_count}")
    logger.info(f"Failed to send: {failure_count}")
    
    if failure_count > 0:
        sys.exit(1) # Exit with error if any sends failed
    else:
        sys.exit(0) 