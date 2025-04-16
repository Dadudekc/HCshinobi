"""Cursor dispatcher agent for handling cursor-related tasks."""
import os
import sys
import json
import random
import asyncio
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid

from dreamforge.core.coordination.base_agent import BaseAgent
from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType, BusError
from dreamforge.core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
from dreamforge.core.utils.performance_logger import PerformanceLogger
from dreamforge.core.memory.governance_memory_engine import log_event

# --- Configuration ---
AGENT_ID = "CursorDispatcher"
POLL_INTERVAL_SECONDS = 5

class CursorDispatcher(BaseAgent):
    """Cursor dispatcher agent for handling cursor-related tasks."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the cursor dispatcher."""
        super().__init__(config)
        self._running = False
        self.perf_logger = PerformanceLogger(AGENT_ID)
        
    async def start(self):
        """Start the cursor dispatcher agent."""
        try:
            await super().start()
            self._running = True
            log_event("AGENT_START", AGENT_ID, {"message": "Cursor Dispatcher agent started"})
            
            # Subscribe to command messages
            await self.bus.subscribe(
                MessageType.COMMAND,
                self._handle_command,
                lambda msg: msg.target == "cursor"
            )
            
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Failed to start Cursor Dispatcher",
                "details": str(e),
                "traceback": traceback.format_exc()
            })
            raise
            
    async def stop(self):
        """Stop the cursor dispatcher agent."""
        try:
            self._running = False
            await super().stop()
            log_event("AGENT_STOP", AGENT_ID, {"message": "Cursor Dispatcher agent stopped"})
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Error stopping Cursor Dispatcher",
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
                    task_type=command_data.get("action", "execute_command"),
                    priority=TaskPriority.NORMAL,
                    input_data=command_data
                )
                
                # Process the command based on action type
                if task.task_type == "generate_code":
                    result = await self._handle_generate_code(task)
                elif task.task_type == "edit_file":
                    result = await self._handle_edit_file(task)
                else:
                    result = await self._handle_execute_command(task)
                
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
                error_msg = f"Failed to process cursor command: {str(e)}"
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

    async def _handle_generate_code(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle code generation tasks."""
        with self.perf_logger.track_operation("generate_code", {"task_id": task.task_id}):
            try:
                log_event("CURSOR_TASK_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "generate_code",
                    "prompt": task.input_data.get("prompt", "")
                })
                
                # Simulate code generation
                await asyncio.sleep(random.uniform(0.5, 2))  # Simulated processing time
                
                if "fail" in task.input_data.get("prompt", "").lower():
                    raise ValueError("Simulated failure in code generation")
                    
                generated_code = f"def generated_function():\n    # Code generated for task {task.task_id}\n    print('Hello from generated code!')\n    return True"
                
                log_event("CURSOR_TASK_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "generate_code",
                    "status": "success"
                })
                
                return {
                    "status": "success",
                    "code_generated": generated_code
                }
                
            except Exception as e:
                log_event("CURSOR_TASK_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "generate_code",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _handle_edit_file(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle file editing tasks."""
        with self.perf_logger.track_operation("edit_file", {"task_id": task.task_id}):
            try:
                target_file = task.input_data.get("target_file", "")
                log_event("CURSOR_TASK_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "edit_file",
                    "target_file": target_file
                })
                
                # Simulate file editing
                await asyncio.sleep(random.uniform(0.5, 2))  # Simulated processing time
                
                log_event("CURSOR_TASK_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "edit_file",
                    "target_file": target_file,
                    "status": "success"
                })
                
                return {
                    "status": "success",
                    "file_edited": target_file,
                    "changes_applied": True
                }
                
            except Exception as e:
                log_event("CURSOR_TASK_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "edit_file",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _handle_execute_command(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle generic command execution tasks."""
        with self.perf_logger.track_operation("execute_command", {"task_id": task.task_id}):
            try:
                log_event("CURSOR_TASK_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "execute_command",
                    "command": task.input_data
                })
                
                # Simulate command execution
                await asyncio.sleep(random.uniform(0.5, 2))  # Simulated processing time
                
                log_event("CURSOR_TASK_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "execute_command",
                    "status": "success"
                })
                
                return {
                    "status": "success",
                    "output": "Command executed successfully (simulated)."
                }
                
            except Exception as e:
                log_event("CURSOR_TASK_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "action": "execute_command",
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

# --- Run Agent ---
async def main():
    """Run the Cursor Dispatcher agent."""
    try:
        config = {
            "agent_id": AGENT_ID
        }
        
        agent = CursorDispatcher(config)
        await agent.start()
        
        # Keep the agent running
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        log_event("AGENT_INFO", AGENT_ID, {"message": "Shutting down on user request"})
    except Exception as e:
        log_event("AGENT_FATAL", AGENT_ID, {
            "error": "Fatal error in Cursor Dispatcher",
            "details": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        if agent:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())