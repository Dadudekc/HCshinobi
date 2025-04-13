"""
Consolidated Task Manager
Combines functionality from both core implementations into a single, unified task manager.
"""

import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

class TaskPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class Task:
    id: str
    name: str
    handler: Callable
    priority: TaskPriority = TaskPriority.MEDIUM
    schedule: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    status: str = "pending"
    
class TaskManager:
    """Unified task management system."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, Task] = {}
        self.task_metrics: Dict[str, Dict[str, Any]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
        
        # Thread safety
        self._lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        
        # Start scheduler
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._running = True
        self._scheduler_thread.start()
        
    def register_task(
        self,
        name: str,
        handler: Callable,
        priority: TaskPriority = TaskPriority.MEDIUM,
        schedule: Optional[str] = None,
        required_permissions: Optional[List[str]] = None
    ) -> str:
        """Register a new task."""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            handler=handler,
            priority=priority,
            schedule=schedule,
            required_permissions=required_permissions or []
        )
        
        with self._lock:
            self.tasks[task_id] = task
            
        self.logger.info(f"Registered task {name} with ID {task_id}")
        return task_id
        
    def schedule_task(
        self,
        task_id: str,
        params: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        deadline: Optional[datetime] = None
    ) -> str:
        """Schedule a task for execution."""
        with self._lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
                
            execution_id = str(uuid.uuid4())
            task = self.tasks[task_id]
            
            scheduled_task = Task(
                id=execution_id,
                name=task.name,
                handler=task.handler,
                priority=task.priority,
                params=params or {},
                dependencies=dependencies or [],
                required_permissions=task.required_permissions,
                deadline=deadline
            )
            
            self.running_tasks[execution_id] = scheduled_task
            
            if dependencies:
                self.dependencies[execution_id] = set(dependencies)
                
        self.logger.info(f"Scheduled task {task.name} with execution ID {execution_id}")
        return execution_id
        
    def get_task_status(self, execution_id: str) -> Dict[str, Any]:
        """Get the status of a scheduled task."""
        with self._lock:
            if execution_id not in self.running_tasks:
                return {"status": "not_found"}
                
            task = self.running_tasks[execution_id]
            return {
                "id": task.id,
                "name": task.name,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "deadline": task.deadline.isoformat() if task.deadline else None
            }
            
    def _scheduler_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                self._process_tasks()
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
            time.sleep(1)
            
    def _process_tasks(self):
        """Process scheduled tasks."""
        with self._lock:
            for execution_id, task in list(self.running_tasks.items()):
                if task.status != "pending":
                    continue
                    
                if execution_id in self.dependencies:
                    if not self._check_dependencies(execution_id):
                        continue
                        
                self._execute_task(execution_id, task)
                
    def _check_dependencies(self, execution_id: str) -> bool:
        """Check if all dependencies are met."""
        deps = self.dependencies[execution_id]
        return all(
            dep not in self.running_tasks or
            self.running_tasks[dep].status == "completed"
            for dep in deps
        )
        
    def _execute_task(self, execution_id: str, task: Task):
        """Execute a task."""
        try:
            task.status = "running"
            result = task.handler(**task.params)
            task.status = "completed"
            self._update_metrics(task, "success")
        except Exception as e:
            task.status = "failed"
            self._update_metrics(task, "failed", error=str(e))
            self.logger.error(f"Task {task.name} failed: {e}")
            
    def _update_metrics(self, task: Task, status: str, error: str = None):
        """Update task metrics."""
        with self._metrics_lock:
            if task.name not in self.task_metrics:
                self.task_metrics[task.name] = {
                    "total_runs": 0,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "last_run": None,
                    "last_error": None
                }
                
            metrics = self.task_metrics[task.name]
            metrics["total_runs"] += 1
            metrics["last_run"] = datetime.utcnow()
            
            if status == "success":
                metrics["successful_runs"] += 1
            else:
                metrics["failed_runs"] += 1
                metrics["last_error"] = error
                
    def shutdown(self):
        """Shutdown the task manager."""
        self._running = False
        self._scheduler_thread.join(timeout=5)
        self.logger.info("Task manager shutdown complete") 