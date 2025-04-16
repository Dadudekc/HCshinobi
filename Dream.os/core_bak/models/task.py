import sys
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime, timezone

# Add project root for imports if needed (for log_event)
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import logger (handle potential import error for standalone use)
try:
    from core.governance_memory_engine import log_event
except ImportError:
    print(f"[TaskModel] Warning: Real log_event not imported. Using dummy.")
    def log_event(etype, src, dtls): print(f"[LOG] {etype} | {src} | {dtls}")

class TaskStatus(Enum):
    """Enumeration for the possible statuses of a Task."""
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    BLOCKED = "Blocked"
    NEEDS_REVIEW = "Needs Review"

@dataclass
class Task:
    """Represents a single, trackable unit of work within the system.

    Attributes:
        description (str): A clear, concise description of what the task entails.
        task_id (str): A unique identifier for the task, typically auto-generated.
        status (TaskStatus): The current state of the task (e.g., Pending, Completed).
        priority (int): Numerical priority (lower number means higher priority).
        dependencies (List[str]): A list of `task_id`s that must be completed before this task can start.
        estimated_time (Optional[str]): A human-readable estimate of duration (e.g., "2h", "30m").
        actual_time (Optional[str]): A human-readable record of the actual time spent.
        assigned_to (Optional[str]): The ID of the agent or user currently responsible for the task.
        created_at (datetime): Timestamp (UTC) when the task object was created.
        updated_at (datetime): Timestamp (UTC) when the task object was last modified.
        details (Dict[str, Any]): A dictionary for storing task-specific metadata or parameters.
        result (Optional[Any]): Stores the output or outcome of the task upon completion or failure.
        notes: (Optional[str]): Human-readable notes or comments about the task.
    """
    description: str
    task_id: str = field(default_factory=lambda: f"T-{uuid.uuid4()}")
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 3
    dependencies: List[str] = field(default_factory=list)
    estimated_time: Optional[str] = None
    actual_time: Optional[str] = None
    assigned_to: Optional[str] = None
    # Use datetime objects, default to now(UTC)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    notes: Optional[str] = None

    def __post_init__(self):
        """Perform post-initialization validation and setup."""
        # Ensure timestamps are timezone-aware (UTC)
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
            
        # Basic validation example
        if not self.description or not self.description.strip():
            raise ValueError("Task description cannot be empty.")
            
        # Coerce status to Enum if provided as string (basic handling)
        if isinstance(self.status, str):
            try:
                self.status = TaskStatus(self.status)
            except ValueError:
                 # Log warning if coercion fails, default to Pending
                 log_event("MODEL_WARNING", "Task", {"task_id": self.task_id, "warning": f"Invalid status string '{self.status}' provided. Defaulting to PENDING."})
                 self.status = TaskStatus.PENDING
        elif not isinstance(self.status, TaskStatus):
             log_event("MODEL_WARNING", "Task", {"task_id": self.task_id, "warning": f"Invalid status type '{type(self.status)}' provided. Defaulting to PENDING."})
             self.status = TaskStatus.PENDING

    def update_status(self, new_status: TaskStatus, update_timestamp: bool = True):
        """Updates the task's status and optionally the updated_at timestamp.

        Args:
            new_status (TaskStatus): The new status to set.
            update_timestamp (bool): Whether to update the `updated_at` timestamp. Defaults to True.
        """
        if not isinstance(new_status, TaskStatus):
            # Log error and potentially raise exception or ignore
            log_event("MODEL_ERROR", "Task", {"task_id": self.task_id, "error": f"Invalid status type provided to update_status: {type(new_status)}"})
            # Or: raise TypeError("new_status must be a TaskStatus Enum member")
            return # Ignore invalid status update for now

        old_status = self.status
        self.status = new_status
        if update_timestamp:
            self.updated_at = datetime.now(timezone.utc)
            
        # Log the status change
        log_event("TASK_STATUS_UPDATE", "Task", {
            "task_id": self.task_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "updated_at": self.updated_at.isoformat()
        })

# Example Usage:
if __name__ == '__main__':
    # Example using the refined Task class
    try:
        task1 = Task(description="Define project scope", priority=1)
        print(f"Task 1 Created: ID={task1.task_id}, Status={task1.status}, Created={task1.created_at.isoformat()}")

        task2 = Task(description="Create initial design mockups", dependencies=[task1.task_id])
        print(f"Task 2 Created: ID={task2.task_id}, DependsOn={task2.dependencies}")

        task3 = Task(task_id="T-MANUAL", description="Review design mockups", status="Blocked", dependencies=[task2.task_id]) # Status as string
        print(f"Task 3 Created: ID={task3.task_id}, Status={task3.status}")

        print("\nUpdating Task 2 status...")
        task2.update_status(TaskStatus.IN_PROGRESS)
        print(f"Task 2 Status: {task2.status}, Updated: {task2.updated_at.isoformat()}")
        
        print("\nAttempting invalid status update...")
        task2.update_status("InvalidStatusString")
        print(f"Task 2 Status after invalid update: {task2.status}")
        
        # Example of validation failure
        # print("\nAttempting task with empty description...")
        # invalid_task = Task(description="")
        
    except ValueError as ve:
        print(f"\nCaught Validation Error: {ve}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}") 