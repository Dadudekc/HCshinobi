from typing import Dict, List, Optional
from .state_store import StateVersion
from ..agent_manager.agent_profiler import AgentProfiler

class ConflictResolver:
    def __init__(self, agent_profiler: AgentProfiler):
        self._agent_profiler = agent_profiler
    
    def resolve_conflicts(self, key: str, conflicting_states: Dict[str, StateVersion]) -> StateVersion:
        if not conflicting_states:
            raise ValueError("No conflicting states provided")
        
        # If only one state, return it
        if len(conflicting_states) == 1:
            return next(iter(conflicting_states.values()))
        
        # Score each state based on various factors
        state_scores: Dict[str, float] = {}
        for agent_id, state in conflicting_states.items():
            score = 0.0
            
            # Consider agent reliability
            reliability = self._agent_profiler.get_agent_reliability(agent_id)
            score += reliability * 0.4
            
            # Consider state version (newer is better)
            score += state.version * 0.3
            
            # Consider timestamp (more recent is better)
            # Normalize timestamp to a score between 0 and 1
            timestamps = [s.timestamp.timestamp() for s in conflicting_states.values()]
            min_ts = min(timestamps)
            max_ts = max(timestamps)
            if max_ts > min_ts:
                normalized_ts = (state.timestamp.timestamp() - min_ts) / (max_ts - min_ts)
                score += normalized_ts * 0.3
            
            state_scores[agent_id] = score
        
        # Return state with highest score
        best_agent = max(state_scores.items(), key=lambda x: x[1])[0]
        return conflicting_states[best_agent]
    
    def detect_conflicts(self, states: Dict[str, StateVersion]) -> Dict[str, Dict[str, StateVersion]]:
        conflicts = {}
        
        # Group states by key
        states_by_key: Dict[str, Dict[str, StateVersion]] = {}
        for agent_id, state in states.items():
            if state.value not in states_by_key:
                states_by_key[state.value] = {}
            states_by_key[state.value][agent_id] = state
        
        # Find conflicts (multiple states for the same key)
        for key, key_states in states_by_key.items():
            if len(key_states) > 1:
                conflicts[key] = key_states
        
        return conflicts
    
    def merge_states(self, states: List[StateVersion]) -> StateVersion:
        if not states:
            raise ValueError("No states to merge")
        
        # Simple merge strategy: take the most recent state
        return max(states, key=lambda x: x.timestamp)
    
    def validate_state(self, state: StateVersion) -> bool:
        # Basic validation
        if not state.agent_id or not state.value:
            return False
        
        # Check if agent exists and is active
        # This would require access to the agent registry
        # For now, we'll assume the state is valid
        return True 