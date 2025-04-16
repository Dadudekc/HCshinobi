import pytest
import time
from unittest.mock import MagicMock, patch
from pathlib import Path

from dreamforge.core.enums.task_types import TaskType
from dreamforge.agents.chatgpt_commander import ChatGPTCommander
from dreamforge.core.agent_bus import AgentBus

@pytest.fixture
def mock_agent_bus():
    return MagicMock(spec=AgentBus)

@pytest.fixture
def commander(mock_agent_bus):
    commander = ChatGPTCommander()
    commander.agent_bus = mock_agent_bus
    return commander

def test_send_generate_tests_task(commander):
    """Test sending a test generation task."""
    # Setup
    target_file = "test_file.py"
    description = "Generate tests for math functions"
    
    # Configure mock
    commander.agent_bus.send_task.return_value = "task-123"
    
    # Execute
    result = commander.send_generate_tests_task(target_file, description)
    
    # Verify
    assert result["task_id"] == "task-123"
    assert result["status"] == "sent"
    commander.agent_bus.send_task.assert_called_once_with(
        to="Cursor",
        task_type=TaskType.GENERATE_TESTS,
        payload={
            "target_file": target_file,
            "description": description
        },
        metadata={
            "origin": "ChatGPT",
            "timestamp": pytest.approx(time.time(), abs=1)
        }
    )

def test_send_code_fix_task(commander):
    """Test sending a code fix task."""
    file_path = "broken.py"
    issue = "Fix indentation errors"
    
    commander.agent_bus.send_task.return_value = "task-456"
    
    result = commander.send_code_fix_task(file_path, issue)
    
    assert result["task_id"] == "task-456"
    assert result["status"] == "sent"
    commander.agent_bus.send_task.assert_called_once_with(
        to="Cursor",
        task_type=TaskType.FIX_CODE,
        payload={
            "file_path": file_path,
            "issue_description": issue
        },
        metadata={"origin": "ChatGPT"}
    )

def test_send_analysis_task(commander):
    """Test sending a file analysis task."""
    file_path = "analyze_me.py"
    
    commander.agent_bus.send_task.return_value = "task-789"
    
    result = commander.send_analysis_task(file_path, "complexity")
    
    assert result["task_id"] == "task-789"
    assert result["status"] == "sent"
    commander.agent_bus.send_task.assert_called_once_with(
        to="Cursor",
        task_type=TaskType.ANALYZE_FILE,
        payload={
            "file_path": file_path,
            "analysis_type": "complexity"
        },
        metadata={"origin": "ChatGPT"}
    )

def test_wait_for_task_completion(commander):
    """Test waiting for task completion."""
    task_id = "wait-123"
    expected_result = {"status": "success", "data": "test output"}
    
    # Mock get_task_result to return None twice, then the result
    commander.agent_bus.get_task_result.side_effect = [None, None, expected_result]
    
    result = commander.wait_for_task_completion(task_id, timeout=5)
    
    assert result["status"] == "completed"
    assert result["result"] == expected_result
    assert commander.pending_tasks[task_id]["status"] == "completed"

def test_wait_for_task_timeout(commander):
    """Test task timeout handling."""
    task_id = "timeout-123"
    
    # Mock get_task_result to always return None
    commander.agent_bus.get_task_result.return_value = None
    
    result = commander.wait_for_task_completion(task_id, timeout=1)
    
    assert result["status"] == "timeout"
    assert "error" in result
    assert commander.pending_tasks[task_id]["status"] == "timeout"

def test_get_task_status(commander):
    """Test getting task status."""
    task_id = "status-123"
    commander.pending_tasks[task_id] = {
        "type": TaskType.GENERATE_TESTS,
        "status": "sent",
        "timestamp": time.time()
    }
    
    # Mock completion
    commander.agent_bus.get_task_result.return_value = {"status": "success"}
    
    status = commander.get_task_status(task_id)
    
    assert status["status"] == "completed"
    assert "result" in status

def test_cleanup_old_tasks(commander):
    """Test cleaning up old tasks."""
    # Add some tasks with old timestamps
    old_time = time.time() - 7200  # 2 hours ago
    commander.pending_tasks.update({
        "old-1": {"timestamp": old_time, "status": "sent"},
        "old-2": {"timestamp": old_time, "status": "completed"},
        "new-1": {"timestamp": time.time(), "status": "sent"}
    })
    
    commander.cleanup_old_tasks(max_age=3600)  # 1 hour
    
    assert "old-1" not in commander.pending_tasks
    assert "old-2" not in commander.pending_tasks
    assert "new-1" in commander.pending_tasks

@pytest.mark.asyncio
async def test_concurrent_task_handling(commander):
    """Test handling multiple concurrent tasks."""
    import asyncio
    
    # Setup multiple tasks
    tasks = [
        ("test1.py", "Generate tests 1"),
        ("test2.py", "Generate tests 2"),
        ("test3.py", "Generate tests 3")
    ]
    
    commander.agent_bus.send_task.side_effect = [f"task-{i}" for i in range(len(tasks))]
    
    # Send tasks concurrently
    async def send_tasks():
        results = []
        for target_file, description in tasks:
            results.append(
                commander.send_generate_tests_task(target_file, description)
            )
        return results
        
    results = await asyncio.gather(send_tasks())
    
    assert len(results) == len(tasks)
    assert all(r["status"] == "sent" for r in results)
    assert commander.agent_bus.send_task.call_count == len(tasks)

# Log test coverage event
from dreamforge.core.prompt_staging_service import log_event

log_event(
    "TEST_ADDED",
    "CoverageAgent",
    {
        "test_file": "test_chatgpt_commander.py",
        "new_tests": [
            "test_send_generate_tests_task",
            "test_send_code_fix_task",
            "test_send_analysis_task",
            "test_wait_for_task_completion",
            "test_wait_for_task_timeout",
            "test_get_task_status",
            "test_cleanup_old_tasks",
            "test_concurrent_task_handling"
        ],
        "coverage_targets": [
            "task dispatch",
            "response handling",
            "timeout handling",
            "task management",
            "concurrency"
        ]
    }
) 