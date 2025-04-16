"""Tests for agent message bus system."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from dreamforge.core.agent_bus import AgentBus, Message, MessageType, BusError
from dreamforge.core.memory.governance_memory_engine import log_event

@pytest.fixture
async def agent_bus():
    """Create an agent bus instance for testing."""
    bus = AgentBus()
    log_event("TEST_ADDED", "TestAgentBus", {"test": "agent_bus_fixture"})
    yield bus
    await bus.shutdown()

@pytest.mark.asyncio
async def test_agent_bus_initialization(agent_bus):
    """Test agent bus initialization."""
    assert agent_bus.is_running
    assert len(agent_bus.subscribers) == 0
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_agent_bus_initialization"})

@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe(agent_bus):
    """Test subscription management."""
    callback = AsyncMock()
    
    # Test subscription
    subscription_id = await agent_bus.subscribe(MessageType.COMMAND, callback)
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_subscribe_and_unsubscribe"})
    
    assert subscription_id in agent_bus.subscribers
    assert agent_bus.subscribers[subscription_id].callback == callback
    assert agent_bus.subscribers[subscription_id].message_type == MessageType.COMMAND
    
    # Test unsubscription
    await agent_bus.unsubscribe(subscription_id)
    assert subscription_id not in agent_bus.subscribers

@pytest.mark.asyncio
async def test_publish_message(agent_bus, create_test_message, wait_for_message_processing):
    """Test message publishing and delivery."""
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
    
    await agent_bus.subscribe(MessageType.EVENT, callback)
    message = create_test_message()
    
    await agent_bus.publish(message)
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_publish_message"})
    
    await wait_for_message_processing()
    
    assert len(received_messages) == 1
    assert received_messages[0].content == {"test": "data"}
    assert received_messages[0].sender == "test_agent"

@pytest.mark.asyncio
async def test_message_filtering(agent_bus, create_test_message, wait_for_message_processing):
    """Test message filtering by type."""
    command_messages = []
    event_messages = []
    
    async def command_callback(message):
        command_messages.append(message)
    
    async def event_callback(message):
        event_messages.append(message)
    
    await agent_bus.subscribe(MessageType.COMMAND, command_callback)
    await agent_bus.subscribe(MessageType.EVENT, event_callback)
    
    # Publish different types of messages
    command_msg = create_test_message(msg_type=MessageType.COMMAND)
    event_msg = create_test_message(msg_type=MessageType.EVENT)
    
    await agent_bus.publish(command_msg)
    await agent_bus.publish(event_msg)
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_message_filtering"})
    
    await wait_for_message_processing()
    
    assert len(command_messages) == 1
    assert len(event_messages) == 1
    assert command_messages[0].type == MessageType.COMMAND
    assert event_messages[0].type == MessageType.EVENT

@pytest.mark.asyncio
async def test_message_correlation(agent_bus, create_test_message, wait_for_message_processing):
    """Test message correlation tracking."""
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
    
    await agent_bus.subscribe(MessageType.EVENT, callback)
    
    correlation_id = "corr_123"
    messages = [
        create_test_message(
            content={"seq": 1},
            correlation_id=correlation_id
        ),
        create_test_message(
            content={"seq": 2},
            correlation_id=correlation_id
        )
    ]
    
    for msg in messages:
        await agent_bus.publish(msg)
    
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_message_correlation"})
    await wait_for_message_processing()
    
    assert len(received_messages) == 2
    assert all(msg.correlation_id == correlation_id for msg in received_messages)
    assert received_messages[0].content["seq"] == 1
    assert received_messages[1].content["seq"] == 2

@pytest.mark.asyncio
async def test_error_handling_in_callbacks(agent_bus, create_test_message, wait_for_message_processing):
    """Test error handling in subscriber callbacks."""
    error_logged = False
    
    async def failing_callback(message):
        raise Exception("Test error")
    
    def error_logger(error):
        nonlocal error_logged
        error_logged = True
    
    agent_bus.error_handler = error_logger
    await agent_bus.subscribe(MessageType.EVENT, failing_callback)
    
    message = create_test_message()
    await agent_bus.publish(message)
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_error_handling_in_callbacks"})
    
    await wait_for_message_processing()
    assert error_logged

@pytest.mark.asyncio
async def test_message_ordering(agent_bus, create_test_message, wait_for_message_processing):
    """Test message delivery ordering."""
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
        await asyncio.sleep(0.1)  # Simulate processing time
    
    await agent_bus.subscribe(MessageType.EVENT, callback)
    
    messages = [
        create_test_message(
            content={"seq": i},
            correlation_id=f"test_{i}"
        )
        for i in range(5)
    ]
    
    for msg in messages:
        await agent_bus.publish(msg)
    
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_message_ordering"})
    await asyncio.sleep(1)  # Allow all messages to be processed
    
    assert len(received_messages) == 5
    for i, msg in enumerate(received_messages):
        assert msg.content["seq"] == i

@pytest.mark.asyncio
async def test_bus_shutdown(agent_bus, create_test_message):
    """Test bus shutdown behavior."""
    received_messages = []
    
    async def callback(message):
        received_messages.append(message)
    
    await agent_bus.subscribe(MessageType.EVENT, callback)
    
    # Shutdown the bus
    await agent_bus.shutdown()
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_bus_shutdown"})
    
    # Try to publish after shutdown
    message = create_test_message()
    
    with pytest.raises(BusError):
        await agent_bus.publish(message)
    
    assert len(received_messages) == 0

@pytest.mark.asyncio
async def test_multiple_subscribers_same_type(agent_bus, create_test_message, wait_for_message_processing):
    """Test multiple subscribers for the same message type."""
    callbacks = [AsyncMock() for _ in range(3)]
    
    for callback in callbacks:
        await agent_bus.subscribe(MessageType.EVENT, callback)
    
    message = create_test_message()
    await agent_bus.publish(message)
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_multiple_subscribers_same_type"})
    
    await wait_for_message_processing()
    
    for callback in callbacks:
        callback.assert_called_once_with(message)

@pytest.mark.asyncio
async def test_message_validation(agent_bus, create_test_message):
    """Test message validation on publish."""
    # Test with invalid message type
    with pytest.raises(ValueError):
        await agent_bus.publish(create_test_message(msg_type="invalid_type"))
    
    # Test with missing required fields
    with pytest.raises(ValueError):
        await agent_bus.publish(create_test_message(sender=None))
    
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_message_validation"})

@pytest.mark.asyncio
async def test_subscription_cleanup(agent_bus, create_test_message, wait_for_message_processing):
    """Test cleanup of subscriptions."""
    callback = AsyncMock()
    
    # Create multiple subscriptions
    sub_ids = []
    for _ in range(3):
        sub_id = await agent_bus.subscribe(MessageType.EVENT, callback)
        sub_ids.append(sub_id)
    
    # Unsubscribe from each
    for sub_id in sub_ids:
        await agent_bus.unsubscribe(sub_id)
    
    log_event("TEST_ADDED", "TestAgentBus", {"test": "test_subscription_cleanup"})
    
    # Verify all subscriptions are removed
    assert len(agent_bus.subscribers) == 0
    
    # Publish a message to ensure no callbacks are triggered
    message = create_test_message()
    await agent_bus.publish(message)
    await wait_for_message_processing()
    
    callback.assert_not_called() 