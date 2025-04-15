import os
import json
import datetime
from pathlib import Path

# === CONFIGURATION ===
PROJECT_ROOT = Path("D:/Dream.OS/").resolve()
AGENT_IDS = [1, 2, 3, 4, 5, 6, 7, 8]  # Expand as needed

def agent_mailbox(agent_id):
    agent_dir = PROJECT_ROOT / "mailbox" / f"agent_{agent_id}"
    return {
        "dir": agent_dir,
        "tasks": agent_dir / "task_list.json",
        "inbox": agent_dir / "inbox" / "usage_block_status.json",
        "outbox": agent_dir / "outbox"
    }

PROJECT_BOARD = PROJECT_ROOT / "project_board.json"

def now_str():
    return datetime.datetime.utcnow().isoformat() + "Z"

def file_has_main_block(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return 'if __name__ == "__main__"' in f.read()
    except (UnicodeDecodeError, FileNotFoundError):
        return True

def init_mailbox_if_needed(agent_id):
    mailbox = agent_mailbox(agent_id)
    for path in [mailbox["tasks"], mailbox["inbox"]]:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)
    return mailbox

def add_task_to_mailbox(mailbox, task):
    with open(mailbox["tasks"], "r+", encoding="utf-8") as f:
        tasks = json.load(f)
        if not any(t["task_id"] == task["task_id"] for t in tasks):
            tasks.append(task)
            f.seek(0)
            json.dump(tasks, f, indent=2)
            f.truncate()

def add_project_board_update(entry):
    PROJECT_BOARD.parent.mkdir(parents=True, exist_ok=True)
    if PROJECT_BOARD.exists():
        with open(PROJECT_BOARD, "r+", encoding="utf-8") as f:
            board = json.load(f)
            board.append(entry)
            f.seek(0)
            json.dump(board, f, indent=2)
            f.truncate()
    else:
        with open(PROJECT_BOARD, "w", encoding="utf-8") as f:
            json.dump([entry], f, indent=2)

def enqueue_tasks_to_all_agents(file_path: Path):
    abs_path = str(file_path.resolve())
    filename = file_path.name
    task_id = f"INJECT_USAGE_BLOCK_{filename}"
    timestamp = now_str()

    board_entry = {
        "component": filename,
        "usage_block": "missing",
        "last_checked": timestamp,
        "path": abs_path
    }
    add_project_board_update(board_entry)

    for agent_id in AGENT_IDS:
        mailbox = init_mailbox_if_needed(agent_id)
        task = {
            "agent_id": f"agent_{agent_id}",
            "task_id": task_id,
            "description": f"Inject and validate __main__ usage block for {filename}",
            "status": "pending",
            "priority": "high",
            "file": abs_path,
            "timestamp": timestamp
        }
        add_task_to_mailbox(mailbox, task)
        print(f"[QUEUED] {filename} → agent_{agent_id}")

def scan_for_usage_block_tasks():
    for root, _, files in os.walk(PROJECT_ROOT):
        for filename in files:
            if filename.endswith(".py") and "__pycache__" not in root:
                full_path = Path(root) / filename
                if not file_has_main_block(full_path):
                    enqueue_tasks_to_all_agents(full_path)

if __name__ == "__main__":
    print(">>> 🧠 Scanning for usage block gaps...")
    scan_for_usage_block_tasks()
    print(">>> ✅ Tasks distributed to agent mailboxes.")
