"""Shared test fixtures and utilities."""
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message
)
from dreamforge.core.utils.performance_logger import PerformanceLogger

@pytest.fixture
def mock_agent_bus():
    """Create a mock agent bus with async capabilities."""
    mock = Mock(spec=AgentBus)
    mock.publish = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.unsubscribe = AsyncMock()
    mock.start = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock

@pytest.fixture
def mock_perf_logger():
    """Create a mock performance logger."""
    return Mock(spec=PerformanceLogger)

def create_test_message(
    msg_type=MessageType.EVENT,
    sender="test_agent",
    content=None,
    correlation_id=None
):
    """Create a test message with default values."""
    return Message(
        type=msg_type,
        sender=sender,
        content=content or {"test": "data"},
        correlation_id=correlation_id or "test_123"
    )

def create_test_task(
    task_type="test_task",
    agent_id="test_agent",
    input_data=None,
    priority=TaskPriority.NORMAL,
    status=TaskStatus.PENDING
):
    """Create a test task with default values."""
    task = create_task_message(
        task_type=task_type,
        agent_id=agent_id,
        input_data=input_data or {"test": "data"}
    )
    return task._replace(priority=priority, status=status)

@pytest.fixture
async def wait_for_message_processing():
    """Helper to wait for async message processing."""
    async def _wait():
        await asyncio.sleep(0.1)
    return _wait 