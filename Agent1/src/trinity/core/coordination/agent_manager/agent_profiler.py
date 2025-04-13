from typing import Dict, List, Optional
from pydantic import BaseModel

class AgentProfile(BaseModel):
    agent_id: str
    performance_metrics: Dict[str, float]
    reliability_score: float
    specialization_areas: List[str]
    historical_tasks: List[str]

class AgentProfiler:
    def __init__(self):
        self._profiles: Dict[str, AgentProfile] = {}
    
    def create_profile(self, agent_id: str) -> AgentProfile:
        if agent_id in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} already exists")
        
        profile = AgentProfile(
            agent_id=agent_id,
            performance_metrics={},
            reliability_score=1.0,
            specialization_areas=[],
            historical_tasks=[]
        )
        self._profiles[agent_id] = profile
        return profile
    
    def update_performance_metrics(self, agent_id: str, metrics: Dict[str, float]) -> None:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        self._profiles[agent_id].performance_metrics.update(metrics)
    
    def update_reliability_score(self, agent_id: str, score: float) -> None:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        self._profiles[agent_id].reliability_score = score
    
    def add_specialization(self, agent_id: str, specialization: str) -> None:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        if specialization not in self._profiles[agent_id].specialization_areas:
            self._profiles[agent_id].specialization_areas.append(specialization)
    
    def record_task_completion(self, agent_id: str, task_id: str) -> None:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        self._profiles[agent_id].historical_tasks.append(task_id)
    
    def get_profile(self, agent_id: str) -> Optional[AgentProfile]:
        return self._profiles.get(agent_id)
    
    def get_agent_specializations(self, agent_id: str) -> List[str]:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        return self._profiles[agent_id].specialization_areas
    
    def get_agent_reliability(self, agent_id: str) -> float:
        if agent_id not in self._profiles:
            raise ValueError(f"Profile for agent {agent_id} not found")
        return self._profiles[agent_id].reliability_score 