#!/usr/bin/env python3
"""
Standalone tool to generate a status report from the task_list.json file.

Usage:
  python task_list_status_report.py [--task-list <PATH>] [--output <OUTPUT_MD_PATH>] [--max-age-days <DAYS>]

Example:
  python tools/task_list_status_report.py --output task_report.md --max-age-days 30
  python tools/task_list_status_report.py # Prints to stdout, no age limit
"""

import json
import argparse
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Defaults relative to this script's location
DEFAULT_TASK_LIST_PATH = Path(__file__).parent.parent / "runtime" / "task_list.json"

# Required fields (subset from validator)
REQUIRED_KEYS = ["task_id", "status", "task_type", "timestamp_created"]

def generate_report(task_list_path: Path, output_file: Path | None, max_age_days: int | None):
    """Reads task list, analyzes, and generates a Markdown report."""
    if not task_list_path.is_file():
        print(f"❌ Error: Task list file not found: {task_list_path.resolve()}")
        return

    tasks = []
    try:
        with open(task_list_path, "r", encoding="utf-8") as f:
            tasks_data = json.load(f)
            if isinstance(tasks_data, list):
                tasks = tasks_data
            else:
                print(f"❌ Error: Task list file root is not a JSON list: {task_list_path.resolve()}")
                return
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format in {task_list_path.resolve()}: {e}")
        return
    except Exception as e:
        print(f"❌ Error reading task list file {task_list_path.resolve()}: {e}")
        return

    report = io.StringIO()
    now_utc = datetime.now(timezone.utc)

    report.write(f"# Task List Status Report\n\")
    report.write(f"Generated: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\")
    report.write(f"Source File: `{task_list_path.resolve()}`\n\")
    if max_age_days is not None:
        report.write(f"Filtering tasks older than {max_age_days} days.\n\")
    report.write(f"Total Tasks Found: {len(tasks)}\n\n")

    tasks_by_status = defaultdict(list)
    missing_fields_tasks = []
    dependency_map = defaultdict(list)
    age_threshold = now_utc - timedelta(days=max_age_days) if max_age_days is not None else None

    valid_tasks_count = 0
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            missing_fields_tasks.append({"index": i + 1, "issue": "Not a dictionary"})
            continue

        task_id = task.get("task_id", f"<MISSING_ID_INDEX_{i+1}>")
        missing_keys = [key for key in REQUIRED_KEYS if key not in task]
        if missing_keys:
            missing_fields_tasks.append({"id": task_id, "issue": f"Missing keys: {missing_keys}"})
            # Continue processing status if possible

        status = task.get("status", "<MISSING_STATUS>")
        created_ts_str = task.get("timestamp_created")
        created_ts = None
        if created_ts_str:
            try:
                created_ts = datetime.fromisoformat(created_ts_str.replace('Z', '+00:00'))
            except ValueError:
                missing_fields_tasks.append({"id": task_id, "issue": f"Invalid timestamp_created format: {created_ts_str}"})
        else:
             missing_fields_tasks.append({"id": task_id, "issue": "Missing timestamp_created"})
             # Cannot reliably check age or add to status counts without timestamp
             continue 

        # Filter by age if applicable
        if age_threshold and created_ts and created_ts < age_threshold:
            continue
            
        valid_tasks_count += 1 # Count tasks that pass the age filter and have a timestamp
        
        task['_age_days'] = (now_utc - created_ts).days if created_ts else -1 # Add age for sorting
        tasks_by_status[status].append(task)

        # Map dependencies
        deps = task.get("depends_on", [])
        if isinstance(deps, list) and deps:
            dependency_map[task_id].extend(deps)
        elif isinstance(deps, str) and deps:
             dependency_map[task_id].append(deps)
             
    report.write(f"Tasks Processed (after age filter): {valid_tasks_count}\n\n")

    # --- Report by Status --- 
    report.write("## Tasks by Status\n\n")
    status_order = ["PENDING", "PROCESSING", "DISPATCHED", "FAILED", "ERROR", "COMPLETED", "<MISSING_STATUS>"] # Ensure specific order
    found_statuses = set(tasks_by_status.keys())
    
    for status in status_order:
        if status in tasks_by_status:
            report.write(f"### {status} ({len(tasks_by_status[status])})\n\")
            # Sort by age, oldest first
            sorted_tasks = sorted(tasks_by_status[status], key=lambda t: t.get('_age_days', -1), reverse=True)
            report.write("| Task ID | Age (Days) | Task Type | Target Agent | Created Timestamp |\n")
            report.write("|---------|------------|-----------|--------------|-------------------|\n")
            for task in sorted_tasks:
                task_id = task.get("task_id", "N/A")
                age = task.get("_age_days", "N/A")
                task_type = task.get("task_type", "N/A")
                target = task.get("target_agent", "N/A")
                created = task.get("timestamp_created", "N/A")
                report.write(f"| {task_id} | {age} | {task_type} | {target} | {created} |\n")
            report.write("\n")
            found_statuses.remove(status)
            
    # Report any unexpected statuses
    for status in found_statuses:
         report.write(f"### {status} ({len(tasks_by_status[status])}) - *Unexpected Status*\n\")
         # (Similar table structure as above)
         report.write("| Task ID | Age (Days) | Task Type | Target Agent | Created Timestamp |\n")
         report.write("|---------|------------|-----------|--------------|-------------------|\n")
         for task in sorted(tasks_by_status[status], key=lambda t: t.get('_age_days', -1), reverse=True):
             task_id = task.get("task_id", "N/A")
             age = task.get("_age_days", "N/A")
             task_type = task.get("task_type", "N/A")
             target = task.get("target_agent", "N/A")
             created = task.get("timestamp_created", "N/A")
             report.write(f"| {task_id} | {age} | {task_type} | {target} | {created} |\n")
         report.write("\n")

    # --- Report Missing Fields --- 
    if missing_fields_tasks:
        report.write("## Tasks with Missing/Invalid Required Fields\n\n")
        report.write("| Task ID / Index | Issue Description |\n")
        report.write("|-----------------|-------------------|\n")
        for issue in missing_fields_tasks:
            task_ref = issue.get("id") or f"Index {issue.get('index', '?')}"
            report.write(f"| {task_ref} | {issue['issue']} |\n")
        report.write("\n")

    # --- Report Dependencies (Basic) --- 
    if dependency_map:
        report.write("## Task Dependencies (Task ID -> Depends On)\n\n")
        for task_id, deps in sorted(dependency_map.items()):
            report.write(f"- **`{task_id}`** -> `{', '.join(deps)}`\n")
        report.write("\n")
        
    # --- Output Report --- 
    report_content = report.getvalue()
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"✅ Report generated: {output_file.resolve()}")
        except Exception as e:
            print(f"❌ Error writing report to {output_file}: {e}")
            print("\n--- Report Content ---")
            print(report_content) # Print to stdout as fallback
    else:
        print(report_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a status report from task_list.json.")
    parser.add_argument("--task-list", default=str(DEFAULT_TASK_LIST_PATH.resolve()), help="Path to the task_list.json file.")
    parser.add_argument("--output", help="Optional path to save the Markdown report. If omitted, prints to stdout.")
    parser.add_argument("--max-age-days", type=int, default=None, help="Only include tasks created within the last N days.")

    args = parser.parse_args()

    task_list_file_path = Path(args.task_list).resolve()
    output_path = Path(args.output).resolve() if args.output else None
    
    if output_path and not output_path.parent.is_dir():
        print(f"❌ Error: Output directory does not exist: {output_path.parent}")
        exit(1)

    generate_report(task_list_file_path, output_path, args.max_age_days) 