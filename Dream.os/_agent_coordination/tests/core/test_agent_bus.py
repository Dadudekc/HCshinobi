import pytest
import asyncio
from core.agent_bus import AgentBus, AgentStatus
from core.coordination.dispatcher import EventType, Event
import json
import shutil
from pathlib import Path

@pytest.fixture
async def agent_bus():
    bus = AgentBus()
    yield bus
    await bus._dispatcher.stop()

@pytest.mark.asyncio
async def test_register_agent(agent_bus):
    # Track events
    events = []
    async def event_handler(event):
        events.append(event)
    agent_bus.register_handler(EventType.SYSTEM, event_handler)
    
    # Register agent
    await agent_bus.register_agent("agent1", ["capability1"])
    
    # Verify registration
    info = await agent_bus.get_agent_info("agent1")
    assert info["agent_id"] == "agent1"
    assert info["status"] == AgentStatus.IDLE
    assert info["capabilities"] == ["capability1"]
    assert "agent1" in agent_bus.active_agents
    
    # Verify event was dispatched
    await asyncio.sleep(0.1)  # Allow event processing
    assert len(events) == 1
    assert events[0].data["type"] == "agent_registered"
    assert events[0].data["agent_id"] == "agent1"
    
    # Test duplicate registration
    with pytest.raises(ValueError):
        await agent_bus.register_agent("agent1", ["capability2"])

@pytest.mark.asyncio
async def test_unregister_agent(agent_bus):
    # Track events
    events = []
    async def event_handler(event):
        events.append(event)
    agent_bus.register_handler(EventType.SYSTEM, event_handler)
    
    # Register and then unregister
    await agent_bus.register_agent("agent1", ["capability1"])
    await agent_bus.unregister_agent("agent1")
    
    # Verify agent is gone
    with pytest.raises(ValueError):
        await agent_bus.get_agent_info("agent1")
    assert "agent1" not in agent_bus.active_agents
    
    # Verify events were dispatched
    await asyncio.sleep(0.1)  # Allow event processing
    assert len(events) == 2
    assert events[0].data["type"] == "agent_registered"
    assert events[1].data["type"] == "agent_unregistered"
    assert events[1].data["agent_id"] == "agent1"
    
    # Test unregistering non-existent agent
    with pytest.raises(ValueError):
        await agent_bus.unregister_agent("agent2")

@pytest.mark.asyncio
async def test_update_agent_status(agent_bus):
    # Track events
    events = []
    async def event_handler(event):
        events.append(event)
    agent_bus.register_handler(EventType.SYSTEM, event_handler)
    
    # Register agent
    await agent_bus.register_agent("agent1", ["capability1"])
    
    # Update status
    await agent_bus.update_agent_status(
        "agent1", 
        AgentStatus.BUSY,
        task="test_task",
        error=None
    )
    
    # Verify status update
    info = await agent_bus.get_agent_info("agent1")
    assert info["status"] == AgentStatus.BUSY
    assert info["current_task"] == "test_task"
    assert info["error_message"] is None
    
    # Verify events were dispatched
    await asyncio.sleep(0.1)  # Allow event processing
    assert len(events) == 2  # registration + status update
    assert events[1].data["type"] == "status_change"
    assert events[1].data["status"] == AgentStatus.BUSY
    
    # Test shutdown ready status
    await agent_bus.update_agent_status("agent1", AgentStatus.SHUTDOWN_READY)
    assert "agent1" in agent_bus.shutdown_ready

@pytest.mark.asyncio
async def test_get_available_agents(agent_bus):
    # Register agents with different capabilities
    await agent_bus.register_agent("agent1", ["cap1", "cap2"])
    await agent_bus.register_agent("agent2", ["cap1"])
    await agent_bus.register_agent("agent3", ["cap2", "cap3"])
    
    # Test finding agents with specific capabilities
    available = await agent_bus.get_available_agents(["cap1"])
    assert set(available) == {"agent1", "agent2"}
    
    # Make agent busy
    await agent_bus.update_agent_status("agent1", AgentStatus.BUSY)
    available = await agent_bus.get_available_agents(["cap1"])
    assert available == ["agent2"]

@pytest.mark.asyncio
async def test_shutdown_sequence(agent_bus):
    # Track events
    events = []
    async def event_handler(event):
        events.append(event)
    agent_bus.register_handler(EventType.SYSTEM, event_handler)
    
    # Register agents
    await agent_bus.register_agent("agent1", ["capability1"])
    await agent_bus.register_agent("agent2", ["capability2"])
    
    # Start shutdown
    shutdown_task = asyncio.create_task(agent_bus.broadcast_shutdown())
    
    # Simulate agents responding to shutdown
    await agent_bus.update_agent_status("agent1", AgentStatus.SHUTDOWN_READY)
    await agent_bus.update_agent_status("agent2", AgentStatus.SHUTDOWN_READY)
    
    # Wait for shutdown to complete
    try:
        await asyncio.wait_for(shutdown_task, timeout=1.0)
    except asyncio.TimeoutError:
        pytest.fail("Shutdown sequence timed out")
    
    # Verify shutdown state
    assert agent_bus.shutdown_in_progress
    assert len(agent_bus.shutdown_ready) == 2
    
    # Verify shutdown events
    await asyncio.sleep(0.1)  # Allow event processing
    shutdown_events = [e for e in events if e.data["type"].startswith("shutdown_")]
    assert len(shutdown_events) >= 3  # initiated, phase events, completed
    assert shutdown_events[0].data["type"] == "shutdown_initiated"
    assert shutdown_events[-1].data["type"] == "shutdown_completed"

@pytest.mark.asyncio
async def test_pre_shutdown_diagnostics(agent_bus):
    # Track events
    events = []
    async def event_handler(event):
        events.append(event)
    agent_bus.register_handler(EventType.SYSTEM, event_handler)
    
    # Register agents in various states
    await agent_bus.register_agent("agent1", ["capability1"])  # Healthy agent
    await agent_bus.register_agent("agent2", ["capability2"])  # Will be error state
    await agent_bus.register_agent("agent3", ["capability3"])  # Will be shutdown ready
    
    # Set up different agent states
    await agent_bus.update_agent_status("agent2", AgentStatus.ERROR, error="Test error")
    await agent_bus.update_agent_status("agent3", AgentStatus.SHUTDOWN_READY)
    
    # Create required directories
    for dir_name in ["memory", "logs", "config", "temp"]:
        path = Path(dir_name)
        path.mkdir(parents=True, exist_ok=True)
    
    # Create agent state files
    memory_path = Path("memory/agents")
    memory_path.mkdir(parents=True, exist_ok=True)
    
    for agent_id in ["agent1", "agent3"]:
        agent_dir = memory_path / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        
        # Create valid mailbox.json
        mailbox = {
            "agent_id": agent_id,
            "status": "idle",
            "pending_operations": []
        }
        (agent_dir / "mailbox.json").write_text(json.dumps(mailbox))
        
        # Create valid task_list.json
        tasks = [{
            "task_id": "task1",
            "status": "completed",
            "priority": 1
        }]
        (agent_dir / "task_list.json").write_text(json.dumps(tasks))
    
    # Run diagnostics
    diagnostics = await agent_bus.run_pre_shutdown_diagnostics()
    
    # Verify diagnostics structure
    assert "timestamp" in diagnostics
    assert "checks" in diagnostics
    assert "total_passed" in diagnostics
    assert "total_failed" in diagnostics
    assert "critical_warnings" in diagnostics
    
    # Verify agent status check
    agent_check = diagnostics["checks"]["agent_status"]
    assert not agent_check["passed"]  # Should fail due to agent2 in error state
    assert agent_check["critical"]  # Critical because active agent has error
    assert any("agent2" in err for err in agent_check["errors"])
    
    # Verify state files check
    state_check = diagnostics["checks"]["state_files"]
    assert state_check["passed"]  # All required directories exist
    
    # Verify resource check
    resource_check = diagnostics["checks"]["resources"]
    assert resource_check["passed"]  # No open files or processes
    
    # Verify event system check
    event_check = diagnostics["checks"]["event_system"]
    assert event_check["passed"]  # Event system is running
    
    # Verify event was dispatched
    await asyncio.sleep(0.1)  # Allow event processing
    diagnostic_events = [e for e in events if e.data["type"] == "pre_shutdown_check"]
    assert len(diagnostic_events) == 1
    assert diagnostic_events[0].data["status"] == "errors_detected"
    
    # Clean up test directories
    for dir_name in ["memory", "logs", "config", "temp"]:
        path = Path(dir_name)
        if path.exists():
            shutil.rmtree(path)

@pytest.mark.asyncio
async def test_shutdown_with_failed_diagnostics(agent_bus):
    # Register an agent in error state
    await agent_bus.register_agent("agent1", ["capability1"])
    await agent_bus.update_agent_status("agent1", AgentStatus.ERROR, error="Critical error")
    
    # Attempt shutdown
    with pytest.raises(RuntimeError, match="Critical pre-shutdown checks failed"):
        await agent_bus.broadcast_shutdown()
    
    # Verify shutdown was not initiated
    assert not agent_bus.shutdown_in_progress 