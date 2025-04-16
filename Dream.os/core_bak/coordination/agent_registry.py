"""Manages agent registration, status, and querying within the Agent Bus."""

import asyncio
from typing import Dict, List, Optional, Set, Callable, Any

from .bus_types import AgentStatus

class AgentRegistry:
    """Handles the lifecycle and state management of registered agents."""

    def __init__(self, dispatch_event_callback: Callable):
        self.agents: Dict[str, Dict] = {}
        self.active_agents: Set[str] = set()
        self.shutdown_ready: Set[str] = set()
        self._lock = asyncio.Lock()
        self._dispatch_event = dispatch_event_callback # Callback to dispatch events

    async def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """Register a new agent with its capabilities."""
        async with self._lock:
            if agent_id in self.agents:
                raise ValueError(f"Agent {agent_id} is already registered")
            
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "status": AgentStatus.IDLE,
                "capabilities": capabilities,
                "current_task": None,
                "error_message": None
            }
            self.active_agents.add(agent_id)
            
            # Dispatch registration event
            await self._dispatch_event(
                "agent_registered",
                {"agent_id": agent_id, "capabilities": capabilities}
            )

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
            
            del self.agents[agent_id]
            self.active_agents.discard(agent_id)
            self.shutdown_ready.discard(agent_id)
            
            # Dispatch unregistration event
            await self._dispatch_event(
                "agent_unregistered",
                {"agent_id": agent_id}
            )

    async def update_agent_status(self, agent_id: str, status: AgentStatus, 
                                task: Optional[str] = None, 
                                error: Optional[str] = None) -> None:
        """Update an agent's status."""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
                
            agent = self.agents[agent_id]
            agent["status"] = status
            agent["current_task"] = task
            agent["error_message"] = error
            
            if status == AgentStatus.SHUTDOWN_READY:
                self.shutdown_ready.add(agent_id)
            
            # Dispatch status change event
            await self._dispatch_event(
                "status_change",
                {
                    "agent_id": agent_id,
                    "status": status.value, # Ensure Enum value is sent
                    "task": task,
                    "error": error
                }
            )

    async def get_available_agents(self, required_capabilities: List[str]) -> List[str]:
        """Get list of idle agents that have all required capabilities."""
        async with self._lock:
            available = []
            for agent_id, info in self.agents.items():
                if (info["status"] == AgentStatus.IDLE and
                    all(cap in info["capabilities"] for cap in required_capabilities)):
                    available.append(agent_id)
            return available

    async def get_agent_info(self, agent_id: str) -> Dict:
        """Get information about a specific agent."""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
            # Return a copy to prevent external modification
            info = self.agents[agent_id].copy()
            info["status"] = info["status"].value # Ensure Enum value is returned
            return info

    async def get_all_agents(self) -> Dict[str, Dict]:
        """Get information about all registered agents."""
        async with self._lock:
            # Return a deep copy with status values
            all_info = {}
            for agent_id, info in self.agents.items():
                agent_copy = info.copy()
                agent_copy["status"] = agent_copy["status"].value
                all_info[agent_id] = agent_copy
            return all_info

    async def get_active_agents_set(self) -> Set[str]:
        """Get the set of currently active agent IDs."""
        async with self._lock:
            return self.active_agents.copy()

    async def get_shutdown_ready_set(self) -> Set[str]:
        """Get the set of agent IDs ready for shutdown."""
        async with self._lock:
            return self.shutdown_ready.copy() 