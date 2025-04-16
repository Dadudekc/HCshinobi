"""Workflow agent for Dream.OS."""
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
from dreamforge.core.prompt_staging_service import stage_and_execute_prompt
from dreamforge.core.template_engine import default_template_engine as template_engine
from dreamforge.core.utils.performance_logger import PerformanceLogger
from dreamforge.core.memory.governance_memory_engine import log_event
from dreamforge.core.llm_parser import extract_json_from_response

# --- Configuration ---
AGENT_ID = "WorkflowAgent"
WORKFLOW_STORAGE_DIR = config.WORKFLOW_STORAGE_DIR

def _get_value_from_context(var_path_str: str, context: dict):
    """Safely retrieves a value from nested context using dot notation."""
    parts = var_path_str.split('.')
    current_val = context
    for i, part in enumerate(parts):
        if isinstance(current_val, dict):
            if part not in current_val:
                 joined_path = ".".join(parts[:i+1])
                 raise KeyError(f"Variable '{joined_path}' not found (part '{part}' missing in dict)")
            current_val = current_val[part]
        else:
            joined_path = ".".join(parts[:i+1])
            raise KeyError(f"Cannot access part '{part}' in non-dict value for path '{joined_path}'")
    return current_val

class WorkflowAgent(BaseAgent):
    """Agent responsible for managing and executing workflows."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the workflow agent."""
        super().__init__(config)
        self.memory_manager = config.get('memory_manager') or MemoryManager(config.MEMORY_DIR)
        self.current_workflow = None
        self._running = False
        self.perf_logger = PerformanceLogger(AGENT_ID)
        
    async def start(self):
        """Start the workflow agent."""
        try:
            await super().start()
            self._running = True
            log_event("AGENT_START", AGENT_ID, {"message": "Workflow agent started"})
            
            # Subscribe to command messages
            await self.bus.subscribe(
                MessageType.COMMAND,
                self._handle_command,
                lambda msg: msg.target == "workflow"
            )
            
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Failed to start Workflow Agent",
                "details": str(e),
                "traceback": traceback.format_exc()
            })
            raise
            
    async def stop(self):
        """Stop the workflow agent."""
        try:
            self._running = False
            await super().stop()
            log_event("AGENT_STOP", AGENT_ID, {"message": "Workflow agent stopped"})
        except Exception as e:
            log_event("AGENT_ERROR", AGENT_ID, {
                "error": "Error stopping Workflow Agent",
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
                    task_type=command_data.get("action", "execute_workflow"),
                    priority=TaskPriority.NORMAL,
                    input_data=command_data
                )
                
                # Process the command based on action type
                if task.task_type == "generate_workflow":
                    result = await self._handle_generate_workflow(task)
                elif task.task_type == "execute_workflow":
                    result = await self._handle_execute_workflow(task)
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
                error_msg = f"Failed to process workflow command: {str(e)}"
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

    async def _handle_generate_workflow(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle workflow generation tasks."""
        with self.perf_logger.track_operation("generate_workflow", {"task_id": task.task_id}):
            try:
                prompt = task.input_data.get("prompt")
                if not prompt:
                    raise ValueError("No prompt provided for workflow generation")
                
                log_event("WORKFLOW_GENERATION_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "prompt_length": len(prompt)
                })
                
                # Stage and execute prompt
                prompt_context = {"user_prompt": prompt}
                template_path = "agents/prompts/workflow/generate_workflow.j2"
                prompt_text = template_engine.render(template_path, prompt_context)
                
                if not prompt_text:
                    raise ValueError("Failed to render workflow generation template")
                
                # Execute LLM prompt
                llm_response = await stage_and_execute_prompt(
                    prompt_text,
                    agent_id=self.agent_id,
                    purpose="generate_workflow"
                )
                
                if not llm_response:
                    raise ValueError("No response received from LLM for workflow generation")
                
                # Parse response
                workflow_definition = self._parse_llm_workflow(llm_response)
                if not workflow_definition:
                    raise ValueError("Failed to parse workflow from LLM response")
                
                # Save workflow
                if not await self.save_workflow(workflow_definition):
                    raise ValueError("Failed to save generated workflow")
                
                log_event("WORKFLOW_GENERATION_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "workflow_id": workflow_definition.get("workflow_id")
                })
                
                return {
                    "status": "success",
                    "workflow": workflow_definition
                }
                
            except Exception as e:
                log_event("WORKFLOW_GENERATION_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def _handle_execute_workflow(self, task: TaskMessage) -> Dict[str, Any]:
        """Handle workflow execution tasks."""
        with self.perf_logger.track_operation("execute_workflow", {"task_id": task.task_id}):
            try:
                workflow_id = task.input_data.get("workflow_id")
                inputs = task.input_data.get("inputs", {})
                
                if not workflow_id:
                    raise ValueError("No workflow_id provided for execution")
                
                log_event("WORKFLOW_EXECUTION_START", AGENT_ID, {
                    "task_id": task.task_id,
                    "workflow_id": workflow_id,
                    "input_keys": list(inputs.keys())
                })
                
                # Load workflow
                workflow_def = await self.load_workflow(workflow_id)
                if not workflow_def:
                    raise ValueError(f"Workflow definition '{workflow_id}' not found")
                
                # Initialize execution context
                step_outputs = {'input': inputs}
                steps = sorted(
                    workflow_def.get('steps', []),
                    key=lambda x: x.get('step_id', float('inf'))
                )
                
                # Execute steps
                for step in steps:
                    step_id = step.get('step_id')
                    step_name = step.get('name', f'Step {step_id}')
                    target_agent = step.get('agent')
                    command = step.get('command')
                    raw_params = step.get('params', {})
                    output_var = step.get('output_var')
                    
                    if not target_agent or not command:
                        raise ValueError(f"Invalid step definition in step {step_id}")
                    
                    # Interpolate parameters
                    try:
                        params = self._interpolate_params(raw_params, step_outputs)
                    except Exception as e:
                        raise ValueError(f"Parameter interpolation failed for step {step_id}: {str(e)}")
                    
                    # Execute step
                    step_result = await self.bus.publish(Message(
                        type=MessageType.COMMAND,
                        sender=self.agent_id,
                        target=target_agent,
                        content={
                            "command": command,
                            "params": params
                        }
                    ))
                    
                    # Store output if needed
                    if output_var:
                        step_outputs[output_var] = step_result.get('result')
                    
                    log_event("WORKFLOW_STEP_COMPLETE", AGENT_ID, {
                        "task_id": task.task_id,
                        "workflow_id": workflow_id,
                        "step_id": step_id,
                        "step_name": step_name
                    })
                
                log_event("WORKFLOW_EXECUTION_COMPLETE", AGENT_ID, {
                    "task_id": task.task_id,
                    "workflow_id": workflow_id
                })
                
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "outputs": step_outputs
                }
                
            except Exception as e:
                log_event("WORKFLOW_EXECUTION_ERROR", AGENT_ID, {
                    "task_id": task.task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                raise

    async def save_workflow(self, workflow_definition: dict) -> bool:
        """Save a workflow definition to storage."""
        with self.perf_logger.track_operation("save_workflow"):
            try:
                if not os.path.exists(WORKFLOW_STORAGE_DIR):
                    os.makedirs(WORKFLOW_STORAGE_DIR)
                
                workflow_id = workflow_definition.get('workflow_id')
                if not workflow_id:
                    workflow_id = str(uuid.uuid4())
                    workflow_definition['workflow_id'] = workflow_id
                
                filepath = os.path.join(WORKFLOW_STORAGE_DIR, f"{workflow_id}.json")
                with open(filepath, 'w') as f:
                    json.dump(workflow_definition, f, indent=2)
                
                log_event("WORKFLOW_SAVED", AGENT_ID, {
                    "workflow_id": workflow_id,
                    "filepath": filepath
                })
                
                return True
                
            except Exception as e:
                log_event("WORKFLOW_SAVE_ERROR", AGENT_ID, {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                return False

    async def load_workflow(self, workflow_id: str) -> Optional[dict]:
        """Load a workflow definition from storage."""
        with self.perf_logger.track_operation("load_workflow", {"workflow_id": workflow_id}):
            try:
                filepath = os.path.join(WORKFLOW_STORAGE_DIR, f"{workflow_id}.json")
                if not os.path.exists(filepath):
                    log_event("WORKFLOW_NOT_FOUND", AGENT_ID, {
                        "workflow_id": workflow_id,
                        "filepath": filepath
                    })
                    return None
                
                with open(filepath, 'r') as f:
                    workflow_def = json.load(f)
                
                log_event("WORKFLOW_LOADED", AGENT_ID, {
                    "workflow_id": workflow_id
                })
                
                return workflow_def
                
            except Exception as e:
                log_event("WORKFLOW_LOAD_ERROR", AGENT_ID, {
                    "workflow_id": workflow_id,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                return None

    def _parse_llm_workflow(self, llm_response: str) -> Optional[dict]:
        """Parse LLM response into a workflow definition."""
        try:
            workflow_json = extract_json_from_response(llm_response)
            if not workflow_json:
                raise ValueError("No JSON found in LLM response")
            
            # Validate required fields
            required_fields = ['name', 'description', 'steps']
            for field in required_fields:
                if field not in workflow_json:
                    raise ValueError(f"Missing required field '{field}' in workflow definition")
            
            return workflow_json
            
        except Exception as e:
            log_event("WORKFLOW_PARSE_ERROR", AGENT_ID, {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "llm_response": llm_response[:500]  # Log first 500 chars only
            })
            return None

    def _interpolate_params(self, raw_params: dict | list | str, context: dict) -> dict | list | str:
        """Interpolate parameters using context values."""
        def _recursive_render(item):
            if isinstance(item, str):
                try:
                    # Handle direct variable references
                    if item.startswith('$'):
                        var_path = item[1:]
                        return _get_value_from_context(var_path, context)
                    # Handle template strings
                    template = template_engine.from_string(item)
                    return template.render(context)
                except Exception as e:
                    raise ValueError(f"Parameter interpolation failed: {str(e)}")
            elif isinstance(item, dict):
                return {k: _recursive_render(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [_recursive_render(v) for v in item]
            return item
            
        return _recursive_render(raw_params)

# --- Run Agent ---
async def main():
    """Run the Workflow agent."""
    try:
        config = {
            "agent_id": AGENT_ID,
            "memory_manager": MemoryManager(config.MEMORY_DIR)
        }
        
        agent = WorkflowAgent(config)
        await agent.start()
        
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        log_event("AGENT_INFO", AGENT_ID, {"message": "Shutting down on user request"})
    except Exception as e:
        log_event("AGENT_FATAL", AGENT_ID, {
            "error": "Fatal error in Workflow Agent",
            "details": str(e),
            "traceback": traceback.format_exc()
        })
    finally:
        if agent:
            await agent.stop()

if __name__ == "__main__":
    asyncio.run(main()) 