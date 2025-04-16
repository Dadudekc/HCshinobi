# _agent_coordination/config.py

from pathlib import Path

# --- Core Paths ---
WORKSPACE_ROOT = Path(__file__).parent.resolve()

# --- Key Directories --- #
PROPOSALS_DIR = WORKSPACE_ROOT / "proposals"
LOG_DIR = WORKSPACE_ROOT / "logs"
TOOLS_DIR = WORKSPACE_ROOT / "tools"

# --- Key File Paths --- #
RULEBOOK_PATH = WORKSPACE_ROOT / "rulebook.md"
PROPOSALS_FILE_PATH = PROPOSALS_DIR / "rulebook_update_proposals.md"
PROJECT_BOARD_PATH = WORKSPACE_ROOT / "project_board.md"

# --- Logging Files --- #
REFLECTION_LOG_FILE = LOG_DIR / "reflection_log.md"
SECURITY_SCAN_LOG_FILE = LOG_DIR / "security_scan_log.md"
AGENT_ACTIVITY_LOG_FILE = LOG_DIR / "agent_activity.log"

# --- Mailbox Structure --- #
INBOX_SUBDIR = "inbox"
OUTBOX_SUBDIR = "outbox"
INBOX_PROCESSED_SUBDIR = "inbox_processed"
INBOX_ERROR_SUBDIR = "inbox_errors"
OUTBOX_PROCESSED_SUBDIR = "outbox_processed"
OUTBOX_ERROR_SUBDIR = "outbox_errors"

# --- Message Formatting --- #
MESSAGE_FORMAT = ".json"
PROPOSAL_SEPARATOR = "\n---\n"

# --- Status Constants --- #
STATUS_ACCEPTED = "Accepted"
STATUS_APPLIED = "Applied"
STATUS_ERROR_APPLYING = "Error Applying"
STATUS_BLOCKED_BY_RULE = "Blocked by Rule Conflict"
STATUS_PROPOSED = "Proposed"
STATUS_DONE = "Done"
STATUS_ERROR = "Error" 