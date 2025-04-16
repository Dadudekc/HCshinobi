"""Models for workflow definitions and steps."""
from typing import Dict, Any, List, Optional
from datetime import datetime

class WorkflowStep:
    """A single step in a workflow."""
    
    def __init__(self, step_id: str, description: str, dependencies: List[str] = None):
        """Initialize a workflow step."""
        self.step_id = step_id
        self.description = description
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None
        self.started_at = None
        self.completed_at = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary."""
        return {
            "id": self.step_id,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create step from dictionary."""
        step = cls(
            step_id=data["id"],
            description=data["description"],
            dependencies=data.get("dependencies", [])
        )
        step.status = data.get("status", "pending")
        step.result = data.get("result")
        step.started_at = data.get("started_at")
        step.completed_at = data.get("completed_at")
        return step
        
    def start(self) -> None:
        """Mark step as started."""
        self.status = "running"
        self.started_at = datetime.now().isoformat()
        
    def complete(self, result: Any = None) -> None:
        """Mark step as completed."""
        self.status = "completed"
        self.result = result
        self.completed_at = datetime.now().isoformat()
        
    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self.status = "failed"
        self.result = {"error": error}
        self.completed_at = datetime.now().isoformat()

class WorkflowDefinition:
    """A complete workflow definition."""
    
    def __init__(self, workflow_id: str, name: str, description: str):
        """Initialize a workflow definition."""
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.status = "pending"
        self.created_at = datetime.now().isoformat()
        self.updated_at = None
        
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
        self._update()
        
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self.steps.get(step_id)
        
    def update_step(self, step_id: str, status: str, result: Any = None) -> None:
        """Update a step's status and result."""
        step = self.get_step(step_id)
        if not step:
            return
            
        if status == "running":
            step.start()
        elif status == "completed":
            step.complete(result)
        elif status == "failed":
            step.fail(result)
            
        self._update()
        
    def _update(self) -> None:
        """Update workflow status and timestamp."""
        self.updated_at = datetime.now().isoformat()
        
        # Update overall workflow status
        if not self.steps:
            self.status = "pending"
        elif any(step.status == "failed" for step in self.steps.values()):
            self.status = "failed"
        elif all(step.status == "completed" for step in self.steps.values()):
            self.status = "completed"
        elif any(step.status == "running" for step in self.steps.values()):
            self.status = "running"
        else:
            self.status = "pending"
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary."""
        return {
            "id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "steps": {
                step_id: step.to_dict()
                for step_id, step in self.steps.items()
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        """Create workflow from dictionary."""
        workflow = cls(
            workflow_id=data["id"],
            name=data["name"],
            description=data["description"]
        )
        workflow.status = data.get("status", "pending")
        workflow.created_at = data.get("created_at", workflow.created_at)
        workflow.updated_at = data.get("updated_at")
        
        # Load steps
        for step_data in data.get("steps", {}).values():
            step = WorkflowStep.from_dict(step_data)
            workflow.steps[step.step_id] = step
            
        return workflow 