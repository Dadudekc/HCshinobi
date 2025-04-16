# Tests for CalendarAgent

import sys
import os
import pytest
from unittest.mock import patch, MagicMock, call
import json
from datetime import datetime, timedelta

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the class to test
from agents.calendar_agent import CalendarAgent, AGENT_ID

# --- Fixtures ---

@pytest.fixture
def sample_tasks_input():
    """Provides a sample list of tasks for scheduling."""
    return [
        {
            'task_id': 'T001', 
            'description': 'Task 1', 
            'estimated_time': '1h', 
            'dependencies': []
        },
        {
            'task_id': 'T002', 
            'description': 'Task 2', 
            'estimated_time': '2h', 
            'dependencies': ['T001']
        }
    ]

@pytest.fixture
def mock_llm_schedule_response():
    """Provides a mock LLM response for schedule_tasks."""
    scheduled_tasks = [
        {
            'task_id': 'T001',
            'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
            'end_time': (datetime.now() + timedelta(hours=2)).isoformat(),
            'scheduling_status': 'Scheduled'
        },
        {
            'task_id': 'T002',
            'scheduling_status': 'Failed: No Slots' # Example failure status
        }
    ]
    return f'```json\n{json.dumps(scheduled_tasks)}\n```'

@pytest.fixture
def mock_llm_slots_response():
    """Provides a mock LLM response for find_available_slots."""
    slots = [
        {'start_time': '2025-01-01T09:00:00', 'end_time': '2025-01-01T10:00:00'},
        {'start_time': '2025-01-01T14:00:00', 'end_time': '2025-01-01T15:00:00'}
    ]
    return f'```json\n{json.dumps(slots)}\n```'

@pytest.fixture
def calendar_agent_instance():
    """Provides a standard instance of CalendarAgent."""
    return CalendarAgent()

# --- schedule_tasks Tests ---

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule') # Mock internal method
def test_schedule_tasks_success(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, sample_tasks_input, mock_llm_schedule_response):
    """Test successful task scheduling."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = [] # Assume no existing events for simplicity
    mock_render.return_value = "Rendered Schedule Prompt"
    mock_stage_prompt.return_value = mock_llm_schedule_response
    
    result_tasks = agent.schedule_tasks(sample_tasks_input)
    
    assert isinstance(result_tasks, list)
    assert len(result_tasks) == 2
    # Check merged data for T001
    task1 = next(t for t in result_tasks if t['task_id'] == 'T001')
    assert task1['scheduling_status'] == 'Scheduled'
    assert 'start_time' in task1
    assert 'end_time' in task1
    # Check merged data for T002
    task2 = next(t for t in result_tasks if t['task_id'] == 'T002')
    assert task2['scheduling_status'] == 'Failed: No Slots'
    assert 'start_time' not in task2 # Should not have times if failed
    
    mock_load_schedule.assert_called_once()
    mock_render.assert_called_once_with(
        "agents/prompts/calendar/schedule_tasks.j2",
        {"tasks": sample_tasks_input, "existing_events": []}
    )
    mock_stage_prompt.assert_called_once_with(
        "Rendered Schedule Prompt",
        agent_id=AGENT_ID,
        purpose="schedule_tasks"
    )

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_schedule_tasks_missing_in_response(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, sample_tasks_input):
    """Test handling when LLM response omits a task."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Schedule Prompt"
    # Response only includes T001
    mock_response = '```json\n[{"task_id": "T001", "scheduling_status": "Scheduled"}]\n```'
    mock_stage_prompt.return_value = mock_response
    
    result_tasks = agent.schedule_tasks(sample_tasks_input)
    
    assert len(result_tasks) == 2
    task1 = next(t for t in result_tasks if t['task_id'] == 'T001')
    task2 = next(t for t in result_tasks if t['task_id'] == 'T002')
    assert task1['scheduling_status'] == 'Scheduled'
    assert task2['scheduling_status'] == 'Failed: Missing in LLM response'

@patch('agents.calendar_agent.render_template')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_schedule_tasks_render_fails(mock_load_schedule, mock_render, calendar_agent_instance, sample_tasks_input):
    """Test schedule_tasks when template rendering fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = None
    
    result_tasks = agent.schedule_tasks(sample_tasks_input)
    
    assert len(result_tasks) == 2
    assert all(t['scheduling_status'] == 'Failed: Template Error' for t in result_tasks)
    mock_load_schedule.assert_called_once()

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_schedule_tasks_llm_fails(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, sample_tasks_input):
    """Test schedule_tasks when LLM call fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Schedule Prompt"
    mock_stage_prompt.return_value = None
    
    result_tasks = agent.schedule_tasks(sample_tasks_input)
    
    assert len(result_tasks) == 2
    assert all(t['scheduling_status'] == 'Failed: LLM Error' for t in result_tasks)

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_schedule_tasks_parsing_fails(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, sample_tasks_input):
    """Test schedule_tasks when LLM response parsing fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Schedule Prompt"
    mock_stage_prompt.return_value = "Not JSON"
    
    result_tasks = agent.schedule_tasks(sample_tasks_input)
    
    assert len(result_tasks) == 2
    assert all(t['scheduling_status'] == 'Failed: Parsing Error' for t in result_tasks)

# --- find_available_slots Tests ---

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_find_available_slots_success(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, mock_llm_slots_response):
    """Test successful slot finding."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Slots Prompt"
    mock_stage_prompt.return_value = mock_llm_slots_response
    duration = 60
    constraints = {"work_hours": "9-5"}
    
    slots = agent.find_available_slots(duration, constraints)
    
    assert isinstance(slots, list)
    assert len(slots) == 2
    assert slots[0]['start_time'] == '2025-01-01T09:00:00'
    assert slots[1]['end_time'] == '2025-01-01T15:00:00'
    
    mock_load_schedule.assert_called_once()
    mock_render.assert_called_once_with(
        "agents/prompts/calendar/find_available_slots.j2",
        {"duration_minutes": duration, "constraints": constraints, "existing_events": []}
    )
    mock_stage_prompt.assert_called_once_with(
        "Rendered Slots Prompt",
        agent_id=AGENT_ID,
        purpose="find_available_slots"
    )

@patch('agents.calendar_agent.render_template')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_find_available_slots_render_fails(mock_load_schedule, mock_render, calendar_agent_instance):
    """Test find_available_slots when template rendering fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = None
    
    slots = agent.find_available_slots(60)
    
    assert slots == []
    mock_load_schedule.assert_called_once()

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_find_available_slots_llm_fails(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance):
    """Test find_available_slots when LLM call fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Slots Prompt"
    mock_stage_prompt.return_value = None
    
    slots = agent.find_available_slots(60)
    
    assert slots == []

@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_find_available_slots_parsing_fails(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance):
    """Test find_available_slots when LLM response parsing fails."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = []
    mock_render.return_value = "Rendered Slots Prompt"
    mock_stage_prompt.return_value = "Not JSON"
    
    slots = agent.find_available_slots(60)
    
    assert slots == []

# Add a new test for complex constraints
@patch('agents.calendar_agent.render_template')
@patch('agents.calendar_agent.stage_and_execute_prompt')
@patch.object(CalendarAgent, '_load_existing_schedule')
def test_find_available_slots_complex_constraints(mock_load_schedule, mock_stage_prompt, mock_render, calendar_agent_instance, mock_llm_slots_response):
    """Test find_available_slots with multiple constraints."""
    agent = calendar_agent_instance
    mock_load_schedule.return_value = [{'summary': 'Existing Event', 'start': '2025-01-01T11:00:00', 'end': '2025-01-01T12:00:00'}] # Add an existing event
    mock_render.return_value = "Rendered Complex Slots Prompt"
    mock_stage_prompt.return_value = mock_llm_slots_response # Reuse existing mock response
    duration = 30
    constraints = {
        "earliest_start": "2025-01-01T08:00:00",
        "latest_end": "2025-01-01T17:00:00",
        "buffer_minutes": 15
    }

    slots = agent.find_available_slots(duration, constraints)

    assert isinstance(slots, list)
    # The exact validation depends on the mocked LLM response and the agent's parsing.
    # Here, we reuse the mock response, so we expect the same output.
    assert len(slots) == 2
    assert slots[0]['start_time'] == '2025-01-01T09:00:00'

    mock_load_schedule.assert_called_once()
    mock_render.assert_called_once_with(
        "agents/prompts/calendar/find_available_slots.j2",
        {"duration_minutes": duration, "constraints": constraints, "existing_events": mock_load_schedule.return_value}
    )
    mock_stage_prompt.assert_called_once_with(
        "Rendered Complex Slots Prompt",
        agent_id=AGENT_ID,
        purpose="find_available_slots"
    )

# Remove placeholder tests
# def test_schedule_tasks():
#     assert True # Placeholder
#
# def test_find_available_slots():
#     assert True # Placeholder 