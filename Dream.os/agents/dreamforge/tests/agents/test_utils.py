"""Shared test utilities for agent testing."""
import json
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, AsyncMock

# Sample test data
SAMPLE_PLAN = [
    {
        'task_id': 'TASK-001',
        'description': 'Define project scope',
        'status': 'Pending',
        'dependencies': [],
        'estimated_time': '2h',
        'assigned_to': 'PlannerAgent'
    },
    {
        'task_id': 'TASK-002',
        'description': 'Develop prototype',
        'status': 'Pending',
        'dependencies': ['TASK-001'],
        'estimated_time': '8h',
        'assigned_to': 'DevTeam'
    }
]

def create_llm_response(content: Any) -> str:
    """Create a mock LLM response with JSON content."""
    return f"Some preceding text ```json\n{json.dumps(content)}\n``` Trailing text."

def create_mock_llm_chain() -> Mock:
    """Create a mock LLM chain for testing."""
    mock = Mock()
    mock.stage_and_execute_prompt = AsyncMock()
    mock.render_template = Mock()
    return mock

def validate_plan(plan: List[Dict[str, Any]], expected_plan: List[Dict[str, Any]]) -> None:
    """Validate a plan against expected data."""
    assert isinstance(plan, list)
    assert len(plan) == len(expected_plan)
    
    for actual, expected in zip(plan, expected_plan):
        for key in expected:
            assert actual[key] == expected[key]

def validate_plan_refinement(
    refined_plan: List[Dict[str, Any]],
    original_plan: List[Dict[str, Any]],
    expected_changes: Dict[str, Any]
) -> None:
    """Validate plan refinement results."""
    assert isinstance(refined_plan, list)
    assert len(refined_plan) >= len(original_plan)
    
    # Check that original tasks are preserved with changes
    for orig_task in original_plan:
        task_id = orig_task['task_id']
        refined_task = next((t for t in refined_plan if t['task_id'] == task_id), None)
        assert refined_task is not None
        
        # Check expected changes
        changes = expected_changes.get(task_id, {})
        for key, value in changes.items():
            assert refined_task[key] == value
    
    # Check new tasks
    new_task_ids = set(t['task_id'] for t in refined_plan) - set(t['task_id'] for t in original_plan)
    expected_new_tasks = {
        task_id: task_data 
        for task_id, task_data in expected_changes.items() 
        if task_id not in set(t['task_id'] for t in original_plan)
    }
    assert new_task_ids == set(expected_new_tasks.keys())

def validate_llm_call(
    mock_render: Mock,
    mock_stage_prompt: Mock,
    expected_template: str,
    expected_vars: Dict[str, Any],
    expected_agent_id: str,
    expected_purpose: str
) -> None:
    """Validate LLM chain call sequence."""
    mock_render.assert_called_once_with(expected_template, expected_vars)
    mock_stage_prompt.assert_called_once_with(
        mock_render.return_value,
        agent_id=expected_agent_id,
        purpose=expected_purpose
    )

def setup_mock_llm_chain(
    mock_render: Mock,
    mock_stage_prompt: Mock,
    render_result: Optional[str] = "Rendered Prompt",
    stage_result: Optional[str] = None
) -> None:
    """Set up mock LLM chain with specified results."""
    mock_render.return_value = render_result
    mock_stage_prompt.return_value = stage_result 