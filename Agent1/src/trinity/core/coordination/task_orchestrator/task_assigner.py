from typing import Dict, List, Optional
from .task_queue import Task, TaskStatus
from ..agent_manager.agent_registry import AgentRegistry
from ..agent_manager.agent_profiler import AgentProfiler

class TaskAssigner:
    def __init__(self, agent_registry: AgentRegistry, agent_profiler: AgentProfiler):
        self._agent_registry = agent_registry
        self._agent_profiler = agent_profiler
    
    def find_suitable_agent(self, task: Task) -> Optional[str]:
        # Get all active agents
        active_agents = [
            agent for agent in self._agent_registry.get_all_agents()
            if agent.status == "active"
        ]
        
        if not active_agents:
            return None
        
        # Score agents based on capabilities and reliability
        agent_scores: Dict[str, float] = {}
        for agent in active_agents:
            score = 0.0
            
            # Check capabilities match
            if any(cap in agent.capabilities for cap in task.description.lower().split()):
                score += 0.4
            
            # Consider reliability score
            reliability = self._agent_profiler.get_agent_reliability(agent.agent_id)
            score += reliability * 0.3
            
            # Consider specialization match
            specializations = self._agent_profiler.get_agent_specializations(agent.agent_id)
            if any(spec in task.description.lower() for spec in specializations):
                score += 0.3
            
            agent_scores[agent.agent_id] = score
        
        # Return agent with highest score
        if agent_scores:
            return max(agent_scores.items(), key=lambda x: x[1])[0]
        return None
    
    def assign_task(self, task: Task) -> bool:
        if task.status != TaskStatus.PENDING:
            return False
        
        suitable_agent = self.find_suitable_agent(task)
        if not suitable_agent:
            return False
        
        task.assigned_agent = suitable_agent
        task.status = TaskStatus.ASSIGNED
        return True
    
    def reassign_task(self, task: Task) -> bool:
        if task.status not in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
            return False
        
        suitable_agent = self.find_suitable_agent(task)
        if not suitable_agent or suitable_agent == task.assigned_agent:
            return False
        
        task.assigned_agent = suitable_agent
        return True
    
    def get_agent_workload(self, agent_id: str, tasks: List[Task]) -> int:
        return len([
            task for task in tasks
            if task.assigned_agent == agent_id
            and task.status in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]
        ]) 