# print("--- EXECUTING PLANNER AGENT (TOP) ---", flush=True)  # Removed debug print
import os
import sys
import traceback
import json  # For parsing LLM response
import re    # For parsing LLM response
from dreamforge.core.prompt_staging_service import stage_and_execute_prompt  # Assuming this exists
from dreamforge.core.template_engine import template_engine  # Using the default template engine instance
from dreamforge.core.governance_memory_engine import log_event
from dreamforge.core.llm_parser import extract_json_from_response
from dreamforge.core.governance_memory_engine import GovernanceMemoryEngine  # Corrected path
from dotenv import load_dotenv
from dreamforge.core.llm.llm_api import get_llm_client  # Assuming the implementation exists
import logging # Added
import asyncio # Added
from typing import Dict, List, Optional, Any

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# del sys  # Do not remove sys since it's used for flushing stderr
print(f"Root directory: {project_root}", flush=True)

AGENT_ID = "PlannerAgent"

# Import BaseAgent and AgentBus
from core.coordination.base_agent import BaseAgent
from core.coordination.agent_bus import AgentBus
from core.models.task import Task, TaskStatus # For creating dispatched tasks

class PlannerAgent(BaseAgent):
    """Agent responsible for breaking down goals into actionable task lists.
    Uses BaseAgent for lifecycle, bus communication, and logging.
    """
    
    def __init__(self, agent_id: str, agent_bus: AgentBus, llm_provider: Optional[Any] = None, template_dir: str = "agents/prompts/planner"):
        """Initializes the PlannerAgent."""
        super().__init__(agent_id=agent_id, agent_bus=agent_bus)
        self.llm_parser = LLMParser(llm_provider=llm_provider)
        self.template_engine = TemplateEngine(template_dir=template_dir)
        self.logger.info(f"PlannerAgent initialized with template directory: {template_dir}")
    
    async def _on_start(self):
        await super()._on_start()
        # Register handlers for commands this agent can process
        self.register_command_handler("generate_plan_from_goal", self._handle_generate_plan_command)
        self.register_command_handler("refine_plan", self._handle_refine_plan_command)
        self.logger.info("Registered command handlers for plan generation and refinement.")

    async def _handle_generate_plan_command(self, task: TaskMessage) -> Dict[str, Any]:
        """Handles the 'generate_plan_from_goal' command."""
        goal = task.input_data.get("goal")
        if not goal:
            error_msg = "Missing 'goal' in input_data for generate_plan_from_goal task."
            self.logger.error(f"Task {task.task_id}: {error_msg}")
            return {"status": "error", "error": error_msg}

        self.logger.info(f"Task {task.task_id}: Starting plan generation for goal: '{goal}'")
        try:
            # Generate the plan (list of task dicts)
            plan_tasks_data = await self.plan_from_goal(goal)

            if not plan_tasks_data:
                self.logger.warning(f"Task {task.task_id}: Plan generation resulted in an empty plan for goal: '{goal}'")
                # Return success but indicate no tasks generated?
                return {"status": "success", "message": "Plan generated, but resulted in no tasks.", "data": {"plan_tasks": []}}

            # Dispatch the generated tasks via AgentBus
            dispatched_task_ids = await self._dispatch_plan_tasks(plan_tasks_data, parent_task_id=task.task_id)

            self.logger.info(f"Task {task.task_id}: Successfully generated and dispatched {len(dispatched_task_ids)} plan tasks.")
            # Return success, maybe include dispatched task IDs in result
            return {"status": "success", "data": {"dispatched_task_ids": dispatched_task_ids}}

        except Exception as e:
            error_msg = f"Failed to generate or dispatch plan for task {task.task_id}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {"status": "error", "error": error_msg}

    async def _handle_refine_plan_command(self, task: TaskMessage) -> Dict[str, Any]:
        """Handles the 'refine_plan' command."""
        current_plan_data = task.input_data.get("current_plan")
        refinement_instructions = task.input_data.get("refinement_instructions")

        if not isinstance(current_plan_data, list) or not refinement_instructions:
            error_msg = "Missing or invalid 'current_plan' (list) or 'refinement_instructions' (str) in input_data for refine_plan task."
            self.logger.error(f"Task {task.task_id}: {error_msg}")
            return {"status": "error", "error": error_msg}

        self.logger.info(f"Task {task.task_id}: Starting plan refinement with instructions: '{refinement_instructions}'")
        try:
            # Refine the plan
            refined_plan_tasks_data = await self.refine_plan(current_plan_data, refinement_instructions)

            if not refined_plan_tasks_data:
                self.logger.warning(f"Task {task.task_id}: Plan refinement resulted in an empty plan.")
                return {"status": "success", "message": "Plan refined, but resulted in no tasks.", "data": {"refined_plan_tasks": []}}

            # TODO: Decide how to handle refined tasks. Dispatch them? Return them?
            # For now, just return the refined plan data.
            self.logger.info(f"Task {task.task_id}: Successfully refined plan resulting in {len(refined_plan_tasks_data)} tasks.")
            return {"status": "success", "data": {"refined_plan_tasks": refined_plan_tasks_data}}

        except Exception as e:
            error_msg = f"Failed to refine plan for task {task.task_id}: {e}"
            self.logger.error(error_msg, exc_info=True)
            return {"status": "error", "error": error_msg}

    async def plan_from_goal(self, goal: str) -> list[dict]:
        """
        Internal logic: Takes a goal and generates a structured list of task dictionaries.
        Does NOT dispatch tasks, only returns the data.
        """
        self.logger.info(f"Generating plan internally for goal: '{goal}'")
        plan_tasks_data = []
        try:
            prompt_context = {"goal": goal}
            # TODO: Augment context (available agents, etc.)
            template_name = "generate_plan.j2"
            prompt_text = self.template_engine.render(template_name, prompt_context)

            if not prompt_text:
                self.logger.error(f"Failed to render plan template '{template_name}'")
                return []

            self.logger.debug(f"Sending plan generation request to LLM for goal: '{goal}'")
            llm_response_text = await self.llm_parser.get_response(prompt_text)

            if not llm_response_text:
                self.logger.error(f"No response received from LLM for planning goal: '{goal}'")
                return []

            self.logger.debug("Parsing LLM response for plan.")
            plan_tasks_data = self._parse_llm_plan(llm_response_text)

            if plan_tasks_data:
                self.logger.info(f"LLM generated plan with {len(plan_tasks_data)} tasks for goal: '{goal}'")
            else:
                self.logger.warning(f"Plan parsing failed or resulted in empty plan for goal: '{goal}'. LLM Response: {llm_response_text[:500]}...")

        except Exception as e:
            self.logger.error(f"Error during plan_from_goal for '{goal}': {e}", exc_info=True)
            plan_tasks_data = []  # Return empty plan on error

        return plan_tasks_data

    async def refine_plan(self, current_plan_data: list[dict], refinement_instructions: str) -> list[dict]:
        """
        Internal logic: Refines an existing plan based on instructions.
        Returns the refined list of task dictionaries.
        """
        self.logger.info(f"Refining plan internally based on instructions: '{refinement_instructions}'")
        refined_plan_data = current_plan_data # Default to original
        try:
            prompt_context = {
                "current_plan": json.dumps(current_plan_data, indent=2), # Pass plan as JSON string
                "refinement_instructions": refinement_instructions
            }
            template_name = "refine_plan.j2"
            prompt_text = self.template_engine.render(template_name, prompt_context)

            if not prompt_text:
                self.logger.error(f"Failed to render refinement template '{template_name}'")
                return current_plan_data # Return original plan

            self.logger.debug("Sending plan refinement request to LLM.")
            llm_response_text = await self.llm_parser.get_response(prompt_text)

            if not llm_response_text:
                self.logger.error("No response received from LLM for plan refinement.")
                return current_plan_data # Return original plan

            self.logger.debug("Parsing LLM response for refined plan.")
            parsed_plan_data = self._parse_llm_plan(llm_response_text)

            if parsed_plan_data:
                refined_plan_data = parsed_plan_data
                self.logger.info(f"Plan refined successfully, resulting in {len(refined_plan_data)} tasks.")
            else:
                self.logger.warning(f"Plan refinement parsing failed. LLM Response: {llm_response_text[:500]}...")

        except Exception as e:
            self.logger.error(f"Error during refine_plan: {e}", exc_info=True)

        return refined_plan_data

    def _parse_llm_plan(self, llm_response: str) -> list[dict]:
        """Parses the LLM response (expecting a JSON list of tasks)."""
        self.logger.debug("Attempting to extract JSON task list from LLM response.")
        try:
             parsed_data = self.llm_parser.parse_json_response(llm_response)
        except Exception as e:
             self.logger.error(f"Failed to parse JSON from LLM response: {e}", exc_info=True)
             self.logger.debug(f"LLM Response causing parse error: {llm_response}")
             return []

        if isinstance(parsed_data, list):
            # Basic validation: check if items are dictionaries
            if all(isinstance(item, dict) for item in parsed_data):
                 self.logger.info(f"Successfully parsed plan JSON list with {len(parsed_data)} tasks.")
                 return parsed_data
            else:
                 self.logger.warning(f"Parsed JSON list contains non-dictionary items.")
                 return []
        elif isinstance(parsed_data, dict) and 'tasks' in parsed_data and isinstance(parsed_data['tasks'], list):
             # Handle case where LLM wraps the list in a {"tasks": [...]} object
             self.logger.info(f"Parsed plan JSON list (extracted from 'tasks' key) with {len(parsed_data['tasks'])} tasks.")
             return parsed_data['tasks']
        else:
            self.logger.warning(f"Parsed JSON from LLM is not a list or expected dict format. Type: {type(parsed_data).__name__}")
            return []

    async def _dispatch_plan_tasks(self, tasks_data: list[dict], parent_task_id: Optional[str] = None) -> List[str]:
        """Creates TaskMessage objects and dispatches them via AgentBus."""
        dispatched_task_ids = []
        self.logger.info(f"Dispatching {len(tasks_data)} generated tasks...")
        for task_info in tasks_data:
            try:
                # --- Create TaskMessage --- 
                # Infer target agent or use provided (defaulting to self for now if missing)
                target_agent_id = task_info.get("assigned_to") or task_info.get("agent_id") or self.agent_id # TODO: Improve agent inference
                task_type = task_info.get("task_type") or "execute_task" # Default task type
                input_data = task_info # Pass the whole original task dict as input for now
                # Could extract specific fields like description, params, etc.
                input_data["description"] = task_info.get("description", "N/A")

                new_task_msg = create_task_message(
                    task_type=task_type,
                    agent_id=target_agent_id,
                    input_data=input_data,
                    source_agent_id=self.agent_id,
                    parent_task_id=parent_task_id,
                    # priority=TaskPriority(task_info.get("priority", "normal")), # Add priority parsing if needed
                    metadata=task_info.get("metadata", {})
                )

                # --- Publish Command via Bus --- 
                command_topic = f"agent.{target_agent_id}.command"
                message = {
                    "sender_id": self.agent_id,
                    "correlation_id": new_task_msg.correlation_id,
                    "data": new_task_msg.to_dict()
                }
                await self.agent_bus.publish(command_topic, message)
                self.logger.info(f"Dispatched task {new_task_msg.task_id} ({task_type}) to agent '{target_agent_id}' on topic '{command_topic}'")
                dispatched_task_ids.append(new_task_msg.task_id)

            except Exception as e:
                self.logger.error(f"Failed to create or dispatch task from data {task_info}: {e}", exc_info=True)
                # Continue dispatching other tasks
        return dispatched_task_ids

# --- Example Execution (Updated) ---
if __name__ == "__main__":
    # Setup basic logging for the test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main_logger = logging.getLogger("__main__")

    main_logger.info("--- Testing PlannerAgent --- START ---")

    # Mock AgentBus
    class MockAgentBus:
        def __init__(self):
            self.published_messages = []
            self.logger = logging.getLogger("MockAgentBus")

        async def subscribe(self, topic, handler):
            self.logger.info(f"(Mock) Subscribed to {topic}")
            return f"sub_{topic}"

        async def publish(self, topic, message):
            self.published_messages.append((topic, message))
            self.logger.info(f"(Mock) Published to {topic}: {json.dumps(message, indent=2)}")

        async def unsubscribe(self, sub_id):
             self.logger.info(f"(Mock) Unsubscribed from {sub_id}")

        async def start(self): self.logger.info("(Mock) Start called")
        async def stop(self): self.logger.info("(Mock) Stop called")
        async def shutdown(self): self.logger.info("(Mock) Shutdown called")

    # Mock LLM Client/Provider (simple version)
    class MockLLMProvider:
        async def get_llm_response(self, prompt: str) -> str:
            # Simulate LLM response based on prompt content
            if "fetch the current weather" in prompt:
                # Simulate a plan response for the weather goal
                mock_plan = [
                    {"task_id": "TASK-001", "description": "Find a reliable weather API (e.g., OpenWeatherMap)", "status": "Pending", "dependencies": [], "estimated_time": "30m", "assigned_to": "research_agent"},
                    {"task_id": "TASK-002", "description": "Get API key for the chosen weather API", "status": "Pending", "dependencies": ["TASK-001"], "estimated_time": "15m", "assigned_to": "developer_agent"},
                    {"task_id": "TASK-003", "description": "Write Python script using requests library to call API with key and location", "status": "Pending", "dependencies": ["TASK-002"], "estimated_time": "1h", "assigned_to": "developer_agent"},
                    {"task_id": "TASK-004", "description": "Parse the API response to extract relevant weather info (temperature, description)", "status": "Pending", "dependencies": ["TASK-003"], "estimated_time": "30m", "assigned_to": "developer_agent"},
                    {"task_id": "TASK-005", "description": "Print the extracted weather information to the console", "status": "Pending", "dependencies": ["TASK-004"], "estimated_time": "5m", "assigned_to": "developer_agent"}
                ]
                return json.dumps(mock_plan) # Return plan as JSON string
            elif "refine the plan" in prompt:
                # Simulate a refined plan response
                 mock_refined_plan = [
                     {"task_id": "TASK-R1", "description": "Research weather APIs focusing on free tiers", "status": "Pending"},
                     {"task_id": "TASK-R2", "description": "Implement API call with error handling", "status": "Pending"},
                     {"task_id": "TASK-R3", "description": "Add function to format weather output nicely", "status": "Pending"}
                 ]
                 return json.dumps(mock_refined_plan)
            else:
                return "[]" # Default empty plan

    async def run_test():
        mock_bus = MockAgentBus()
        mock_llm = MockLLMProvider()
        planner_agent_id = "planner_test_01"
        # Adjust template path if needed, assuming it's relative to agents dir
        template_path = os.path.join(os.path.dirname(__file__), 'prompts', 'planner')
        if not os.path.isdir(template_path):
             main_logger.warning(f"Template directory not found at {template_path}, using default 'agents/prompts/planner'")
             template_path = "agents/prompts/planner"

        planner = PlannerAgent(agent_id=planner_agent_id, agent_bus=mock_bus, llm_provider=mock_llm, template_dir=template_path)

        try:
            await planner.start() # Register handlers

            # Simulate receiving a task to generate a plan
            goal = "Write a short python script to fetch the current weather for London, UK, and print it."
            generate_task_msg = create_task_message(
                 task_type="generate_plan_from_goal",
                 agent_id=planner_agent_id,
                 input_data={"goal": goal},
                 source_agent_id="supervisor"
            )
            main_logger.info(f"\nSimulating command task: {generate_task_msg.task_id} (generate_plan_from_goal)")
            # Directly call the handler as BaseAgent would
            handler_result = await planner._handle_generate_plan_command(generate_task_msg)
            main_logger.info(f"Handler result: {handler_result}")

            # Check if tasks were published
            dispatched_count = 0
            for topic, msg in mock_bus.published_messages:
                if topic.startswith("agent.") and topic.endswith(".command"):
                    dispatched_count += 1
            main_logger.info(f"Found {dispatched_count} dispatched task commands on mock bus.")
            assert dispatched_count > 0, "Expected planner to dispatch generated tasks."
            assert handler_result["status"] == "success"

            # Simulate receiving a task to refine a plan
            # (Assuming initial plan was generated and we want to refine it)
            # refine_task_msg = ...
            # await planner._handle_refine_plan_command(refine_task_msg)
            # ... add checks for refinement ...

        except Exception as e:
            main_logger.error(f"An error occurred during the test: {e}", exc_info=True)
        finally:
            main_logger.info("Stopping planner agent...")
            await planner.stop()

    # Run the async test function
    try:
         asyncio.run(run_test())
    except Exception as e:
         main_logger.critical(f"Top-level exception in test runner: {e}", exc_info=True)

    main_logger.info("--- PlannerAgent Test Complete --- END ---")
