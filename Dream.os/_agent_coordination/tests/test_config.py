import os
from pathlib import Path
import pytest
from config import (
    WORKSPACE_ROOT, PROPOSALS_DIR, LOG_DIR, TOOLS_DIR,
    RULEBOOK_PATH, PROPOSALS_FILE_PATH, PROJECT_BOARD_PATH,
    REFLECTION_LOG_FILE, SECURITY_SCAN_LOG_FILE, AGENT_ACTIVITY_LOG_FILE,
    INBOX_SUBDIR, OUTBOX_SUBDIR, INBOX_PROCESSED_SUBDIR,
    INBOX_ERROR_SUBDIR, OUTBOX_PROCESSED_SUBDIR, OUTBOX_ERROR_SUBDIR,
    MESSAGE_FORMAT, PROPOSAL_SEPARATOR,
    STATUS_ACCEPTED, STATUS_APPLIED, STATUS_ERROR_APPLYING,
    STATUS_BLOCKED_BY_RULE, STATUS_PROPOSED, STATUS_DONE, STATUS_ERROR
)

def log_event(event_type, agent_id, data):
    """Mock log_event function for test coverage reporting."""
    print(f"[{event_type}] Agent: {agent_id}, Data: {data}")

def test_workspace_root_exists():
    """Test that WORKSPACE_ROOT points to a valid directory."""
    assert WORKSPACE_ROOT.exists()
    assert WORKSPACE_ROOT.is_dir()
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_workspace_root_exists"})

def test_directory_paths():
    """Test that directory paths are properly configured."""
    # Test that paths are relative to workspace root
    assert PROPOSALS_DIR.parent == WORKSPACE_ROOT
    assert LOG_DIR.parent == WORKSPACE_ROOT
    assert TOOLS_DIR.parent == WORKSPACE_ROOT
    
    # Test directory names
    assert PROPOSALS_DIR.name == "proposals"
    assert LOG_DIR.name == "logs"
    assert TOOLS_DIR.name == "tools"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_directory_paths"})

def test_file_paths():
    """Test that file paths are properly configured."""
    # Test that paths are in correct directories
    assert PROPOSALS_FILE_PATH.parent == PROPOSALS_DIR
    assert RULEBOOK_PATH.parent == WORKSPACE_ROOT
    assert PROJECT_BOARD_PATH.parent == WORKSPACE_ROOT
    
    # Test file names
    assert RULEBOOK_PATH.name == "rulebook.md"
    assert PROPOSALS_FILE_PATH.name == "rulebook_update_proposals.md"
    assert PROJECT_BOARD_PATH.name == "project_board.md"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_file_paths"})

def test_log_file_paths():
    """Test that log file paths are properly configured."""
    # Test that paths are in log directory
    assert REFLECTION_LOG_FILE.parent == LOG_DIR
    assert SECURITY_SCAN_LOG_FILE.parent == LOG_DIR
    assert AGENT_ACTIVITY_LOG_FILE.parent == LOG_DIR
    
    # Test file names
    assert REFLECTION_LOG_FILE.name == "reflection_log.md"
    assert SECURITY_SCAN_LOG_FILE.name == "security_scan_log.md"
    assert AGENT_ACTIVITY_LOG_FILE.name == "agent_activity.log"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_log_file_paths"})

def test_mailbox_subdirs():
    """Test that mailbox subdirectory names are properly configured."""
    # Test that subdirectory names are strings and non-empty
    assert isinstance(INBOX_SUBDIR, str) and INBOX_SUBDIR
    assert isinstance(OUTBOX_SUBDIR, str) and OUTBOX_SUBDIR
    assert isinstance(INBOX_PROCESSED_SUBDIR, str) and INBOX_PROCESSED_SUBDIR
    assert isinstance(INBOX_ERROR_SUBDIR, str) and INBOX_ERROR_SUBDIR
    assert isinstance(OUTBOX_PROCESSED_SUBDIR, str) and OUTBOX_PROCESSED_SUBDIR
    assert isinstance(OUTBOX_ERROR_SUBDIR, str) and OUTBOX_ERROR_SUBDIR
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_mailbox_subdirs"})

def test_message_format():
    """Test that message format is properly configured."""
    assert MESSAGE_FORMAT == ".json"
    assert PROPOSAL_SEPARATOR == "\n---\n"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_message_format"})

def test_status_constants():
    """Test that status constants are properly configured."""
    # Test that status constants are strings and non-empty
    assert isinstance(STATUS_ACCEPTED, str) and STATUS_ACCEPTED
    assert isinstance(STATUS_APPLIED, str) and STATUS_APPLIED
    assert isinstance(STATUS_ERROR_APPLYING, str) and STATUS_ERROR_APPLYING
    assert isinstance(STATUS_BLOCKED_BY_RULE, str) and STATUS_BLOCKED_BY_RULE
    assert isinstance(STATUS_PROPOSED, str) and STATUS_PROPOSED
    assert isinstance(STATUS_DONE, str) and STATUS_DONE
    assert isinstance(STATUS_ERROR, str) and STATUS_ERROR
    
    # Test status values
    assert STATUS_ACCEPTED == "Accepted"
    assert STATUS_APPLIED == "Applied"
    assert STATUS_ERROR_APPLYING == "Error Applying"
    assert STATUS_BLOCKED_BY_RULE == "Blocked by Rule Conflict"
    assert STATUS_PROPOSED == "Proposed"
    assert STATUS_DONE == "Done"
    assert STATUS_ERROR == "Error"
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_status_constants"})

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 