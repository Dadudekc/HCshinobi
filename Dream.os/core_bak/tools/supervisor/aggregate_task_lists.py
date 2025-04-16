#!/usr/bin/env python3
"""
Standalone tool to scan the project for task_list.md files, parse checklist items,
and aggregate them into a single master JSON file.

Usage:
  python aggregate_task_lists.py [--root <PROJECT_ROOT>] [--output <OUTPUT_JSON_PATH>]

Example:
  python tools/aggregate_task_lists.py --output ../runtime/master_task_list.json
  python tools/aggregate_task_lists.py # Outputs to ./master_task_list.json
"""

import json
import argparse
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone

# Regex to find markdown checklist items
# - Group 1: Check state (' ' or 'x')
# - Group 2: Task description
TASK_REGEX = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.*)$")

# Default output file name
DEFAULT_OUTPUT_FILENAME = "master_task_list.json"

def parse_markdown_tasks(file_path: Path):
    """Parses a single task_list.md file and yields task dictionaries."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tasks = []
            for i, line in enumerate(f):
                match = TASK_REGEX.match(line)
                if match:
                    status_char = match.group(1).lower()
                    description = match.group(2).strip()
                    
                    status = "COMPLETED" if status_char == 'x' else "PENDING"
                    
                    tasks.append({
                        "description": description,
                        "status": status,
                        "original_line": i + 1
                    })
            return tasks
    except Exception as e:
        print(f"⚠️ Warning: Failed to read or parse {file_path}: {e}")
        return []

def aggregate_tasks(root_dir: Path, output_path: Path):
    """Finds all task_list.md files, parses them, and writes the master JSON."""
    print(f"Scanning for task_list.md files under: {root_dir}")
    master_task_list = []
    files_processed = 0
    tasks_found_total = 0
    
    # Use rglob to find all task_list.md files recursively
    for md_file_path in root_dir.rglob("task_list.md"):
        # Basic exclusion for common ignored directories
        if any(part.startswith('.') or part == '__pycache__' or part == 'node_modules' for part in md_file_path.parts):
             continue
             
        print(f"  Processing: {md_file_path.relative_to(root_dir)}")
        files_processed += 1
        parsed_tasks = parse_markdown_tasks(md_file_path)
        
        module_name = md_file_path.parent.name
        relative_path_str = str(md_file_path.relative_to(root_dir)).replace('\\', '/') # Use forward slashes
        
        for task_data in parsed_tasks:
            tasks_found_total += 1
            master_task_list.append({
                "task_id": str(uuid.uuid4()),
                "description": task_data["description"],
                "status": task_data["status"],
                "source_file": relative_path_str,
                "module": module_name,
                "original_line": task_data["original_line"],
                "timestamp_aggregated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            
    print(f"\nProcessed {files_processed} task_list.md files.")
    print(f"Found {tasks_found_total} tasks in total.")
    
    # Write the aggregated list to the output JSON file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(master_task_list, f, indent=2)
        print(f"✅ Successfully aggregated tasks to: {output_path.resolve()}")
    except Exception as e:
        print(f"❌ Error writing master task list to {output_path}: {e}")

if __name__ == "__main__":
    # Assume the script is run from the workspace root or _agent_coordination
    # Make the default root relative to the script's location for better portability
    default_root = Path(__file__).parent.parent.parent # Assumes tools/_agent_coordination/PROJECT_ROOT
    default_output = Path.cwd() / DEFAULT_OUTPUT_FILENAME # Default output in Current Working Directory

    parser = argparse.ArgumentParser(description="Aggregate markdown task lists into a master JSON file.")
    parser.add_argument("--root", default=str(default_root), help="Root directory of the project to scan.")
    parser.add_argument("--output", default=str(default_output), help=f"Path to save the master JSON file (defaults to ./{DEFAULT_OUTPUT_FILENAME} in CWD).")

    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    output_path = Path(args.output).resolve()

    if not root_path.is_dir():
        print(f"❌ Error: Root path specified is not a valid directory: {root_path}")
        exit(1)
        
    if not output_path.parent.is_dir():
        print(f"❌ Error: Output directory does not exist: {output_path.parent}")
        exit(1)

    aggregate_tasks(root_path, output_path) 