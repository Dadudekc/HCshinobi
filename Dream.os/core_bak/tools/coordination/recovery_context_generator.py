import json
from pathlib import Path
import argparse
from project_scanner import ProjectScanner
import datetime # Add datetime import
import os # Add os import for directory creation
import shutil # Add shutil for file copying

# --- Constants --- #
# Define output directory relative to the script's location
TOOLS_DIR = Path(__file__).parent.resolve()
WORKSPACE_ROOT = TOOLS_DIR.parent # Assumes tools/ is one level down from root
# Base output directory for all contexts
BASE_OUTPUT_DIR = WORKSPACE_ROOT / "outputs" / "recovery_contexts" 
LATEST_CONTEXT_FILENAME_SUFFIX = "_latest.json"


# --- STALL CLASSIFICATION --- #
def categorize_stall(log_text: str) -> str:
    log_text = log_text.lower()
    if "awaiting directive" in log_text or "passive mode" in log_text:
        return "LOOP_BREAK"
    if "awaiting user input" in log_text:
        return "NO_INPUT"
    if "missing context" in log_text:
        return "MISSING_CONTEXT"
    if "no tasks" in log_text:
        return "NEEDS_TASKS"
    return "UNCLEAR_OBJECTIVE"

# --- RECOVERY CONTEXT BUILDER --- #
def generate_recovery_context(agent_name: str, log_text: str, project_root: Path) -> dict:
    scanner = ProjectScanner(project_root=project_root)
    scanner.scan_project()
    analysis = scanner.analysis

    agent_name_lower = agent_name.lower()
    matched_files = []
    candidate_methods = []

    # Search for agent class in live scan
    for file_path, data in analysis.items():
        if not file_path.endswith(".py"):
            continue
        for class_name, class_data in data.get("classes", {}).items():
            # More robust matching: check if agent name is a substring of class name
            if agent_name_lower in class_name.lower(): 
                matched_files.append(file_path)
                candidate_methods.extend(class_data.get("methods", []))

    stall_category = categorize_stall(log_text)

    fix_hint = {
        "LOOP_BREAK": "Check that the agent's `run_once()` or feedback loop is not skipped. Ensure fallback to mailbox/tasklist works.",
        "NO_INPUT": "Verify that agent handles idle states by checking shared tasklist or onboarding instructions.",
        "MISSING_CONTEXT": "Ensure agent reloads memory or reinitializes context on restart.",
        "NEEDS_TASKS": "Detect taskless startup and derive goals from system state.",
        "UNCLEAR_OBJECTIVE": "Check onboarding. Inject missing objectives or redefine agent purpose.",
    }.get(stall_category, "Review agent logs and project state to diagnose.")

    return {
        "agent": agent_name,
        "stall_category": stall_category,
        "detected_issue": log_text.strip()[:500],
        "relevant_files": matched_files[:5],
        "recommended_fix": fix_hint,
        "project_root": str(project_root.resolve()),
        "task_summary": f"Recover stalled agent `{agent_name}`. Category: {stall_category}. Methods: {', '.join(candidate_methods[:5]) or 'unknown'}.",
        "context_snippet": log_text.strip()[:300],
        # Add generation timestamp
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

# --- CLI WRAPPER --- #
def main():
    parser = argparse.ArgumentParser(description="Live-scan recovery context generator for Dream.OS agents.")
    parser.add_argument("--agent", required=True, help="Name of the stalled agent class (e.g., ArchitectsEdgeAgent)")
    parser.add_argument("--log", required=True, help="Path to the stalled log file or inline string")
    parser.add_argument("--inline", action="store_true", help="Use --log as inline text")
    parser.add_argument("--project-root", default=".", help="Path to project directory (defaults to cwd)")
    # Remove the --output argument, as it's now handled internally
    # parser.add_argument("--output", default="recovery_context.json", help="Where to save the output JSON") 

    args = parser.parse_args()
    project_root = Path(args.project_root).resolve()
    agent_name = args.agent
    log_text = args.log if args.inline else Path(args.log).read_text()

    # Generate the context
    result = generate_recovery_context(agent_name, log_text, project_root)

    # --- File Output Logic --- # 
    now = datetime.datetime.now(datetime.timezone.utc)
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    
    # Define agent-specific output directory
    agent_output_dir = BASE_OUTPUT_DIR / agent_name
    agent_output_dir.mkdir(parents=True, exist_ok=True) # Ensure it exists
    
    # Define timestamped and latest file paths
    timestamped_filename = f"{agent_name}_{timestamp_str}.json"
    timestamped_filepath = agent_output_dir / timestamped_filename
    latest_filename = f"{agent_name}{LATEST_CONTEXT_FILENAME_SUFFIX}" 
    latest_filepath = agent_output_dir / latest_filename # Place latest within agent dir too

    # Save the timestamped file
    try:
        with open(timestamped_filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Timestamped recovery context saved to: {timestamped_filepath}")
    except Exception as e:
        print(f"\n❌ Error saving timestamped recovery context to {timestamped_filepath}: {e}", file=sys.stderr)
        # Decide if we should exit or just warn?

    # Update the latest file (using copy for atomicity/simplicity)
    try:
        with open(latest_filepath, "w", encoding="utf-8") as f:
             json.dump(result, f, indent=2)
        # Alternative: shutil.copyfile(timestamped_filepath, latest_filepath)
        print(f"✅ Latest recovery context updated at: {latest_filepath}")
    except Exception as e:
        print(f"\n❌ Error updating latest recovery context file {latest_filepath}: {e}", file=sys.stderr)

    # Output summary to console
    print(f"\n🧠 Stall: {result['stall_category']}")
    print(f"📁 Files: {', '.join(result['relevant_files']) or 'None found'}")
    print(f"📝 Summary: {result['task_summary']}")

if __name__ == "__main__":
    main() 