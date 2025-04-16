import os
import sys
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dreamforge.core.llm_bridge import call_llm, _SOURCE_ID

@pytest.fixture
def mock_log_event():
    """Mock the log_event function."""
    with patch('dreamforge.core.llm_bridge.log_event') as mock:
        yield mock

def test_call_llm_task_list_response(mock_log_event):
    """Test LLM response for task list prompts."""
    prompt = "Generate a task list for project X"
    result = call_llm(prompt)
    
    # Verify JSON structure in response
    assert '```json' in result
    assert '```' in result
    
    # Extract and validate JSON
    json_content = result.split('```json\n')[1].split('\n```')[0]
    tasks = json.loads(json_content)
    assert isinstance(tasks, list)
    assert len(tasks) > 0
    assert all(isinstance(task, dict) for task in tasks)
    assert all('id' in task for task in tasks)
    
    # Verify logging
    mock_log_event.assert_called()

def test_call_llm_default_response():
    """Test default LLM response for non-task prompts."""
    prompt = "Tell me about the weather"
    result = call_llm(prompt)
    assert result == "Dummy LLM response"

def test_call_llm_with_custom_model():
    """Test LLM call with custom model parameter."""
    prompt = "Test prompt"
    model = "gpt-4"
    result = call_llm(prompt, model=model)
    assert result is not None

def test_call_llm_with_temperature():
    """Test LLM call with custom temperature."""
    prompt = "Test prompt"
    temperature = 0.5
    result = call_llm(prompt, temperature=temperature)
    assert result is not None

@pytest.mark.parametrize("invalid_prompt", [
    None,
    "",
    " ",
    "\n",
])
def test_call_llm_invalid_prompts(invalid_prompt, mock_log_event):
    """Test LLM handling of invalid prompts."""
    result = call_llm(invalid_prompt)
    assert result is None
    mock_log_event.assert_called()

def test_call_llm_example_prompts():
    """Test all example prompts from main block."""
    test_prompts = [
        "Subject: Test Success\nGenerate a plan for testing.",
        "Subject: Test Failure\nPlease fail this request.",
        "Subject: Generate Plan\nUser Goal: Test.\nGenerate task plan instructions...",
        '''Subject: Schedule Tasks
TASKS TO SCHEDULE:
```json
[
  {
    "task_id": "T1",
    "description": "Task 1",
    "dependencies": [],
    "estimated_time": "1h"
  }
]
```
EXISTING CALENDAR EVENTS: []
Instructions...'''
    ]
    
    for prompt in test_prompts:
        result = call_llm(prompt)
        assert result is not None
        assert isinstance(result, str)

@patch('dreamforge.core.llm_bridge.log_event')
def test_call_llm_error_handling(mock_log):
    """Test error handling in LLM bridge."""
    with patch('json.dumps') as mock_dumps:
        mock_dumps.side_effect = Exception("Simulated error")
        prompt = "task list with error"
        result = call_llm(prompt)
        assert result is None
        mock_log.assert_called_with(
            "AGENT_ERROR",
            _SOURCE_ID,
            {"error": "Error calling LLM: Simulated error"}
        )

def test_source_id_constant():
    """Test _SOURCE_ID constant is correctly defined."""
    assert _SOURCE_ID == "LLMBridge"
    assert isinstance(_SOURCE_ID, str) 