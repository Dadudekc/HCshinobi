#!/usr/bin/env python
import time
import argparse
import random

print("--- Running diagnostics.py ---")

parser = argparse.ArgumentParser(description="Run simulated system diagnostics.")
parser.add_argument("--level", default="basic", choices=["basic", "full"], help="Level of diagnostics to run")
parser.add_argument("--auto", action="store_true", help="Run in automated mode")
args = parser.parse_args()

print(f"Running {args.level} diagnostics... (Auto mode: {args.auto})")

# Simulate diagnostic steps
print("Checking agent process status...")
time.sleep(0.3)
print("  StallRecoveryAgent: Running")
print("  TaskDispatcher: Running")
print("  CursorControlAgent: Running")

print("Checking mailbox queue lengths...")
time.sleep(0.2)
print("  CursorControlAgent/inbox: 0 messages")

print("Checking task list health...")
time.sleep(0.4)
# Simulate finding an old failed task
has_old_failed = random.choice([True, False])
if has_old_failed:
    print("  WARNING: Found old FAILED tasks in task_list.json")
else:
    print("  Task list looks clean.")

if args.level == "full":
    print("Running full checks...")
    print("  Checking context file integrity...")
    time.sleep(0.5)
    print("  Context files OK.")

print("Diagnostics complete.")

# Exit with 0 if basic checks pass, or 1 if warning found
exit_code = 1 if has_old_failed else 0 
print(f"Exiting with code: {exit_code}")
exit(exit_code) 