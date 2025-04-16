"""Tests for the CursorDispatcher agent."""
import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
from dreamforge.core.cursor_dispatcher import CursorDispatcher, execute_cursor_task

@pytest.fixture
def mock_agent_bus():
    """Create a mock AgentBus."""
    mock_bus = Mock(spec=AgentBus)
    mock_bus.publish = Mock()
    mock_bus.subscribe = Mock()
    mock_bus.unsubscribe = Mock()
    mock_bus.start = Mock()
    mock_bus.shutdown = Mock()
    return mock_bus

@pytest.fixture
def dispatcher(mock_agent_bus):
    """Create a CursorDispatcher instance with a mock bus."""
    with patch('dreamforge.core.cursor_dispatcher.AgentBus', return_value=mock_agent_bus):
        dispatcher = CursorDispatcher()
        return dispatcher

@pytest.mark.asyncio
async def test_dispatcher_initialization(dispatcher, mock_agent_bus):
    """Test dispatcher initialization."""
    assert dispatcher.agent_bus == mock_agent_bus
    assert dispatcher._subscription_id is None
    assert dispatcher._running is False

@pytest.mark.asyncio
async def test_dispatcher_start(dispatcher, mock_agent_bus):
    """Test dispatcher start sequence."""
    await dispatcher.start()
    
    assert dispatcher._running is True
    mock_agent_bus.subscribe.assert_called_once()
    mock_agent_bus.start.assert_called_once()

@pytest.mark.asyncio
async def test_dispatcher_stop(dispatcher, mock_agent_bus):
    """Test dispatcher stop sequence."""
    # Set up initial state
    dispatcher._running = True
    dispatcher._subscription_id = "test_sub_id"
    
    await dispatcher.stop()
    
    assert dispatcher._running is False
    mock_agent_bus.unsubscribe.assert_called_once_with("test_sub_id")
    mock_agent_bus.shutdown.assert_called_once()

@pytest.mark.asyncio
async def test_handle_successful_command(dispatcher, mock_agent_bus):
    """Test handling a successful command."""
    # Create a test task
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "generate_code", "prompt": "test prompt"}
    )
    
    # Create a test message
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    # Mock execute_cursor_task to return success
    with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task') as mock_execute:
        mock_execute.return_value = {"status": "success", "output": "test output"}
        
        # Handle the command
        await dispatcher._handle_command(message)
        
        # Verify message publishing
        assert mock_agent_bus.publish.call_count == 2  # Status update + response
        
        # Verify the response message
        response_call = mock_agent_bus.publish.call_args_list[1]
        response_msg = response_call[0][0]
        assert response_msg.type == MessageType.RESPONSE
        assert response_msg.correlation_id == "test_correlation"

@pytest.mark.asyncio
async def test_handle_failed_command(dispatcher, mock_agent_bus):
    """Test handling a failed command."""
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "generate_code", "prompt": "fail test"}
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task') as mock_execute:
        mock_execute.return_value = {"status": "error", "error": "test error"}
        
        await dispatcher._handle_command(message)
        
        assert mock_agent_bus.publish.call_count == 2  # Status update + error
        
        error_call = mock_agent_bus.publish.call_args_list[1]
        error_msg = error_call[0][0]
        assert error_msg.type == MessageType.ERROR
        assert error_msg.correlation_id == "test_correlation"

@pytest.mark.asyncio
async def test_handle_unexpected_result(dispatcher, mock_agent_bus):
    """Test handling unexpected result format."""
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "test"}
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task') as mock_execute:
        mock_execute.return_value = None  # Unexpected result
        
        await dispatcher._handle_command(message)
        
        assert mock_agent_bus.publish.call_count == 2
        
        error_call = mock_agent_bus.publish.call_args_list[1]
        error_msg = error_call[0][0]
        assert error_msg.type == MessageType.ERROR
        assert "Unexpected result format" in error_msg.content["error"]

@pytest.mark.asyncio
async def test_publish_status_update(dispatcher, mock_agent_bus):
    """Test publishing status updates."""
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "test"}
    )
    
    await dispatcher._publish_status_update(task)
    
    mock_agent_bus.publish.assert_called_once()
    status_msg = mock_agent_bus.publish.call_args[0][0]
    assert status_msg.type == MessageType.EVENT
    assert status_msg.correlation_id == task.correlation_id

def test_execute_cursor_task_generate_code():
    """Test execute_cursor_task with code generation."""
    result = execute_cursor_task({
        "action": "generate_code",
        "prompt": "test prompt"
    })
    
    assert result["status"] == "success"
    assert "code_generated" in result

def test_execute_cursor_task_edit_file():
    """Test execute_cursor_task with file editing."""
    result = execute_cursor_task({
        "action": "edit_file",
        "target_file": "test.py"
    })
    
    assert result["status"] == "success"
    assert result["file_edited"] == "test.py"
    assert result["changes_applied"] is True

def test_execute_cursor_task_failure():
    """Test execute_cursor_task failure case."""
    result = execute_cursor_task({
        "action": "generate_code",
        "prompt": "fail test"
    })
    
    assert result["status"] == "error"
    assert "error" in result

@pytest.mark.asyncio
async def test_task_priority_ordering(dispatcher, mock_agent_bus):
    """Test that tasks are processed in priority order."""
    # Create tasks with different priorities
    tasks = [
        (TaskPriority.LOW, "low_task"),
        (TaskPriority.NORMAL, "normal_task"),
        (TaskPriority.HIGH, "high_task"),
        (TaskPriority.CRITICAL, "critical_task")
    ]
    
    processed_tasks = []
    
    # Mock execute_cursor_task to track task processing order
    async def mock_process_task(task_input):
        processed_tasks.append(task_input["task_name"])
        return {"status": "success"}
        
    with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task', side_effect=mock_process_task):
        # Submit tasks in reverse priority order
        for priority, task_name in reversed(tasks):
            task = create_task_message(
                task_type="test_task",
                agent_id="TestAgent",
                input_data={"task_name": task_name},
                priority=priority
            )
            
            message = Message(
                type=MessageType.COMMAND,
                sender="TestAgent",
                content=task.to_message_content(),
                correlation_id=f"corr_{task_name}"
            )
            
            await dispatcher._handle_command(message)
            
        # Process all tasks
        while not dispatcher._task_queue.empty():
            priority, task, correlation_id = await dispatcher._task_queue.get()
            await dispatcher._process_single_task(task, correlation_id)
            dispatcher._task_queue.task_done()
            
    # Verify tasks were processed in priority order
    expected_order = ["critical_task", "high_task", "normal_task", "low_task"]
    assert processed_tasks == expected_order

@pytest.mark.asyncio
async def test_task_cancellation(dispatcher, mock_agent_bus):
    """Test task cancellation."""
    # Create a long-running task
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "long_running"},
        priority=TaskPriority.NORMAL
    )
    
    # Create cancellation request
    cancel_task = create_task_message(
        task_type="cancel_task",
        agent_id="TestAgent",
        input_data={"target_task_id": task.task_id},
        priority=TaskPriority.HIGH
    )
    
    # Mock execute_cursor_task to simulate long-running task
    async def mock_long_running_task(task_input):
        await asyncio.sleep(10)  # Long running operation
        return {"status": "success"}
        
    with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task', side_effect=mock_long_running_task):
        # Start the task
        message = Message(
            type=MessageType.COMMAND,
            sender="TestAgent",
            content=task.to_message_content(),
            correlation_id="test_correlation"
        )
        
        # Submit task
        await dispatcher._handle_command(message)
        
        # Get and start processing the task
        priority, queued_task, correlation_id = await dispatcher._task_queue.get()
        process_task = asyncio.create_task(dispatcher._process_single_task(queued_task, correlation_id))
        dispatcher._active_tasks[task.task_id] = process_task
        
        # Send cancellation request
        cancel_message = Message(
            type=MessageType.COMMAND,
            sender="TestAgent",
            content=cancel_task.to_message_content(),
            correlation_id="cancel_correlation"
        )
        
        await dispatcher._handle_command(cancel_message)
        
        # Verify task was cancelled
        assert task.task_id not in dispatcher._active_tasks
        
        # Verify cancellation response
        cancel_response = mock_agent_bus.publish.call_args_list[-1][0][0]
        assert cancel_response.type == MessageType.RESPONSE
        assert "cancelled" in cancel_response.content["message"]

@pytest.mark.asyncio
async def test_invalid_task_cancellation(dispatcher, mock_agent_bus):
    """Test cancellation of non-existent task."""
    cancel_task = create_task_message(
        task_type="cancel_task",
        agent_id="TestAgent",
        input_data={"target_task_id": "non_existent_task"},
        priority=TaskPriority.HIGH
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=cancel_task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    await dispatcher._handle_command(message)
    
    # Verify error response
    error_response = mock_agent_bus.publish.call_args[0][0]
    assert error_response.type == MessageType.ERROR
    assert "not found" in error_response.content["error"]

@pytest.mark.asyncio
async def test_missing_task_id_cancellation(dispatcher, mock_agent_bus):
    """Test cancellation request without task ID."""
    cancel_task = create_task_message(
        task_type="cancel_task",
        agent_id="TestAgent",
        input_data={},  # Missing target_task_id
        priority=TaskPriority.HIGH
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=cancel_task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    await dispatcher._handle_command(message)
    
    # Verify error response
    error_response = mock_agent_bus.publish.call_args[0][0]
    assert error_response.type == MessageType.ERROR
    assert "No target_task_id provided" in error_response.content["error"]

@pytest.mark.asyncio
async def test_graceful_shutdown(dispatcher, mock_agent_bus):
    """Test graceful shutdown with active tasks."""
    # Create and start some tasks
    tasks = []
    for i in range(3):
        task = create_task_message(
            task_type="test_task",
            agent_id="TestAgent",
            input_data={"task_num": i},
            priority=TaskPriority.NORMAL
        )
        
        # Mock long-running tasks
        async def mock_long_task(task_input):
            await asyncio.sleep(10)
            return {"status": "success"}
            
        with patch('dreamforge.core.cursor_dispatcher.execute_cursor_task', side_effect=mock_long_task):
            process_task = asyncio.create_task(dispatcher._process_single_task(task, f"corr_{i}"))
            dispatcher._active_tasks[task.task_id] = process_task
            tasks.append(task)
            
    # Stop the dispatcher
    await dispatcher.stop()
    
    # Verify all tasks were cancelled
    assert len(dispatcher._active_tasks) == 0
    for task_id in [t.task_id for t in tasks]:
        assert task_id not in dispatcher._active_tasks 