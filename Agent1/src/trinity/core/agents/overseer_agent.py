import os
import time
import logging
import datetime
import re
from pathlib import Path

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OverseerAgent")

# --- Configuration ---
# Use relative paths from the script location assuming it's run from project root
# or adjust based on actual execution context.
COORD_DIR = Path("src/_agent_coordination")
PROJECT_BOARD_FILE = COORD_DIR / "Agent1" / "project_board" / "README.md"
AGENT_DIRS = {
    "Writer": COORD_DIR / "Writer"
    # Add other supervised agents here
}

# --- Agent Functions ---

def get_tasks_from_board(board_file: Path) -> list[tuple[str, str]]:
    """Parses the project board (markdown) to find tasks in the TODO section."""
    tasks = []
    try:
        with open(board_file, 'r') as f:
            content = f.read()
        # Find the TODO section (simple regex, might need refinement)
        todo_match = re.search(r"##\s+TODO\s*(.*?)(?:##|$)", content, re.IGNORECASE | re.DOTALL)
        if todo_match:
            todo_section = todo_match.group(1)
            # Find checklist items that are not checked
            for line in todo_section.strip().split('\n'):
                task_match = re.match(r"^\s*-\s*\[\s\]\s*(.*)", line.strip())
                if task_match:
                    task_id = f"task_{len(tasks)+1:03d}" # Simple ID generation
                    task_desc = task_match.group(1).strip()
                    tasks.append((task_id, task_desc))
    except FileNotFoundError:
        logger.error(f"Project board file not found: {board_file}")
    except Exception as e:
        logger.error(f"Error reading project board: {e}")
    return tasks

def check_agent_idle(agent_name: str) -> bool:
    """Checks if an agent is idle (simple check: inbox is empty)."""
    inbox_dir = AGENT_DIRS[agent_name] / "inbox"
    try:
        if not any(inbox_dir.iterdir()): # Check if directory is empty
            return True
    except FileNotFoundError:
        logger.error(f"Inbox not found for agent: {agent_name}")
    except Exception as e:
        logger.error(f"Error checking {agent_name} inbox: {e}")
    return False

def assign_task(agent_name: str, task_id: str, task_desc: str):
    """Assigns a task by creating a file in the agent's inbox."""
    inbox_dir = AGENT_DIRS[agent_name] / "inbox"
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    task_file = inbox_dir / f"task_{task_id}_from_Overseer_{timestamp}.txt"
    try:
        with open(task_file, 'w') as f:
            f.write(f"TASK_ID: {task_id}\n")
            f.write(f"ASSIGNED_TO: {agent_name}\n")
            f.write(f"DESCRIPTION: {task_desc}\n")
        logger.info(f"Assigned task '{task_id}: {task_desc}' to {agent_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to assign task {task_id} to {agent_name}: {e}")
        return False

def update_board_task_status(board_file: Path, task_desc: str, new_status: str = "[x]"):
    """Updates the status of a task on the board (very basic implementation)."""
    # WARNING: This is prone to race conditions and errors in complex scenarios.
    # It reads the whole file, modifies in memory, and writes back.
    try:
        with open(board_file, 'r') as f:
            lines = f.readlines()

        new_lines = []
        updated = False
        for line in lines:
            # Match the unchecked task with the specific description
            if f"- [ ] {task_desc}" in line and not updated:
                # Replace '[ ]' with the new status marker
                new_line = line.replace("- [ ]", f"- {new_status}", 1)
                # Optionally add agent/timestamp info
                new_line = new_line.strip() + f" (Assigned by Overseer @ {datetime.datetime.now().strftime('%H:%M:%S')})\n"
                new_lines.append(new_line)
                updated = True
                logger.info(f"Marking task '{task_desc}' as assigned on board.")
            else:
                new_lines.append(line)

        if updated:
            with open(board_file, 'w') as f:
                f.writelines(new_lines)
        else:
             logger.warning(f"Did not find task '{task_desc}' on board to update status.")

    except Exception as e:
        logger.error(f"Error updating project board: {e}")

# --- Main Loop ---
def run_overseer_cycle():
    logger.info("Overseer starting cycle...")
    tasks = get_tasks_from_board(PROJECT_BOARD_FILE)
    if not tasks:
        logger.info("No pending tasks found on the board.")
        return

    logger.info(f"Found {len(tasks)} pending tasks: {tasks}")

    # Simple logic: Find the first task and assign to the first idle agent
    task_id, task_desc = tasks[0] # Get the first task

    assigned = False
    for agent_name in AGENT_DIRS.keys():
        if check_agent_idle(agent_name):
            logger.info(f"Agent {agent_name} is idle. Assigning task {task_id}.")
            if assign_task(agent_name, task_id, task_desc):
                # If assignment succeeds, update the board
                update_board_task_status(PROJECT_BOARD_FILE, task_desc, "[>]" ) # Mark as assigned/in progress
                assigned = True
                break # Assign only one task per cycle in this simple version
        else:
            logger.info(f"Agent {agent_name} is busy (inbox not empty).")

    if not assigned:
        logger.info("No idle agents found to assign the task.")

    logger.info("Overseer cycle finished.")

if __name__ == "__main__":
    # Simple loop for demonstration
    while True:
        run_overseer_cycle()
        logger.info("Sleeping for 15 seconds...")
        time.sleep(15) 