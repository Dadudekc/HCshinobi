import os
import sys
import threading

# Add project root for imports if necessary
script_dir = os.path.dirname(__file__) # dreamforge/core/coordination
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components
try:
    from dreamforge.core.governance_memory_engine import log_event # UPDATED IMPORT PATH
except ImportError as e:
    print(f"[AgentBus] Warning: Failed to import log_event: {e}. Using fallback.")
    # --- Fallback --- 
    def log_event(event_type, agent_source, details): 
        print(f"[DummyLogger-AgentBus] {event_type} | {agent_source} | {details}")
    # --- End Fallback ---

_SOURCE_ID = "AgentBus"

class AgentBus:
    """
    A Singleton class responsible for routing messages between registered agents.
    Ensures that only one instance of the bus exists.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        # Singleton pattern: Ensure only one instance is created
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Initialize only once
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initializes the AgentBus (only if not already initialized)."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._agents = {}
            self._initialized = True
            log_event("BUS_INITIALIZED", _SOURCE_ID, {"message": "AgentBus Singleton instance created."})            

    def register_agent(self, agent_id: str, agent_instance):
        """
        Registers an agent instance with the bus.

        Args:
            agent_id: The unique identifier for the agent.
            agent_instance: The instance of the agent class.
        """
        with self._lock:
            if agent_id in self._agents:
                log_event("BUS_WARNING", _SOURCE_ID, {"warning": f"Agent already registered: {agent_id}. Overwriting registration.", "existing_instance": str(self._agents[agent_id])})
            # Check if agent instance has the required receive_message method
            if not hasattr(agent_instance, 'receive_message') or not callable(getattr(agent_instance, 'receive_message')):
                 log_event("BUS_ERROR", _SOURCE_ID, {"error": f"Agent {agent_id} missing callable 'receive_message' method. Registration failed.", "instance_type": type(agent_instance).__name__})
                 return False
            self._agents[agent_id] = agent_instance
            log_event("AGENT_REGISTERED", _SOURCE_ID, {"agent_id": agent_id, "instance_type": type(agent_instance).__name__})
            return True

    def unregister_agent(self, agent_id: str):
        """
        Unregisters an agent from the bus.

        Args:
            agent_id: The ID of the agent to unregister.
        """
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                log_event("AGENT_UNREGISTERED", _SOURCE_ID, {"agent_id": agent_id})
                return True
            else:
                log_event("BUS_WARNING", _SOURCE_ID, {"warning": f"Attempted to unregister non-existent agent: {agent_id}"})
                return False

    def send_message(self, sender_id: str, recipient_id: str, message: dict) -> bool:
        """
        Sends a message from one agent to another registered agent.

        Args:
            sender_id: The ID of the sending agent.
            recipient_id: The ID of the recipient agent.
            message: The message payload (dictionary).

        Returns:
            True if the message was successfully delivered (i.e., recipient found and method called),
            False otherwise.
        """
        log_event("MESSAGE_SENT", _SOURCE_ID, {"sender": sender_id, "recipient": recipient_id, "message_snippet": str(message)[:100]})
        recipient_instance = None
        with self._lock:
            recipient_instance = self._agents.get(recipient_id)

        if recipient_instance:
            try:
                # Assume agent has a method like receive_message(sender_id, message)
                recipient_instance.receive_message(sender_id, message)
                log_event("MESSAGE_DELIVERED", _SOURCE_ID, {"sender": sender_id, "recipient": recipient_id})
                return True
            except Exception as e:
                log_event("BUS_ERROR", _SOURCE_ID, {
                    "error": f"Error delivering message to agent: {recipient_id}",
                    "recipient_instance": str(recipient_instance),
                    "details": str(e)
                })
                return False
        else:
            log_event("BUS_WARNING", _SOURCE_ID, {"warning": f"Recipient agent not found: {recipient_id}", "sender": sender_id})
            return False

    def get_agent(self, agent_id: str):
        """Retrieves a registered agent instance."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list:
        """Returns a list of registered agent IDs."""
        with self._lock:
            return list(self._agents.keys())

# Example Usage
if __name__ == '__main__':
    print("[AgentBus] Running example...")

    # Dummy Agent Class for testing
    class MockAgent:
        def __init__(self, agent_id):
            self.id = agent_id
            self.received_messages = []
        
        def receive_message(self, sender_id, message):
            print(f"  [{self.id}] Received message from [{sender_id}]: {message}")
            self.received_messages.append((sender_id, message))
        
        def __str__(self):
            return f"MockAgent(id={self.id})"

    # Get AgentBus instance (Singleton)
    bus1 = AgentBus()
    bus2 = AgentBus() # Should be the same instance

    print(f"Bus Instance 1 ID: {id(bus1)}")
    print(f"Bus Instance 2 ID: {id(bus2)}")
    print(f"Instances are the same: {bus1 is bus2}")

    # Create Mock Agents
    agent_a = MockAgent("AgentA")
    agent_b = MockAgent("AgentB")
    agent_c_no_receive = object() # Agent without receive_message

    # Register Agents
    print("\nRegistering Agents...")
    bus1.register_agent(agent_a.id, agent_a)
    bus1.register_agent(agent_b.id, agent_b)
    bus1.register_agent("AgentC", agent_c_no_receive) # Should fail
    bus1.register_agent(agent_a.id, agent_a) # Test re-registration warning

    print(f"\nRegistered Agents: {bus1.list_agents()}")

    # Send Messages
    print("\nSending Messages...")
    success1 = bus1.send_message("AgentA", "AgentB", {"type": "GREETING", "text": "Hello Agent B!"})
    success2 = bus1.send_message("AgentB", "AgentA", {"type": "REPLY", "text": "Hi Agent A!"})
    success3 = bus1.send_message("AgentA", "AgentX", {"type": "ERROR", "text": "Nobody here..."}) # Non-existent recipient
    success4 = bus1.send_message("AgentA", "AgentC", {"type": "ERROR", "text": "Should not be delivered"}) # AgentC failed registration

    print(f"\nDelivery Success: A->B: {success1}, B->A: {success2}, A->X: {success3}, A->C: {success4}")

    # Verify received messages
    print(f"\nAgent A Received: {agent_a.received_messages}")
    print(f"Agent B Received: {agent_b.received_messages}")

    # Unregister Agent
    print("\nUnregistering Agent A...")
    bus1.unregister_agent("AgentA")
    print(f"Registered Agents: {bus1.list_agents()}")
    success5 = bus1.send_message("AgentB", "AgentA", {"type": "FAREWELL", "text": "Bye Agent A!"})
    print(f"Delivery Success B->A (after unregister): {success5}")

    print("\n[AgentBus] Example finished.") 