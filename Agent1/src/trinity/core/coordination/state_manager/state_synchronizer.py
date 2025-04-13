from typing import Dict, List, Optional
from .state_store import StateStore, StateVersion
from ..agent_manager.agent_registry import AgentRegistry

class StateSynchronizer:
    def __init__(self, state_store: StateStore, agent_registry: AgentRegistry):
        self._state_store = state_store
        self._agent_registry = agent_registry
    
    def synchronize_state(self, agent_id: str, key: str, value: Any) -> StateVersion:
        # Get current state
        current_state = self._state_store.get_state(key)
        
        # Create new state version
        new_state = self._state_store.set_state(agent_id, key, value)
        
        # Notify other agents of state change
        self._notify_state_change(key, new_state)
        
        return new_state
    
    def get_latest_state(self, key: str) -> Optional[StateVersion]:
        return self._state_store.get_state(key)
    
    def get_state_diff(self, agent_id: str, key: str) -> Optional[StateVersion]:
        agent_state = self._state_store.get_state(key, agent_id)
        latest_state = self._state_store.get_state(key)
        
        if not latest_state:
            return None
        
        if not agent_state or agent_state.version < latest_state.version:
            return latest_state
        
        return None
    
    def get_pending_updates(self, agent_id: str) -> Dict[str, StateVersion]:
        pending_updates = {}
        for key in self._state_store.get_state_keys():
            diff = self.get_state_diff(agent_id, key)
            if diff:
                pending_updates[key] = diff
        return pending_updates
    
    def _notify_state_change(self, key: str, new_state: StateVersion) -> None:
        # In a real implementation, this would notify other agents
        # through a message queue or similar mechanism
        pass
    
    def resolve_conflicts(self, key: str, conflicting_states: Dict[str, StateVersion]) -> StateVersion:
        # Get the most recent state
        latest_state = max(conflicting_states.values(), key=lambda x: x.timestamp)
        return latest_state
    
    def get_state_history(self, key: str) -> List[StateVersion]:
        return self._state_store.get_state_history(key)
    
    def get_agent_states(self, agent_id: str) -> Dict[str, StateVersion]:
        return self._state_store.get_agent_states(agent_id) 