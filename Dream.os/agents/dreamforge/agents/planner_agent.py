"""Planning agent for Dream.OS."""
import asyncio
import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from dreamforge.core import config
from dreamforge.core.memory.memory_manager import MemoryManager
from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType, BusError
from dreamforge.core.coordination.base_agent import BaseAgent
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
from dreamforge.core.utils.performance_logger import PerformanceLogger
from dreamforge.core.memory.governance_memory_engine import log_event

# --- Configuration ---
AGENT_ID = "PlannerAgent"
PLAN_STORAGE_DIR = os.path.join(config.MEMORY_DIR, "plans")

class PlannerAgent(BaseAgent):
    """Agent responsible for planning and coordinating tasks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the planner agent."""
        super().__init__(config)
        self.memory_manager = config.get('memory_manager') or MemoryManager(config.MEMORY_DIR)
        self.current_plan = None
        self._running = False
        self.perf_logger = PerformanceLogger(AGENT_ID)
        
    async def start(self):
        """Start the planner agent."""
        try:
            await super().start()
            self._running = True
            log_event("AGENT_START", AGENT_ID, {"message": "Planner agent started"})
            
            # Subscribe to command messages
            await self.bus.subscribe(
                MessageType.COMMAND,
                self._handle_command,
                lambda msg: msg.target == "planner"
            )
            
            # Create storage directory if needed
            os.makedirs(PLAN_STORAGE_DIR, exist_ok=True)
            
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Failed to start Planner Agent",
                "details": str(e),
                "traceback": traceback.format_exc()
            })
            raise
            
    async def stop(self):
        """Stop the planner agent."""
        try:
            self._running = False
            await super().stop()
            log_event("AGENT_STOP", AGENT_ID, {"message": "Planner agent stopped"})
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Error stopping Planner Agent",
                "details": str(e),
                "traceback": traceback.format_exc()
            })
            raise

    async def _handle_command(self, message: Message):
        """Handle incoming command messages."""
        task_id = str(uuid.uuid4())
        with self.perf_logger.track_operation("handle_command", {"task_id": task_id}):
            try:
                command_data = message.content
                log_event("AGENT_COMMAND", AGENT_ID, {
                    "task_id": task_id,
                    "command": command_data
                })
                
                # Create task message
                task = create_task_message(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    task_type=command_data.get("action", "generate_plan"),
                    priority=TaskPriority.NORMAL,
                    input_data=command_data
                )
                
                # Process the command based on action type
                if task.task_type == "generate_plan":
                    result = await self._handle_generate_plan(task)
                elif task.task_type == "update_plan":
                    result = await self._handle_update_plan(task)
                elif task.task_type == "update_step":
                    result = await self._handle_update_step(task)
                else:
                    raise ValueError(f"Unknown task type: {task.task_type}")
                
                # Update task with result
                task = update_task_status(task, TaskStatus.COMPLETED, result=result)
                
                # Send response
                await self.bus.publish(Message(
                    type=MessageType.RESPONSE,
                    sender=self.agent_id,
                    content=task.to_dict(),
                    correlation_id=message.correlation_id
                ))
                
            except Exception as e:
                error_msg = f"Failed to process planner command: {str(e)}"
                log_event("AGENT_ERROR", AGENT_ID, {
                    "task_id": task_id,
                    "error": error_msg,
                    "traceback": traceback.format_exc()
                })
                
                # Update task with error
                task = update_task_status(task, TaskStatus.FAILED, error=error_msg)
                
                # Send error message
                await self.bus.publish(Message(
                    type=MessageType.ERROR,
                    sender=self.agent_id,
                    content=task.to_dict(),
                    correlation_id=message.correlation_id
                ))

    async def _handle_generate_plan(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle plan generation tasks."""
        with self.perf_logger.track_operation("generate_plan", {"task_id": task.task_id}):
            try:
                context = task.input_data.get("context", {})
                if not context:
                    raise ValueError("No context provided for plan generation")
                
                log_event("PLAN_GENERATION_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "goals": context.get("goals", [])
                })
                
                # Create plan
                plan = await self._create_plan(context)
                
                # Store plan
                await self._store_plan(plan)
                self.current_plan = plan
                
                log_event("PLAN_GENERATION_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "plan_id": plan["id"]
                })
                
                return {
                    "status": "success",
                    "plan": plan
                }
                
            except Exception as e:
                log_event("PLAN_GENERATION_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _handle_update_plan(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle plan update tasks."""
        with self.perf_logger.track_operation("update_plan", {"task_id": task.task_id}):
            try:
                status = task.input_data.get("status")
                if not status:
                    raise ValueError("No status provided for plan update")
                
                if not self.current_plan:
                    raise ValueError("No active plan to update")
                
                log_event("PLAN_UPDATE_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "plan_id": self.current_plan["id"],
                    "new_status": status
                })
                
                # Update plan
                self.current_plan["status"] = status
                self.current_plan["updated_at"] = datetime.now(timezone.utc).isoformat()
                
                # Store updated plan
                await self._store_plan(self.current_plan)
                
                log_event("PLAN_UPDATE_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "plan_id": self.current_plan["id"]
                })
                
                return {
                    "status": "success",
                    "plan": self.current_plan
                }
                
            except Exception as e:
                log_event("PLAN_UPDATE_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _handle_update_step(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle step update tasks."""
        with self.perf_logger.track_operation("update_step", {"task_id": task.task_id}):
            try:
                step_id = task.input_data.get("step_id")
                status = task.input_data.get("status")
                
                if not step_id or not status:
                    raise ValueError("Missing step_id or status for step update")
                
                if not self.current_plan:
                    raise ValueError("No active plan to update")
                
                log_event("STEP_UPDATE_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "plan_id": self.current_plan["id"],
                    "step_id": step_id,
                    "new_status": status
                })
                
                # Update step
                step_updated = False
                for step in self.current_plan["steps"]:
                    if step["id"] == step_id:
                        step["status"] = status
                        step["updated_at"] = datetime.now(timezone.utc).isoformat()
                        step_updated = True
                        break
                
                if not step_updated:
                    raise ValueError(f"Step {step_id} not found in current plan")
                
                # Store updated plan
                await self._store_plan(self.current_plan)
                
                log_event("STEP_UPDATE_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "plan_id": self.current_plan["id"],
                    "step_id": step_id
                })
                
                return {
                    "status": "success",
                    "plan": self.current_plan,
                    "updated_step": step_id
                }
                
            except Exception as e:
                log_event("STEP_UPDATE_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _create_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan from context."""
        with self.perf_logger.track_operation("create_plan"):
            # Extract goals and constraints
            goals = context.get("goals", [])
            constraints = context.get("constraints", {})
            
            # Generate plan structure
            plan = {
                "id": str(uuid.uuid4()),
                "goals": goals,
                "constraints": constraints,
                "steps": await self._generate_steps(goals, constraints),
                "status": "created",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            return plan

    async def _generate_steps(self, goals: List[str], constraints: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate plan steps to achieve goals within constraints."""
        with self.perf_logger.track_operation("generate_steps"):
            steps = []
            
            for goal in goals:
                step = {
                    "id": str(uuid.uuid4()),
                    "goal": goal,
                    "status": "pending",
                    "dependencies": [],
                    "estimated_duration": self._estimate_duration(goal),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                steps.append(step)
                
            return steps

    def _estimate_duration(self, goal: str) -> int:
        """Estimate duration for a goal in minutes."""
        # Simple estimation logic - can be enhanced
        return 30  # Default 30 minutes

    async def _store_plan(self, plan: Dict[str, Any]) -> None:
        """Store plan in memory manager and file system."""
        with self.perf_logger.track_operation("store_plan", {"plan_id": plan["id"]}):
            try:
                # Store in memory manager
                self.memory_manager.store_feedback({
                    "type": "plan",
                    "content": plan,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Store in file system
                filepath = os.path.join(PLAN_STORAGE_DIR, f"{plan['id']}.json")
                with open(filepath, 'w') as f:
                    json.dump(plan, f, indent=2)
                
                log_event("PLAN_SAVED", AGENT_ID, {
                    "plan_id": plan["id"],
                    "filepath": filepath
                })
                
            except Exception as e:
                log_event("PLAN_SAVE_ERROR", AGENT_ID, {
                    "plan_id": plan["id"],
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

# --- Run Agent ---
async def main():
    """Run the Planner agent."""
    try:
        config = {
            "agent_id": AGENT_ID,
            "memory_manager": MemoryManager(config.MEMORY_DIR)
        }
        
        agent = PlannerAgent(config)
        await agent.start()
        
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        log_event("AGENT_INFO", AGENT_ID, {"message": "Shutting down on user request"})
    except Exception as e:
        log_event("AGENT_FATAL", AGENT_ID, {
            "error": "Fatal error in Planner Agent",
            "details": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        if agent:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 