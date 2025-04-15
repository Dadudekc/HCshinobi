import json
# from stall_detector import categorize_stall # Assumes stall_detector exists
from pathlib import Path

def categorize_stall(log_snippet: str) -> str:
    snippet = log_snippet.lower()
    if "awaiting agent commander signal" in snippet:
        return "AWAIT_CONFIRM"
    if "no new messages found" in snippet or "waiting for user input" in snippet:
        return "NO_INPUT"
    if "no tasks" in snippet or "task queue empty" in snippet:
        return "NEEDS_TASKS"
    if "loop detected" in snippet or "repeating prompt" in snippet:
        return "LOOP_BREAK"
    if "context missing" in snippet or "unable to load memory" in snippet:
        return "MISSING_CONTEXT"
    if "unsure what to do" in snippet or "unclear goal" in snippet:
        return "UNCLEAR_OBJECTIVE"
    return "UNCATEGORIZED" # Changed from UNCLEAR_OBJECTIVE default

def produce_project_context(conversation_log: str, project_dir_str: str, return_dict=False): # Added return_dict
    # Guard for Empty Conversation Log
    if not conversation_log or len(conversation_log.strip()) == 0:
        print("Error: Empty conversation log. Cannot generate context.")
        return None

    project_dir = Path(project_dir_str)
    if not project_dir.is_dir():
        print(f"Error: Project directory not found: {project_dir}")
        return None

    log_snippet = conversation_log[-1000:] # Last 1000 chars for analysis
    stall_category = categorize_stall(log_snippet)

    # Basic file gathering - enhance later with context relevance
    try:
        project_files = [str(p.relative_to(project_dir)) for p in project_dir.rglob("*.py") if ".venv" not in str(p)]
    except Exception as e:
        print(f"Error scanning project files: {e}")
        project_files = []

    context = {
        "stall_category": stall_category,
        "conversation_snippet": log_snippet, 
        "relevant_files": project_files[:10],  # Limit for brevity
        "project_root": str(project_dir),
        "suggested_action_keyword": { # Keywords for Cursor prompt generation
            "NO_INPUT": "Check task list and resume autonomous operation.",
            "NEEDS_TASKS": "Generate next logical task based on project goals.",
            "LOOP_BREAK": "Diagnose and fix the execution loop error.",
            "MISSING_CONTEXT": "Attempt context reload or state reset.",
            "AWAIT_CONFIRM": "Analyze context and proceed if safe, else summarize required confirmation.",
            "UNCLEAR_OBJECTIVE": "Review onboarding/goals and define next step."
        }.get(stall_category, "Perform general diagnostics.")
    }

    if return_dict: # Added conditional return
        return context

    # Define output path (consider making this configurable)
    # Using a more generic name accessible by other tools
    output_path = project_dir / "agent_bridge_context.json" 

    try:
        with output_path.open("w", encoding='utf-8') as f:
            json.dump(context, f, indent=2)
        print(f"Project context saved to: {output_path}") # This print only happens if not returning dict
        return output_path
    except Exception as e:
        print(f"Error writing project context file: {e}")
        return None

# Example Usage:
# if __name__ == "__main__":
#     # Example log snippet (replace with actual log reading)
#     log_example = "...Awaiting Agent Commander signal..." 
#     produce_project_context(log_example, project_dir_str=".") # Run from workspace root 