# agents/cursor_integration_agent.py
import asyncio
import json
import logging
import random
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

# --- Core Agent Bus Integration ---
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from _agent_coordination.core.agent_bus import AgentBus
    from _agent_coordination.core.bus_types import AgentStatus
    from core.coordination.dispatcher import Event, EventType
    # --- Import the REAL Cursor Shadow Controller --- #
    from services.cursor_shadow_controller import CursorShadowController
    cursor_controller = CursorShadowController() # Initialize controller
    BUS_AVAILABLE = True
    REAL_CURSOR_INTEGRATION = True

    # === Real Cursor Interaction IMPLEMENTATION ===
    async def send_to_cursor(prompt: str, context: Optional[Dict] = None) -> Dict:
        """
        Uses the Shadow Controller to send prompt and receive response.
        Wraps the synchronous file operations in an async thread.
        """
        logger.info(f"[{AGENT_ID}] Using CursorShadowController to run prompt cycle...")
        try:
            # Run the synchronous file I/O cycle in a separate thread
            loop = asyncio.get_running_loop()
            result = await loop.run_in_thread(
                cursor_controller.run_prompt_cycle,
                prompt,
                context # Pass context if needed by controller
            )
            # run_prompt_cycle now returns the result directly
            return result
        except Exception as e:
            logger.error(f"[{AGENT_ID}] Error during cursor_controller.run_prompt_cycle: {e}", exc_info=True)
            return {"success": False, "error": f"Error in Shadow Controller cycle: {e}"}

    def parse_cursor_response(response: Dict) -> Dict:
        """
        Parses the response dictionary returned by CursorShadowController.
        Assumes the controller returns a dict with 'success' and 'response' or 'error'.
        """
        logger.debug(f"[{AGENT_ID}] Parsing response from Shadow Controller: {response}")
        if not isinstance(response, dict):
             logger.warning(f"[{AGENT_ID}] Unexpected response format from controller: {type(response)}")
             return {"status": "failure", "error": "Invalid response format from controller"}
             
        if response.get("success"):
            return {"status": "success", "result": response.get("response", "Cursor task succeeded (no specific response captured)." )}
        else:
            return {"status": "failure", "error": response.get("error", "Cursor task failed (unknown error from controller).")}
    # === End Real Cursor Interaction IMPLEMENTATION ===

except ImportError as e:
    BUS_AVAILABLE = False
    REAL_CURSOR_INTEGRATION = False # Mark as not available
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    print(f"Warning: Could not import AgentBus/Cursor components ({e}). Bus/Cursor interactions will be simulated.")
    class AgentStatus:
        IDLE = "idle"; BUSY = "busy"; ERROR = "error"; SHUTDOWN_READY = "shutdown_ready"; TERMINATED = "terminated"
    class EventType:
        TASK = "task"; SYSTEM = "system"
    class Event:
        def __init__(self, type, source_id, priority):
            self.type=type; self.source_id=source_id; self.priority=priority; self.data={}
    class PlaceholderAgentBus:
        async def register_agent(self, *args, **kwargs): logger.info("[BUS_SIM][CursorInt] Register...", extra={"agent": AGENT_ID})
        async def update_agent_status(self, *args, **kwargs): logger.info("[BUS_SIM][CursorInt] Update Status...", extra={"agent": AGENT_ID})
        async def dispatch(self, *args, **kwargs): logger.info("[BUS_SIM][CursorInt] Dispatch (No-op)...", extra={"agent": AGENT_ID})
        def register_handler(self, *args, **kwargs): logger.info("[BUS_SIM][CursorInt] Register Handler...", extra={"agent": AGENT_ID})
        async def _dispatch_system_event(self, event_type: str, data: Dict[str, Any], priority: int = 0):
             logger.info(f"[BUS_SIM][CursorInt] Dispatch Event '{event_type}': {data}", extra={"agent": AGENT_ID})
        async def stop(self): logger.info("[BUS_SIM][CursorInt] Stop Bus...", extra={"agent": AGENT_ID})
        async def broadcast_shutdown(self): logger.info("[BUS_SIM][CursorInt] Broadcast Shutdown...", extra={"agent": AGENT_ID})
        def is_running(self): return True
    AgentBus = PlaceholderAgentBus
    # Ensure these placeholders exist in the except block
    async def send_to_cursor(prompt: str, context: Optional[Dict] = None) -> Dict:
        logger.info(f"[CURSOR_SIM] Sending to Cursor: {prompt[:50]}...", extra={"agent": "CursorIntegrationAgent_PH"})
        await asyncio.sleep(random.uniform(1, 3))
        if "fail_task" in prompt.lower(): return {"success": False, "error": "Forced failure for demo"}
        return {"success": True, "response": f"Simulated Cursor processed: {prompt[:30]}"}
    def parse_cursor_response(response: Dict) -> Dict:
        logger.info(f"[CURSOR_SIM] Parsing Cursor response: {response}", extra={"agent": "CursorIntegrationAgent_PH"})
        if response.get("success"): return {"status": "success", "result": response.get("response")}
        return {"status": "failure", "error": response.get("error", "Simulated parse error")}

# Global variable to hold the bus instance
agent_bus_instance: Optional[AgentBus] = None

# --- Cursor Integration Agent Logic --- #

logger = logging.getLogger(__name__)
# Configure logger here if not already done in the except block for placeholders
if not BUS_AVAILABLE:
     logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

AGENT_ID = "CursorIntegrationAgent"

def format_prompt_for_cursor(task_details: Dict[str, Any]) -> str:
    """Creates a suitable prompt/command for Cursor based on task details."""
    task_id = task_details.get('task_id', '[unknown_task]') # Use placeholder if missing
    task_type = task_details.get("task_type")
    details = task_details.get("details", {}) # Use details directly, don't shadow
    params = details # Alias for clarity in templates below

    # --- Base Prompt Structure --- #
    # Include Task ID and Type at the top for all prompts
    prompt = f"Task ID: {task_id}\nType: {task_type}\n\nInstructions:\n"

    # --- Specific Task Type Formatting --- #
    if task_type == "social_post":
        prompt += f"Draft and send a social media post.\nPlatform: {params.get('platform', '[Not Specified]')}\nContent: {params.get('content', '')}"

    elif task_type == "comment":
        prompt += f"Post a comment.\nOriginal Post URL: {params.get('post_url', '[Not Specified]')}\nComment: {params.get('comment', '')}"

    elif task_type == "clarify_objective":
        prompt += f"The following task has stalled due to unclear objective or insufficient information.\n\n"
        prompt += f"Original Task ID: {task_id}\n"
        prompt += f"Context: {params.get('relevant_files', '[No specific files provided]')}\n"
        prompt += f"Instruction Hint: {params.get('instruction_hint', '[No hint provided]')}\n\n"
        prompt += f"Please suggest a clearer, executable next step or provide refined instructions to unblock the agent."

    elif task_type == "context_reload":
        prompt += f"The agent {params.get('target_agent', '[Unknown Agent]')} requires a full context reload to regain situational awareness.\n\n"
        prompt += f"Please review the code and memory structure relevant to this agent and provide a summary of:\n"
        prompt += f"- What this agent is responsible for\n"
        prompt += f"- What it appears to be missing or stalled on\n"
        prompt += f"- What the next action should be\n\n"
        prompt += f"Original Task: {task_id}"
        # Note: May need to provide file paths or context snippets here too in practice

    elif task_type == "diagnose_loop":
        prompt += f"A critical loop has stalled or entered an unstable state.\n\n"
        prompt += f"Target: {params.get('log_file', '[Log file not specified]')}\n"
        prompt += f"Symptoms: {params.get('symptoms', '[No symptoms described]')}\n\n"
        prompt += f"Please read the logs and:\n"
        prompt += f"- Identify what caused the failure or loop\n"
        prompt += f"- Propose a fix or a new sequence for reactivation"

    elif task_type == "feedback_analysis":
        prompt += f"A task failed and feedback has been logged.\n\n"
        prompt += f"Task ID: {task_id}\n"
        prompt += f"Error Summary: {params.get('error_summary', '[No error summary provided]')}\n"
        prompt += f"Relevant Context: {params.get('context_snippet', '[No context provided]')}\n\n"
        prompt += f"Please:\n"
        prompt += f"1. Identify the reason for failure\n"
        prompt += f"2. Propose an updated plan to fix or retry the task"

    elif task_type == "engage_competitive_protocol":
        prompt += f"You are entering competitive task resolution mode.\n\n"
        prompt += f"Review the file: {params.get('master_task_list_path', '[Task list path not specified]')}\n\n"
        prompt += f"Your goal:\n"
        prompt += f"- Identify the highest-priority or most urgent open task\n"
        prompt += f"- Write the exact code or reasoning needed to complete it\n"
        prompt += f"- Output a plan or implementation that fully resolves the task\n\n"
        prompt += f"Do not simulate. Do not summarize. Complete."

    else: # Generic fallback for unknown task types
        # Keep the original generic fallback
        prompt += f"Execute task of type '{task_type}' with details: {json.dumps(params)}"
        logger.warning(f"[{AGENT_ID}] Using generic prompt format for unknown task type: {task_type}")

    # --- Add retry info if present (applies to all types) --- #
    if details.get("retry_attempt"):
        prompt += f"\n\nNote: This is retry attempt #{details['retry_attempt']}. Last error was: {details.get('last_error', 'None')}"

    return prompt

async def execute_task_in_cursor(task_details: Dict[str, Any]) -> Dict[str, Any]:
    """Formats prompt, sends to Cursor via Shadow Controller, parses response."""
    task_id = task_details.get("task_id")
    logger.info(f"[{AGENT_ID}] Formatting prompt for task {task_id}...")
    prompt = format_prompt_for_cursor(task_details)

    logger.info(f"[{AGENT_ID}] Sending task {task_id} to Cursor via Shadow Controller...")
    try:
        # Calls the implemented send_to_cursor (which uses the controller)
        raw_cursor_response = await send_to_cursor(prompt, context=task_details) # Pass task details as context?
        
        logger.info(f"[{AGENT_ID}] Received raw response from Shadow Controller for task {task_id}. Parsing...")
        # Calls the implemented parse_cursor_response
        parsed_result = parse_cursor_response(raw_cursor_response)
        
        logger.info(f"[{AGENT_ID}] Parsed result for task {task_id}: {parsed_result.get('status')}")
        return parsed_result
    except Exception as e:
        # Catch errors from send/parse if they weren't caught internally
        logger.error(f"[{AGENT_ID}] Exception during Cursor interaction cycle for task {task_id}: {e}", exc_info=True)
        return {"status": "failure", "error": f"Cursor interaction cycle exception: {str(e)}"}

async def handle_bus_event(event: Event):
    """Handles incoming tasks and system events."""
    global agent_bus_instance
    if not agent_bus_instance:
         logger.error(f"[{AGENT_ID}] Agent bus instance not available.")
         return

    if event.type == EventType.TASK and event.data.get("type") == "process_social_task":
        task_details = event.data
        task_id = task_details.get("task_id", "unknown_task")
        start_time = time.monotonic()
        logger.info(f"[{AGENT_ID}] Received task '{task_id}'. Processing...")
        try:
            await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.BUSY, task=task_id)
            execution_result = await execute_task_in_cursor(task_details)
            outcome_event_type = "task_completed" if execution_result["status"] == "success" else "task_failed"
            outcome_payload = {"type": outcome_event_type,"task_id": task_id,}
            if execution_result["status"] == "success": outcome_payload["result"] = execution_result.get("result")
            else: outcome_payload["error"] = execution_result.get("error")
            outcome_event = Event(type=EventType.TASK, source_id=AGENT_ID, priority=1); outcome_event.data = outcome_payload
            dispatch_method = getattr(agent_bus_instance, '_dispatch_system_event', getattr(agent_bus_instance, 'dispatch', None))
            if dispatch_method:
                 if hasattr(agent_bus_instance, '_dispatch_system_event'): await dispatch_method(outcome_event_type, outcome_payload, priority=1)
                 else: await dispatch_method(AGENT_ID, outcome_event_type, outcome_payload)
            else: logger.error(f"[{AGENT_ID}] Cannot dispatch event, no suitable dispatch method found.")
            logger.info(f"[{AGENT_ID}] Reported {outcome_event_type} for task {task_id}. Duration: {time.monotonic() - start_time:.2f}s")
            final_status = AgentStatus.IDLE if execution_result["status"] == "success" else AgentStatus.ERROR
            error_msg = None if execution_result["status"] == "success" else execution_result.get("error")
            await agent_bus_instance.update_agent_status(AGENT_ID, final_status, error=error_msg)
            if final_status == AgentStatus.ERROR: await asyncio.sleep(0.5); await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
        except Exception as e:
            proc_time = time.monotonic() - start_time
            logger.error(f"[{AGENT_ID}] Critical error processing task {task_id} after {proc_time:.2f}s: {e}", exc_info=True)
            error_payload = {"type": "task_failed", "task_id": task_id, "error": f"Agent exception: {str(e)}"}
            try:
                 dispatch_method = getattr(agent_bus_instance, '_dispatch_system_event', getattr(agent_bus_instance, 'dispatch', None))
                 if dispatch_method:
                    if hasattr(agent_bus_instance, '_dispatch_system_event'): await dispatch_method("task_failed", error_payload, priority=1)
                    else: await dispatch_method(AGENT_ID, "task_failed", error_payload)
                 await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.ERROR, error=str(e))
                 await asyncio.sleep(0.5); await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
            except Exception as report_e: logger.error(f"[{AGENT_ID}] Failed to report critical task failure for {task_id}: {report_e}")
    elif event.type == EventType.SYSTEM:
         event_data = event.data; event_sub_type = event_data.get("type")
         if event_sub_type == "shutdown_directive":
              logger.info(f"[{AGENT_ID}] Received shutdown directive phase: {event_data.get('phase')}. Preparing.")
              await asyncio.sleep(0.1)
              try: await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.SHUTDOWN_READY); logger.info(f"[{AGENT_ID}] Reported SHUTDOWN_READY.")
              except Exception as e: logger.error(f"[{AGENT_ID}] Failed to update status to SHUTDOWN_READY: {e}")
         else: logger.debug(f"[{AGENT_ID}] Ignoring SYSTEM event subtype: {event_sub_type}")

async def main_loop(bus_instance: AgentBus):
    """Main loop for the agent."""
    global agent_bus_instance
    agent_bus_instance = bus_instance

    # Register with the Agent Bus
    try:
        # Declare capabilities accurately
        await agent_bus_instance.register_agent(AGENT_ID, capabilities=["social_interaction", "cursor_execution"])
        logger.info(f"{AGENT_ID} registered with Agent Bus.")
        await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
    except Exception as e:
        logger.error(f"Failed to register {AGENT_ID} with Agent Bus: {e}", exc_info=True)
        return

    # Register event handlers
    agent_bus_instance.register_handler(EventType.TASK, handle_bus_event)
    agent_bus_instance.register_handler(EventType.SYSTEM, handle_bus_event)
    logger.info(f"[{AGENT_ID}] Registered event handlers.")

    # Keep agent alive, waiting for events
    while True:
        if not agent_bus_instance or not getattr(agent_bus_instance, 'is_running', lambda: True)():
             logger.warning(f"[{AGENT_ID}] Agent bus is not running. Stopping agent loop.")
             break
        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info(f"[{AGENT_ID}] main loop cancelled.")
            break
        except Exception as loop_e:
            logger.error(f"Error in [{AGENT_ID}] main loop: {loop_e}", exc_info=True)
            await asyncio.sleep(5)

    # Cleanup on exit
    logger.info(f"Shutting down {AGENT_ID}.")
    try:
        if agent_bus_instance:
            await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.TERMINATED)
    except Exception as cleanup_e:
        logger.error(f"Error during {AGENT_ID} cleanup: {cleanup_e}")

if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
    print(f">>> Running module: {__file__}")

    parser = argparse.ArgumentParser(description='Cursor Integration Agent Demo')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Demo Setup --- #
    bus = AgentBus() if BUS_AVAILABLE else PlaceholderAgentBus()
    agent_bus_instance = bus

    async def run_agent_demo():
        agent_task = asyncio.create_task(main_loop(bus))
        print(f"\n>>> {AGENT_ID} started. Integration Active: {REAL_CURSOR_INTEGRATION}. Waiting for tasks...")
        print("(Run social_task_orchestrator.py in another terminal to send tasks)")
        print("(Press Ctrl+C to stop)")
        try:
            await agent_task
        except asyncio.CancelledError:
            logger.info(f"{AGENT_ID} demo run cancelled.")
        except Exception as e:
            logger.error(f"Error running {AGENT_ID} demo: {e}", exc_info=True)
        finally:
            if not agent_task.done():
                agent_task.cancel()
                try: await agent_task
                except asyncio.CancelledError: pass
            if hasattr(bus, 'stop'):
                await bus.stop()

    try:
        asyncio.run(run_agent_demo())
    except KeyboardInterrupt:
        print(f"\n>>> {AGENT_ID} demo stopped by user.")
    except Exception as e:
        print(f"\n>>> Error during {AGENT_ID} demo execution: {e}")

    print(f">>> Module {__file__} execution finished.") 