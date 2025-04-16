#!/usr/bin/env python3
import os
from pathlib import Path

EXPECTED_DIRECTORIES = [
    "agents",
    "core",
    "runtime",
    "tools",
    "_agent_coordination"
]

EXPECTED_FILES = [
    "runtime/task_list.json",
    "_agent_coordination/dispatchers/task_dispatcher.py",
    # Adjusted expected agents based on earlier context
    # "agents/cursor_control_agent.py", 
    # "agents/social_task_orchestrator.py"
]

def check_structure(root: Path):
    print(f"\n📦 Checking project structure under: {root}\n")
    missing_dirs = []
    found_dirs = []
    for folder in EXPECTED_DIRECTORIES:
        path = root / folder
        if path.exists() and path.is_dir():
            status = "✅ Found"
            found_dirs.append(path)
        else:
            status = "❌ Missing"
            missing_dirs.append(folder)
        print(f"{status}: {folder}/")
    
    if missing_dirs:
        print(f"\n⚠️ Missing Expected Directories: {', '.join(missing_dirs)}")

    print("\n📄 Checking critical files:\n")
    missing_files = []
    for file in EXPECTED_FILES:
        path = root / file
        status = "✅ Found" if path.exists() and path.is_file() else "❌ Missing"
        if not (path.exists() and path.is_file()):
            missing_files.append(file)
        print(f"{status}: {file}")
    
    if missing_files:
        print(f"\n⚠️ Missing Expected Critical Files: {', '.join(missing_files)}")

    print("\n🧩 Checking for task_list.md files in expected modules:\n")
    missing_task_lists = []
    # Check only within the directories expected to exist or found
    dirs_to_check = [root / d for d in EXPECTED_DIRECTORIES]
    # Also check common top-level dirs found earlier
    dirs_to_check.extend([root / d for d in ['social', 'docs', 'tests', 'scripts', 'dreamforge', 'config']])
    
    checked_dirs = set() # Avoid checking the same dir twice if listed explicitly and found via iteration
    
    for dir_path in dirs_to_check:
        if not dir_path.is_dir() or dir_path in checked_dirs:
            continue
            
        checked_dirs.add(dir_path)
        tl_path = dir_path / "task_list.md"
        if tl_path.exists() and tl_path.is_file():
            status = "✅ Found"
        else:
            status = "❌ Missing"
            missing_task_lists.append(f"{dir_path.relative_to(root)}/task_list.md")
        print(f"{status} {dir_path.relative_to(root)}/task_list.md")
        
    if missing_task_lists:
         print(f"\n⚠️ Missing task_list.md Files in Key Modules: {', '.join(missing_task_lists)}")

    print("\n✨ Structure check complete.")

if __name__ == "__main__":
    import argparse
    # Assume the script is run from the workspace root or _agent_coordination
    # Make the default relative to the script's location for better portability
    default_root = Path(__file__).parent.parent.parent # Assumes tools/_agent_coordination/PROJECT_ROOT
    
    parser = argparse.ArgumentParser(description="Check project structure for key files and directories.")
    parser.add_argument("--root", default=str(default_root), help="Root directory of the project to check.")
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    if not root_path.is_dir():
        print(f"Error: Root path specified is not a valid directory: {root_path}")
        exit(1)
        
    check_structure(root_path) 