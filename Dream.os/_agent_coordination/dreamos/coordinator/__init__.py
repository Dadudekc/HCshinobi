"""Dream.OS Agent Coordination System."""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

class AgentDomain(str, Enum):
    """Domains of responsibility for agents."""
    TASK_ORCHESTRATOR = "task_orchestrator"
    PROMPT_PLANNER = "prompt_planner"
    CURSOR_EXECUTOR = "cursor_executor"
    FEEDBACK_VERIFIER = "feedback_verifier"

class AgentState(str, Enum):
    """Possible states for an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    WAITING = "waiting"
    BLOCKED = "blocked"

@dataclass
class AgentContext:
    """Context information for agent operations."""
    domain: AgentDomain
    agent_id: str
    state: AgentState
    current_task: Optional[str]
    memory: Dict[str, any]
    last_update: datetime
    dependencies: List[str]

@dataclass
class AgentMessage:
    """Message passed between agents."""
    source: str
    target: str
    message_type: str
    content: Dict[str, any]
    timestamp: datetime
    priority: int = 1
    requires_response: bool = False
    correlation_id: Optional[str] = None

@dataclass
class CoordinationEvent:
    """Event representing a coordination action."""
    event_type: str
    source_domain: AgentDomain
    target_domain: AgentDomain
    context: Dict[str, any]
    timestamp: datetime
    status: str = "pending"
    result: Optional[Dict] = None

class CoordinationStatus:
    """Status tracking for coordination activities."""
    def __init__(self):
        self.active_agents: Dict[str, AgentContext] = {}
        self.pending_messages: List[AgentMessage] = []
        self.active_events: List[CoordinationEvent] = []
        self.domain_states: Dict[AgentDomain, AgentState] = {
            domain: AgentState.IDLE for domain in AgentDomain
        }
        self.last_sync: datetime = datetime.utcnow()

    def update_agent(self, agent_id: str, context: AgentContext) -> None:
        """Update agent context."""
        self.active_agents[agent_id] = context
        
    def get_domain_agents(self, domain: AgentDomain) -> List[AgentContext]:
        """Get all agents in a domain."""
        return [
            agent for agent in self.active_agents.values()
            if agent.domain == domain
        ]
        
    def add_message(self, message: AgentMessage) -> None:
        """Queue a new message."""
        self.pending_messages.append(message)
        
    def add_event(self, event: CoordinationEvent) -> None:
        """Track a new coordination event."""
        self.active_events.append(event)
        
    def update_domain_state(self, domain: AgentDomain, state: AgentState) -> None:
        """Update state of an entire domain."""
        self.domain_states[domain] = state

    def assign_task_to_agent(self, domain: AgentDomain, task_id: str) -> Optional[AgentContext]:
        """Assign a task to the first available agent in the domain."""
        idle_agents = [
            agent for agent in self.get_domain_agents(domain)
            if agent.state == AgentState.IDLE
        ]
        if idle_agents:
            agent = idle_agents[0]
            agent.state = AgentState.BUSY
            agent.current_task = task_id
            agent.last_update = datetime.utcnow()
            self.update_agent(agent.agent_id, agent)
            return agent
        return None

    def resolve_message(self, correlation_id: str, response: Dict[str, any]) -> bool:
        """Mark a message as responded and store the result if needed."""
        for i, msg in enumerate(self.pending_messages):
            if msg.correlation_id == correlation_id:
                del self.pending_messages[i]
                # Optionally store response in memory/log
                # logger.info(f"Message {correlation_id} resolved with response: {response}")
                return True
        return False

    def tick(self):
        """Perform a coordination tick—scan, check health, process timeouts."""
        now = datetime.utcnow()
        for agent in self.active_agents.values():
            if agent.state in [AgentState.BUSY, AgentState.WAITING]:
                # If agent hasn't updated in X seconds, mark as BLOCKED (e.g., 60s)
                if (now - agent.last_update).total_seconds() > 60:
                    agent.state = AgentState.BLOCKED
                    self.update_agent(agent.agent_id, agent)
                    # TODO: Potentially trigger a recovery event or message

        self.last_sync = now

    def to_dict(self) -> Dict[str, any]:
        """Serialize the coordination state to a dictionary."""
        # Ensure datetime objects are serializable (ISO format)
        def serialize_agent(agent: AgentContext) -> Dict:
            d = vars(agent)
            d["last_update"] = d["last_update"].isoformat() if d["last_update"] else None
            d["domain"] = d["domain"].value # Enum to string
            d["state"] = d["state"].value # Enum to string
            return d
            
        def serialize_message(msg: AgentMessage) -> Dict:
            d = vars(msg)
            d["timestamp"] = d["timestamp"].isoformat() if d["timestamp"] else None
            return d
            
        def serialize_event(event: CoordinationEvent) -> Dict:
            d = vars(event)
            d["timestamp"] = d["timestamp"].isoformat() if d["timestamp"] else None
            d["source_domain"] = d["source_domain"].value # Enum to string
            d["target_domain"] = d["target_domain"].value # Enum to string
            return d
            
        return {
            "active_agents": {k: serialize_agent(v) for k, v in self.active_agents.items()},
            "pending_messages": [serialize_message(m) for m in self.pending_messages],
            "active_events": [serialize_event(e) for e in self.active_events],
            "domain_states": {k.value: v.value for k, v in self.domain_states.items()},
            "last_sync": self.last_sync.isoformat() if self.last_sync else None
        }

    # Optional persistence methods (can be added later if needed)
    # def persist_to_file(self, path: str) -> None:
    #     with open(path, 'w') as f:
    #         json.dump(self.to_dict(), f, indent=2)

    # @classmethod
    # def load_from_file(cls, path: str) -> 'CoordinationStatus':
    #     with open(path, 'r') as f:
    #         data = json.load(f)
    #     # TODO: Reconstruct CoordinationStatus from data (handle enums, datetimes)
    #     instance = cls()
    #     # ... reconstruction logic ...
    #     return instance

    # Optional helper method (can be added later if needed)
    # def register_agent(self, agent_id: str, domain: AgentDomain, initial_state: AgentState = AgentState.IDLE) -> None:
    #     if agent_id not in self.active_agents:
    #         context = AgentContext(
    #             domain=domain,
    #             agent_id=agent_id,
    #             state=initial_state,
    #             current_task=None,
    #             memory={},
    #             last_update=datetime.utcnow(),
    #             dependencies=[]
    #         )
    #         self.update_agent(agent_id, context) 