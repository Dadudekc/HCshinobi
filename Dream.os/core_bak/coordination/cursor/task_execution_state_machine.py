"""Task execution state machine for Cursor fleet automation."""

import asyncio
import json
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import uuid

from .cursor_instance_controller import (
    CursorInstanceController,
    CursorCommand,
    CommandResult
)
from .task_execution_monitor import create_monitor, TaskExecutionMonitor

class TaskState(Enum):
    """States for task execution lifecycle."""
    PENDING = "pending"
    PREPARING = "preparing"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class StepState(Enum):
    """States for individual step execution."""
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"
    SKIPPED = "skipped"

@dataclass
class TaskStep:
    """Individual step in a task execution plan."""
    action: str
    element: Optional[str] = None
    timeout: float = 5.0
    retries: int = 2
    retry_delay: float = 1.0
    required: bool = True
    state: StepState = StepState.PENDING
    result: Optional[CommandResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert step to dictionary format."""
        return {
            "action": self.action,
            "element": self.element,
            "timeout": self.timeout,
            "retries": self.retries,
            "retry_delay": self.retry_delay,
            "required": self.required,
            "state": self.state.value,
            "result": self.result.to_dict() if self.result else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

@dataclass
class TaskExecutionPlan:
    """Complete plan for executing a task."""
    task_id: str
    steps: List[TaskStep]
    state: TaskState = TaskState.PENDING
    cursor_instance_id: Optional[str] = None
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskExecutionPlan':
        """Create plan from dictionary format."""
        steps = [
            TaskStep(**step) if isinstance(step, dict) else step
            for step in data.get("steps", [])
        ]
        return cls(
            task_id=data.get("task_id", str(uuid.uuid4())),
            steps=steps,
            cursor_instance_id=data.get("cursor_instance_id"),
            state=TaskState(data.get("state", "pending"))
        )
    
    def to_dict(self) -> Dict:
        """Convert plan to dictionary format."""
        return {
            "task_id": self.task_id,
            "steps": [step.to_dict() for step in self.steps],
            "state": self.state.value,
            "cursor_instance_id": self.cursor_instance_id,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }

class TaskExecutionStateMachine:
    """Orchestrates task execution across Cursor instances."""
    
    def __init__(
        self,
        cursor_controller: CursorInstanceController,
        feedback_callback: Optional[callable] = None,
        enable_monitor: bool = True
    ):
        self.controller = cursor_controller
        self.feedback_callback = feedback_callback
        self.logger = logging.getLogger("TaskExecutionStateMachine")
        self.active_tasks: Dict[str, TaskExecutionPlan] = {}
        
        # Initialize visual monitor if enabled
        self.monitor: Optional[TaskExecutionMonitor] = None
        if enable_monitor:
            self.monitor = create_monitor()
            # Override feedback callback to include monitor updates
            original_callback = self.feedback_callback
            def monitor_callback(data: Dict):
                if self.monitor:
                    self.monitor.handle_feedback(data)
                if original_callback:
                    original_callback(data)
            self.feedback_callback = monitor_callback
    
    def _emit_feedback(self, task_id: str, event_type: str, data: Dict):
        """Emit feedback about task execution."""
        if self.feedback_callback:
            try:
                self.feedback_callback({
                    "task_id": task_id,
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat(),
                    "data": data
                })
            except Exception as e:
                self.logger.error(f"Error emitting feedback: {str(e)}")
    
    def _step_to_commands(self, step: TaskStep) -> List[CursorCommand]:
        """Convert a task step to a list of CursorCommands."""
        commands = []
        
        if step.action == "wait_for_element":
            commands.append(CursorCommand(
                "wait",
                {
                    "element_type": step.element,
                    "timeout": step.timeout,
                },
                retry_count=step.retries,
                retry_delay=step.retry_delay
            ))
        elif step.action == "click":
            # For clicks, we usually want to wait first
            commands.append(CursorCommand(
                "wait",
                {
                    "element_type": step.element,
                    "timeout": step.timeout
                },
                retry_count=step.retries,
                retry_delay=step.retry_delay
            ))
            commands.append(CursorCommand(
                "click",
                {
                    "element_type": step.element
                },
                retry_count=step.retries,
                retry_delay=step.retry_delay
            ))
        elif step.action == "verify_element":
            commands.append(CursorCommand(
                "wait",
                {
                    "element_type": step.element,
                    "timeout": step.timeout,
                    "present": True
                },
                retry_count=step.retries,
                retry_delay=step.retry_delay
            ))
        elif step.action == "verify_element_gone":
            commands.append(CursorCommand(
                "wait",
                {
                    "element_type": step.element,
                    "timeout": step.timeout,
                    "present": False
                },
                retry_count=step.retries,
                retry_delay=step.retry_delay
            ))
        else:
            raise ValueError(f"Unknown action type: {step.action}")
            
        return commands
    
    async def execute_step(
        self,
        step: TaskStep,
        instance_id: Optional[str]
    ) -> bool:
        """Execute a single task step."""
        try:
            step.state = StepState.RUNNING
            step.started_at = datetime.now()
            
            # Convert step to commands
            commands = self._step_to_commands(step)
            
            # Execute command chain
            results = await self.controller.execute_chain(
                *commands,
                instance_id=instance_id
            )
            
            # Store last result
            if results:
                step.result = results[-1]
                
            # Check if all commands succeeded
            success = all(r.success for r in results)
            
            step.state = StepState.COMPLETED if success else StepState.FAILED
            step.completed_at = datetime.now()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Step execution failed: {str(e)}")
            step.state = StepState.FAILED
            step.completed_at = datetime.now()
            if not step.result:
                step.result = CommandResult(
                    success=False,
                    message=str(e),
                    timestamp=datetime.now(),
                    duration=0,
                    error=e
                )
            return False
    
    async def execute_plan(
        self,
        plan: Union[TaskExecutionPlan, Dict]
    ) -> TaskExecutionPlan:
        """Execute a complete task plan."""
        # Convert dict to plan if needed
        if isinstance(plan, dict):
            plan = TaskExecutionPlan.from_dict(plan)
            
        self.active_tasks[plan.task_id] = plan
        plan.state = TaskState.PREPARING
        plan.started_at = datetime.now()
        
        try:
            self._emit_feedback(
                plan.task_id,
                "task_started",
                {"plan": plan.to_dict()}
            )
            
            plan.state = TaskState.RUNNING
            
            # Execute each step
            for step in plan.steps:
                self._emit_feedback(
                    plan.task_id,
                    "step_started",
                    {"step": step.to_dict()}
                )
                
                success = await self.execute_step(
                    step,
                    plan.cursor_instance_id
                )
                
                self._emit_feedback(
                    plan.task_id,
                    "step_completed",
                    {
                        "step": step.to_dict(),
                        "success": success
                    }
                )
                
                if not success and step.required:
                    plan.state = TaskState.FAILED
                    plan.error_message = f"Required step failed: {step.action}"
                    break
            
            # Check if all steps completed
            if plan.state != TaskState.FAILED:
                if all(s.state == StepState.COMPLETED for s in plan.steps):
                    plan.state = TaskState.COMPLETED
                else:
                    plan.state = TaskState.FAILED
                    plan.error_message = "Not all steps completed successfully"
            
        except Exception as e:
            plan.state = TaskState.FAILED
            plan.error_message = str(e)
            self.logger.error(f"Plan execution failed: {str(e)}")
            
        finally:
            plan.completed_at = datetime.now()
            self._emit_feedback(
                plan.task_id,
                "task_completed",
                {"plan": plan.to_dict()}
            )
            
        return plan
    
    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """Get current state of a task."""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id].to_dict()
        return None

async def main():
    """Example usage of TaskExecutionStateMachine."""
    # Initialize controller
    controller = CursorInstanceController()
    
    # Create state machine with monitor enabled
    state_machine = TaskExecutionStateMachine(
        controller,
        enable_monitor=True
    )
    
    # Example task plan
    plan = {
        "task_id": "test-task-1",
        "steps": [
            {
                "action": "wait_for_element",
                "element": "accept_button",
                "timeout": 5.0,
                "retries": 2
            },
            {
                "action": "click",
                "element": "accept_button",
                "retries": 1
            },
            {
                "action": "verify_element",
                "element": "resume_button",
                "timeout": 7.0
            }
        ]
    }
    
    try:
        # Execute plan
        result = await state_machine.execute_plan(plan)
        
        # Keep the application running to show the monitor
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await controller.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 