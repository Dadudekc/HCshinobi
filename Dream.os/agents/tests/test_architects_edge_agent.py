# Tests for ArchitectsEdgeAgent

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call
import json

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the class to test
from agents.architects_edge_agent import ArchitectsEdgeAgent, AGENT_ID

# Mock the AgentBus instance that the agent might try to create
# We primarily mock the *dispatch* method called on the instance.
@pytest.fixture
def mock_agent_bus_instance():
    mock_bus = MagicMock()
    mock_bus.dispatch = MagicMock(return_value="Dispatch Success") # Mock the dispatch method
    return mock_bus

@pytest.fixture
@patch('agents.architects_edge_agent.AgentBus') # Patch the class
def architects_edge_agent_instance(MockAgentBus, mock_agent_bus_instance):
    """Provides an instance of ArchitectsEdgeAgent with mocked AgentBus."""
    # Configure the patched AgentBus class to return our mock instance when called
    MockAgentBus.return_value = mock_agent_bus_instance
    agent = ArchitectsEdgeAgent() # This will now get the mocked bus instance
    return agent, mock_agent_bus_instance # Return agent and the mock bus for assertions

# --- Test Cases ---

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_success(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test successful interpretation of a directive."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = "Rendered Prompt Text"
    mock_action_dict = {
        "agent": "PlannerAgent",
        "command": "plan_from_goal",
        "params": {"goal": "Test Goal"}
    }
    mock_llm_response = f"Some text before... ```json\n{json.dumps(mock_action_dict)}\n``` ...some text after"
    mock_stage_prompt.return_value = mock_llm_response

    directive = "Plan how to test the system."
    action = agent.interpret_directive(directive)

    assert action == mock_action_dict
    mock_render.assert_called_once_with(
        "agents/prompts/architects_edge/interpret_directive.j2",
        {"directive": directive}
    )
    mock_stage_prompt.assert_called_once_with(
        "Rendered Prompt Text",
        agent_id=AGENT_ID,
        purpose="interpret_directive"
    )

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_render_fails(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test failure when template rendering fails."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = None # Simulate render failure

    directive = "Render fail test."
    action = agent.interpret_directive(directive)

    assert action is None
    mock_stage_prompt.assert_not_called()

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_llm_fails(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test failure when LLM call returns nothing."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = "Rendered Prompt Text"
    mock_stage_prompt.return_value = None # Simulate LLM failure

    directive = "LLM fail test."
    action = agent.interpret_directive(directive)

    assert action is None
    mock_stage_prompt.assert_called_once()

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_parsing_fails_no_json(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test failure when LLM response does not contain a JSON block."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = "Rendered Prompt Text"
    mock_stage_prompt.return_value = "This response has no JSON."

    directive = "No JSON test."
    action = agent.interpret_directive(directive)

    assert action is None

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_parsing_fails_bad_json(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test failure when LLM response contains invalid JSON."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = "Rendered Prompt Text"
    mock_stage_prompt.return_value = "```json\n{\"agent\": \"Planner\", \"command\": bad_json, }\n```"

    directive = "Bad JSON test."
    action = agent.interpret_directive(directive)

    assert action is None

@patch('agents.architects_edge_agent.render_template')
@patch('agents.architects_edge_agent.stage_and_execute_prompt')
def test_interpret_directive_parsing_fails_missing_keys(mock_stage_prompt, mock_render, architects_edge_agent_instance):
    """Test failure when parsed JSON lacks required keys."""
    agent, _ = architects_edge_agent_instance
    mock_render.return_value = "Rendered Prompt Text"
    mock_stage_prompt.return_value = "```json\n{\"agent\": \"Planner\"}\n```" # Missing command

    directive = "Missing keys test."
    action = agent.interpret_directive(directive)

    assert action is None

def test_dispatch_to_dreamforge_success(architects_edge_agent_instance):
    """Test successful dispatch of a valid action."""
    agent, mock_bus = architects_edge_agent_instance
    action = {
        "agent": "PlannerAgent",
        "command": "plan_from_goal",
        "params": {"goal": "Dispatch Goal"}
    }

    agent.dispatch_to_dreamforge(action)

    mock_bus.dispatch.assert_called_once_with(
        target_agent_id="PlannerAgent",
        method_name="plan_from_goal",
        goal="Dispatch Goal"
    )

def test_dispatch_to_dreamforge_no_params(architects_edge_agent_instance):
    """Test successful dispatch with no params in action."""
    agent, mock_bus = architects_edge_agent_instance
    action = {
        "agent": "CalendarAgent",
        "command": "get_schedule"
        # No 'params' key
    }

    agent.dispatch_to_dreamforge(action)

    mock_bus.dispatch.assert_called_once_with(
        target_agent_id="CalendarAgent",
        method_name="get_schedule"
        # No kwargs expected
    )

def test_dispatch_to_dreamforge_invalid_action_none(architects_edge_agent_instance):
    """Test dispatch attempt with None action."""
    agent, mock_bus = architects_edge_agent_instance
    agent.dispatch_to_dreamforge(None)
    mock_bus.dispatch.assert_not_called()

def test_dispatch_to_dreamforge_invalid_action_dict(architects_edge_agent_instance):
    """Test dispatch attempt with invalid action dictionary (missing keys)."""
    agent, mock_bus = architects_edge_agent_instance
    agent.dispatch_to_dreamforge({"agent": "PlannerAgent"}) # Missing command
    mock_bus.dispatch.assert_not_called()

def test_dispatch_to_dreamforge_invalid_params(architects_edge_agent_instance):
    """Test dispatch attempt with invalid params format."""
    agent, mock_bus = architects_edge_agent_instance
    action = {
        "agent": "PlannerAgent",
        "command": "plan_from_goal",
        "params": "not_a_dictionary"
    }
    agent.dispatch_to_dreamforge(action)
    mock_bus.dispatch.assert_not_called() 