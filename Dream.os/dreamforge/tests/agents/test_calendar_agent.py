import pytest
import os
import sys
import json

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/tests/agents
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Module to test
from dreamforge.agents.calendar_agent import CalendarAgent

# --- Test Fixtures --- 

@pytest.fixture(scope="module")
def calendar_agent():
    return CalendarAgent(llm_config={})

@pytest.fixture
def original_tasks():
    return [
        {"task_id": "T1", "description": "Task 1", "dependencies": [], "estimated_time": "1h", "assigned_to": "A"},
        {"task_id": "T2", "description": "Task 2", "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B"},
        {"task_id": "T3", "description": "Task 3", "dependencies": [], "estimated_time": "30m", "assigned_to": "A"}
    ]

# --- Test Data --- 

# LLM response where T1 is scheduled, T2 fails, T3 is not returned
LLM_RESPONSE_PARTIAL_SCHEDULE = '''
```json
[
  {
    "task_id": "T1", 
    "start_time": "2025-01-10T09:00:00Z",
    "end_time": "2025-01-10T10:00:00Z",
    "scheduling_status": "Scheduled"
  },
  {
    "task_id": "T2", 
    "start_time": null,
    "end_time": null,
    "scheduling_status": "Failed: Conflicts"
  },
  {
    "task_id": "T_UNKNOWN", 
    "start_time": "2025-01-10T11:00:00Z",
    "end_time": "2025-01-10T12:00:00Z",
    "scheduling_status": "Scheduled" 
  }
]
```
'''
EXPECTED_PARTIAL_SCHEDULE_MERGE = [
    {"task_id": "T1", "description": "Task 1", "dependencies": [], "estimated_time": "1h", "assigned_to": "A", "start_time": "2025-01-10T09:00:00Z", "end_time": "2025-01-10T10:00:00Z", "scheduling_status": "Scheduled"},
    {"task_id": "T2", "description": "Task 2", "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B", "start_time": None, "end_time": None, "scheduling_status": "Failed: Conflicts"},
    {"task_id": "T3", "description": "Task 3", "dependencies": [], "estimated_time": "30m", "assigned_to": "A", "start_time": None, "end_time": None, "scheduling_status": "Failed: Missing in LLM response"}
]

# LLM response with all tasks scheduled successfully (direct JSON)
LLM_RESPONSE_FULL_SCHEDULE = '''
[
  {
    "task_id": "T1", 
    "start_time": "2025-01-10T09:00:00Z",
    "end_time": "2025-01-10T10:00:00Z",
    "scheduling_status": "Scheduled"
  },
  {
    "task_id": "T2", 
    "start_time": "2025-01-10T10:15:00Z",
    "end_time": "2025-01-10T12:15:00Z",
    "scheduling_status": "Scheduled"
  },
  {
    "task_id": "T3", 
    "start_time": "2025-01-10T13:00:00Z",
    "end_time": "2025-01-10T13:30:00Z",
    "scheduling_status": "Scheduled"
  }
]
'''
EXPECTED_FULL_SCHEDULE_MERGE = [
    {"task_id": "T1", "description": "Task 1", "dependencies": [], "estimated_time": "1h", "assigned_to": "A", "start_time": "2025-01-10T09:00:00Z", "end_time": "2025-01-10T10:00:00Z", "scheduling_status": "Scheduled"},
    {"task_id": "T2", "description": "Task 2", "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B", "start_time": "2025-01-10T10:15:00Z", "end_time": "2025-01-10T12:15:00Z", "scheduling_status": "Scheduled"},
    {"task_id": "T3", "description": "Task 3", "dependencies": [], "estimated_time": "30m", "assigned_to": "A", "start_time": "2025-01-10T13:00:00Z", "end_time": "2025-01-10T13:30:00Z", "scheduling_status": "Scheduled"}
]

LLM_RESPONSE_INVALID_ITEM = '''
[
  {"task_id": "T1", "scheduling_status": "Scheduled"},
  {"invalid": "item"}
]
'''
EXPECTED_INVALID_ITEM_MERGE = [
    {"task_id": "T1", "description": "Task 1", "dependencies": [], "estimated_time": "1h", "assigned_to": "A", "start_time": None, "end_time": None, "scheduling_status": "Scheduled"},
    {"task_id": "T2", "description": "Task 2", "dependencies": ["T1"], "estimated_time": "2h", "assigned_to": "B", "start_time": None, "end_time": None, "scheduling_status": "Failed: Missing in LLM response"},
    {"task_id": "T3", "description": "Task 3", "dependencies": [], "estimated_time": "30m", "assigned_to": "A", "start_time": None, "end_time": None, "scheduling_status": "Failed: Missing in LLM response"}
]

LLM_RESPONSE_INVALID_JSON = '["task_id": "T1"'
LLM_RESPONSE_NON_JSON = "Could not schedule tasks."
LLM_RESPONSE_WRONG_TYPE = '{"scheduled_tasks": []}'

# --- Helper to compare lists of dicts ignoring order --- 
def assert_list_of_dicts_equal(list1, list2):
    assert len(list1) == len(list2)
    # Sort lists based on a stable key like task_id before comparison
    list1_sorted = sorted(list1, key=lambda x: x['task_id'])
    list2_sorted = sorted(list2, key=lambda x: x['task_id'])
    assert list1_sorted == list2_sorted

# --- Tests for _parse_llm_schedule_response --- 

def test_parse_schedule_partial(calendar_agent, original_tasks):
    """Test parsing a response where some tasks are scheduled/failed and others missing."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_PARTIAL_SCHEDULE, original_tasks)
    assert_list_of_dicts_equal(result, EXPECTED_PARTIAL_SCHEDULE_MERGE)

def test_parse_schedule_full_success(calendar_agent, original_tasks):
    """Test parsing a response where all tasks were scheduled successfully."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_FULL_SCHEDULE, original_tasks)
    assert_list_of_dicts_equal(result, EXPECTED_FULL_SCHEDULE_MERGE)

def test_parse_schedule_invalid_item(calendar_agent, original_tasks):
    """Test parsing a response containing an invalid item (e.g., missing task_id)."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_INVALID_ITEM, original_tasks)
    assert_list_of_dicts_equal(result, EXPECTED_INVALID_ITEM_MERGE)

def test_parse_schedule_invalid_json(calendar_agent, original_tasks):
    """Test parsing malformed JSON."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_INVALID_JSON, original_tasks)
    assert result is None

def test_parse_schedule_non_json(calendar_agent, original_tasks):
    """Test parsing non-JSON text."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_NON_JSON, original_tasks)
    assert result is None

def test_parse_schedule_wrong_type(calendar_agent, original_tasks):
    """Test parsing valid JSON that is not a list."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_WRONG_TYPE, original_tasks)
    assert result is None

def test_parse_schedule_empty_response(calendar_agent, original_tasks):
    """Test parsing an empty JSON list response."""
    result = calendar_agent._parse_llm_schedule_response("[]", original_tasks)
    # Should return original tasks marked as missing
    expected_missing = [
        {**t, 'start_time': None, 'end_time': None, 'scheduling_status': 'Failed: Missing in LLM response'} 
        for t in original_tasks
    ]
    assert_list_of_dicts_equal(result, expected_missing)

def test_parse_schedule_empty_input_tasks(calendar_agent):
    """Test parsing when the original task list is empty."""
    result = calendar_agent._parse_llm_schedule_response(LLM_RESPONSE_FULL_SCHEDULE, [])
    assert result == [] # Expect empty list back, possibly warnings logged about unknown task IDs 