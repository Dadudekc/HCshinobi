import os
import time
import logging
import datetime
from pathlib import Path
import re

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WriterAgent")

# --- Configuration ---
AGENT_NAME = "Writer"
COORD_DIR = Path("src/_agent_coordination")
INBOX_DIR = COORD_DIR / AGENT_NAME / "inbox"
OUTBOX_DIR = COORD_DIR / AGENT_NAME / "outbox"

# --- Agent Functions ---
def process_task_file(task_file: Path) -> bool:
    """Processes a task file from the inbox."""
    try:
        with open(task_file, 'r') as f:
            content = f.read()
        logger.info(f"Received task file {task_file.name}:\n{content}")

        # Simulate doing work based on content
        # Extract task ID for reporting
        task_id = "unknown_task"
        match = re.search(r"TASK_ID:\s*(\S+)", content)
        if match:
            task_id = match.group(1)

        # Simulate work completion
        time.sleep(2) # Pretend to work
        result_summary = f"Completed task {task_id}: Wrote a summary."

        # Write result to outbox
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = OUTBOX_DIR / f"result_{task_id}_from_{AGENT_NAME}_{timestamp}.txt"
        with open(result_file, 'w') as f:
            f.write(f"TASK_ID: {task_id}\n")
            f.write(f"STATUS: Done\n")
            f.write(f"RESULT: {result_summary}\n")
        logger.info(f"Wrote result for task {task_id} to {result_file.name}")

        # Delete processed task file from inbox
        os.remove(task_file)
        logger.info(f"Deleted processed task file: {task_file.name}")
        return True

    except Exception as e:
        logger.error(f"Error processing task file {task_file.name}: {e}")
        # Optionally move the file to an error directory instead of deleting
        return False

# --- Main Loop ---
def run_writer_cycle():
    logger.info(f"{AGENT_NAME} checking inbox...")
    try:
        processed_task = False
        for item in INBOX_DIR.iterdir():
            if item.is_file() and item.name.startswith("task_"):
                logger.info(f"Found task file: {item.name}")
                if process_task_file(item):
                    processed_task = True
                    break # Process one task per cycle

        if not processed_task:
            logger.info("No new tasks found.")

    except FileNotFoundError:
        logger.error(f"Inbox directory not found: {INBOX_DIR}")
    except Exception as e:
        logger.error(f"Error in writer cycle: {e}")

if __name__ == "__main__":
    # Ensure directories exist
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)

    # Simple loop for demonstration
    while True:
        run_writer_cycle()
        logger.info("Sleeping for 10 seconds...")
        time.sleep(10) 