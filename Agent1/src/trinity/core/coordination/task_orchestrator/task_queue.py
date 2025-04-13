from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from .onboarding_task import OnboardingTask, OnboardingStep

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    task_id: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = []
    assigned_agent: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    is_onboarding: bool = False
    onboarding_step: Optional[str] = None

class TaskQueue:
    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._priority_queues: Dict[TaskPriority, List[str]] = {
            priority: [] for priority in TaskPriority
        }
        self._onboarding = OnboardingTask()
        self._agent_onboarding: Dict[str, List[str]] = {}  # agent_id -> completed steps
        self._agent_onboarding_results: Dict[str, Dict[str, Dict[str, Any]]] = {}  # agent_id -> step_id -> results
    
    def create_task(self, task_id: str, description: str, priority: TaskPriority, 
                   dependencies: List[str] = None, is_onboarding: bool = False, 
                   onboarding_step: Optional[str] = None) -> Task:
        if task_id in self._tasks:
            raise ValueError(f"Task {task_id} already exists")
        
        task = Task(
            task_id=task_id,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            is_onboarding=is_onboarding,
            onboarding_step=onboarding_step
        )
        self._tasks[task_id] = task
        self._priority_queues[priority].append(task_id)
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        task.status = status
        task.updated_at = datetime.now()
        
        # If this is an onboarding task and it's completed, update onboarding progress
        if task.is_onboarding and status == TaskStatus.COMPLETED:
            agent_id = task.assigned_agent
            if agent_id and task.onboarding_step:
                if agent_id not in self._agent_onboarding:
                    self._agent_onboarding[agent_id] = []
                if task.onboarding_step not in self._agent_onboarding[agent_id]:
                    self._agent_onboarding[agent_id].append(task.onboarding_step)
    
    def assign_task(self, task_id: str, agent_id: str) -> None:
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        task.assigned_agent = agent_id
        task.status = TaskStatus.ASSIGNED
        task.updated_at = datetime.now()
    
    def get_next_task(self, agent_id: str, priority: Optional[TaskPriority] = None) -> Optional[Task]:
        # Check if agent needs onboarding
        if agent_id not in self._agent_onboarding or not self._agent_onboarding[agent_id]:
            next_step = self._onboarding.get_next_step([])
            if next_step:
                task_id = f"onboarding_{next_step.step_id}_{agent_id}"
                if task_id not in self._tasks:
                    self.create_task(
                        task_id=task_id,
                        description=next_step.description,
                        priority=TaskPriority.HIGH,
                        is_onboarding=True,
                        onboarding_step=next_step.step_id
                    )
                return self._tasks[task_id]
        
        # Get next onboarding step if agent is in the process
        if agent_id in self._agent_onboarding:
            next_step = self._onboarding.get_next_step(self._agent_onboarding[agent_id])
            if next_step:
                task_id = f"onboarding_{next_step.step_id}_{agent_id}"
                if task_id not in self._tasks:
                    self.create_task(
                        task_id=task_id,
                        description=next_step.description,
                        priority=TaskPriority.HIGH,
                        is_onboarding=True,
                        onboarding_step=next_step.step_id
                    )
                return self._tasks[task_id]
        
        # Get regular tasks based on priority
        if priority:
            if self._priority_queues[priority]:
                task_id = self._priority_queues[priority][0]
                return self._tasks[task_id]
        else:
            for p in [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]:
                if self._priority_queues[p]:
                    task_id = self._priority_queues[p][0]
                    return self._tasks[task_id]
        return None
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        return [
            task for task in self._tasks.values()
            if task.status == status
        ]
    
    def get_tasks_by_agent(self, agent_id: str) -> List[Task]:
        return [
            task for task in self._tasks.values()
            if task.assigned_agent == agent_id
        ]
    
    def remove_task(self, task_id: str) -> None:
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self._tasks[task_id]
        self._priority_queues[task.priority].remove(task_id)
        del self._tasks[task_id]
    
    def get_onboarding_status(self, agent_id: str) -> Dict[str, Any]:
        completed_steps = self._agent_onboarding.get(agent_id, [])
        results = self._agent_onboarding_results.get(agent_id, {})
        return self._onboarding.get_completion_status(completed_steps, results)
    
    def update_onboarding_results(self, agent_id: str, step_id: str, results: Dict[str, Any]) -> None:
        if agent_id not in self._agent_onboarding_results:
            self._agent_onboarding_results[agent_id] = {}
        self._agent_onboarding_results[agent_id][step_id] = results
        
        # Check if step is complete
        if self._onboarding.is_step_complete(step_id, results):
            if agent_id not in self._agent_onboarding:
                self._agent_onboarding[agent_id] = []
            if step_id not in self._agent_onboarding[agent_id]:
                self._agent_onboarding[agent_id].append(step_id) 