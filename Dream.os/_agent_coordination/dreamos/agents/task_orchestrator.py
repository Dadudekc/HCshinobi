"""TaskOrchestratorAgent - Handles task queue management and orchestration."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import asdict

from dreamos.agents import TaskMetadata

logger = logging.getLogger(__name__)

class TaskOrchestratorAgent:
    """Agent responsible for managing and orchestrating task execution."""
    
    def __init__(self, queue_dir: str = "queue"):
        """Initialize the TaskOrchestratorAgent.
        
        Args:
            queue_dir: Directory for storing task queue and related files
        """
        self.queue_dir = Path(queue_dir)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.queue_dir / "tasks.json"
        self.task_queue: List[TaskMetadata] = []
        self._load_queue()
        
    def _load_queue(self) -> None:
        """Load existing task queue from file."""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                    self.task_queue = [
                        TaskMetadata(**task) for task in tasks_data
                    ]
                logger.info(f"Loaded {len(self.task_queue)} tasks from queue")
            except Exception as e:
                logger.error(f"Failed to load task queue: {e}")
                self.task_queue = []
    
    def _save_queue(self) -> None:
        """Save current task queue to file."""
        try:
            with open(self.tasks_file, 'w') as f:
                json.dump([asdict(task) for task in self.task_queue], f, indent=2)
            logger.info("Task queue saved successfully")
        except Exception as e:
            logger.error(f"Failed to save task queue: {e}")
    
    def add_task(self, 
                 description: str,
                 target_files: List[str],
                 priority: int = 1,
                 dependencies: Optional[List[str]] = None,
                 success_criteria: Optional[Dict] = None) -> TaskMetadata:
        """Add a new task to the queue.
        
        Args:
            description: Task description/title
            target_files: List of files to be modified
            priority: Task priority (1-5, 1 highest)
            dependencies: List of task IDs this task depends on
            success_criteria: Dict of criteria for task success
            
        Returns:
            TaskMetadata object for the created task
        """
        task_id = f"task_{len(self.task_queue) + 1:03d}"
        
        task = TaskMetadata(
            task_id=task_id,
            priority=priority,
            estimated_complexity=self._estimate_complexity(target_files),
            target_files=target_files,
            dependencies=dependencies or [],
            success_criteria=success_criteria or {},
            created_at=datetime.utcnow(),
            status="pending"
        )
        
        self.task_queue.append(task)
        self._save_queue()
        logger.info(f"Added new task: {task_id}")
        return task
    
    def get_next_task(self) -> Optional[TaskMetadata]:
        """Get the next task ready for execution.
        
        Returns:
            TaskMetadata object if a task is ready, None otherwise
        """
        ready_tasks = [
            task for task in self.task_queue
            if task.status == "pending" and self._are_dependencies_met(task)
        ]
        
        if not ready_tasks:
            return None
            
        return min(ready_tasks, key=lambda t: (t.priority, t.created_at))
    
    def update_task_status(self, task_id: str, status: str) -> None:
        """Update the status of a task.
        
        Args:
            task_id: ID of the task to update
            status: New status value
        """
        for task in self.task_queue:
            if task.task_id == task_id:
                task.status = status
                self._save_queue()
                logger.info(f"Updated task {task_id} status to {status}")
                break
    
    def _are_dependencies_met(self, task: TaskMetadata) -> bool:
        """Check if all dependencies for a task are completed.
        
        Args:
            task: TaskMetadata object to check
            
        Returns:
            True if all dependencies are met, False otherwise
        """
        for dep_id in task.dependencies:
            dep_task = next(
                (t for t in self.task_queue if t.task_id == dep_id), None
            )
            if not dep_task or dep_task.status != "completed":
                return False
        return True
    
    def _estimate_complexity(self, target_files: List[str]) -> float:
        """Estimate task complexity based on target files.
        
        Args:
            target_files: List of files to be modified
            
        Returns:
            Estimated complexity score
        """
        # TODO: Implement more sophisticated complexity estimation
        return len(target_files) * 1.5
    
    def get_task_by_id(self, task_id: str) -> Optional[TaskMetadata]:
        """Get a task by its ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            TaskMetadata object if found, None otherwise
        """
        return next(
            (task for task in self.task_queue if task.task_id == task_id),
            None
        )
    
    def get_queue_status(self) -> Dict:
        """Get current status of the task queue.
        
        Returns:
            Dict containing queue statistics
        """
        statuses = {}
        for task in self.task_queue:
            statuses[task.status] = statuses.get(task.status, 0) + 1
            
        return {
            "total_tasks": len(self.task_queue),
            "status_counts": statuses,
            "ready_tasks": sum(1 for task in self.task_queue 
                             if task.status == "pending" and 
                             self._are_dependencies_met(task))
        } 