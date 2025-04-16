import os
import pytest
import json
import time
import datetime
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Need to import the module itself to mock its constants
import monitor_analyzer_agent

from monitor_analyzer_agent import (
    load_rules_from_rulebook,
    load_tasks, # Assuming task loading exists
    is_halt_unnecessary,
    log_unnecessary_halt,
    broadcast_alert,
    request_rulebook_update,
    HaltStatusHandler
)

# --- Fixtures --- #

@pytest.fixture
def temp_rulebook_for_monitor(tmp_path):
    rulebook_content = """
### Rule 1
- ID: GEN-001
```yaml
rules:
  - id: GEN-001
    description: Must avoid halt unless input needed.
    keywords: [halt, input, proceed]
    applies_to: all_agents
```
### Rule 2
- ID: GEN-002
```yaml
rules:
  - id: GEN-002
    description: Specific agent rule.
    keywords: [agent2, specific]
    applies_to: Agent2
```
### Rule 3
- ID: GEN-003
```yaml
rules:
  - id: GEN-003
    description: Rulebook update rule.
    keywords: [update, clarify]
    applies_to: monitor_analyzer_agent # Monitor needs this rule
```
"""
    agent1_dir = tmp_path / "Agent1"
    agent1_dir.mkdir(exist_ok=True)
    file_path = agent1_dir / "rulebook.md"
    file_path.write_text(rulebook_content, encoding='utf-8')
    return str(file_path)

@pytest.fixture
def temp_task_pool_empty(tmp_path):
    # Simulate case where task pool is empty or doesn't exist
    file_path = tmp_path / "Agent1" / "project_board" / "task_pool.json"
    # Ensure parent dirs exist for path construction, even if file doesn't
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return str(file_path)

@pytest.fixture
def temp_logs_path(tmp_path):
    # Fixture specifically for the log file path
    log_file = tmp_path / "logs" / "unnecessary_halts.md"
    log_file.parent.mkdir(exist_ok=True)
    log_file.touch()
    return str(log_file)

@pytest.fixture
def temp_agent_dirs_root(tmp_path):
    # Fixture specifically for the root monitoring directory
    # Create structure for monitor to broadcast to
    agent1_inbox = tmp_path / "Agent1" / "inbox"
    agent2_inbox = tmp_path / "Agent2" / "inbox"
    agent1_outbox = tmp_path / "Agent1" / "outbox" # For handler test
    agent2_outbox = tmp_path / "Agent2" / "outbox" # For handler test
    agent1_inbox.mkdir(parents=True, exist_ok=True)
    agent2_inbox.mkdir(parents=True, exist_ok=True)
    agent1_outbox.mkdir(parents=True, exist_ok=True)
    agent2_outbox.mkdir(parents=True, exist_ok=True)
    return str(tmp_path)

@pytest.fixture
def temp_proposals_path(tmp_path):
    # Fixture specifically for the proposals file path
    proposals_file = tmp_path / "Agent1" / "rulebook_update_proposals.md"
    proposals_file.parent.mkdir(exist_ok=True)
    proposals_file.touch()
    return str(proposals_file)

# --- Tests for Rule/Task Loading --- #

def test_load_rules(temp_rulebook_for_monitor):
    rules = load_rules_from_rulebook(temp_rulebook_for_monitor)
    assert len(rules) == 3
    assert rules[0]['id'] == 'GEN-001'
    assert rules[2]['id'] == 'GEN-003'

def test_load_tasks_file_not_found(temp_task_pool_empty):
    tasks = load_tasks(temp_task_pool_empty)
    assert tasks == []

# --- Tests for is_halt_unnecessary --- #

@pytest.fixture
def sample_rules(temp_rulebook_for_monitor):
    return load_rules_from_rulebook(temp_rulebook_for_monitor)

def test_halt_unnecessary_keyword_match(sample_rules):
    unnecessary, details = is_halt_unnecessary("Agent halted waiting for input", "Agent1", sample_rules, [])
    assert unnecessary is True
    assert "GEN-001" in details

def test_halt_necessary_no_match(sample_rules):
    unnecessary, details = is_halt_unnecessary("Complex calculation error", "Agent1", sample_rules, [])
    assert unnecessary is False
    assert "Reason not found" in details

def test_halt_agent_specific_match(sample_rules):
    unnecessary, details = is_halt_unnecessary("Agent2 specific procedure", "Agent2", sample_rules, [])
    assert unnecessary is True
    assert "GEN-002" in details

def test_halt_agent_specific_no_match(sample_rules):
    unnecessary, details = is_halt_unnecessary("Agent2 specific procedure", "Agent1", sample_rules, [])
    assert unnecessary is False # Rule GEN-002 doesn't apply to Agent1

# --- Tests for Logging/Broadcasting/Updating (Requires Mocking Paths) --- #

def test_log_unnecessary_halt(temp_logs_path, mocker):
    # Patch the global path
    mocker.patch('monitor_analyzer_agent.LOG_FILE_PATH', temp_logs_path)
    timestamp = datetime.datetime.now()
    log_unnecessary_halt("AgentTest", "Test Reason", "Rule XYZ", timestamp)
    content = Path(temp_logs_path).read_text()
    assert "AgentTest" in content
    assert "Test Reason" in content
    assert "Rule XYZ" in content

def test_broadcast_alert(temp_agent_dirs_root, sample_rules, mocker):
    # Patch the ABSOLUTE root path used by the broadcast function
    mocker.patch('monitor_analyzer_agent.ABS_AGENT_DIRS_ROOT', temp_agent_dirs_root)

    # Get paths within the temp dir for assertion
    agent1_inbox = Path(temp_agent_dirs_root) / "Agent1" / "inbox"
    agent2_inbox = Path(temp_agent_dirs_root) / "Agent2" / "inbox"

    broadcast_alert("AgentViolator", "Broke Rule 1", "Rule GEN-001 details", sample_rules)

    agent1_alerts = list(agent1_inbox.glob("*.json"))
    agent2_alerts = list(agent2_inbox.glob("*.json"))

    assert len(agent1_alerts) == 1, f"Expected 1 alert in {agent1_inbox}, found {len(agent1_alerts)}"
    assert len(agent2_alerts) == 1, f"Expected 1 alert in {agent2_inbox}, found {len(agent2_alerts)}"

    with open(agent1_alerts[0], 'r') as f:
        alert_data = json.load(f)
    assert alert_data['type'] == "rule_alert"
    assert alert_data['violating_agent'] == "AgentViolator"
    assert "rule GEN-001" in alert_data['message']

def test_request_rulebook_update(temp_proposals_path, mocker):
    # Patch the proposals file path constant used by the function
    mocker.patch('monitor_analyzer_agent.PROPOSALS_FILE_PATH', temp_proposals_path)
    # Patch AGENT_DIRS_ROOT just in case (though proposals path is now direct)
    mocker.patch('monitor_analyzer_agent.ABS_AGENT_DIRS_ROOT', os.path.dirname(temp_proposals_path)) # Mock root based on proposal path

    request_rulebook_update("AgentX", "Reason unclear", "Rule GEN-001 doesn't cover case Y")

    content = Path(temp_proposals_path).read_text()
    assert "[AUTO] Clarification Rule" in content
    assert "AgentX" in content
    assert "Reason unclear" in content
    # Check reasoning using json.dumps format as used in the function
    assert json.dumps("Rule GEN-001 doesn't cover case Y") in content

# --- Tests for HaltStatusHandler --- #
# Use the specific path fixtures for clarity
def test_halt_status_handler(mocker, tmp_path, temp_rulebook_for_monitor, temp_logs_path, temp_agent_dirs_root, temp_proposals_path):
    # 1. Patch all necessary global paths explicitly
    # Paths used by functions called within process_status_file
    mocker.patch('monitor_analyzer_agent.LOG_FILE_PATH', temp_logs_path)
    mocker.patch('monitor_analyzer_agent.ABS_AGENT_DIRS_ROOT', temp_agent_dirs_root)
    mocker.patch('monitor_analyzer_agent.PROPOSALS_FILE_PATH', temp_proposals_path)
    # Mock the functions called to isolate HaltStatusHandler logic if needed,
    # or let them run using patched paths. Let's mock request_rulebook_update.
    mock_request_update = mocker.patch('monitor_analyzer_agent.request_rulebook_update', autospec=True)
    # Path for rule loading (ensure handler uses the right one)
    mocker.patch('monitor_analyzer_agent.RULEBOOK_PATH', temp_rulebook_for_monitor)
    # Path for task loading (ensure handler uses the right one)
    task_pool_path = tmp_path / "Agent1" / "project_board" / "task_pool.json"
    task_pool_path.parent.mkdir(parents=True, exist_ok=True)
    task_pool_path.touch() # empty task pool
    mocker.patch('monitor_analyzer_agent.TASK_POOL_PATH', str(task_pool_path))


    # 2. Create mock agent structure and status file
    agent2_outbox = Path(temp_agent_dirs_root) / "Agent2" / "outbox"
    # agent2_outbox.mkdir(parents=True, exist_ok=True) # Already created by temp_agent_dirs_root fixture
    halt_file = agent2_outbox / "status_halt.json"
    halt_data = {
        "status": "halted",
        "agent_name": "Agent2", # Ensure agent name is in payload
        "reason": "Agent halted waiting for input",
        "timestamp": datetime.datetime.now().isoformat() # Include timestamp
    }
    halt_file.write_text(json.dumps(halt_data), encoding='utf-8')

    # 3. Instantiate handler and call process method directly
    rules = load_rules_from_rulebook(temp_rulebook_for_monitor)
    handler = HaltStatusHandler(rules, []) # Pass loaded rules
    # Process the file (wait slightly to ensure file write is complete)
    time.sleep(0.1)
    handler.process_status_file(str(halt_file))

    # 4. Assertions
    # Check logs
    log_content = Path(temp_logs_path).read_text()
    assert "Agent2" in log_content
    assert "Agent halted waiting for input" in log_content
    assert "rule GEN-001" in log_content # Check for lowercase 'rule'
    assert "Reason potentially covered by rule GEN-001" in log_content

    # Check broadcasts (check if inbox files were created)
    agent1_inbox = Path(temp_agent_dirs_root) / "Agent1" / "inbox"
    agent1_alerts = list(agent1_inbox.glob("*.json"))
    assert len(agent1_alerts) >= 1 # Should have received at least one alert

    # Check if request_rulebook_update was called correctly via the mock
    mock_request_update.assert_called_once()
    call_args, _ = mock_request_update.call_args
    assert call_args[0] == "Agent2"
    assert call_args[1] == "Agent halted waiting for input"
    assert "GEN-001" in call_args[2]


    pass 