"""
Command-Line Interface (CLI) tool to inject tasks into the Dream.OS task list.

Usage:
  python scripts/inject_task.py --action RUN_TERMINAL_COMMAND --params '{"command": "echo Hello from CLI"}'
  python scripts/inject_task.py --action GET_EDITOR_CONTENT --priority 1
  python scripts/inject_task.py --action OPEN_FILE --params '{"file_path": "/path/to/your/file.txt"}' --task-id custom_open_task
"""

import argparse
import json
import os
import sys
import uuid
from datetime import datetime

# Assuming TaskStatus might be defined elsewhere, but for standalone use:
class TaskStatus:
    PENDING = "PENDING"

# Define the path to the input file relative to the project root
# Assumes this script is run from the project root or `scripts/` dir
try:
    # Find project root (assuming script is in project_root/scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if not os.path.exists(os.path.join(project_root, "core")):
         # Maybe script is in project root?
         project_root = os.getcwd()
except NameError:
     # __file__ not defined (e.g., interactive) - assume CWD is project root
     project_root = os.getcwd()

DEFAULT_INPUT_FILE = os.path.join(project_root, "run", "input_tasks.jsonl")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Inject a task into the Dream.OS task list.")
    parser.add_argument("--action", required=True, help="The action the target agent should perform.")
    parser.add_argument("--params", type=str, default="{}", 
                        help="JSON string representing the parameters for the action. E.g., '{\"command\": \"ls\"}'")
    parser.add_argument("--task-id", type=str, default=None, help="Optional specific ID for the task.")
    parser.add_argument("--priority", type=int, default=50, help="Task priority (lower number is higher priority).")
    parser.add_argument("--target-agent", type=str, default=None, 
                        help="Optional specific agent to target. Defaults based on action if known.")
    parser.add_argument("--depends-on", type=str, default="", 
                        help="Comma-separated list of task IDs this task depends on.")
    parser.add_argument("--input-file", type=str, default=DEFAULT_INPUT_FILE, 
                        help=f"Path to the input task file (default: {DEFAULT_INPUT_FILE})")

    return parser.parse_args()

def main():
    args = parse_arguments()

    # Validate and parse JSON params
    try:
        params_dict = json.loads(args.params)
        if not isinstance(params_dict, dict):
            raise ValueError("Params must be a JSON object (dictionary).")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON string provided for --params: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Generate task ID if not provided
    task_id = args.task_id if args.task_id else f"cli_injected_{uuid.uuid4().hex[:8]}"

    # Parse dependencies
    dependencies = [dep.strip() for dep in args.depends_on.split(',') if dep.strip()]

    # Construct the task object
    task = {
        "task_id": task_id,
        "action": args.action,
        "params": params_dict,
        "status": TaskStatus.PENDING,
        "priority": args.priority,
        "depends_on": dependencies,
        "retry_count": 0,
        "repair_attempts": 0,
        "injected_at": datetime.now().isoformat(),
        "injected_by": "cli_tool"
    }

    if args.target_agent:
        task["target_agent"] = args.target_agent
    # Optional: Add default target_agent logic based on action here if desired
    # elif args.action in ["RUN_TERMINAL_COMMAND", ...]: task["target_agent"] = "CursorControlAgent"

    # Ensure the run directory exists
    input_file_dir = os.path.dirname(args.input_file)
    try:
        os.makedirs(input_file_dir, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create directory {input_file_dir}: {e}", file=sys.stderr)
        sys.exit(1)

    # Append the task as a JSON line to the input file
    try:
        task_json_line = json.dumps(task)
        with open(args.input_file, 'a', encoding='utf-8') as f:
            f.write(task_json_line + '\n')
        print(f"Successfully injected task '{task_id}' into {args.input_file}")
        print(f"Task details: {task_json_line}")
    except IOError as e:
        print(f"Error: Could not write to input file {args.input_file}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 