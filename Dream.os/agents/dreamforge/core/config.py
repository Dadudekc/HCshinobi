"""Configuration module for Dream.OS."""
import os
from pathlib import Path

# Base paths
ROOT_DIR = Path(__file__).parent.parent.parent
WORKSPACE_DIR = ROOT_DIR / "workspace"
MEMORY_DIR = ROOT_DIR / "memory"
LOGS_DIR = ROOT_DIR / "logs"

# Ensure directories exist
for directory in [WORKSPACE_DIR, MEMORY_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Agent configuration
AGENT_CONFIG = {
    "max_retries": 3,
    "timeout_seconds": 30,
    "batch_size": 100
}

# Workflow configuration
WORKFLOW_STORAGE_DIR = ROOT_DIR / "workflows"
WORKFLOW_STORAGE_DIR.mkdir(exist_ok=True)

# Cursor bridge configuration
CURSOR_INPUT_FILE = ROOT_DIR / "cursor_input.json"
CURSOR_OUTPUT_FILE = ROOT_DIR / "cursor_output.json"

# Memory configuration
MEMORY_CONFIG = {
    "max_history": 1000,
    "cleanup_interval": 3600  # 1 hour
}

# Project analysis
PROJECT_ANALYSIS_FILE = ROOT_DIR / "project_analysis.json"

# Environment variables (with defaults)
DEBUG = os.getenv("DREAM_OS_DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("DREAM_OS_LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("DREAM_OS_ENV", "development") 