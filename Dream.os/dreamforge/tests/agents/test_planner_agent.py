import pytest
import os
import sys

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/tests/agents
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Module to test
from dreamforge.agents.planner_agent import PlannerAgent

# --- Test Cases --- 

# Instantiate agent once for tests (can use dummy config)
@pytest.fixture(scope="module")
def planner_agent():
    # Mock dependencies if necessary for parser tests (not needed here)
    return PlannerAgent(llm_config={})

# --- Test Data --- 

VALID_JSON_LIST_STR = '''
[
  {
    "task_id": "T1", "description": "Task One", "status": "pending",
    "dependencies": [], "estimated_time": "1h", "assigned_to": "A"
  },
  {
    "task_id": "T2", "description": "Task Two", "status": "pending",
    "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B"
  }
]
'''

VALID_JSON_IN_MARKDOWN = f'''
Some introductory text.
```json
{VALID_JSON_LIST_STR}
```
Some concluding text.
'''

VALID_JSON_DICT_WRAPPER = '''
{
  "comment": "Here is the plan",
  "tasks": 
  [
    {
      "task_id": "T1", "description": "Task One", "status": "pending",
      "dependencies": [], "estimated_time": "1h", "assigned_to": "A"
    }
  ]
}
'''

INVALID_JSON_STR = '''
[
  {"task_id": "T1", "description": "Task One",
]
''' # Missing closing brace and comma (Added closing quote)

NON_JSON_TEXT = "This is just plain text, not JSON at all."

JSON_WRONG_TYPE = '{"message": "This is a dict, not a list"}'

EXPECTED_LIST_OUTPUT = [
  {
    "task_id": "T1", "description": "Task One", "status": "pending",
    "dependencies": [], "estimated_time": "1h", "assigned_to": "A"
  },
  {
    "task_id": "T2", "description": "Task Two", "status": "pending",
    "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B"
  }
]

EXPECTED_DICT_WRAPPER_OUTPUT = [
    {
      "task_id": "T1", "description": "Task One", "status": "pending",
      "dependencies": [], "estimated_time": "1h", "assigned_to": "A"
    }
]

# --- Tests for _parse_llm_plan_response --- 

def test_parse_valid_json_list(planner_agent):
    """Test parsing a direct JSON list string."""
    result = planner_agent._parse_llm_plan_response(VALID_JSON_LIST_STR)
    assert result == EXPECTED_LIST_OUTPUT

def test_parse_valid_json_in_markdown(planner_agent):
    """Test parsing JSON within a markdown code block."""
    result = planner_agent._parse_llm_plan_response(VALID_JSON_IN_MARKDOWN)
    assert result == EXPECTED_LIST_OUTPUT

def test_parse_valid_json_dict_wrapper(planner_agent):
    """Test parsing JSON where the list is wrapped in a dictionary under the 'tasks' key."""
    result = planner_agent._parse_llm_plan_response(VALID_JSON_DICT_WRAPPER)
    assert result == EXPECTED_DICT_WRAPPER_OUTPUT

def test_parse_invalid_json(planner_agent):
    """Test parsing malformed JSON."""
    result = planner_agent._parse_llm_plan_response(INVALID_JSON_STR)
    assert result is None

def test_parse_non_json_text(planner_agent):
    """Test parsing plain text that is not JSON."""
    result = planner_agent._parse_llm_plan_response(NON_JSON_TEXT)
    assert result is None

def test_parse_json_wrong_type(planner_agent):
    """Test parsing valid JSON that is not a list or the expected dict wrapper."""
    result = planner_agent._parse_llm_plan_response(JSON_WRONG_TYPE)
    assert result is None

def test_parse_empty_string(planner_agent):
    """Test parsing an empty string."""
    result = planner_agent._parse_llm_plan_response("")
    assert result is None

def test_parse_none_input(planner_agent):
    """Test parsing None input (though type hints suggest str)."""
    # While the type hint is str, defensive check is good.
    # Check how the actual code handles it - it uses strip(), which would raise AttributeError
    with pytest.raises(AttributeError): 
        planner_agent._parse_llm_plan_response(None)

# --- Tests for plan_from_goal (Integration with Mocked LLM) --- 

@pytest.mark.parametrize(
    "mock_llm_response, expected_result",
    [
        # Case 1: Successful response (JSON in markdown)
        (VALID_JSON_IN_MARKDOWN, EXPECTED_LIST_OUTPUT),
        # Case 2: Successful response (Direct JSON list)
        (VALID_JSON_LIST_STR, EXPECTED_LIST_OUTPUT),
        # Case 3: Successful response (Dict wrapper)
        (VALID_JSON_DICT_WRAPPER, EXPECTED_DICT_WRAPPER_OUTPUT),
        # Case 4: LLM returns invalid JSON
        (INVALID_JSON_STR, None),
        # Case 5: LLM returns non-JSON text
        (NON_JSON_TEXT, None),
        # Case 6: LLM returns None or error indicator (handled by agent before parser)
        (None, None),
        ("Error: Some LLM Error", None),
    ]
)
def test_plan_from_goal_mocked_llm(monkeypatch, planner_agent, mock_llm_response, expected_result):
    """Test plan_from_goal with mocked stage_and_execute_prompt."""
    
    # Mock the stage_and_execute_prompt function within the agent's module
    def mock_stage_prompt(*args, **kwargs):
        # Basic logging to simulate the call being made
        print(f"Mock stage_and_execute_prompt called with subject: {kwargs.get('prompt_subject', '?')}")
        return mock_llm_response
        
    monkeypatch.setattr("dreamforge.agents.planner_agent.stage_and_execute_prompt", mock_stage_prompt)
    
    # Mock render_template to just return a non-empty string (content doesn't matter for this test)
    monkeypatch.setattr("dreamforge.agents.planner_agent.render_template", lambda name, ctx: "Mock prompt content")

    # Call the method under test
    user_goal = "Test goal"
    actual_result = planner_agent.plan_from_goal(user_goal)
    
    # Assert the result
    assert actual_result == expected_result

def test_plan_from_goal_template_render_fails(monkeypatch, planner_agent):
    """Test plan_from_goal when template rendering fails."""
    # Mock render_template to return None
    monkeypatch.setattr("dreamforge.agents.planner_agent.render_template", lambda name, ctx: None)
    
    # Mock stage_and_execute_prompt (shouldn't be called)
    def mock_stage_prompt_should_not_run(*args, **kwargs):
        pytest.fail("stage_and_execute_prompt should not be called if template rendering fails")
        
    monkeypatch.setattr("dreamforge.agents.planner_agent.stage_and_execute_prompt", mock_stage_prompt_should_not_run)

    user_goal = "Test goal where template fails"
    actual_result = planner_agent.plan_from_goal(user_goal)
    
    assert actual_result is None 