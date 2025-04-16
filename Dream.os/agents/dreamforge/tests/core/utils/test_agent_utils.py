"""Tests for agent utility functions."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from dreamforge.core.utils.agent_utils import (
    with_error_handling,
    with_performance_tracking,
    publish_task_update,
    publish_error,
    handle_task_cancellation,
    log_task_performance,
    AgentError,
    TaskProcessingError,
    MessageHandlingError
)
from dreamforge.core.coordination.message_patterns import TaskStatus
from dreamforge.core.coordination.agent_bus import MessageType

# Remove duplicate fixtures - now using shared ones from conftest.py

@pytest.mark.asyncio
async def test_error_handling_decorator():
    """Test the error handling decorator."""
    error_msg = "Test error"
    
    @with_error_handling(AgentError)
    async def failing_func():
        raise ValueError(error_msg)
    
    with pytest.raises(AgentError) as exc_info:
        await failing_func()
    assert str(exc_info.value) == error_msg

@pytest.mark.asyncio
async def test_performance_tracking_decorator(mock_perf_logger):
    """Test the performance tracking decorator."""
    class TestClass:
        def __init__(self):
            self.perf_logger = mock_perf_logger
            
        @with_performance_tracking("test_op")
        async def tracked_method(self):
            await asyncio.sleep(0.1)
            return "success"
    
    test_obj = TestClass()
    result = await test_obj.tracked_method()
    
    assert result == "success"
    mock_perf_logger.track_operation.assert_called_once_with("test_op")

@pytest.mark.asyncio
async def test_publish_task_update(mock_agent_bus, create_test_task):
    """Test publishing task status updates."""
    task = create_test_task()
    
    await publish_task_update(
        mock_agent_bus,
        task,
        "test_agent",
        "test_correlation"
    )
    
    mock_agent_bus.publish.assert_called_once()
    published_msg = mock_agent_bus.publish.call_args[0][0]
    assert published_msg.type == MessageType.EVENT
    assert published_msg.sender == "test_agent"
    assert published_msg.correlation_id == "test_correlation"

@pytest.mark.asyncio
async def test_publish_error(mock_agent_bus):
    """Test publishing error messages."""
    error_msg = "Test error"
    details = {"extra": "info"}
    
    await publish_error(
        mock_agent_bus,
        error_msg,
        "test_agent",
        "test_correlation",
        details
    )
    
    mock_agent_bus.publish.assert_called_once()
    published_msg = mock_agent_bus.publish.call_args[0][0]
    assert published_msg.type == MessageType.ERROR
    assert published_msg.sender == "test_agent"
    assert published_msg.correlation_id == "test_correlation"
    assert published_msg.content["error"] == error_msg
    assert published_msg.content["extra"] == "info"

@pytest.mark.asyncio
async def test_handle_task_cancellation(mock_agent_bus):
    """Test task cancellation handling."""
    active_tasks = {}
    mock_task = AsyncMock()
    task_id = "test_task"
    active_tasks[task_id] = mock_task
    
    await handle_task_cancellation(
        task_id,
        active_tasks,
        mock_agent_bus,
        "test_agent",
        "test_correlation"
    )
    
    mock_task.cancel.assert_called_once()
    mock_agent_bus.publish.assert_called_once()
    published_msg = mock_agent_bus.publish.call_args[0][0]
    assert published_msg.type == MessageType.RESPONSE
    assert "cancelled" in published_msg.content["message"]

@pytest.mark.asyncio
async def test_handle_task_cancellation_not_found(mock_agent_bus):
    """Test cancellation of non-existent task."""
    active_tasks = {}
    
    await handle_task_cancellation(
        "non_existent",
        active_tasks,
        mock_agent_bus,
        "test_agent",
        "test_correlation"
    )
    
    mock_agent_bus.publish.assert_called_once()
    published_msg = mock_agent_bus.publish.call_args[0][0]
    assert published_msg.type == MessageType.ERROR
    assert "not found" in published_msg.content["error"]

def test_log_task_performance(mock_perf_logger, create_test_task):
    """Test task performance logging."""
    task = create_test_task(status=TaskStatus.COMPLETED)
    task = task._replace(result={"output": "test"})
    
    log_task_performance(task, "test_agent", mock_perf_logger)
    
    mock_perf_logger.log_outcome.assert_called_once()
    call_args = mock_perf_logger.log_outcome.call_args[1]
    assert call_args["task_id"] == task.task_id
    assert call_args["agent_id"] == "test_agent"
    assert call_args["task_type"] == task.task_type
    assert call_args["status"] == task.status.value

def test_log_task_performance_error_handling(mock_perf_logger, create_test_task):
    """Test error handling in performance logging."""
    task = create_test_task()
    
    mock_perf_logger.log_outcome.side_effect = Exception("Test error")
    
    # Should not raise exception
    log_task_performance(task, "test_agent", mock_perf_logger)

@pytest.mark.asyncio
async def test_error_handling_nested_decorators():
    """Test error handling with nested decorators."""
    error_msg = "Nested error"
    
    @with_error_handling(AgentError)
    @with_performance_tracking("nested_op")
    async def nested_func():
        raise ValueError(error_msg)
    
    with pytest.raises(AgentError) as exc_info:
        await nested_func()
    assert str(exc_info.value) == error_msg

@pytest.mark.asyncio
async def test_publish_task_update_with_large_payload(mock_agent_bus, create_test_task):
    """Test publishing task updates with large payloads."""
    large_data = {"data": "x" * 1000000}  # 1MB of data
    task = create_test_task(input_data=large_data)
    
    await publish_task_update(
        mock_agent_bus,
        task,
        "test_agent",
        "test_correlation"
    )
    
    mock_agent_bus.publish.assert_called_once()
    published_msg = mock_agent_bus.publish.call_args[0][0]
    assert published_msg.type == MessageType.EVENT
    assert len(str(published_msg.content)) <= 1000000

@pytest.mark.asyncio
async def test_concurrent_task_cancellation(mock_agent_bus):
    """Test cancelling multiple tasks concurrently."""
    active_tasks = {}
    task_ids = ["task1", "task2", "task3"]
    
    for task_id in task_ids:
        active_tasks[task_id] = AsyncMock()
    
    await asyncio.gather(*[
        handle_task_cancellation(
            task_id,
            active_tasks,
            mock_agent_bus,
            "test_agent",
            f"corr_{task_id}"
        )
        for task_id in task_ids
    ])
    
    assert mock_agent_bus.publish.call_count == len(task_ids)
    for task_mock in active_tasks.values():
        task_mock.cancel.assert_called_once()

def test_log_task_performance_with_missing_fields(mock_perf_logger, create_test_task):
    """Test performance logging with missing optional fields."""
    task = create_test_task()
    
    log_task_performance(task, "test_agent", mock_perf_logger)
    
    mock_perf_logger.log_outcome.assert_called_once()
    call_args = mock_perf_logger.log_outcome.call_args[1]
    assert call_args["task_id"] == task.task_id
    assert call_args.get("result") is None
    assert call_args.get("error") is None 