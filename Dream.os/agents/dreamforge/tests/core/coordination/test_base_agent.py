"""Tests for the BaseAgent class."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
from dreamforge.core.coordination.base_agent import BaseAgent

class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    def __init__(self):
        super().__init__("TestAgent")
        self.start_called = False
        self.stop_called = False
        
    async def _on_start(self):
        self.start_called = True
        
    async def _on_stop(self):
        self.stop_called = True

@pytest.fixture
def mock_agent_bus():
    """Create a mock AgentBus."""
    mock_bus = Mock(spec=AgentBus)
    mock_bus.publish = AsyncMock()
    mock_bus.subscribe = AsyncMock()
    mock_bus.unsubscribe = AsyncMock()
    mock_bus.start = AsyncMock()
    mock_bus.shutdown = AsyncMock()
    return mock_bus

@pytest.fixture
def test_agent(mock_agent_bus):
    """Create a TestAgent instance with a mock bus."""
    with patch('dreamforge.core.coordination.base_agent.AgentBus', return_value=mock_agent_bus):
        agent = TestAgent()
        return agent

@pytest.mark.asyncio
async def test_agent_initialization(test_agent, mock_agent_bus):
    """Test agent initialization."""
    assert test_agent.agent_id == "TestAgent"
    assert test_agent.agent_bus == mock_agent_bus
    assert test_agent._subscription_id is None
    assert test_agent._running is False
    assert len(test_agent._command_handlers) == 0

@pytest.mark.asyncio
async def test_agent_start_stop(test_agent, mock_agent_bus):
    """Test agent start and stop sequence."""
    # Test start
    await test_agent.start()
    assert test_agent._running is True
    assert test_agent.start_called is True
    mock_agent_bus.subscribe.assert_called_once()
    mock_agent_bus.start.assert_called_once()
    
    # Test stop
    await test_agent.stop()
    assert test_agent._running is False
    assert test_agent.stop_called is True
    mock_agent_bus.unsubscribe.assert_called_once()
    mock_agent_bus.shutdown.assert_called_once()

@pytest.mark.asyncio
async def test_command_handler_registration(test_agent):
    """Test command handler registration."""
    async def test_handler(task: TaskMessage):
        return {"status": "success", "result": "test"}
        
    test_agent.register_command_handler("test_command", test_handler)
    assert "test_command" in test_agent._command_handlers
    assert test_agent._command_handlers["test_command"] == test_handler

@pytest.mark.asyncio
async def test_handle_command_success(test_agent, mock_agent_bus):
    """Test successful command handling."""
    # Register test handler
    async def test_handler(task: TaskMessage):
        return {"status": "success", "result": "test_output"}
        
    test_agent.register_command_handler("test_command", test_handler)
    
    # Create test task
    task = create_task_message(
        task_type="test_command",
        agent_id="TestAgent",
        input_data={"test": "data"},
        priority=TaskPriority.NORMAL
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    # Start agent and handle command
    await test_agent.start()
    await test_agent._handle_command(message)
    
    # Process the task from queue
    priority, queued_task, correlation_id = await test_agent._task_queue.get()
    await test_agent._process_single_task(queued_task, correlation_id)
    
    # Verify message publishing
    assert mock_agent_bus.publish.call_count >= 2  # Status updates + response
    
    # Verify the final response
    response_call = mock_agent_bus.publish.call_args_list[-1]
    response_msg = response_call[0][0]
    assert response_msg.type == MessageType.RESPONSE
    assert response_msg.correlation_id == "test_correlation"

@pytest.mark.asyncio
async def test_handle_command_error(test_agent, mock_agent_bus):
    """Test error handling in command processing."""
    # Register test handler that raises an exception
    async def error_handler(task: TaskMessage):
        raise ValueError("Test error")
        
    test_agent.register_command_handler("error_command", error_handler)
    
    # Create test task
    task = create_task_message(
        task_type="error_command",
        agent_id="TestAgent",
        input_data={"test": "data"}
    )
    
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    # Start agent and handle command
    await test_agent.start()
    await test_agent._handle_command(message)
    
    # Process the task from queue
    priority, queued_task, correlation_id = await test_agent._task_queue.get()
    await test_agent._process_single_task(queued_task, correlation_id)
    
    # Verify error response
    error_call = mock_agent_bus.publish.call_args_list[-1]
    error_msg = error_call[0][0]
    assert error_msg.type == MessageType.ERROR
    assert "Test error" in error_msg.content["error"]

@pytest.mark.asyncio
async def test_task_cancellation(test_agent, mock_agent_bus):
    """Test task cancellation."""
    # Create a long-running task
    task = create_task_message(
        task_type="test_task",
        agent_id="TestAgent",
        input_data={"action": "long_running"}
    )
    
    # Create cancellation request
    cancel_task = create_task_message(
        task_type="cancel_task",
        agent_id="TestAgent",
        input_data={"target_task_id": task.task_id}
    )
    
    # Register test handler
    async def long_running_handler(task: TaskMessage):
        await asyncio.sleep(10)
        return {"status": "success"}
        
    test_agent.register_command_handler("test_task", long_running_handler)
    
    # Start agent
    await test_agent.start()
    
    # Submit task
    message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=task.to_message_content(),
        correlation_id="test_correlation"
    )
    
    await test_agent._handle_command(message)
    
    # Get and start processing the task
    priority, queued_task, correlation_id = await test_agent._task_queue.get()
    process_task = asyncio.create_task(test_agent._process_single_task(queued_task, correlation_id))
    test_agent._active_tasks[task.task_id] = process_task
    
    # Send cancellation request
    cancel_message = Message(
        type=MessageType.COMMAND,
        sender="TestAgent",
        content=cancel_task.to_message_content(),
        correlation_id="cancel_correlation"
    )
    
    await test_agent._handle_command(cancel_message)
    
    # Verify task was cancelled
    assert task.task_id not in test_agent._active_tasks
    
    # Verify cancellation response
    cancel_response = mock_agent_bus.publish.call_args_list[-1][0][0]
    assert cancel_response.type == MessageType.RESPONSE
    assert "cancelled" in cancel_response.content["message"]

@pytest.mark.asyncio
async def test_task_priority_ordering(test_agent, mock_agent_bus):
    """Test that tasks are processed in priority order."""
    processed_tasks = []
    
    # Register test handler
    async def test_handler(task: TaskMessage):
        processed_tasks.append(task.input_data["task_name"])
        return {"status": "success"}
        
    test_agent.register_command_handler("test_task", test_handler)
    
    # Create tasks with different priorities
    tasks = [
        (TaskPriority.LOW, "low_task"),
        (TaskPriority.NORMAL, "normal_task"),
        (TaskPriority.HIGH, "high_task"),
        (TaskPriority.CRITICAL, "critical_task")
    ]
    
    # Start agent
    await test_agent.start()
    
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
        
        await test_agent._handle_command(message)
        
    # Process all tasks
    while not test_agent._task_queue.empty():
        priority, task, correlation_id = await test_agent._task_queue.get()
        await test_agent._process_single_task(task, correlation_id)
        test_agent._task_queue.task_done()
        
    # Verify tasks were processed in priority order
    expected_order = ["critical_task", "high_task", "normal_task", "low_task"]
    assert processed_tasks == expected_order 