#!/usr/bin/env python3
"""
Standalone tool to validate agent onboarding consistency.

Checks if agents found in mailboxes and/or task list are mentioned
in the AGENT_ONBOARDING.md file and have corresponding mailbox folders.

Usage:
  python validate_agent_onboarding.py [--mailbox-root <PATH>] [--task-list <PATH>] [--onboarding-doc <PATH>]

Example:
  python tools/validate_agent_onboarding.py
"""

import json
import argparse
import re
from pathlib import Path
from collections import defaultdict

# Defaults relative to this script's location
DEFAULT_MAILBOX_ROOT = Path(__file__).parent.parent / "runtime" / "mailboxes"
DEFAULT_TASK_LIST_PATH = Path(__file__).parent.parent / "runtime" / "task_list.json"
# Assuming AGENT_ONBOARDING.md is in the parent (_agent_coordination) directory
DEFAULT_ONBOARDING_DOC = Path(__file__).parent.parent / "AGENT_ONBOARDING.md"

def validate_onboarding(mailbox_root: Path, task_list_path: Path, onboarding_doc_path: Path):
    """Performs the validation checks."""
    print("--- Agent Onboarding Validation ---")
    print(f"Mailbox Root: {mailbox_root.resolve()}")
    print(f"Task List:    {task_list_path.resolve()}")
    print(f"Onboarding Doc: {onboarding_doc_path.resolve()}\n")

    agents_found = set()
    agents_in_mailbox = set()
    agents_in_tasklist = set()
    missing_mailbox = []
    missing_onboarding_doc = []

    # 1. Find agents from Mailbox directories
    if mailbox_root.is_dir():
        for item in mailbox_root.iterdir():
            if item.is_dir():
                agent_name = item.name
                agents_found.add(agent_name)
                agents_in_mailbox.add(agent_name)
    else:
        print(f"Warning: Mailbox root directory not found: {mailbox_root}")

    # 2. Find agents from Task List target_agent field
    if task_list_path.is_file():
        try:
            with open(task_list_path, "r", encoding="utf-8") as f:
                tasks = json.load(f)
                if isinstance(tasks, list):
                    for task in tasks:
                        if isinstance(task, dict) and "target_agent" in task and task["target_agent"]:
                            agent_name = task["target_agent"]
                            agents_found.add(agent_name)
                            agents_in_tasklist.add(agent_name)
        except Exception as e:
            print(f"Warning: Failed to read or parse task list {task_list_path}: {e}")
    else:
         print(f"Warning: Task list file not found: {task_list_path}")
         
    # 3. Read Onboarding Doc content
    onboarding_content = ""
    if onboarding_doc_path.is_file():
        try:
            with open(onboarding_doc_path, "r", encoding="utf-8") as f:
                onboarding_content = f.read()
        except Exception as e:
             print(f"Warning: Failed to read onboarding doc {onboarding_doc_path}: {e}")
    else:
        print(f"Warning: Onboarding document not found: {onboarding_doc_path}")

    # 4. Perform Checks
    print("--- Validation Checks ---")
    all_checks_passed = True
    
    if not agents_found:
        print("No agents found in mailboxes or task list. Validation cannot proceed effectively.")
        return
        
    sorted_agents = sorted(list(agents_found))
    
    for agent in sorted_agents:
        agent_issues = []
        # Check Mailbox folder
        if not (mailbox_root / agent).is_dir():
            agent_issues.append("Missing Mailbox Directory")
            missing_mailbox.append(agent)
            
        # Check Onboarding Doc mention (simple case-sensitive check)
        # A more robust check might use regex for headings or specific formatting
        if onboarding_content and agent not in onboarding_content:
            agent_issues.append("Not mentioned in Onboarding Doc")
            missing_onboarding_doc.append(agent)
            
        # Check Command Handler - Placeholder - Requires specific knowledge
        # command_handler_exists = check_command_handler(agent) # Hypothetical function
        # if not command_handler_exists:
        #     agent_issues.append("Missing Command Handler (Check implementation)")
            
        if agent_issues:
            print(f"❌ Agent: {agent} - Issues: { ', '.join(agent_issues)}")
            all_checks_passed = False
        else:
            print(f"✅ Agent: {agent} - Checks passed (Mailbox Dir, Onboarding Doc mention)")
            
    print("\n--- Summary ---")
    print(f"Total Unique Agents Found: {len(agents_found)}")
    print(f" - From Mailboxes: {len(agents_in_mailbox)}")
    print(f" - From Task List: {len(agents_in_tasklist)}")
    
    if missing_mailbox:
        print(f"⚠️ Agents missing Mailbox Directory: {missing_mailbox}")
    if missing_onboarding_doc:
        print(f"⚠️ Agents not mentioned in {onboarding_doc_path.name}: {missing_onboarding_doc}")
        
    if all_checks_passed:
        print("\n✨ Validation Successful: All checked agents seem consistent.")
    else:
        print("\n❌ Validation Failed: Issues found with agent consistency.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate agent onboarding consistency.")
    parser.add_argument("--mailbox-root", default=str(DEFAULT_MAILBOX_ROOT.resolve()), help="Root directory for mailboxes.")
    parser.add_argument("--task-list", default=str(DEFAULT_TASK_LIST_PATH.resolve()), help="Path to the task_list.json file.")
    parser.add_argument("--onboarding-doc", default=str(DEFAULT_ONBOARDING_DOC.resolve()), help="Path to the AGENT_ONBOARDING.md file.")

    args = parser.parse_args()

    validate_onboarding(Path(args.mailbox_root).resolve(), 
                        Path(args.task_list).resolve(), 
                        Path(args.onboarding_doc).resolve()) 