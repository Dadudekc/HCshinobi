import os

# --- Project Root Calculation ---
# Assumes this file is in core/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# -----------------------------

# --- Core Paths ---
TEMP_DIR = os.path.join(project_root, "temp")
LOG_DIR = os.path.join(project_root, "runtime") # Directory for logs
MEMORY_DIR = os.path.join(project_root, "memory") # Main memory dir
ANALYSIS_DIR = os.path.join(project_root, "analysis")
WORKFLOW_DIR_RELATIVE_TO_AGENTS = "workflows" # Used by workflow_agent

# --- File Paths ---
# Governance Log
GOVERNANCE_LOG_FILE = os.path.join(LOG_DIR, 'governance_memory.jsonl')

# Prompt Staging / Cursor Bridge
CURSOR_INPUT_FILE = os.path.join(TEMP_DIR, 'cursor_input.txt')
CURSOR_OUTPUT_FILE = os.path.join(TEMP_DIR, 'cursor_output.json')

# Project Scanner
PROJECT_ANALYSIS_FILE = os.path.join(ANALYSIS_DIR, 'project_analysis.json') # Assuming it lands here

# Performance Logger
PERFORMANCE_LOG_FILE = os.path.join(MEMORY_DIR, "performance_log.jsonl")

# Meta Architect
RULEBOOK_PATH = os.path.join(LOG_DIR, "rulebook.md") # Canonical rulebook
PROPOSAL_FILE = os.path.join(ANALYSIS_DIR, "rulebook_update_proposals.md")
REPORT_DIR = os.path.join(ANALYSIS_DIR, "architect_reports")

# Ensure base directories exist (optional, can be done by services)
# os.makedirs(TEMP_DIR, exist_ok=True)
# os.makedirs(LOG_DIR, exist_ok=True)
# os.makedirs(MEMORY_DIR, exist_ok=True)
# os.makedirs(ANALYSIS_DIR, exist_ok=True)
# os.makedirs(REPORT_DIR, exist_ok=True)

# --- Other Constants ---
# (Add other shared constants like timeouts, thresholds, etc. here if needed)

# --- Example Usage ---
if __name__ == "__main__":
    print("--- Testing Core Config Paths ---")
    print(f"Project Root: {project_root}")
    print(f"Log Dir: {LOG_DIR}")
    print(f"Temp Dir: {TEMP_DIR}")
    print(f"Governance Log: {GOVERNANCE_LOG_FILE}")
    print(f"Cursor Input: {CURSOR_INPUT_FILE}")
    print(f"Workflow Dir (relative): {WORKFLOW_DIR_RELATIVE_TO_AGENTS}")
    print("--- Config Test Complete ---") 