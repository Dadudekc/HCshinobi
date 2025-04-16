"""
Agent responsible for interacting with the Cursor application via the CursorCoordinator.
Receives tasks from the AgentBus and executes them using the coordinator.
"""
import logging
import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from coordination.agent_bus import AgentBus, Message
from coordination.cursor_coordinator import CursorCoordinator

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

AGENT_NAME = "CursorControlAgent"

class CursorControlAgent:
    """Agent that controls Cursor UI interactions based on bus messages."""

    def __init__(self, agent_bus: AgentBus, launch_new_instance: bool = False):
        """
        Initializes the agent, coordinator, and registers with the bus.

        Args:
            agent_bus: The central AgentBus instance.
            launch_new_instance: Passed to CursorCoordinator to force launching a new instance.
        """
        self.agent_name = AGENT_NAME
        self.bus = agent_bus
        logger.info(f"Initializing {self.agent_name}...")

        try:
            # Coordinator handles finding/launching Cursor
            self.coordinator = CursorCoordinator(launch_new_instance=launch_new_instance)
            if not self.coordinator.target_instance_id:
                 raise RuntimeError("CursorCoordinator failed to target an instance.")
        except Exception as e:
             logger.error(f"Failed to initialize CursorCoordinator: {e}", exc_info=True)
             # Agent cannot function without coordinator
             self.coordinator = None
             # Optionally, do not register if init fails
             # return

        # Register agent and message handler
        self.bus.register_agent(self.agent_name, capabilities=["cursor_control"])
        # Handle messages specifically directed to this agent
        self.bus.register_handler(self.agent_name, self.handle_message)
        # Also handle broadcast messages of type CURSOR_COMMAND
        self.bus.register_handler("CURSOR_COMMAND", self.handle_message) 

        logger.info(f"{self.agent_name} initialized and registered with AgentBus.")

    def handle_message(self, message: Message):
        """Processes incoming messages directed to this agent or of type CURSOR_COMMAND."""
        if not self.coordinator:
            logger.error(f"{self.agent_name} received message but coordinator is not available.")
            # Optionally send error response
            if message.sender != self.agent_name: # Avoid loops
                 self.bus.send_message(self.agent_name, message.sender, "ERROR", {"error": "Coordinator unavailable"}, request_id=message.id)
            return

        logger.info(f"{self.agent_name} received message: {message.type} from {message.sender}")
        # Basic request/response pattern based on message type or payload content
        # Example: payload = {"action": "ACTION_NAME", "params": {...}}
        payload = message.payload
        response_payload: Dict[str, Any] = {}
        status = "ERROR" # Default to error unless successful

        action = payload.get("action")
        params = payload.get("params", {})

        try:
            if action == "GET_EDITOR_CONTENT":
                content = self.coordinator.get_editor_content()
                response_payload["content"] = content
                status = "SUCCESS" if content is not None else "FAILED"
            elif action == "RUN_TERMINAL_COMMAND":
                command = params.get("command")
                wait = params.get("wait", True)
                if command:
                    success = self.coordinator.run_terminal_command(command, wait=wait)
                    response_payload["command_executed"] = command
                    response_payload["success"] = success
                    status = "SUCCESS" if success else "FAILED"
                else:
                    response_payload["error"] = "Missing 'command' parameter."
                    status = "BAD_REQUEST"
            elif action == "GET_TERMINAL_OUTPUT":
                 max_lines = params.get("max_lines")
                 output = self.coordinator.get_terminal_output(max_lines=max_lines)
                 response_payload["output"] = output
                 if output is not None:
                     status = "SUCCESS"
                 else:
                     status = "FAILED"
                     response_payload["error"] = "Failed to retrieve terminal output. Terminal might be inactive or an error occurred."
            elif action == "OPEN_FILE":
                 file_path = params.get("file_path")
                 if file_path:
                     success = self.coordinator.open_file_in_editor(file_path)
                     response_payload["file_opened"] = file_path
                     response_payload["success"] = success
                     status = "SUCCESS" if success else "FAILED"
                 else:
                    response_payload["error"] = "Missing 'file_path' parameter."
                    status = "BAD_REQUEST"
            elif action == "INSERT_TEXT":
                text_to_insert = params.get("text")
                location = params.get("location") # Optional: could be line number, 'cursor', etc.
                if text_to_insert is not None: # Check for None, empty string might be valid
                    # Assuming coordinator has an insert_text method
                    # success = self.coordinator.insert_text(text_to_insert, location=location)
                    # Placeholder implementation:
                    logger.warning(f"Placeholder: Received INSERT_TEXT action with text: '{text_to_insert[:50]}...', location: {location}. Not implemented yet.")
                    success = False # Mark as failed until implemented
                    response_payload["action_performed"] = "INSERT_TEXT (Placeholder)"
                    response_payload["success"] = success
                    status = "FAILED_NOT_IMPLEMENTED" # Specific status
                else:
                    response_payload["error"] = "Missing 'text' parameter for INSERT_TEXT."
                    status = "BAD_REQUEST"
            elif action == "FIND_ELEMENT":
                query = params.get("query")
                element_type = params.get("element_type", "any") # Optional: 'function', 'class', 'variable'
                if query:
                    # Assuming coordinator has a find_element method
                    # result = self.coordinator.find_element(query, element_type=element_type)
                    # Placeholder implementation:
                    logger.warning(f"Placeholder: Received FIND_ELEMENT action with query: '{query}', type: {element_type}. Not implemented yet.")
                    result = None # Mark as failed until implemented
                    response_payload["action_performed"] = "FIND_ELEMENT (Placeholder)"
                    response_payload["result"] = result
                    response_payload["success"] = False
                    status = "FAILED_NOT_IMPLEMENTED" # Specific status
                else:
                    response_payload["error"] = "Missing 'query' parameter for FIND_ELEMENT."
                    status = "BAD_REQUEST"
            # Add more actions here...
            # elif action == "INSERT_TEXT": ...
            # elif action == "FIND_ELEMENT": ...
            else:
                logger.warning(f"Unknown or unsupported action requested: {action}")
                response_payload["error"] = f"Unsupported action: {action}"
                status = "UNKNOWN_ACTION"

        except Exception as e:
            logger.error(f"Error processing action '{action}' for task {message.id}: {e}", exc_info=True)
            response_payload["error"] = f"Internal error during action {action}: {str(e)}"
            status = "EXECUTION_ERROR"

        # Send response back to the original sender (if it wasn't a broadcast to self)
        if message.sender != self.agent_name:
            # Include task_id if present in the original message
            response_task_id = getattr(message, 'task_id', None)
            self.bus.send_message(
                sender=self.agent_name,
                recipient=message.sender, # Send back to original sender
                message_type=f"{action}_RESPONSE", # e.g., GET_EDITOR_CONTENT_RESPONSE
                payload=response_payload,
                status=status,
                request_id=message.id, # Link response to the original request message
                task_id=response_task_id # Include task_id for easier tracking by executor
            )
        elif status.startswith("ERROR") or status.startswith("FAIL") or status == "UNKNOWN_ACTION":
             # Log errors even if message was broadcast or self-sent
             logger.error(f"Error processing message (ID: {message.id}, Action: {action}): {response_payload.get('error', 'Unknown error')}")

    def shutdown(self):
        """Performs cleanup, like closing the controlled Cursor instance if launched by agent."""
        logger.warning(f"Shutting down {self.agent_name}...")
        if self.coordinator and self.coordinator._was_launched:
            logger.info("Closing Cursor instance launched by this agent.")
            self.coordinator.close_cursor(force=True)
        else:
            logger.info("Cursor instance was pre-existing or already closed, not closing.")
        # Unregister?
        # self.bus.deregister_agent(self.agent_name)
        logger.info(f"{self.agent_name} shutdown complete.")


# ========= USAGE BLOCK START ==========
if __name__ == "__main__":
    # 🔌 Example usage — Demonstrates Agent initialization and basic message handling
    # (This assumes AgentBus can be run/tested standalone or mocked)
    print(f">>> Running module: {__file__}")
    abs_file_path = os.path.abspath(__file__)
    filename = os.path.basename(abs_file_path)
    agent_id = "UsageBlockAgent_CCA" # Different ID for this block
    # (Coordination file paths defined)
    coord_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # Assumes core/agents
    status_file = os.path.join(coord_base_dir, "status", "usage_block_status_cca.json") # Unique status file
    task_list_file = os.path.join(coord_base_dir, "task_list.json")
    project_board_file = os.path.join(coord_base_dir, "project_board.json")

    # --- Coordination: Log Start ---
    _log_tool_action(f"UsageBlock_{filename}", "STARTED", f"Executing usage block for {filename}")
    # -----------------------------

    output_summary = []
    errors = None
    execution_status = "failed"
    bus: Optional[AgentBus] = None
    agent: Optional[CursorControlAgent] = None

    try:
        # Instantiate Agent Bus (using placeholder directory)
        print("\n>>> Instantiating AgentBus...")
        mailbox_dir = os.path.join(".", "temp_cca_mailboxes")
        bus = AgentBus(mailbox_base_dir=mailbox_dir)
        output_summary.append(f"AgentBus instantiated (Mailbox: {mailbox_dir}).")
        print(">>> AgentBus instantiated.")

        # Instantiate CursorControlAgent (force new instance for demo)
        print("\n>>> Instantiating CursorControlAgent (launch_new_instance=True)...")
        agent = CursorControlAgent(agent_bus=bus, launch_new_instance=True)
        if not agent.coordinator:
             raise RuntimeError("Agent failed to initialize its CursorCoordinator.")
        output_summary.append(f"{agent.agent_name} instantiated and registered.")
        print(f">>> {agent.agent_name} instantiated.")

        # Simulate sending a message from another agent/controller
        requester_agent = "DemoRequesterAgent"
        print(f"\n>>> Simulating sending message from {requester_agent} to {agent.agent_name}...")

        # --- Test GET_EDITOR_CONTENT --- #
        task_1_payload = {"action": "GET_EDITOR_CONTENT"}
        request_id_1 = bus.send_message(requester_agent, agent.agent_name, "CURSOR_COMMAND", task_1_payload)
        print(f"  Sent GET_EDITOR_CONTENT request (ID: {request_id_1}).")
        output_summary.append(f"Sent: {task_1_payload['action']}")

        # --- Test RUN_TERMINAL_COMMAND --- #
        task_2_payload = {"action": "RUN_TERMINAL_COMMAND", "params": {"command": "echo Hello from Agent!"}}
        request_id_2 = bus.send_message(requester_agent, agent.agent_name, "CURSOR_COMMAND", task_2_payload)
        print(f"  Sent RUN_TERMINAL_COMMAND request (ID: {request_id_2}).")
        output_summary.append(f"Sent: {task_2_payload['action']}")

        # --- Test Unknown Action --- #
        task_3_payload = {"action": "NONEXISTENT_ACTION"}
        request_id_3 = bus.send_message(requester_agent, agent.agent_name, "CURSOR_COMMAND", task_3_payload)
        print(f"  Sent NONEXISTENT_ACTION request (ID: {request_id_3}).")
        output_summary.append(f"Sent: {task_3_payload['action']}")

        # Process messages on the bus for the agent
        print("\n>>> Processing messages for the agent...")
        # In a real system, the bus/agent would have a run loop
        processed_count = bus.process_messages(agent.agent_name, max_messages=5)
        print(f">>> Processed {processed_count} messages for {agent.agent_name}.")
        output_summary.append(f"Processed {processed_count} messages for agent.")

        # Check for responses sent back to the requester
        print(f"\n>>> Checking responses received by {requester_agent}...")
        responses = bus.get_messages(requester_agent)
        output_summary.append(f"Retrieved {len(responses)} messages for requester.")
        print(f">>> Found {len(responses)} messages for {requester_agent}:")

        # Process responses
        for response in responses:
            print(f"Response from {response.sender}: {response.payload}")
            if response.status == "SUCCESS":
                output_summary.append(f"Received successful response from {response.sender}: {response.payload}")
            else:
                output_summary.append(f"Received error response from {response.sender}: {response.payload}")
                if response.status == "ERROR":
                    errors = response.payload.get("error", "Unknown error")
                elif response.status == "EXECUTION_ERROR":
                    errors = response.payload.get("error", "Execution error")
                elif response.status == "BAD_REQUEST":
                    errors = response.payload.get("error", "Bad request")
                elif response.status == "UNKNOWN_ACTION":
                    errors = response.payload.get("error", "Unknown action")

        # Update execution status
        execution_status = "succeeded" if not errors else "failed"

    except Exception as e:
        logger.error(f"Error in usage block: {e}", exc_info=True)
        errors = f"Error in usage block: {str(e)}"
        execution_status = "failed"

    finally:
        # Log usage block completion
        _log_tool_action(f"UsageBlock_{filename}", "COMPLETED", f"Usage block completed. Execution status: {execution_status}")

        # Save usage block status
        usage_block_status = {
            "status": execution_status,
            "errors": errors,
            "output_summary": output_summary,
            "timestamp": datetime.now().isoformat()
        }
        with open(status_file, "w") as f:
            json.dump(usage_block_status, f)

        # Clean up
        if bus:
            bus.shutdown()
        if agent:
            agent.shutdown()

        print("\n>>> Usage block execution completed.")
        print(f">>> Execution status: {execution_status}")
        print(f">>> Errors: {errors}")
        print(f">>> Output summary: {output_summary}")
        print(f">>> Usage block status saved to: {status_file}")

    if errors:
        sys.exit(1)
    else:
        sys.exit(0) 