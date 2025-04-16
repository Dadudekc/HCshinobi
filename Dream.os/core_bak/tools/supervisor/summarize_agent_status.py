#!/usr/bin/env python3
"""
Standalone tool to summarize agent status based on mailbox contents and optionally task list.

Usage:
  python summarize_agent_status.py [--mailbox-root <PATH>] [--task-list <PATH>] [--format <cli|md>]

Example:
  python tools/summarize_agent_status.py
  python tools/summarize_agent_status.py --format md > agent_status_report.md
"""

import os
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# Defaults relative to this script's location
DEFAULT_MAILBOX_ROOT = Path(__file__).parent.parent / "runtime" / "mailboxes"
DEFAULT_TASK_LIST_PATH = Path(__file__).parent.parent / "runtime" / "task_list.json"

def summarize_status(mailbox_root: Path, task_list_path: Path, output_format: str):
    """Gathers status info and prints a report."""
    
    agent_status = defaultdict(lambda: {"inbox": 0, "processed": 0, "error": 0, "last_task_id": "N/A", "last_task_timestamp": "N/A"})

    # --- Scan Mailboxes --- 
    if not mailbox_root.is_dir():
        print(f"Warning: Mailbox root directory not found or not a directory: {mailbox_root}")
    else:
        for agent_dir in mailbox_root.iterdir():
            if not agent_dir.is_dir():
                continue
            agent_name = agent_dir.name
            
            inbox_path = agent_dir / "inbox"
            processed_path = agent_dir / "processed"
            error_path = agent_dir / "error"
            
            agent_status[agent_name]["inbox"] = len(list(inbox_path.glob("*.json"))) if inbox_path.is_dir() else 0
            agent_status[agent_name]["processed"] = len(list(processed_path.glob("*.json"))) if processed_path.is_dir() else 0
            agent_status[agent_name]["error"] = len(list(error_path.glob("*.json"))) if error_path.is_dir() else 0
            
    # --- Scan Task List (Optional) --- 
    agent_last_task = {}
    if task_list_path.is_file():
        try:
            with open(task_list_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                if isinstance(tasks, list):
                    for task in tasks:
                        if isinstance(task, dict):
                            agent = task.get("target_agent")
                            task_id = task.get("task_id")
                            # Use last_updated or timestamp_created
                            timestamp_str = task.get("last_updated") or task.get("timestamp_created") 
                            if agent and task_id and timestamp_str:
                                try:
                                    # Attempt to parse timestamp for comparison
                                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                    if agent not in agent_last_task or timestamp > agent_last_task[agent]["timestamp_obj"]:
                                         agent_last_task[agent] = {"id": task_id, "timestamp_str": timestamp_str, "timestamp_obj": timestamp}
                                except ValueError:
                                    # Handle non-ISO timestamps simply by taking the latest seen
                                    if agent not in agent_last_task:
                                        agent_last_task[agent] = {"id": task_id, "timestamp_str": timestamp_str}
                                    # Could add logic here to store the latest based on string comparison if needed
                                    pass # Silently ignore invalid timestamps for now
                                    
        except Exception as e:
            print(f"Warning: Failed to read or parse task list {task_list_path}: {e}")
            
        # Update agent_status with last task info
        for agent, task_info in agent_last_task.items():
            if agent in agent_status:
                 agent_status[agent]["last_task_id"] = task_info["id"]
                 agent_status[agent]["last_task_timestamp"] = task_info["timestamp_str"]
            # Else: Task list mentions agent not found in mailboxes - could add them here if desired
            # else:
            #    agent_status[agent]["last_task_id"] = task_info["id"]
            #    agent_status[agent]["last_task_timestamp"] = task_info["timestamp_str"]

    # --- Generate Report --- 
    if not agent_status:
        print("No agent data found in mailboxes.")
        return
        
    print("\n--- Agent Status Summary ---")
    now_utc = datetime.now(timezone.utc)
    print(f"Report generated: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    sorted_agents = sorted(agent_status.keys())

    if output_format == "md":
        print("\n| Agent Name | Inbox | Processed | Error | Last Task ID | Last Task Timestamp | Time Since Last Task |")
        print("|------------|-------|-----------|-------|--------------|---------------------|----------------------|")
        for agent in sorted_agents:
            status = agent_status[agent]
            time_since = "N/A"
            if status["last_task_timestamp"] != "N/A":
                try:
                    last_ts = datetime.fromisoformat(status["last_task_timestamp"].replace('Z', '+00:00'))
                    delta = now_utc - last_ts
                    # Format delta nicely (e.g., X days, Y hours, Z mins)
                    secs = delta.total_seconds()
                    days, secs = divmod(secs, 86400)
                    hours, secs = divmod(secs, 3600)
                    mins, secs = divmod(secs, 60)
                    time_since = f"{int(days)}d {int(hours)}h {int(mins)}m" if days > 0 else f"{int(hours)}h {int(mins)}m {int(secs)}s"
                except ValueError:
                    time_since = "Parse Error"
                    
            print(f"| {agent} | {status['inbox']} | {status['processed']} | {status['error']} | {status['last_task_id']} | {status['last_task_timestamp']} | {time_since} |")
    
    else: # Default to CLI table format
        # Simple aligned print
        header = f"{'Agent Name':<30} {'Inbox':>7} {'Processed':>11} {'Error':>7} {'Last Task ID':<20} {'Last Task Timestamp'}"
        print("\n" + header)
        print("-" * len(header))
        for agent in sorted_agents:
            status = agent_status[agent]
            print(f"{agent:<30} {status['inbox']:>7} {status['processed']:>11} {status['error']:>7} {status['last_task_id']:<20} {status['last_task_timestamp']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize agent status from mailboxes and task list.")
    parser.add_argument("--mailbox-root", default=str(DEFAULT_MAILBOX_ROOT.resolve()), help="Root directory for mailboxes.")
    parser.add_argument("--task-list", default=str(DEFAULT_TASK_LIST_PATH.resolve()), help="Path to the task_list.json file.")
    parser.add_argument("--format", choices=["cli", "md"], default="cli", help="Output format (cli table or markdown).")

    args = parser.parse_args()

    summarize_status(Path(args.mailbox_root).resolve(), Path(args.task_list).resolve(), args.format) 