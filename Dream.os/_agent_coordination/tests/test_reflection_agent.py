import os
import pytest
import json
import time

# Add project root to path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from reflection_agent import (
    load_rules_from_rulebook,
    generate_reflection,
    save_reflection,
    submit_proposal,
    AlertHandler
)
from apply_proposals import PROPOSALS_FILE_PATH # Reuse path config

# --- Fixtures --- #

@pytest.fixture
def temp_rulebook_for_reflection(tmp_path):
    rulebook_content = """
### Rule 1
- ID: GEN-001
- Desc: Rule One
```yaml
rules:
  - id: GEN-001
    description: Rule One Description
    keywords: [one, rule]
    applies_to: all_agents
```
### Rule 2
- ID: GEN-002
- Desc: Rule Two
```yaml
rules:
  - id: GEN-002
    description: Rule Two Description
    keywords: [two, unclear]
    applies_to: all_agents
```
"""
    file_path = tmp_path / "rulebook.md"
    file_path.write_text(rulebook_content, encoding='utf-8')
    # Patch the global RULEBOOK_PATH used by the reflection agent module
    # Note: This might have side effects if tests run in parallel without isolation
    import reflection_agent
    reflection_agent.RULEBOOK_PATH = str(file_path)
    return file_path

@pytest.fixture
def temp_proposals_path(tmp_path):
    proposals_file = tmp_path / "rulebook_update_proposals.md"
    # Patch the global path used by the reflection agent module
    import reflection_agent
    reflection_agent.PROPOSALS_FILE_PATH = str(proposals_file)
    # Ensure the file exists for append operations
    proposals_file.touch()
    return proposals_file

@pytest.fixture
def test_dirs(tmp_path):
    agent_name = "AgentTester"
    inbox = tmp_path / agent_name / "inbox"
    outbox = tmp_path / agent_name / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    return agent_name, inbox, outbox

@pytest.fixture
def alert_data_no_rule():
    return {
        "message_id": "alert-1",
        "type": "rule_alert",
        "violating_agent": "AgentX",
        "halt_reason": "System unclear about next step",
        "analysis": "Reason not found in applicable rules or tasks",
        "message": "Alert message content"
    }

@pytest.fixture
def alert_data_rule_found():
    return {
        "message_id": "alert-2",
        "type": "rule_alert",
        "violating_agent": "AgentY",
        "halt_reason": "Rule one violation",
        "analysis": "Reason potentially covered by rule GEN-001: 'Rule One Description'",
        "message": "Alert message content"
    }

@pytest.fixture
def alert_data_ambiguous():
     return {
        "message_id": "alert-3",
        "type": "rule_alert",
        "violating_agent": "AgentZ",
        "halt_reason": "Rule two seems vague and unclear",
        "analysis": "Reason potentially covered by rule GEN-002: 'Rule Two Description'",
        "message": "Alert message content"
    }

# --- Tests for generate_reflection --- #

def test_generate_reflection_no_proposal(alert_data_rule_found, temp_rulebook_for_reflection, mocker):
    mocker.patch.dict(os.environ, {"AGENT_NAME": "TestReflector"})
    rules = load_rules_from_rulebook(temp_rulebook_for_reflection)
    reflection = generate_reflection(alert_data_rule_found, rules)

    assert reflection['type'] == "agent_reflection"
    assert reflection['reflection_agent'] == "TestReflector"
    assert reflection['violating_agent'] == "AgentY"
    assert reflection['mentioned_rule_id'] == "GEN-001"
    assert reflection['suggested_action'] == "monitor_situation"
    assert reflection['proposal_content'] is None
    assert "Action: Monitoring situation." in reflection['thoughts']

def test_generate_reflection_proposes_on_no_rule(alert_data_no_rule, temp_rulebook_for_reflection, mocker):
    mocker.patch.dict(os.environ, {"AGENT_NAME": "TestReflector"})
    rules = load_rules_from_rulebook(temp_rulebook_for_reflection)
    reflection = generate_reflection(alert_data_no_rule, rules)

    assert reflection['suggested_action'] == "propose_rule_update"
    assert reflection['proposal_content'] is not None
    assert "[REFLECT] Proposal" in reflection['proposal_content']
    assert "Reasoning: Monitor analysis did not link halt reason" in reflection['proposal_content']
    assert "Action: Proposing clarification/new rule." in reflection['thoughts']
    assert reflection['mentioned_rule_id'] is None

def test_generate_reflection_proposes_on_ambiguity(alert_data_ambiguous, temp_rulebook_for_reflection, mocker):
    mocker.patch.dict(os.environ, {"AGENT_NAME": "TestReflector"})
    rules = load_rules_from_rulebook(temp_rulebook_for_reflection)
    reflection = generate_reflection(alert_data_ambiguous, rules)

    assert reflection['suggested_action'] == "propose_rule_update"
    assert reflection['proposal_content'] is not None
    assert "[REFLECT] Proposal" in reflection['proposal_content']
    assert "Reasoning: Halt reason ('Rule two seems vague and unclear') contains keywords suggesting ambiguity regarding Rule GEN-002." in reflection['proposal_content']
    assert "Action: Proposing clarification/new rule." in reflection['thoughts']
    assert reflection['mentioned_rule_id'] == "GEN-002"

# --- Tests for save_reflection --- #

def test_save_reflection(test_dirs, alert_data_no_rule, mocker):
    mocker.patch.dict(os.environ, {"AGENT_NAME": "TestReflector"})
    _, _, outbox = test_dirs
    # Minimal reflection data for testing save
    reflection_data = {
        "reflection_id": "reflect-test-123",
        "thoughts": "Test thoughts"
    }
    save_reflection(reflection_data, outbox)
    saved_file = outbox / "reflect-test-123.json"
    assert saved_file.exists()
    with open(saved_file, 'r') as f:
        data = json.load(f)
    assert data["reflection_id"] == "reflect-test-123"
    assert data["thoughts"] == "Test thoughts"

# --- Tests for submit_proposal --- #

def test_submit_proposal(temp_proposals_path):
    proposal_content = "### [REFLECT] Test Proposal\nContent here"
    reflection_id = "reflect-test-456"

    submit_proposal(proposal_content, reflection_id)

    content = temp_proposals_path.read_text(encoding='utf-8')
    assert f"### Proposal from Reflection '{reflection_id}'" in content
    assert proposal_content in content
    # Check append works
    submit_proposal("Second proposal", "reflect-789")
    content = temp_proposals_path.read_text(encoding='utf-8')
    assert "Second proposal" in content

def test_submit_proposal_no_content(temp_proposals_path):
    initial_content = temp_proposals_path.read_text(encoding='utf-8')
    submit_proposal(None, "reflect-null")
    final_content = temp_proposals_path.read_text(encoding='utf-8')
    assert initial_content == final_content # No change

# --- Tests for AlertHandler --- #
# Requires more involved mocking/setup for watchdog interaction

@pytest.mark.skip(reason="Requires mocking watchdog or file system events")
def test_alert_handler_integration(test_dirs, temp_rulebook_for_reflection, temp_proposals_path, alert_data_ambiguous, mocker):
    # This test would simulate file creation in the inbox and check
    # if reflection and proposal files are created correctly.
    agent_name, inbox, outbox = test_dirs
    mocker.patch.dict(os.environ, {"AGENT_NAME": agent_name})

    handler = AlertHandler(agent_name, str(inbox), str(outbox))

    # Simulate file creation
    alert_file_path = inbox / f"{alert_data_ambiguous['message_id']}.json"
    with open(alert_file_path, 'w') as f:
        json.dump(alert_data_ambiguous, f)

    # Give handler time to process (in real scenario watchdog triggers this)
    # For testing, might call handler.process_alert_file(str(alert_file_path)) directly
    # or mock the event triggering.
    time.sleep(0.5) # Simplistic wait

    # Assertions:
    # 1. Check outbox for reflection file
    reflection_files = list(outbox.glob("reflection-*.json"))
    assert len(reflection_files) == 1
    # 2. Check proposals file for appended proposal
    proposal_content = temp_proposals_path.read_text(encoding='utf-8')
    assert "[REFLECT] Proposal" in proposal_content
    assert alert_data_ambiguous['violating_agent'] in proposal_content

    pass 