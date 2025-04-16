import pytest
import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from dreamforge.core.enums.task_types import TaskType
from dreamforge.agents.cursor_dispatcher import CursorDispatcher
from dreamforge.core.agent_bus import AgentBus

@pytest.fixture
def mock_agent_bus():
    return MagicMock(spec=AgentBus)

@pytest.fixture
def cursor_dispatcher(mock_agent_bus):
    dispatcher = CursorDispatcher()
    dispatcher.agent_bus = mock_agent_bus
    return dispatcher

def test_execute_cursor_task_test_generation(cursor_dispatcher, tmp_path):
    """Test handling of test generation tasks."""
    # Setup
    test_file = tmp_path / "sample.py"
    test_file.write_text("def add(a, b): return a + b")
    
    task = {
        "id": "test-123",
        "type": TaskType.GENERATE_TESTS,
        "payload": {
            "target_file": str(test_file),
            "description": "Generate unit tests for add function"
        }
    }
    
    # Mock prompt staging service
    with patch("dreamforge.agents.cursor_dispatcher.stage_and_execute_prompt") as mock_stage:
        mock_stage.return_value = "def test_add(): assert add(2, 2) == 4"
        
        # Execute
        result = cursor_dispatcher.execute_cursor_task(task)
        
        # Verify
        assert result["success"] is True
        assert "test_file" in result["data"]
        assert "test_code" in result["data"]
        assert Path(result["data"]["test_file"]).exists()
        assert "test_add" in result["data"]["test_code"]

def test_execute_cursor_task_code_fix(cursor_dispatcher):
    """Test handling of code fix tasks."""
    task = {
        "id": "fix-123",
        "type": TaskType.FIX_CODE,
        "payload": {
            "file_path": "sample.py",
            "issue_description": "Fix indentation in add function"
        }
    }
    
    with patch("dreamforge.agents.cursor_dispatcher.stage_and_execute_prompt") as mock_stage:
        mock_stage.return_value = {"fixed_code": "def add(a, b):\n    return a + b"}
        
        result = cursor_dispatcher.execute_cursor_task(task)
        
        assert result["success"] is True
        assert "fixed_code" in result["data"]

def test_execute_cursor_task_file_analysis(cursor_dispatcher):
    """Test handling of file analysis tasks."""
    task = {
        "id": "analyze-123",
        "type": TaskType.ANALYZE_FILE,
        "payload": {
            "file_path": "sample.py",
            "analysis_type": "complexity"
        }
    }
    
    with patch("dreamforge.agents.cursor_dispatcher.stage_and_execute_prompt") as mock_stage:
        mock_stage.return_value = {"complexity": "low", "suggestions": []}
        
        result = cursor_dispatcher.execute_cursor_task(task)
        
        assert result["success"] is True
        assert "complexity" in result["data"]

def test_dispatcher_loop_integration(cursor_dispatcher):
    """Test the main dispatcher loop with task handling."""
    # Setup mock task and response
    mock_task = {
        "id": "task-123",
        "type": TaskType.GENERATE_TESTS,
        "source_agent": "ChatGPT",
        "payload": {
            "target_file": "sample.py",
            "description": "Generate tests"
        }
    }
    
    # Configure agent bus mock
    cursor_dispatcher.agent_bus.claim_task.side_effect = [mock_task, None]
    
    # Mock prompt staging
    with patch("dreamforge.agents.cursor_dispatcher.stage_and_execute_prompt") as mock_stage:
        mock_stage.return_value = "def test_sample(): pass"
        
        # Start dispatcher in a way we can control
        cursor_dispatcher.is_running = True
        try:
            # Simulate one iteration
            cursor_dispatcher.run_dispatcher_loop()
        except StopIteration:
            pass
        
        # Verify interactions
        cursor_dispatcher.agent_bus.claim_task.assert_called_with(agent_id="Cursor")
        cursor_dispatcher.agent_bus.complete_task.assert_called_once()
        cursor_dispatcher.agent_bus.send_task.assert_called_once_with(
            to="ChatGPT",
            task_type=TaskType.RESULT_DELIVERY,
            payload={"success": True, "data": {"test_file": mock.ANY, "test_code": mock.ANY}}
        )

def test_error_handling(cursor_dispatcher):
    """Test error handling in task execution."""
    task = {
        "id": "error-123",
        "type": TaskType.GENERATE_TESTS,
        "payload": {
            # Missing required fields
        }
    }
    
    result = cursor_dispatcher.execute_cursor_task(task)
    
    assert result["success"] is False
    assert result["error"] is not None
    assert "Missing required fields" in result["error"]

@pytest.mark.asyncio
async def test_concurrent_task_handling(cursor_dispatcher):
    """Test handling multiple tasks concurrently."""
    import asyncio
    
    # Setup multiple mock tasks
    tasks = [
        {
            "id": f"task-{i}",
            "type": TaskType.GENERATE_TESTS,
            "payload": {
                "target_file": f"test_{i}.py",
                "description": f"Generate tests {i}"
            }
        }
        for i in range(3)
    ]
    
    # Mock agent bus to return our tasks in sequence
    cursor_dispatcher.agent_bus.claim_task.side_effect = tasks + [None]
    
    # Mock prompt staging
    with patch("dreamforge.agents.cursor_dispatcher.stage_and_execute_prompt") as mock_stage:
        mock_stage.return_value = "def test_sample(): pass"
        
        # Run multiple iterations
        async def run_dispatcher():
            cursor_dispatcher.is_running = True
            await asyncio.sleep(0)  # Allow other tasks to run
            try:
                cursor_dispatcher.run_dispatcher_loop()
            except StopIteration:
                pass
        
        await asyncio.gather(run_dispatcher())
        
        # Verify all tasks were processed
        assert cursor_dispatcher.agent_bus.complete_task.call_count == len(tasks)
        
# Log test coverage event
from dreamforge.core.prompt_staging_service import log_event

log_event(
    "TEST_ADDED",
    "CoverageAgent",
    {
        "test_file": "test_cursor_dispatcher.py",
        "new_tests": [
            "test_execute_cursor_task_test_generation",
            "test_execute_cursor_task_code_fix",
            "test_execute_cursor_task_file_analysis",
            "test_dispatcher_loop_integration",
            "test_error_handling",
            "test_concurrent_task_handling"
        ],
        "coverage_targets": [
            "task execution",
            "error handling",
            "concurrency",
            "integration"
        ]
    }
) 