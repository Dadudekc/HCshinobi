# Tests for AgentBus

import sys
import os
import pytest
import threading

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.coordination.agent_bus import AgentBus

# --- Mock Agents for Testing ---
class MockAgent:
    def __init__(self, agent_id="mock_agent"):
        self.agent_id = agent_id
        self.last_call_args = None
        self.last_call_kwargs = None
        self.call_count = 0

    def simple_method(self, *args, **kwargs):
        self.call_count += 1
        self.last_call_args = args
        self.last_call_kwargs = kwargs
        print(f"[{self.agent_id}] simple_method called with args: {args}, kwargs: {kwargs}")
        return f"Result from {self.agent_id}"

    def method_that_raises(self):
        raise ValueError("This method intentionally fails.")

    def _not_callable_attribute(self):
        return "I am not callable in the traditional sense for dispatch"

# --- Pytest Fixture ---
@pytest.fixture(scope="function")
def clean_bus():
    """Provides a clean AgentBus instance for each test function."""
    # Reset the singleton instance before each test
    AgentBus._instance = None
    bus = AgentBus()
    # Clear any agents registered by previous tests (important!)
    bus.agents = {}
    yield bus
    # Optional cleanup after test if needed
    AgentBus._instance = None
    bus.agents = {}


# --- Test Cases ---

def test_singleton_pattern(clean_bus):
    """Verify that AgentBus follows the Singleton pattern."""
    bus1 = AgentBus()
    bus2 = AgentBus()
    assert bus1 is bus2
    assert bus1 is clean_bus # Ensure fixture provides the singleton

def test_singleton_thread_safety():
    """Verify Singleton creation is thread-safe."""
    instances = []
    AgentBus._instance = None # Ensure clean state before threaded test

    def get_instance():
        instances.append(AgentBus())

    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(instances) == 10
    first_instance = instances[0]
    for instance in instances[1:]:
        assert instance is first_instance
    AgentBus._instance = None # Clean up after test

def test_register_agent_success(clean_bus):
    """Test successful agent registration."""
    agent = MockAgent("agent1")
    result = clean_bus.register_agent(agent)
    assert result is True
    assert "agent1" in clean_bus.agents
    assert clean_bus.agents["agent1"] is agent

def test_register_agent_overwrite(clean_bus):
    """Test overwriting an existing agent registration."""
    agent1 = MockAgent("agent1")
    agent2 = MockAgent("agent1") # Same ID
    clean_bus.register_agent(agent1)
    result = clean_bus.register_agent(agent2) # Should overwrite
    assert result is True
    assert "agent1" in clean_bus.agents
    assert clean_bus.agents["agent1"] is agent2 # Should be the new agent

def test_register_agent_no_id(clean_bus):
    """Test registering an object without an agent_id attribute."""
    class NoIdAgent:
        pass
    agent = NoIdAgent()
    result = clean_bus.register_agent(agent)
    assert result is False
    assert len(clean_bus.agents) == 0

def test_unregister_agent_success(clean_bus):
    """Test successful agent unregistration."""
    agent = MockAgent("agent1")
    clean_bus.register_agent(agent)
    assert "agent1" in clean_bus.agents
    result = clean_bus.unregister_agent("agent1")
    assert result is True
    assert "agent1" not in clean_bus.agents

def test_unregister_agent_non_existent(clean_bus):
    """Test unregistering an agent that is not registered."""
    result = clean_bus.unregister_agent("non_existent_agent")
    assert result is False

def test_dispatch_success(clean_bus):
    """Test successful method dispatch with args and kwargs."""
    agent = MockAgent("agent1")
    clean_bus.register_agent(agent)
    result = clean_bus.dispatch("agent1", "simple_method", "arg1", kwarg1="value1")
    assert result == "Result from agent1"
    assert agent.call_count == 1
    assert agent.last_call_args == ("arg1",)
    assert agent.last_call_kwargs == {"kwarg1": "value1"}

def test_dispatch_no_params(clean_bus):
    """Test dispatching a method with no parameters."""
    agent = MockAgent("agent1")
    clean_bus.register_agent(agent)
    # Reuse simple_method which accepts *args, **kwargs
    result = clean_bus.dispatch("agent1", "simple_method")
    assert result == "Result from agent1"
    assert agent.call_count == 1
    assert agent.last_call_args == ()
    assert agent.last_call_kwargs == {}

def test_dispatch_target_agent_not_found(clean_bus):
    """Test dispatching to an unregistered agent ID."""
    result = clean_bus.dispatch("non_existent_agent", "simple_method")
    assert result is None

def test_dispatch_method_not_found(clean_bus):
    """Test dispatching a method that does not exist on the agent."""
    agent = MockAgent("agent1")
    clean_bus.register_agent(agent)
    result = clean_bus.dispatch("agent1", "non_existent_method")
    assert result is None
    assert agent.call_count == 0

def test_dispatch_attribute_not_callable(clean_bus):
    """Test dispatching to an attribute that is not a method."""
    agent = MockAgent("agent1")
    # Monkey patch a non-callable attribute for testing this specific case
    agent.not_a_method = "some string"
    clean_bus.register_agent(agent)
    result = clean_bus.dispatch("agent1", "not_a_method")
    assert result is None
    assert agent.call_count == 0 # Ensure original method wasn't called
    # Test with the explicitly non-callable method defined
    result2 = clean_bus.dispatch("agent1", "_not_callable_attribute")
    assert result2 is None


def test_dispatch_method_raises_exception(clean_bus):
    """Test dispatching a method that raises an exception."""
    agent = MockAgent("agent1")
    clean_bus.register_agent(agent)
    result = clean_bus.dispatch("agent1", "method_that_raises")
    assert result is None # Dispatch should catch exception and return None
    assert agent.call_count == 0 # simple_method should not have been called 