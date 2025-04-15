import pytest
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

# Assuming the agent is importable from the project structure
# Adjust the import path if necessary based on your project layout
from agents.stall_recovery_agent import StallRecoveryAgent

# --- Fixtures ---

@pytest.fixture
def temp_project(tmp_path):
    """Creates a temporary project directory structure for testing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "logs").mkdir()
    (project_dir / "tools").mkdir() # For potential context producer import check
    # Create dummy context producer if needed for import
    (project_dir / "tools" / "project_context_producer.py").touch() 
    # Create dummy log file
    log_file = project_dir / "logs" / "agent_ChatCommander.log"
    log_file.touch()
    # Create dummy task list
    task_list = project_dir / "task_list.json"
    task_list.write_text("[]", encoding="utf-8")
    return project_dir

@pytest.fixture
def recovery_agent(temp_project):
    """Provides an instance of StallRecoveryAgent initialized with temp paths."""
    # Shorten check interval for faster testing if needed, but use default here
    agent = StallRecoveryAgent(
        project_root=str(temp_project), 
        log_file_path="logs/agent_ChatCommander.log",
        check_interval=1 # Use a short interval for testing if running live checks
    )
    # Ensure log file path is correctly set
    agent.log_file_path = temp_project / "logs" / "agent_ChatCommander.log"
    return agent

# --- Mock Data ---

STALL_CONTEXT_MAP = {
    "NO_INPUT": {
        "stall_category": "NO_INPUT",
        "conversation_snippet": "...no new messages found...", 
        "relevant_files": ["main.py", "utils.py"],
        "project_root": ".",
        "suggested_action_keyword": "Check task list and resume autonomous operation."
    },
    "AWAIT_CONFIRM": {
        "stall_category": "AWAIT_CONFIRM",
        "conversation_snippet": "...awaiting agent commander signal...",
        "relevant_files": ["config.py"],
        "project_root": ".",
        "suggested_action_keyword": "Analyze context and proceed if safe, else summarize required confirmation."
    },
    # Add mock context for other categories (LOOP_BREAK, MISSING_CONTEXT, UNCLEAR_OBJECTIVE)
    "LOOP_BREAK": {
        "stall_category": "LOOP_BREAK", 
        "conversation_snippet": "...loop detected...", 
        "relevant_files": ["agent_loop.py"], 
        "project_root": ".", 
        "suggested_action_keyword": "Diagnose and fix the execution loop error."
    },
     "MISSING_CONTEXT": {
        "stall_category": "MISSING_CONTEXT", 
        "conversation_snippet": "...context missing...", 
        "relevant_files": ["memory_manager.py"], 
        "project_root": ".", 
        "suggested_action_keyword": "Attempt context reload or state reset."
    },
     "UNCLEAR_OBJECTIVE": {
        "stall_category": "UNCLEAR_OBJECTIVE", 
        "conversation_snippet": "...unclear goal...", 
        "relevant_files": ["AGENT_ONBOARDING.md"], 
        "project_root": ".", 
        "suggested_action_keyword": "Review onboarding/goals and define next step."
    }
}

# --- Test Cases ---

@patch('agents.stall_recovery_agent.produce_project_context')
@patch('pathlib.Path.stat')
@patch('builtins.open', new_callable=mock_open)
@patch('agents.stall_recovery_agent.StallRecoveryAgent.dispatch_recovery_task') # Mock dispatch to isolate checks
def test_stall_detection_and_context(mock_dispatch, mock_file_open, mock_stat, mock_produce_context, recovery_agent, temp_project):
    """T3.2.1 - T3.2.5 (Combined): Test stall detection and context analysis trigger."""
    # Setup mock stat to simulate unchanged log file size > 0
    mock_stat.return_value.st_size = 1024
    recovery_agent.last_log_size = 1024 # Simulate previous size

    # Setup mock log file content for context producer
    log_content = "... some log data ... awaiting agent commander signal ... more data ..."
    mock_file_open.return_value.read.return_value = log_content

    # Setup mock context producer to return specific context
    mock_produce_context.return_value = STALL_CONTEXT_MAP["AWAIT_CONFIRM"]

    # Trigger the check
    log_tail = recovery_agent.check_for_stall()
    assert log_tail is not None # Stall detected
    recovery_agent.attempt_recovery(log_tail)

    # Assertions
    mock_produce_context.assert_called_once_with(log_tail, str(recovery_agent.project_root), return_dict=True)
    mock_dispatch.assert_called_once() # Check that dispatch was called
    assert mock_dispatch.call_args[0][0]['stall_category'] == "AWAIT_CONFIRM" # Check correct context passed

# Add separate tests for each category if more granular checks are needed

# T3.2.6: Test Recovery Task Injection (Verifying dispatch_recovery_task internal logic)
@patch('builtins.open', new_callable=mock_open, read_data='[]') # Mock file open for task list
@patch('json.dump')
def test_recovery_task_injection(mock_json_dump, mock_file_open, recovery_agent, temp_project):
    """T3.2.6 & T3.2.8: Verify task is correctly formatted and written to task_list.json."""
    context_to_dispatch = STALL_CONTEXT_MAP["NO_INPUT"]
    task_list_path = temp_project / "task_list.json"
    
    # Call the actual dispatch method
    task_id = recovery_agent.dispatch_recovery_task(context_to_dispatch)

    # Assert file handling
    mock_file_open.assert_called_once_with(task_list_path, "r+", encoding="utf-8")
    
    # Assert json.dump call
    assert mock_json_dump.call_count == 1
    args, kwargs = mock_json_dump.call_args
    dispatched_tasks = args[0] # First arg to json.dump is the object
    assert isinstance(dispatched_tasks, list)
    assert len(dispatched_tasks) == 1
    task = dispatched_tasks[0]

    # T3.2.8: Assert task structure and content
    assert task["task_id"] == task_id
    assert task["status"] == "PENDING"
    assert task["task_type"] == "resume_operation" # Specific to NO_INPUT
    assert task["action"] == STALL_CONTEXT_MAP["NO_INPUT"]["suggested_action_keyword"]
    assert "params" in task
    assert task["params"]["stall_category"] == "NO_INPUT"
    assert task["params"]["instruction_hint"] is not None
    assert task["target_agent"] == "CursorControlAgent"
    assert task["timestamp_created"] is not None

# T3.2.7: Test Stall Logging (Verifying log_stall_event internal logic)
@patch('builtins.open', new_callable=mock_open)
@patch('json.dumps') # We check the object passed to dumps
def test_stall_logging(mock_json_dumps, mock_file_open, recovery_agent, temp_project):
    """T3.2.7: Verify stall event is correctly logged."""
    context_to_log = STALL_CONTEXT_MAP["LOOP_BREAK"]
    context_to_log["recovery_task_id"] = "recovery_loop_break_12345"
    log_path = temp_project / "logs" / "stall_events.log"

    # Call the actual logging method
    recovery_agent.log_stall_event(context_to_log, recovery_dispatched=True)

    # Assert file handling
    mock_file_open.assert_called_once_with(log_path, "a", encoding="utf-8")
    mock_file_open().write.assert_called_once() # Check that write was called

    # Assert the content passed to json.dumps
    assert mock_json_dumps.call_count == 1
    args, kwargs = mock_json_dumps.call_args
    logged_entry = args[0] # First arg to json.dumps

    assert logged_entry["stall_category"] == "LOOP_BREAK"
    assert logged_entry["recovery_dispatched"] is True
    assert logged_entry["recovery_task_id"] == "recovery_loop_break_12345"
    assert "timestamp" in logged_entry
    assert logged_entry["suggested_action_keyword"] == STALL_CONTEXT_MAP["LOOP_BREAK"]["suggested_action_keyword"]

# Placeholder for T3.2.8 (partially covered in T3.2.6, can add more specific checks)
def test_task_fields_populated():
    """T3.2.8: Further detailed checks on task field population (if needed)."""
    # This is largely covered by test_recovery_task_injection
    # Add more specific checks here if variations need testing
    pass 

# Example of testing a specific category trigger (complementary to combined test)
@patch('agents.stall_recovery_agent.produce_project_context')
@patch('pathlib.Path.stat')
@patch('builtins.open', new_callable=mock_open)
@patch('agents.stall_recovery_agent.StallRecoveryAgent.dispatch_recovery_task')
def test_specific_stall_category_no_input(mock_dispatch, mock_file_open, mock_stat, mock_produce_context, recovery_agent):
    """Verify NO_INPUT category triggers correct task type via dispatch call."""
    mock_stat.return_value.st_size = 500
    recovery_agent.last_log_size = 500
    mock_file_open.return_value.read.return_value = "... no new messages ..."
    mock_produce_context.return_value = STALL_CONTEXT_MAP["NO_INPUT"]

    log_tail = recovery_agent.check_for_stall()
    assert log_tail is not None
    recovery_agent.attempt_recovery(log_tail)

    mock_dispatch.assert_called_once()
    dispatched_context = mock_dispatch.call_args[0][0]
    assert dispatched_context["stall_category"] == "NO_INPUT"
    # We don't check the *generated* task_type here directly because dispatch_recovery_task
    # is mocked. We tested its internal logic in test_recovery_task_injection.
    # We just check the correct context was *passed* to the (mocked) dispatch function. 