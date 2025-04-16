import pytest
import asyncio
from core.coordination.dispatcher import EventDispatcher, EventType, Event
from core.agent_bus import AgentBus

@pytest.fixture
async def agent_bus():
    return AgentBus()

@pytest.fixture
async def dispatcher(agent_bus):
    disp = EventDispatcher(agent_bus)
    await disp.start()
    yield disp
    await disp.stop()

@pytest.mark.asyncio
async def test_register_handler(dispatcher):
    # Test registering valid handler
    called = False
    
    async def test_handler(event):
        nonlocal called
        called = True
    
    dispatcher.register_handler(EventType.CURSOR, test_handler)
    assert await dispatcher.get_handlers(EventType.CURSOR) == 1
    
    # Test registering invalid event type
    with pytest.raises(ValueError):
        dispatcher.register_handler("invalid", test_handler)

@pytest.mark.asyncio
async def test_dispatch_event(dispatcher):
    received_events = []
    
    async def test_handler(event):
        received_events.append(event)
    
    # Register handlers for different event types
    dispatcher.register_handler(EventType.CURSOR, test_handler)
    dispatcher.register_handler(EventType.CHAT, test_handler)
    
    # Dispatch events
    event1 = Event(
        type=EventType.CURSOR,
        data={"action": "move"},
        source_id="test1"
    )
    event2 = Event(
        type=EventType.CHAT,
        data={"message": "test"},
        source_id="test2"
    )
    
    await dispatcher.dispatch_event(event1)
    await dispatcher.dispatch_event(event2)
    
    # Wait for events to be processed
    await asyncio.sleep(0.1)
    
    assert len(received_events) == 2
    assert received_events[0].type == EventType.CURSOR
    assert received_events[1].type == EventType.CHAT

@pytest.mark.asyncio
async def test_event_priority(dispatcher):
    received_events = []
    
    async def test_handler(event):
        received_events.append(event)
    
    dispatcher.register_handler(EventType.SYSTEM, test_handler)
    
    # Create events with different priorities
    events = [
        Event(type=EventType.SYSTEM, data={}, source_id="test1", priority=2),
        Event(type=EventType.SYSTEM, data={}, source_id="test2", priority=1),
        Event(type=EventType.SYSTEM, data={}, source_id="test3", priority=3)
    ]
    
    # Dispatch events in random order
    for event in events:
        await dispatcher.dispatch_event(event)
    
    # Wait for events to be processed
    await asyncio.sleep(0.1)
    
    # Verify events were processed in priority order
    assert len(received_events) == 3
    assert received_events[0].source_id == "test2"  # priority 1
    assert received_events[1].source_id == "test1"  # priority 2
    assert received_events[2].source_id == "test3"  # priority 3

@pytest.mark.asyncio
async def test_queue_size(dispatcher):
    # Register a slow handler
    async def slow_handler(event):
        await asyncio.sleep(0.2)
    
    dispatcher.register_handler(EventType.CURSOR, slow_handler)
    
    # Dispatch multiple events quickly
    for i in range(5):
        event = Event(
            type=EventType.CURSOR,
            data={"index": i},
            source_id=f"test{i}"
        )
        await dispatcher.dispatch_event(event)
    
    # Check queue size
    size = await dispatcher.get_queue_size()
    assert size > 0
    
    # Wait for all events to be processed
    await asyncio.sleep(1)
    size = await dispatcher.get_queue_size()
    assert size == 0

@pytest.mark.asyncio
async def test_handler_error(dispatcher):
    error_count = 0
    
    async def error_handler(event):
        nonlocal error_count
        error_count += 1
        raise Exception("Test error")
    
    dispatcher.register_handler(EventType.SYSTEM, error_handler)
    
    # Dispatch event that will cause error
    event = Event(
        type=EventType.SYSTEM,
        data={},
        source_id="test"
    )
    await dispatcher.dispatch_event(event)
    
    # Wait for event to be processed
    await asyncio.sleep(0.1)
    
    # Verify handler was called despite error
    assert error_count == 1 