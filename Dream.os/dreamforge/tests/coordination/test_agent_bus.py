import pytest
import os
import sys
import threading

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/tests/coordination
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Module to test
from dreamforge.core.coordination.agent_bus import AgentBus

# --- Mock Agent Class --- 

class MockAgent:
    def __init__(self, agent_id):
        self.id = agent_id
        self.received_log = [] # Store (sender_id, message)

    def receive_message(self, sender_id: str, message: dict):
        print(f"  [{self.id}] Mock Received from [{sender_id}]: {message}") # For test visibility
        self.received_log.append((sender_id, message))
        # Simulate potential processing error
        if message.get("action") == "error":
            raise ValueError("Simulated processing error")

    def __str__(self):
        return f"MockAgent(id={self.id})"

# --- Test Fixtures --- 

# Fixture to provide a clean AgentBus instance for each test function
@pytest.fixture(autouse=True)
def clean_agent_bus():
    # Get the singleton instance
    bus = AgentBus()
    # Store registered agents before test
    # original_agents = bus.list_agents() # Can't easily restore instances
    # Clear agents for the test
    # Access private member for testing purposes - acknowledge risk
    bus._agents = {}
    bus._initialized = True # Ensure it thinks it's initialized if reset
    yield bus # Provide the clean bus instance to the test
    # Teardown: Clear agents again to ensure clean state for next test
    bus._agents = {}

@pytest.fixture
def agent_a():
    return MockAgent("AgentA")

@pytest.fixture
def agent_b():
    return MockAgent("AgentB")

# --- Test Cases --- 

def test_singleton_instance(clean_agent_bus):
    """Verify that multiple calls to AgentBus() return the same instance."""
    bus1 = AgentBus()
    bus2 = AgentBus()
    assert bus1 is bus2
    assert bus1 is clean_agent_bus # Check fixture returns the same instance

def test_register_agent_success(clean_agent_bus, agent_a):
    """Test successful agent registration."""
    assert clean_agent_bus.list_agents() == []
    result = clean_agent_bus.register_agent(agent_a.id, agent_a)
    assert result is True
    assert clean_agent_bus.list_agents() == ["AgentA"]
    assert clean_agent_bus.get_agent("AgentA") is agent_a

def test_register_agent_no_receive_method(clean_agent_bus):
    """Test registration fails if agent lacks receive_message."""
    agent_c = object()
    result = clean_agent_bus.register_agent("AgentC", agent_c)
    assert result is False
    assert clean_agent_bus.list_agents() == []

def test_register_agent_overwrite(clean_agent_bus, agent_a):
    """Test that registering the same ID again overwrites (logs warning)."""
    agent_a_new_instance = MockAgent("AgentA")
    clean_agent_bus.register_agent(agent_a.id, agent_a) # Initial registration
    result = clean_agent_bus.register_agent(agent_a.id, agent_a_new_instance) # Overwrite
    assert result is True
    assert clean_agent_bus.list_agents() == ["AgentA"]
    assert clean_agent_bus.get_agent("AgentA") is agent_a_new_instance # Check instance was updated

def test_unregister_agent_success(clean_agent_bus, agent_a):
    """Test successful agent unregistration."""
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    assert clean_agent_bus.list_agents() == ["AgentA"]
    result = clean_agent_bus.unregister_agent(agent_a.id)
    assert result is True
    assert clean_agent_bus.list_agents() == []
    assert clean_agent_bus.get_agent("AgentA") is None

def test_unregister_agent_not_found(clean_agent_bus):
    """Test unregistering an agent that is not registered."""
    result = clean_agent_bus.unregister_agent("AgentX")
    assert result is False
    assert clean_agent_bus.list_agents() == []

def test_send_message_success(clean_agent_bus, agent_a, agent_b):
    """Test sending a message successfully between registered agents."""
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    clean_agent_bus.register_agent(agent_b.id, agent_b)
    message = {"type": "TEST", "value": 123}
    result = clean_agent_bus.send_message(agent_a.id, agent_b.id, message)
    assert result is True
    assert len(agent_b.received_log) == 1
    assert agent_b.received_log[0] == (agent_a.id, message)
    assert len(agent_a.received_log) == 0 # Sender should not receive

def test_send_message_recipient_not_found(clean_agent_bus, agent_a):
    """Test sending a message to an unregistered recipient."""
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    message = {"type": "TEST", "value": 456}
    result = clean_agent_bus.send_message(agent_a.id, "AgentX", message)
    assert result is False
    assert len(agent_a.received_log) == 0

def test_send_message_recipient_error(clean_agent_bus, agent_a, agent_b):
    """Test sending a message where the recipient's receive_message raises an error."""
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    clean_agent_bus.register_agent(agent_b.id, agent_b)
    message = {"type": "TEST", "action": "error"} # MockAgent will raise ValueError
    result = clean_agent_bus.send_message(agent_a.id, agent_b.id, message)
    assert result is False # Delivery technically failed due to recipient error
    # Agent B still received it before erroring
    assert len(agent_b.received_log) == 1
    assert agent_b.received_log[0] == (agent_a.id, message)

def test_list_agents(clean_agent_bus, agent_a, agent_b):
    """Test listing registered agents."""
    assert clean_agent_bus.list_agents() == []
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    assert clean_agent_bus.list_agents() == ["AgentA"]
    clean_agent_bus.register_agent(agent_b.id, agent_b)
    # Order isn't guaranteed, so compare sets or sorted lists
    assert set(clean_agent_bus.list_agents()) == {"AgentA", "AgentB"}

def test_get_agent(clean_agent_bus, agent_a):
    """Test retrieving a registered agent."""
    assert clean_agent_bus.get_agent("AgentA") is None
    clean_agent_bus.register_agent(agent_a.id, agent_a)
    assert clean_agent_bus.get_agent("AgentA") is agent_a 