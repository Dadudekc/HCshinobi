from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime

class StateVersion(BaseModel):
    value: Any
    version: int
    timestamp: datetime
    agent_id: str

class StateStore:
    def __init__(self):
        self._states: Dict[str, Dict[str, StateVersion]] = {}
        self._version_counters: Dict[str, int] = {}
    
    def set_state(self, agent_id: str, key: str, value: Any) -> StateVersion:
        if key not in self._states:
            self._states[key] = {}
            self._version_counters[key] = 0
        
        version = self._version_counters[key] + 1
        self._version_counters[key] = version
        
        state_version = StateVersion(
            value=value,
            version=version,
            timestamp=datetime.now(),
            agent_id=agent_id
        )
        
        self._states[key][agent_id] = state_version
        return state_version
    
    def get_state(self, key: str, agent_id: Optional[str] = None) -> Optional[StateVersion]:
        if key not in self._states:
            return None
        
        if agent_id:
            return self._states[key].get(agent_id)
        
        # Return the latest version if no agent_id specified
        latest_version = None
        for state in self._states[key].values():
            if latest_version is None or state.version > latest_version.version:
                latest_version = state
        return latest_version
    
    def get_all_states(self, key: str) -> Dict[str, StateVersion]:
        return self._states.get(key, {})
    
    def get_state_history(self, key: str) -> List[StateVersion]:
        if key not in self._states:
            return []
        
        all_versions = []
        for state in self._states[key].values():
            all_versions.append(state)
        
        return sorted(all_versions, key=lambda x: x.version)
    
    def remove_state(self, key: str, agent_id: Optional[str] = None) -> None:
        if key not in self._states:
            return
        
        if agent_id:
            if agent_id in self._states[key]:
                del self._states[key][agent_id]
                if not self._states[key]:
                    del self._states[key]
                    del self._version_counters[key]
        else:
            del self._states[key]
            del self._version_counters[key]
    
    def get_state_keys(self) -> List[str]:
        return list(self._states.keys())
    
    def get_agent_states(self, agent_id: str) -> Dict[str, StateVersion]:
        agent_states = {}
        for key, states in self._states.items():
            if agent_id in states:
                agent_states[key] = states[agent_id]
        return agent_states 