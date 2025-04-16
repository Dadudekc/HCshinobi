import unittest
import os
import json
import time
from unittest.mock import patch, MagicMock

# Updated import paths
# from social_media_agent import SocialMediaAgent, load_strategies, load_config
# from constants import AGENT_ID, DEFAULT_MAILBOX_BASE_DIR_NAME
from core.agents.social_media_agent import SocialMediaAgent, load_strategies, load_config
from core.constants import AGENT_ID_SOCIAL_MEDIA as AGENT_ID, DEFAULT_MAILBOX_BASE_DIR_NAME

# Mock strategies and config path for isolation
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..\config\test_config.json')
STRATEGIES_DIR = os.path.join(os.path.dirname(__file__), '..\strategies')

# --- Path Setup ---
# Assuming this script is in tests/, go up one level to project root
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Determine Agent Inbox Path
# Assumes mailbox base is directly inside the 'social' directory (which is project_root here)
AGENT_MAILBOX_BASE = os.path.join(project_root, DEFAULT_MAILBOX_BASE_DIR_NAME, AGENT_ID)
AGENT_INBOX = os.path.join(AGENT_MAILBOX_BASE, "inbox")

# --- Default Test Parameters ---
DEFAULT_NUM_MESSAGES = 100
DEFAULT_DELAY_MS = 10 # Milliseconds between message drops

# --- Command Templates ---
# Define sample commands the agent can handle
COMMAND_TEMPLATES = [
    # Simple status check (low processing overhead)
    lambda msg_id: {
        "message_id": msg_id,
        "sender": "LoadTester",
        "recipient": AGENT_ID,
        "timestamp": datetime.now().isoformat(),
        "type": "COMMAND",
        "command": "agent_status",
        "details": {}
    },
    # Simple post command (higher overhead, involves strategy loading etc.)
    lambda msg_id: {
        "message_id": msg_id,
        "sender": "LoadTester",
        "recipient": AGENT_ID,
        "timestamp": datetime.now().isoformat(),
        "type": "COMMAND",
        "command": "post",
        "platform": "twitter", # Requires twitter strategy/config
        "details": {
            "text": f"Load test message {msg_id} at {time.time()}"
        }
    },
    # Add other command types as needed (e.g., scrape, login)
    # Ensure the agent is configured to handle the chosen platforms/commands
]

def generate_message_file(inbox_path: str, message_data: dict):
    """Creates a single JSON message file in the inbox."""
    message_id = message_data.get("message_id", str(uuid.uuid4()))
    # Use a timestamp in the filename for potential ordering/uniqueness
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"loadtest_{message_id}_{ts}.json"
    filepath = os.path.join(inbox_path, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(message_data, f, indent=2)
        return True, filepath
    except Exception as e:
        print(f"Error creating message file {filepath}: {e}")
        return False, filepath

def run_load_test(num_messages: int, delay_ms: int):
    """Generates the specified number of messages in the agent's inbox."""
    print("--- Social Agent Load Test Script ---")
    print(f"Target Agent ID: {AGENT_ID}")
    print(f"Target Inbox:  {AGENT_INBOX}")
    print(f"Messages to generate: {num_messages}")
    print(f"Delay between messages: {delay_ms} ms")
    print("-------------------------------------")

    if not os.path.exists(AGENT_INBOX):
        print(f"Error: Agent inbox directory does not exist: {AGENT_INBOX}")
        print("Please ensure the SocialMediaAgent has been run at least once or the directory is created manually.")
        return

    print("Starting message generation...")
    start_time = time.time()
    messages_created = 0
    errors = 0

    # Simple round-robin selection of command templates
    num_templates = len(COMMAND_TEMPLATES)
    if num_templates == 0:
        print("Error: No COMMAND_TEMPLATES defined in the script.")
        return

    for i in range(num_messages):
        msg_id = f"load_{uuid.uuid4()}"
        template_func = COMMAND_TEMPLATES[i % num_templates]
        message = template_func(msg_id)
        
        success, filepath = generate_message_file(AGENT_INBOX, message)
        if success:
            messages_created += 1
            # print(f"Created: {os.path.basename(filepath)}") # Too verbose for load test
        else:
            errors += 1

        if delay_ms > 0:
            time.sleep(delay_ms / 1000.0)
            
        # Provide periodic status update
        if (i + 1) % 100 == 0:
            print(f"Generated {i + 1}/{num_messages} messages...")

    end_time = time.time()
    duration = end_time - start_time

    print("\n--- Load Test Summary ---")
    print(f"Message generation finished.")
    print(f"Successfully created: {messages_created} messages")
    print(f"Errors encountered:   {errors}")
    print(f"Total duration:       {duration:.2f} seconds")
    if duration > 0:
        rate = messages_created / duration
        print(f"Generation rate:      {rate:.2f} messages/second")
    print("-------------------------")
    print("\nInstructions:")
    print("1. Ensure the SocialMediaAgent process is running.")
    print(f"2. Monitor the agent's log file (likely '.logs/agent_operations.log') for processing activity and errors.")
    print(f"3. Observe system resource usage (CPU, Memory) of the agent process.")
    print(f"4. Check the agent's outbox ({os.path.join(AGENT_MAILBOX_BASE, 'outbox')}) for response files.")
    print("-------------------------")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate load test messages for the SocialMediaAgent.")
    parser.add_argument("-n", "--num-messages", type=int, default=DEFAULT_NUM_MESSAGES,
                        help=f"Number of messages to generate (default: {DEFAULT_NUM_MESSAGES})")
    parser.add_argument("-d", "--delay-ms", type=int, default=DEFAULT_DELAY_MS,
                        help=f"Delay in milliseconds between creating messages (default: {DEFAULT_DELAY_MS})")

    args = parser.parse_args()

    run_load_test(args.num_messages, args.delay_ms) 