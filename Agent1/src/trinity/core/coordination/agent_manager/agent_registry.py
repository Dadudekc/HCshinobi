from typing import Dict, List, Optional
from pydantic import BaseModel

class Agent(BaseModel):
    agent_id: str
    capabilities: List[str]
    resources: List[str]
    status: str = "active"
    last_heartbeat: float = 0.0

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Agent] = {}
    
    def register_agent(self, agent_id: str, capabilities: List[str], resources: List[str]) -> Agent:
        if agent_id in self._agents:
            raise ValueError(f"Agent {agent_id} already registered")
        
        agent = Agent(
            agent_id=agent_id,
            capabilities=capabilities,
            resources=resources
        )
        self._agents[agent_id] = agent
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)
    
    def update_agent_status(self, agent_id: str, status: str) -> None:
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found")
        self._agents[agent_id].status = status
    
    def update_agent_heartbeat(self, agent_id: str, timestamp: float) -> None:
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found")
        self._agents[agent_id].last_heartbeat = timestamp
    
    def get_all_agents(self) -> List[Agent]:
        return list(self._agents.values())
    
    def get_agents_by_capability(self, capability: str) -> List[Agent]:
        return [
            agent for agent in self._agents.values()
            if capability in agent.capabilities
        ]
    
    def remove_agent(self, agent_id: str) -> None:
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id} not found")
        del self._agents[agent_id] 