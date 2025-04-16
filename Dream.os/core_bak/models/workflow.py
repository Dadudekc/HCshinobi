import sys
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
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
    print(f"[WorkflowModel] Warning: Real log_event not imported. Using dummy.")
    def log_event(etype, src, dtls): print(f"[LOG] {etype} | {src} | {dtls}")


@dataclass
class WorkflowStep:
    """Represents a single, executable step within a workflow.

    Attributes:
        step_id (int): A unique sequential identifier for the step within the workflow.
        name (str): A human-readable name for the step.
        agent (str): The ID of the agent responsible for executing this step.
        command (str): The specific method/command to be invoked on the target agent.
        params (Dict[str, Any]): Parameters to pass to the agent command, potentially containing template strings for interpolation (e.g., `{{ input.value }}`).
        output_var (Optional[str]): If provided, the result of this step will be stored in the workflow context under this variable name for use in subsequent steps.
        description (Optional[str]): A more detailed description of the step's purpose.
        max_retries (int): Number of times to retry this step upon failure. Defaults to 0.
        retry_delay_seconds (int): Number of seconds to wait before retrying. Defaults to 5.
    """
    step_id: int
    name: str
    agent: str
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    output_var: Optional[str] = None
    description: Optional[str] = None
    max_retries: int = 0
    retry_delay_seconds: int = 5

    def __post_init__(self):
        """Validate step attributes after initialization."""
        if not isinstance(self.step_id, int) or self.step_id <= 0:
            raise ValueError(f"step_id must be a positive integer (got {self.step_id})")
        if not self.name or not self.name.strip():
            raise ValueError("WorkflowStep name cannot be empty.")
        if not self.agent or not self.agent.strip():
            raise ValueError("WorkflowStep agent cannot be empty.")
        if not self.command or not self.command.strip():
            raise ValueError("WorkflowStep command cannot be empty.")
        if not isinstance(self.params, dict):
            # Attempt coercion? For now, raise error.
            raise TypeError(f"WorkflowStep params must be a dictionary (got {type(self.params)})")
        if self.max_retries < 0:
            log_event("MODEL_WARNING", "WorkflowStep", {"step_id": self.step_id, "warning": f"max_retries cannot be negative ({self.max_retries}). Setting to 0."})
            self.max_retries = 0
        if self.retry_delay_seconds < 0:
            log_event("MODEL_WARNING", "WorkflowStep", {"step_id": self.step_id, "warning": f"retry_delay_seconds cannot be negative ({self.retry_delay_seconds}). Setting to 0."})
            self.retry_delay_seconds = 0

@dataclass
class WorkflowDefinition:
    """Defines a structured, repeatable workflow composed of multiple steps.

    Attributes:
        name (str): A human-readable name for the workflow.
        workflow_id (str): A unique identifier for the workflow, typically auto-generated.
        description (Optional[str]): A more detailed description of the workflow's purpose.
        input_schema (Optional[Dict[str, Any]]): A schema (e.g., JSON Schema draft) describing the expected input data structure for the workflow.
        steps (List[WorkflowStep]): An ordered list of steps that constitute the workflow.
        created_at (datetime): Timestamp (UTC) when the workflow definition was created.
        version (int): Version number of the workflow definition.
    """
    name: str
    workflow_id: str = field(default_factory=lambda: f"WF-{uuid.uuid4()}")
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = field(default_factory=dict)
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    def __post_init__(self):
        """Validate workflow definition after initialization."""
        if not self.name or not self.name.strip():
            raise ValueError("WorkflowDefinition name cannot be empty.")
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        # Validate steps are WorkflowStep instances and check for duplicate step_ids
        step_ids = set()
        validated_steps = []
        if not isinstance(self.steps, list):
             raise TypeError(f"WorkflowDefinition steps must be a list (got {type(self.steps)})")
             
        for i, step_data in enumerate(self.steps):
            if isinstance(step_data, WorkflowStep):
                step = step_data
            elif isinstance(step_data, dict):
                try:
                    step = WorkflowStep(**step_data)
                    log_event("MODEL_INFO", "WorkflowDefinition", {"workflow_id": self.workflow_id, "info": f"Coerced step {i} from dict to WorkflowStep."})
                except Exception as e:
                     raise TypeError(f"Error coercing step {i} from dict: {e}")
            else:
                raise TypeError(f"Step {i} must be a WorkflowStep or a dictionary, not {type(step_data)}")

            if step.step_id in step_ids:
                raise ValueError(f"Duplicate step_id {step.step_id} found in workflow definition.")
            step_ids.add(step.step_id)
            validated_steps.append(step)
            
        # Replace original steps list with potentially coerced/validated one
        self.steps = validated_steps

# Example Usage:
if __name__ == '__main__':
    try:
        step1_data = {
            "step_id": 1,
            "name": "Generate Plan",
            "agent": "PlannerAgent",
            "command": "plan_from_goal",
            "params": {"goal": "{{input.goal}}"},
            "output_var": "plan_result",
            "max_retries": 1 # Example retry
        }
        step1 = WorkflowStep(**step1_data) # Create using dict

        step2 = WorkflowStep(
            step_id=2,
            name="Schedule Tasks",
            agent="CalendarAgent",
            command="schedule_tasks",
            params={"tasks": "{{ step_1.plan_result }}"} # Note: Interpolation depends on context naming
        )

        workflow_def = WorkflowDefinition(
            name="Plan and Schedule Goal Workflow",
            description="Takes a goal, generates a plan, and schedules the tasks.",
            input_schema={"goal": {"type": "string", "description": "The high-level goal"}},
            steps=[step1, step2] # Use created step objects
        )

        print(f"Workflow Created: ID={workflow_def.workflow_id}, Name={workflow_def.name}, Created={workflow_def.created_at.isoformat()}")
        print(f"Step 1: ID={workflow_def.steps[0].step_id}, Agent={workflow_def.steps[0].agent}, Retries={workflow_def.steps[0].max_retries}")
        print(f"Step 2: ID={workflow_def.steps[1].step_id}, Command={workflow_def.steps[1].command}")
        
        # Example Validation Failure (Duplicate ID)
        # print("\nAttempting duplicate step ID...")
        # step3 = WorkflowStep(step_id=1, name="Duplicate Step", agent="AgentC", command="cmd3")
        # wf_fail = WorkflowDefinition(name="FailWF", steps=[step1, step3])
        
        # Example Validation Failure (Empty Step Name)
        # print("\nAttempting empty step name...")
        # step_empty_name = WorkflowStep(step_id=3, name="  ", agent="AgentD", command="cmd4")
        # wf_fail2 = WorkflowDefinition(name="FailWF2", steps=[step_empty_name])

    except (ValueError, TypeError) as ve:
        print(f"\nCaught Validation Error: {ve}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}") 