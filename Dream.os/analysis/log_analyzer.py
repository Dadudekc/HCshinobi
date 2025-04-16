import json
import os
from collections import Counter, defaultdict
from datetime import datetime

LOG_PATH = os.path.join("memory", "performance_log.jsonl")

def load_logs():
    if not os.path.exists(LOG_PATH):
        print(f"Performance log file not found: {LOG_PATH}")
        return []
    try:
        with open(LOG_PATH, 'r', encoding='utf-8') as f:
            # Filter out empty lines that might occur
            return [json.loads(line) for line in f if line.strip()] 
    except Exception as e:
        print(f"Error loading or parsing log file {LOG_PATH}: {e}")
        return []

def analyze():
    logs = load_logs()
    if not logs:
        print("No performance logs to analyze.")
        return

    agent_stats = defaultdict(lambda: Counter())
    recent_errors = []
    total_tasks = len(logs)

    print(f"Analyzing {total_tasks} log entries...")

    # Process all logs for overall stats
    for entry in logs:  
        agent_id = entry.get('agent_id', 'UnknownAgent')
        status = entry.get('status', 'UnknownStatus')
        agent_stats[agent_id][status] += 1

        if status == "ERROR" or status == "FAILURE":
            recent_errors.append({
                "task_id": entry.get("task_id", "N/A"),
                "agent": agent_id,
                "error": entry.get("error_message", "No error message"),
                "timestamp": entry.get("end_time", entry.get("log_timestamp"))
            })

    print("\n--- Task Success/Failure Summary ---")
    for agent, stats in agent_stats.items():
        success = stats.get('SUCCESS', 0)
        failure = stats.get('FAILURE', 0)
        error = stats.get('ERROR', 0)
        total = success + failure + error
        success_rate = (success / total * 100) if total > 0 else 0
        print(f"> {agent}: Total={total}, Success={success} ({success_rate:.1f}%), Failure={failure}, Error={error}")
        # Optional: print raw counts: print(f"{agent}: {dict(stats)}")

    if recent_errors:
        print("\n--- Recent Errors (Last 10) ---")
        # Sort errors by timestamp descending to show newest first
        recent_errors.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        for e in recent_errors[:10]: 
            print(f"- [{e.get('timestamp', 'No Timestamp')}] Task: {e.get('task_id', 'N/A')} Agent: {e['agent']} -> {e['error']}")
    else:
        print("\n--- No Recent Errors Found ---")

if __name__ == "__main__":
    analyze() 