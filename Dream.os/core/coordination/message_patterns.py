"""Standardized message patterns for agent coordination."""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime, timezone # Ensure timezone awareness

class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    CLAIMED = "claimed" # Optional: If tasks need explicit claiming
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """Task priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TaskMessage:
    """Standard task message format, used as the 'data' field in AgentBus messages."""
    task_id: str
    agent_id: str # Target agent ID
    task_type: str # The specific action/command requested
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None # ID linking related messages (e.g., request/response)
    source_agent_id: Optional[str] = None # Agent initiating the task
    parent_task_id: Optional[str] = None # If this is a subtask
    subtasks: List[str] = field(default_factory=list) # IDs of child tasks
    metadata: Dict[str, Any] = field(default_factory=dict) # For extra contextual info

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to a dictionary suitable for JSON serialization in message bus."""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "status": self.status.value,
            "input_data": self.input_data,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "correlation_id": self.correlation_id,
            "source_agent_id": self.source_agent_id,
            "parent_task_id": self.parent_task_id,
            "subtasks": self.subtasks,
            "metadata": self.metadata
        }

    # Renamed from_message_content to from_dict for clarity
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMessage':
        """Create TaskMessage from a dictionary (e.g., parsed from message bus)."""
        # Handle potential missing optional fields gracefully
        # Convert enums and timestamps back from string representation
        try:
            return cls(
                task_id=data["task_id"],
                agent_id=data["agent_id"],
                task_type=data["task_type"],
                priority=TaskPriority(data.get("priority", TaskPriority.NORMAL.value)),
                status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
                input_data=data.get("input_data", {}),
                result=data.get("result"),
                error=data.get("error"),
                created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
                updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(timezone.utc),
                correlation_id=data.get("correlation_id"),
                source_agent_id=data.get("source_agent_id"),
                parent_task_id=data.get("parent_task_id"),
                subtasks=data.get("subtasks", []),
                metadata=data.get("metadata", {})
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in task data: {e}") from e
        except Exception as e:
            # Log or handle other potential errors during reconstruction
            raise ValueError(f"Error reconstructing TaskMessage from dict: {e}") from e

def create_task_message(
    task_type: str,
    agent_id: str, # Target agent
    input_data: Dict[str, Any],
    source_agent_id: Optional[str] = None, # Source agent
    priority: TaskPriority = TaskPriority.NORMAL,
    parent_task_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TaskMessage:
    """Helper function to create a new TaskMessage instance with defaults."""
    from uuid import uuid4

    # Generate default correlation ID if not provided
    effective_correlation_id = correlation_id or f"corr_{uuid4().hex[:8]}"

    return TaskMessage(
        task_id=f"task_{uuid4().hex}", # Generate a unique task ID
        agent_id=agent_id,
        task_type=task_type,
        priority=priority,
        status=TaskStatus.PENDING,
        input_data=input_data,
        correlation_id=effective_correlation_id,
        source_agent_id=source_agent_id,
        parent_task_id=parent_task_id,
        subtasks=[],
        metadata=metadata or {}
    )

def update_task_status(
    task: TaskMessage,
    new_status: TaskStatus,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    subtasks: Optional[List[str]] = None
) -> TaskMessage:
    """Update task status and related fields, returning the modified task."""
    if not isinstance(task, TaskMessage):
         raise TypeError("Input 'task' must be a TaskMessage instance")

    task.status = new_status
    task.updated_at = datetime.now(timezone.utc) # Use timezone aware now

    if result is not None:
        task.result = result
        task.error = None # Clear error if setting result
    if error is not None:
        task.error = error
        task.result = None # Clear result if setting error
    if subtasks is not None:
         task.subtasks = subtasks

    return task 