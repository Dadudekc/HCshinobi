from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from log import logger
from _core.coordination.cursor.cursor_instance import CursorInstance
from _core.coordination.cursor.cursor_instance_controller import CursorInstanceController
from _core.coordination.cursor.cursor_command import CursorCommand
from _core.coordination.cursor.command_result import CommandResult
from _core.coordination.cursor.task_execution_plan import TaskExecutionPlan
from _core.coordination.cursor.task_execution_state_machine import TaskExecutionStateMachine

class StepState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    FAILED = "failed"
    COMPLETED = "completed"
    SKIPPED = "skipped"

@dataclass
class TaskStep:
    action: str
    element: str
    timeout: float
    retries: int
    retry_delay: float
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskExecutionPlan:
    pass

class TaskExecutionStateMachine:
    def __init__(self,
                 cursor_controller: CursorInstanceController,
                 feedback_callback: Optional[callable] = None,
                 enable_monitor: bool = True):
        pass

    def _step_to_commands(self, step: TaskStep) -> List[CursorCommand]:
        """Convert a task step to a list of low-level CursorCommands."""
        commands = []
        action = step.action
        params = step.params or {}
        element = step.element
        timeout = step.timeout
        retries = step.retries
        retry_delay = step.retry_delay
        
        if action == "wait_for_element":
            commands.append(CursorCommand(
                "wait", {"element_type": element, "timeout": timeout, "present": True},
                timeout=timeout, retry_count=retries, retry_delay=retry_delay
            ))
        elif action == "wait_for_element_gone":
             commands.append(CursorCommand(
                "wait", {"element_type": element, "timeout": timeout, "present": False},
                timeout=timeout, retry_count=retries, retry_delay=retry_delay
            ))
        elif action == "click":
            commands.append(CursorCommand(
                "click", {"element_type": element},
                timeout=timeout, retry_count=retries, retry_delay=retry_delay
            ))
        elif action == "verify_element":
            commands.append(CursorCommand(
                "wait", {"element_type": element, "timeout": timeout, "present": True},
                timeout=timeout, retry_count=retries, retry_delay=retry_delay
            ))
        elif action == "type_text":
            text_to_type = params.get("text")
            if text_to_type is None:
                 raise ValueError(f"Missing 'text' parameter in params for type_text step")
            commands.append(CursorCommand(
                "type", {"element_type": element, "text": text_to_type},
                timeout=timeout, retry_count=retries, retry_delay=retry_delay 
            ))
        else:
            logger.warning(f"Action type '{action}' might not be directly convertible to low-level commands. Check step definition.")
            
        return commands

    async def execute_step(self, step: TaskStep, instance: CursorInstance) -> bool:
        """Execute a single task step on a specific instance."""
        if not instance:
             logger.error("Cannot execute step: Invalid CursorInstance provided.")
             step.state = StepState.FAILED
             step.result = CommandResult(success=False, message="Invalid instance provided", timestamp=datetime.now(), duration=0)
             return False
             
        instance_id = instance.window.id
        step_info = f"Action: {step.action}, Element: {step.element or 'N/A'}"
        logger.info(f"[{instance_id}] Executing Step: {step_info}")
        
        try:
            step.state = StepState.RUNNING
            step.started_at = datetime.now()
            self._emit_feedback(plan.task_id, "step_started", {"step": step.to_dict(), "instance_id": instance_id})

            commands = self._step_to_commands(step)
            
            results = await self.controller.execute_chain(
                *commands, 
                instance=instance
            )
            
            if results:
                step.result = results[-1]
                success = all(r.success for r in results)
            else:
                success = not step.required 
                step.result = CommandResult(success=success, message=f"No commands generated for action '{step.action}'", timestamp=datetime.now(), duration=0)
                logger.warning(f"[{instance_id}] Step {step_info} generated no commands.")
            
            step.state = StepState.COMPLETED if success else StepState.FAILED
            step.completed_at = datetime.now()
            logger.info(f"[{instance_id}] Step finished with state: {step.state.value}")
            self._emit_feedback(plan.task_id, "step_completed", {"step": step.to_dict(), "instance_id": instance_id})
            
            return success
            
        except Exception as e:
            logger.error(f"[{instance_id}] Step execution failed: {step_info} - {e}", exc_info=True)
            step.state = StepState.FAILED
            step.completed_at = datetime.now()
            error_message = str(e)
            if not step.result or step.result.success:
                step.result = CommandResult(
                    success=False, message=error_message, timestamp=datetime.now(), 
                    duration=(datetime.now() - step.started_at).total_seconds() if step.started_at else 0,
                    error=e
                )
            else:
                step.result.message = f"{step.result.message}; Step Error: {error_message}"
                step.result.success = False
                step.result.error = e
                
            self._emit_feedback(plan.task_id, "step_failed", {"step": step.to_dict(), "instance_id": instance_id})
            return False

    async def execute_plan(self, plan: Union[TaskExecutionPlan, Dict], instance: Optional[CursorInstance] = None) -> TaskExecutionPlan:
        """Executes a full TaskExecutionPlan, assigning an instance if not provided."""
        if isinstance(plan, dict):
             plan = TaskExecutionPlan.from_dict(plan)

        if not self.running:
             logger.warning(f"State machine stopped. Cannot execute plan {plan.task_id}.")
             plan.state = TaskState.CANCELLED
             plan.error_message = "State machine stopped"
             return plan

        assigned_instance = instance
        instance_id = None
        plan.state = TaskState.PREPARING
        plan.started_at = datetime.now()
        self.active_tasks[plan.task_id] = plan
        self._emit_feedback(plan.task_id, "task_started", {"plan": plan.to_dict()})

        try:
            if not assigned_instance:
                logger.info(f"[{plan.task_id}] Acquiring instance...")
                assigned_instance = self.controller.get_available_instance()
                if not assigned_instance:
                    raise RuntimeError("No available Cursor instance for plan execution.")
                logger.info(f"[{plan.task_id}] Assigned to instance: {assigned_instance.window.id}")
            
            instance_id = assigned_instance.window.id
            plan.cursor_instance_id = instance_id
            plan.state = TaskState.RUNNING
            self._emit_feedback(plan.task_id, "task_running", {"instance_id": instance_id})
            
            for step_index, step in enumerate(plan.steps):
                 logger.debug(f"[{instance_id}][{plan.task_id}] Starting step {step_index + 1}/{len(plan.steps)}")
                 step_success = await self.execute_step(step, assigned_instance)
                 
                 if not step_success and step.required:
                      logger.error(f"[{instance_id}][{plan.task_id}] Required step failed. Aborting plan.")
                      plan.state = TaskState.FAILED
                      plan.error_message = f"Required step failed: {step.action} ({step.element or 'N/A'}) - {step.result.message if step.result else 'Unknown reason'}"
                      break
                 elif not step_success:
                      logger.warning(f"[{instance_id}][{plan.task_id}] Optional step failed. Continuing plan.")
                      step.state = StepState.SKIPPED
                      self._emit_feedback(plan.task_id, "step_skipped", {"step": step.to_dict(), "instance_id": instance_id})
            else:
                 logger.info(f"[{instance_id}][{plan.task_id}] All steps processed successfully.")
                 plan.state = TaskState.COMPLETED

        except Exception as e:
            logger.error(f"[{instance_id or 'N/A'}][{plan.task_id}] Plan execution failed: {e}", exc_info=True)
            plan.state = TaskState.FAILED
            plan.error_message = str(e)

        finally:
            plan.completed_at = datetime.now()
            final_event = "task_completed" if plan.state == TaskState.COMPLETED else "task_failed"
            self._emit_feedback(plan.task_id, final_event, {"plan": plan.to_dict(), "instance_id": instance_id})
            self.active_tasks.pop(plan.task_id, None)

        return plan 