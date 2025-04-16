import os
import sys
import json
import threading
import traceback

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # core/coordination
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Core Service Imports ---
try:
    from core.memory.governance_memory_engine import log_event
except ImportError:
    print("[AgentBus Error ❌] Failed to import governance_memory_engine. Using dummy logger.")
    def log_event(event_type, source, details): print(f"[Dummy Log] Event: {event_type}, Source: {source}, Details: {details}")
# ---------------------------

_SOURCE = "AgentBus"

class AgentBus:
    """A Singleton message bus for inter-agent communication."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super(AgentBus, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initializes the AgentBus singleton instance."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self.agents = {}
            self._initialized = True
            log_event("SYSTEM_COMPONENT_INITIALIZED", _SOURCE, {"component": "AgentBus", "instance_id": id(self)})

    def register_agent(self, agent_instance):
        """Registers an agent instance with the bus."""
        if not hasattr(agent_instance, 'agent_id'):
            log_event("BUS_ERROR", _SOURCE, {"error": "Agent instance lacks 'agent_id' attribute"})
            return False
            
        agent_id = agent_instance.agent_id
        with self._lock:
            if agent_id in self.agents:
                log_event("BUS_WARNING", _SOURCE, {"warning": f"Agent ID '{agent_id}' already registered. Overwriting.", "existing_instance": str(self.agents[agent_id])})
            self.agents[agent_id] = agent_instance
            log_event("AGENT_REGISTERED", _SOURCE, {"agent_id": agent_id, "agent_class": agent_instance.__class__.__name__})
            return True

    def unregister_agent(self, agent_id: str):
        """Unregisters an agent instance from the bus."""
        with self._lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                log_event("AGENT_UNREGISTERED", _SOURCE, {"agent_id": agent_id})
                return True
            else:
                log_event("BUS_WARNING", _SOURCE, {"warning": f"Attempted to unregister non-existent agent ID: {agent_id}"})
                return False

    def get_agent(self, agent_id: str):
        """Retrieves a registered agent instance."""
        with self._lock:
            return self.agents.get(agent_id)

    def dispatch(self, target_agent_id: str, method_name: str, **kwargs):
        """Dispatches a method call to a registered agent."""
        log_context = {"target_agent": target_agent_id, "method": method_name, "params": list(kwargs.keys())}
        log_event("BUS_DISPATCH_RECEIVED", _SOURCE, log_context)
        
        agent_instance = self.get_agent(target_agent_id)
        
        if agent_instance is None:
            log_event("BUS_DISPATCH_FAILED", _SOURCE, {**log_context, "error": "Target agent not found"})
            return None # Indicate agent not found
            
        if not hasattr(agent_instance, method_name):
            log_event("BUS_DISPATCH_FAILED", _SOURCE, {**log_context, "error": "Method not found on agent", "agent_class": agent_instance.__class__.__name__})
            return None # Indicate method not found
            
        method = getattr(agent_instance, method_name)
        if not callable(method):
            log_event("BUS_DISPATCH_FAILED", _SOURCE, {**log_context, "error": "Target attribute is not callable", "agent_class": agent_instance.__class__.__name__})
            return None # Indicate not callable
            
        try:
            log_event("BUS_DISPATCH_EXECUTING", _SOURCE, log_context)
            result = method(**kwargs)
            log_event("BUS_DISPATCH_SUCCESS", _SOURCE, {**log_context, "result_type": type(result).__name__})
            return result
        except Exception as e:
            log_event("BUS_DISPATCH_ERROR", _SOURCE, {
                **log_context,
                "error": "Exception during agent method execution", 
                "exception_type": type(e).__name__,
                "details": str(e), 
                "traceback": traceback.format_exc()
            })
            return None # Indicate execution error

# --- Example Usage ---
if __name__ == "__main__":
    print("--- Testing AgentBus ---")

    # Mock Agent Class
    class MockAgent:
        def __init__(self, agent_id):
            self.agent_id = agent_id
            self.processed_messages = []
        
        def process_message(self, message: str, sender: str):
            print(f"[{self.agent_id}] Received: '{message}' from {sender}")
            result = f"Processed: {message}"
            self.processed_messages.append(result)
            return result

    # Get Bus Instance (Singleton)
    bus1 = AgentBus()
    bus2 = AgentBus()
    print(f"Bus Instance 1 ID: {id(bus1)}")
    print(f"Bus Instance 2 ID: {id(bus2)}")
    assert id(bus1) == id(bus2)
    print("Singleton test: PASSED")

    # Register Agents
    agent_a = MockAgent("AgentA")
    agent_b = MockAgent("AgentB")
    bus1.register_agent(agent_a)
    bus1.register_agent(agent_b)
    print(f"Registered agents: {list(bus1.agents.keys())}")

    # Dispatch Test 1 (A -> B)
    print("\nDispatching A -> B...")
    dispatch_result1 = bus1.dispatch(
        target_agent_id="AgentB", 
        method_name="process_message", 
        message="Hello from A", 
        sender="AgentA"
    )
    print(f"Dispatch 1 Result: {dispatch_result1}")
    assert dispatch_result1 == "Processed: Hello from A"
    assert agent_b.processed_messages == ["Processed: Hello from A"]

    # Dispatch Test 2 (B -> A)
    print("\nDispatching B -> A...")
    dispatch_result2 = bus2.dispatch( # Use second instance variable
        target_agent_id="AgentA", 
        method_name="process_message", 
        message="Reply from B", 
        sender="AgentB"
    )
    print(f"Dispatch 2 Result: {dispatch_result2}")
    assert dispatch_result2 == "Processed: Reply from B"
    assert agent_a.processed_messages == ["Processed: Reply from B"]
    
    # Dispatch Failure Test (Agent Not Found)
    print("\nDispatching to NonExistentAgent...")
    dispatch_result3 = bus1.dispatch(target_agent_id="NonExistent", method_name="do_something")
    print(f"Dispatch 3 Result: {dispatch_result3}")
    assert dispatch_result3 is None
    
    # Dispatch Failure Test (Method Not Found)
    print("\nDispatching unknown_method to AgentA...")
    dispatch_result4 = bus1.dispatch(target_agent_id="AgentA", method_name="unknown_method")
    print(f"Dispatch 4 Result: {dispatch_result4}")
    assert dispatch_result4 is None
    
    # Unregister Agent
    print("\nUnregistering AgentB...")
    unreg_result = bus1.unregister_agent("AgentB")
    print(f"Unregister successful: {unreg_result}")
    assert unreg_result is True
    assert "AgentB" not in bus1.agents
    dispatch_result5 = bus1.dispatch(target_agent_id="AgentB", method_name="process_message", message="Test")
    print(f"Dispatch to unregistered AgentB result: {dispatch_result5}")
    assert dispatch_result5 is None

    print("\n--- AgentBus Test Complete ---")
