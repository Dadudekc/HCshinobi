#!/usr/bin/env python
"""
Standalone tool to validate the structure and content of the task_list.json file.

Usage:
  python task_list_validator.py [--task-list <PATH>]

Checks for:
- Valid JSON format.
- Each entry is a dictionary.
- Presence of required keys (task_id, status, task_type, timestamp_created).
- Valid status values (PENDING, PROCESSING, DISPATCHED, FAILED, COMPLETED, ERROR).
- Optional: Presence of target_agent if status is DISPATCHED/PROCESSING/COMPLETED/FAILED/ERROR.
"""

import json
import argparse
from pathlib import Path

# Assuming task_list.json is in runtime/ relative to _agent_coordination/
DEFAULT_TASK_LIST_PATH = Path(__file__).parent.parent / "runtime" / "task_list.json"

REQUIRED_KEYS = ["task_id", "status", "task_type", "timestamp_created"]
VALID_STATUSES = {"PENDING", "PROCESSING", "DISPATCHED", "FAILED", "COMPLETED", "ERROR"}
STATUSES_REQUIRING_AGENT = {"PROCESSING", "DISPATCHED", "FAILED", "COMPLETED", "ERROR"}

def validate_task_list(task_list_path: Path):
    """Validates the task list file."""
    if not task_list_path.exists():
        print(f"Error: Task list file not found at {task_list_path}")
        return False

    print(f"Validating {task_list_path}...")
    is_valid = True
    line_number = 0 # For potential future use if loading line-by-line

    try:
        with open(task_list_path, "r", encoding="utf-8") as f:
            # Attempt to load the whole file first for basic JSON validity
            try:
                tasks = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON format - {e}")
                return False

            if not isinstance(tasks, list):
                print("Error: Root element is not a JSON list.")
                return False

            if not tasks:
                print("Warning: Task list is empty.")
                # An empty list is technically valid JSON

            for i, task in enumerate(tasks):
                task_index = i + 1 # 1-based index for reporting
                if not isinstance(task, dict):
                    print(f"Error: Task at index {task_index} is not a dictionary (JSON object).")
                    is_valid = False
                    continue # Skip further checks for this item

                task_id = task.get("task_id", "<MISSING>")

                # Check for required keys
                missing_keys = [key for key in REQUIRED_KEYS if key not in task]
                if missing_keys:
                    print(f"Error: Task '{task_id}' (index {task_index}) missing required keys: {missing_keys}")
                    is_valid = False

                # Check status validity
                status = task.get("status")
                if status and status not in VALID_STATUSES:
                    print(f"Error: Task '{task_id}' (index {task_index}) has invalid status: '{status}'. Valid statuses are: {VALID_STATUSES}")
                    is_valid = False

                # Check for target_agent where appropriate
                # if status and status in STATUSES_REQUIRING_AGENT and not task.get("target_agent"):
                #     print(f"Warning: Task '{task_id}' (index {task_index}) has status '{status}' but missing 'target_agent'.")
                # Optional check - uncomment above lines if desired

    except FileNotFoundError:
        print(f"Error: File not found at {task_list_path}") # Should be caught earlier, but belt-and-suspenders
        return False
    except Exception as e:
        print(f"An unexpected error occurred during validation: {e}")
        return False

    if is_valid:
        print(f"Validation Successful: {task_list_path} appears structurally valid.")
    else:
        print(f"Validation Failed: Issues found in {task_list_path}.")

    return is_valid

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate the task_list.json file.")
    parser.add_argument("--task-list", default=str(DEFAULT_TASK_LIST_PATH.resolve()), help=f"Path to the task_list.json file (defaults to: {DEFAULT_TASK_LIST_PATH.resolve()})")

    args = parser.parse_args()

    task_list_file_path = Path(args.task_list).resolve()

    if not validate_task_list(task_list_file_path):
        exit(1) 