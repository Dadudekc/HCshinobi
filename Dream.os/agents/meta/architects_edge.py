import os
# import sys # Removed
import json
import logging # Add logger import
from typing import Dict, List, Optional, Any

# Remove sys.path manipulation
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# sys.path.insert(0, project_root)

# Update core imports to use absolute paths
from core.coordination.agent_bus import AgentBus
from core.llm_parser import LLMParser
from core.template_engine import TemplateEngine
from core.models.task import Task, TaskStatus

# Import the now refactored BaseAgent
from core.coordination.base_agent import BaseAgent # Path confirmed

# Agent-specific imports (keep relative if they are within the same agent module)
# from agents.prompts.architects_edge import interpret_directive_j2 # Assuming prompts are handled differently or paths updated

# Inherit from BaseAgent
class ArchitectsEdgeAgent(BaseAgent):
    """
    Interprets high-level directives and dispatches tasks to specialized agents.
    Uses BaseAgent for core lifecycle and bus interaction.
    """
    # Update __init__ to call super
    def __init__(self, agent_id: str, agent_bus: AgentBus, template_dir: str = "agents/prompts/architects_edge", llm_provider: Optional[Any] = None):
        # Call BaseAgent's __init__ first
        super().__init__(agent_id=agent_id, agent_bus=agent_bus)
        # self.agent_id = agent_id # Handled by BaseAgent
        # self.agent_bus = agent_bus # Handled by BaseAgent
        self.llm_parser = LLMParser(llm_provider)
        self.template_engine = TemplateEngine(template_dir)
        # self.capabilities.append(self.interpret_directive) # Placeholder for capability registration - revisit
        # Register handler via BaseAgent if appropriate
        # self.register_command_handler("interpret_directive", self._interpret_directive_command) # Example if directive comes as command
        # Or, subscribe to a specific topic if directives come differently
        # self.logger = logging.getLogger(agent_id) # Handled by BaseAgent

    # Override _on_start to subscribe to custom topics if needed
    async def _on_start(self):
        """Agent-specific startup logic. Subscribe to directive topic."""
        await super()._on_start() # Call base class method first
        directive_topic = f"directive.{self.agent_id}" # Example topic
        try:
            # Assuming AgentBus.subscribe takes topic and async handler
            await self.agent_bus.subscribe(directive_topic, self.handle_directive_message)
            self.logger.info(f"Subscribed to directive topic: {directive_topic}")
        except Exception as e:
            self.logger.error(f"Failed to subscribe to directive topic {directive_topic}: {e}", exc_info=True)

    # Assuming directives arrive via subscribed topic, not BaseAgent commands
    async def handle_directive_message(self, topic: str, message: Dict[str, Any]):
        """Handles incoming directive messages from the AgentBus subscription."""
        directive = message.get("data", {}).get("directive")
        correlation_id = message.get("correlation_id") # Track for potential response
        self.logger.info(f"Received directive on topic '{topic}': '{directive}' (CorrID: {correlation_id})")
        if directive:
            # Call the internal logic
            interpretation_result = await self._interpret_directive(directive)
            # TODO: Decide how to respond - maybe publish interpretation result?
            # Example: Publish result to a response topic or the correlation topic
            if correlation_id:
                 response_topic = f"system.response.{correlation_id}"
                 response_message = {
                     "sender_id": self.agent_id,
                     "correlation_id": correlation_id,
                     "data": interpretation_result
                 }
                 try:
                     await self.agent_bus.publish(response_topic, response_message)
                     self.logger.info(f"Published interpretation result to {response_topic}")
                 except Exception as e:
                     self.logger.error(f"Failed to publish interpretation result: {e}", exc_info=True)
            else:
                 self.logger.warning("No correlation ID found for directive, cannot send direct response.")

        else:
            self.logger.warning("Received invalid/empty directive message.")

    # This method might be deprecated if directives handled via subscription
    # Or could be adapted as a command handler if registered with BaseAgent
    # @BaseAgent.capability() # Decorator might change with BaseAgent update
    async def interpret_directive(self, directive: str) -> Dict[str, Any]:
        """
        Public method to interpret a directive (potentially callable via RPC or other means).
        Actual logic is in _interpret_directive.
        """
        self.logger.info(f"Interpreting directive via public method: '{directive}'")
        return await self._interpret_directive(directive)

    # Rename core logic method to indicate it's internal (already done)
    async def _interpret_directive(self, directive: str) -> Dict[str, Any]:
        """Internal logic for interpreting directives and dispatching tasks."""
        self.logger.debug(f"Starting internal interpretation for: '{directive}'")
        # Load the prompt template
        try:
            prompt_content = self.template_engine.load_template("interpret_directive.j2")
        except Exception as e:
            self.logger.error(f"Failed to load template 'interpret_directive.j2': {e}", exc_info=True)
            return {"interpretation": f"Error: Failed to load template - {e}", "dispatched_tasks": []}

        # Prepare context for the template
        available_agents = await self._get_available_agents()
        context = {
            "directive": directive,
            "available_agents": available_agents
        }
        self.logger.debug(f"Rendering template with context: {context}")

        # Render the prompt
        try:
            rendered_prompt = self.template_engine.render_template_from_string(prompt_content, context)
        except Exception as e:
            self.logger.error(f"Failed to render directive template: {e}", exc_info=True)
            return {"interpretation": f"Error: Failed to render template - {e}", "dispatched_tasks": []}

        # Use LLMParser to get structured output
        try:
            parsed_response = await self.llm_parser.parse_response(rendered_prompt)
            self.logger.info(f"LLM interpretation received: {json.dumps(parsed_response, indent=2)}")

            # Validate structure
            if not isinstance(parsed_response, dict) or "tasks" not in parsed_response:
                 self.logger.error("LLM response format invalid. Expected dict with 'tasks'.")
                 return {"interpretation": "Error in LLM response format.", "dispatched_tasks": []}

            # Dispatch tasks based on the interpretation
            tasks_to_dispatch = parsed_response.get("tasks", [])
            if not isinstance(tasks_to_dispatch, list):
                 self.logger.error(f"LLM response format invalid. 'tasks' field is not a list: {tasks_to_dispatch}")
                 return {"interpretation": "Error in LLM response format (tasks not a list).", "dispatched_tasks": []}

            dispatched_tasks_info = await self._dispatch_tasks(tasks_to_dispatch)

            return {
                "interpretation": parsed_response.get("interpretation", "No interpretation provided."),
                "dispatched_tasks": dispatched_tasks_info
            }
        except Exception as e:
            self.logger.error(f"Error during LLM parsing or task dispatch: {e}", exc_info=True)
            return {"interpretation": f"Error: {e}", "dispatched_tasks": []}

    # Rename core logic method to indicate it's internal (already done)
    async def _dispatch_tasks(self, tasks_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dispatches tasks to appropriate agents via the AgentBus."""
        dispatched_info = []
        if not tasks_data:
             self.logger.info("No tasks provided by LLM interpretation to dispatch.")
             return dispatched_info

        self.logger.info(f"Attempting to dispatch {len(tasks_data)} task(s)...")
        for task_info in tasks_data:
            target_agent_id = task_info.get("target_agent")
            action = task_info.get("action")
            details = task_info.get("details", {})

            if not target_agent_id or not action:
                self.logger.warning(f"Skipping invalid task data (missing target_agent or action): {task_info}")
                dispatched_info.append({"task_info": task_info, "status": "skipped_invalid_data"})
                continue

            # Create a Task object
            task_id = f"task_{os.urandom(4).hex()}" # Example ID generation
            new_task = Task(
                task_id=task_id,
                agent_id=target_agent_id,
                status=TaskStatus.PENDING,
                action=action,
                data=details,
                source_agent_id=self.agent_id
            )

            # Construct command message for AgentBus
            # Use the command topic pattern expected by BaseAgent
            command_topic = f"agent.{target_agent_id}.command"
            message = {
                # "type": "task_assignment", # BaseAgent expects task in 'data' field
                "sender_id": self.agent_id,
                "correlation_id": f"corr_{task_id}", # Example correlation ID
                "data": new_task.to_dict() # Send task data in 'data' field
            }

            try:
                # Use AgentBus to publish the command message
                await self.agent_bus.publish(command_topic, message)
                self.logger.info(f"Dispatched task '{action}' to agent '{target_agent_id}' on topic '{command_topic}' (Task ID: {task_id})")
                dispatched_info.append({
                    "task_id": task_id,
                    "target_agent": target_agent_id,
                    "action": action,
                    "status": "dispatched"
                })
            except Exception as e:
                self.logger.error(f"Failed to dispatch task {task_id} to {target_agent_id}: {e}", exc_info=True)
                dispatched_info.append({
                    "task_id": task_id,
                    "target_agent": target_agent_id,
                    "action": action,
                    "status": f"dispatch_failed: {e}"
                })

        return dispatched_info

    async def _get_available_agents(self) -> List[str]:
        """Placeholder: Fetches a list of available agents."""
        # In a real scenario, this might query the AgentBus or a service registry
        self.logger.debug("Fetching available agents (using placeholder logic).")
        # Example: Directly ask AgentBus if it has a method (this is unlikely)
        if hasattr(self.agent_bus, 'get_registered_agents'):
             try:
                 # This method likely doesn't exist, replace with actual mechanism
                 # return await self.agent_bus.get_registered_agents()
                 self.logger.warning("'get_registered_agents' called on AgentBus - likely a placeholder.")
                 pass # Fall through to placeholder
             except Exception as e:
                 self.logger.error(f"Error calling placeholder get_registered_agents: {e}")
                 # Fall through to placeholder

        # TODO: Implement proper agent discovery mechanism (e.g., query registry via bus)
        placeholder_agents = ["planner_agent", "calendar_agent", "social_agent", "reflection_agent"]
        self.logger.warning(f"Using placeholder agent list: {placeholder_agents}")
        return placeholder_agents

# Example usage (conditional execution for testing)
if __name__ == "__main__":
    import asyncio

    # Configure logging for the test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Basic mock AgentBus for testing
    class MockAgentBus:
        def __init__(self):
            self.subscriptions = {}
            self.published_messages = []
            self.logger = logging.getLogger("MockAgentBus")

        async def subscribe(self, topic, handler):
            if topic not in self.subscriptions:
                self.subscriptions[topic] = []
            self.subscriptions[topic].append(handler)
            self.logger.info(f"Subscribed handler to topic: {topic}")
            return f"sub_{topic}" # Return a mock subscription ID

        async def publish(self, topic, message):
            self.published_messages.append((topic, message))
            self.logger.info(f"Published to {topic}: {json.dumps(message, indent=2)}")
            # Simulate message delivery
            if topic in self.subscriptions:
                 self.logger.debug(f"Delivering message on {topic} to {len(self.subscriptions[topic])} handler(s)." )
                 for handler in self.subscriptions[topic]:
                     # Simulate async call
                     asyncio.create_task(handler(topic, message))
            else:
                 self.logger.debug(f"No subscriptions found for topic {topic}")

        async def unsubscribe(self, sub_id):
            # Simple mock: find topic by sub_id prefix
            removed = False
            for topic, handlers in list(self.subscriptions.items()):
                if sub_id == f"sub_{topic}":
                    del self.subscriptions[topic]
                    self.logger.info(f"Unsubscribed from topic: {topic}")
                    removed = True
                    break
            if not removed:
                 self.logger.warning(f"Attempted to unsubscribe with unknown ID: {sub_id}")

        # Add other methods BaseAgent might call if needed (e.g., shutdown)
        async def shutdown(self):
            self.logger.info("Shutdown called (no-op in mock)")


    async def main():
        mock_bus = MockAgentBus()
        agent_id = "architects_edge_test_01"
        template_dir_path = os.path.join(os.path.dirname(__file__), '..\..\agents', 'prompts', 'architects_edge') # Adjust path
        # Fallback if relative path fails during direct execution
        if not os.path.exists(template_dir_path):
             template_dir_path = "agents/prompts/architects_edge"
        print(f"Using template directory: {template_dir_path}")

        # Create agent instance
        agent = ArchitectsEdgeAgent(agent_id=agent_id, agent_bus=mock_bus, template_dir=template_dir_path)

        try:
             # Start the agent (calls _on_start, subscribes)
             await agent.start()

             # Simulate receiving a directive message
             directive_topic = f"directive.{agent.agent_id}"
             directive = "Analyze the latest project report and schedule a follow-up meeting."
             correlation_id = f"corr_{os.urandom(4).hex()}"
             directive_message = {
                 "sender_id": "supervisor_agent",
                 "correlation_id": correlation_id,
                 "data": {"directive": directive}
             }
             print(f"\nSimulating publish of directive to '{directive_topic}'")
             await mock_bus.publish(directive_topic, directive_message)

             # Allow time for interpretation and task dispatch
             await asyncio.sleep(2) # Increased sleep to allow for LLM call + dispatch

             print("\nChecking published messages on mock bus:")
             dispatched_task_found = False
             response_found = False
             for topic, msg in mock_bus.published_messages:
                 if topic.startswith("agent.") and topic.endswith(".command"):
                     print(f"  Found dispatched task command on topic '{topic}': {json.dumps(msg['data'], indent=2)}")
                     dispatched_task_found = True
                 elif topic == f"system.response.{correlation_id}":
                     print(f"  Found interpretation response: {json.dumps(msg['data'], indent=2)}")
                     response_found = True

             if not dispatched_task_found:
                  print("  WARNING: No dispatched task command message found on bus.")
             if not response_found:
                  print("  WARNING: No interpretation response message found on bus.")

        except Exception as e:
            logging.getLogger(agent_id).error(f"An error occurred during the test: {e}", exc_info=True)
        finally:
            # Stop the agent
            print("\nStopping agent...")
            await agent.stop()

    asyncio.run(main())