# agents/prompt_feedback_loop_agent.py
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any
import uuid # For generating new task IDs

# --- Core Agent Bus Integration ---
import sys
# Add the coordination core directory to sys.path if not standard
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from _agent_coordination.core.agent_bus import AgentBus
    from _agent_coordination.core.bus_types import AgentStatus
    from core.coordination.dispatcher import Event, EventType
    # --- CSCL Integration Import --- #
    # We need to dispatch TO CursorIntegrationAgent, not directly use controller here
    CURSOR_INTEGRATION_AGENT_ID = "CursorIntegrationAgent" # Assume this agent handles CSCL tasks
    BUS_AVAILABLE = True
except ImportError as e:
    BUS_AVAILABLE = False
    print(f"Warning: Could not import AgentBus components ({e}). Bus interactions will be simulated.")
    # Define placeholders if import fails
    class AgentStatus:
        IDLE = "idle"
        BUSY = "busy"
        ERROR = "error"
        SHUTDOWN_READY = "shutdown_ready"
        TERMINATED = "terminated"
    class EventType:
        TASK = "task"
        SYSTEM = "system"
    class Event:
        def __init__(self, type, source_id, priority):
            self.type=type; self.source_id=source_id; self.priority=priority; self.data={}
    class PlaceholderAgentBus:
        async def register_agent(self, *args, **kwargs): logger.info("[BUS_SIM][Feedback] Registering agent...")
        async def update_agent_status(self, *args, **kwargs): logger.info("[BUS_SIM][Feedback] Updating status...")
        async def dispatch(self, target_agent_id: str, command: str, payload: Dict[str, Any], **kwargs): # Add kwargs for dispatch
            logger.info(f"[BUS_SIM][Feedback] Dispatching '{command}' to '{target_agent_id}', payload: {payload}")
            # Simulate success for dispatch call
            return {"status": "success", "message": "Dispatch simulated"}
        def register_handler(self, *args, **kwargs): logger.info("[BUS_SIM][Feedback] Registering handler...")
        async def stop(self): logger.info("[BUS_SIM][Feedback] Stopping bus...")
        async def broadcast_shutdown(self): logger.info("[BUS_SIM][Feedback] Broadcasting shutdown...")
        def is_running(self): return True
    AgentBus = PlaceholderAgentBus
    CURSOR_INTEGRATION_AGENT_ID = "CursorIntegrationAgent_PH" # Placeholder target

# Global variable to hold the bus instance (either real or placeholder)
agent_bus_instance: Optional[AgentBus] = None

# --- Feedback Agent Logic --- #

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

AGENT_ID = "PromptFeedbackLoopAgent"
# This agent reads/writes the *same* task list as the orchestrator
TASK_LIST_PATH = Path("memory/SocialTaskOrchestrator_tasks.json")
MAX_RETRIES = 3

# Use a lock for file access, although ideally a proper DB/queue handles concurrency
_file_lock = asyncio.Lock()

async def handle_failed_task(event_data: Dict[str, Any]):
    """Processes a task_failed event, potentially rescheduling or dispatching for analysis."""
    task_id = event_data.get("task_id")
    error_message = event_data.get("error", "Unknown error")
    source_agent = event_data.get("source_id", "Unknown agent")

    if not task_id:
        logger.warning("Received task_failed event with no task_id.")
        return

    logger.info(f"Processing failure for task {task_id} from agent {source_agent}. Error: {error_message}")

    async with _file_lock:
        # --- Load Tasks --- #
        if not TASK_LIST_PATH.exists():
            logger.error(f"Task list {TASK_LIST_PATH} not found. Cannot process failure for {task_id}.")
            return
        try:
            with open(TASK_LIST_PATH, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                tasks = json.loads(content) if content else []
            if not isinstance(tasks, list):
                 logger.error(f"Task list {TASK_LIST_PATH} is not a valid JSON list.")
                 return
        except Exception as e:
            logger.error(f"Failed to load or parse task list {TASK_LIST_PATH}: {e}")
            return

        # --- Find and Update Task --- #
        task_found = False
        task_index = -1
        original_task_details = {}

        for i, task in enumerate(tasks):
            if task.get("task_id") == task_id:
                task_found = True
                task_index = i
                original_task_details = task.get("details", {})
                current_status = task.get("status")
                if current_status != "failed":
                     logger.warning(f"Task {task_id} received failure event, but status in file is '{current_status}'. Ignoring.")
                     return # Exit early if status doesn't match
                break

        if not task_found:
             logger.warning(f"Received failure event for task {task_id}, but task not found or status mismatch.")
             return

        # Proceed with retry/analysis logic
        task = tasks[task_index]
        retries = task.get("retry_count", 0)
        logger.info(f"Task {task_id} current retry count: {retries}")

        if retries < MAX_RETRIES:
            # --- Simple Retry Logic --- #
            logger.info(f"Retrying task {task_id} (Attempt {retries + 1}/{MAX_RETRIES}).")
            tasks[task_index]["retry_count"] = retries + 1
            tasks[task_index]["status"] = "pending" # Reset status
            tasks[task_index]["updated_at"] = datetime.now().isoformat()
            if isinstance(tasks[task_index].get("details"), dict):
                 tasks[task_index]["details"]["last_error"] = error_message
                 tasks[task_index]["details"]["retry_attempt"] = retries + 1
            tasks[task_index].pop("result", None)
        else:
            # --- Max Retries Reached: Dispatch for CSCL Analysis --- #
            logger.warning(f"Task {task_id} reached max retries ({MAX_RETRIES}). Dispatching for analysis via {CURSOR_INTEGRATION_AGENT_ID}.")

            # 1. Update original task status
            tasks[task_index]["status"] = "failed_pending_analysis"
            tasks[task_index]["error"] = f"[Max Retries Reached, Pending Analysis] {error_message}"
            tasks[task_index]["updated_at"] = datetime.now().isoformat()

            # 2. Create new analysis task
            analysis_task_id = f"analysis-{task_id}-{uuid.uuid4().hex[:4]}"
            analysis_task_payload = {
                "task_id": analysis_task_id,
                "task_type": "feedback_analysis",
                "status": "pending", # This new task needs to be picked up
                "created_at": datetime.now().isoformat(),
                "source_agent": AGENT_ID, # Originated from feedback loop
                "priority": task.get("priority", 5) + 1, # Slightly lower priority than original?
                "details": {
                    "original_task_id": task_id,
                    "error_summary": error_message,
                    # Attempt to get some context - might need improvement
                    "context_snippet": json.dumps(original_task_details, indent=2)[:1000] # Truncate original details
                    # Future: Could include log file paths if available
                }
            }
            # Append the new analysis task to the list
            tasks.append(analysis_task_payload)
            logger.info(f"Created new analysis task {analysis_task_id} for failed task {task_id}.")

            # 3. Dispatch the NEW analysis task (implicitly via saving the list)
            # The orchestrator should pick up the new 'pending' analysis task.
            # No direct dispatch needed here if orchestrator monitors the list.
            # We just need to save the list with the new task and updated original task.

        # --- Save Updated Tasks (covers both retry and analysis cases) --- #
        try:
            with open(TASK_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2)
            logger.debug(f"Saved updated task list after processing failure for {task_id}.")
        except Exception as e:
            logger.error(f"Failed to save updated task list {TASK_LIST_PATH}: {e}")

async def handle_bus_event(event: Event):
    """Handles events received from the Agent Bus."""
    global agent_bus_instance
    if not agent_bus_instance:
         logger.error(f"[{AGENT_ID}] Agent bus instance not available.")
         return

    if event.type == EventType.TASK and event.data.get("type") == "task_failed":
        await handle_failed_task(event.data)

    elif event.type == EventType.SYSTEM:
        event_data = event.data
        event_sub_type = event_data.get("type")
        if event_sub_type == "shutdown_directive":
            logger.info(f"[{AGENT_ID}] Received shutdown directive. Preparing.")
            try:
                await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.SHUTDOWN_READY)
            except Exception as e:
                logger.error(f"[{AGENT_ID}] Failed to update status to SHUTDOWN_READY: {e}")
        else:
            logger.debug(f"[{AGENT_ID}] Ignoring SYSTEM event subtype: {event_sub_type}")

async def main_loop(bus_instance: AgentBus):
    """Main loop for the feedback agent."""
    global agent_bus_instance
    agent_bus_instance = bus_instance

    # Register with the Agent Bus
    try:
        await agent_bus_instance.register_agent(AGENT_ID, capabilities=["task_feedback_processing", "retry_logic", "failure_analysis_dispatch"])
        logger.info(f"{AGENT_ID} registered with Agent Bus.")
        await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
    except Exception as e:
        logger.error(f"Failed to register {AGENT_ID} with Agent Bus: {e}", exc_info=True)
        return

    # Register event handler to listen for failed tasks and system events
    agent_bus_instance.register_handler(EventType.TASK, handle_bus_event)
    agent_bus_instance.register_handler(EventType.SYSTEM, handle_bus_event)
    logger.info(f"[{AGENT_ID}] Registered event handlers.")

    # Keep agent alive, waiting for events
    while True:
        if not agent_bus_instance or not getattr(agent_bus_instance, 'is_running', lambda: True)():
            logger.warning(f"[{AGENT_ID}] Agent bus is not running. Stopping agent loop.")
            break
        try:
            await asyncio.sleep(5) # Sleep and check bus status periodically
        except asyncio.CancelledError:
            logger.info(f"[{AGENT_ID}] main loop cancelled.")
            break
        except Exception as loop_e:
            logger.error(f"Error in [{AGENT_ID}] main loop: {loop_e}", exc_info=True)
            await asyncio.sleep(60) # Longer sleep on error

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

    parser = argparse.ArgumentParser(description='Prompt Feedback Loop Agent Demo')
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

    async def run_feedback_demo():
        # Start the agent's main loop
        agent_task = asyncio.create_task(main_loop(bus))

        print(f"\n>>> {AGENT_ID} simulation started. Waiting for failed task events via Agent Bus...")
        print("(Run orchestrator and simulated coordinator to generate events)")
        print("(Press Ctrl+C to stop)")

        # Keep the demo running until interrupted
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
            # Stop the bus if it was instantiated here
            if hasattr(bus, 'stop'):
                await bus.stop()

    try:
        asyncio.run(run_feedback_demo())
    except KeyboardInterrupt:
        print(f"\n>>> {AGENT_ID} demo stopped by user.")
    except Exception as e:
        print(f"\n>>> Error during {AGENT_ID} demo execution: {e}")

    print(f">>> Module {__file__} execution finished.") 