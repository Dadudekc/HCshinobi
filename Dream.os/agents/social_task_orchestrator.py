# agents/social_task_orchestrator.py
import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Any

# --- Core Agent Bus Integration ---
# Assuming the refactored AgentBus and its components are accessible via this path
import sys
# Add the coordination core directory to sys.path if not standard
# Determine the project root based on the current file's location
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import necessary components (adjust if Event/EventType moved)
try:
    from _agent_coordination.core.agent_bus import AgentBus
    from _agent_coordination.core.bus_types import AgentStatus
    from core.coordination.dispatcher import Event, EventType
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
    class EventType:
        TASK = "task"
        SYSTEM = "system"
    class Event:
        def __init__(self, type, source_id, priority):
            self.type=type; self.source_id=source_id; self.priority=priority; self.data={}
    class PlaceholderAgentBus:
        async def register_agent(self, *args, **kwargs): logger.info("[BUS_SIM] Registering agent...")
        async def update_agent_status(self, *args, **kwargs): logger.info("[BUS_SIM] Updating status...")
        async def dispatch(self, target_agent_id: str, command: str, payload: Dict[str, Any]):
            logger.info(f"[BUS_SIM] Dispatching '{command}' to '{target_agent_id}' payload: {payload}")
            return {"status": "success", "message": "Task dispatched (simulated)."}
        def register_handler(self, *args, **kwargs): logger.info("[BUS_SIM] Registering handler...")
        async def stop(self): logger.info("[BUS_SIM] Stopping bus...")
        async def broadcast_shutdown(self): logger.info("[BUS_SIM] Broadcasting shutdown...")
        def is_running(self): return True # Assume running for simulation
    AgentBus = PlaceholderAgentBus # Use placeholder for type hinting

# Global variable to hold the bus instance (either real or placeholder)
agent_bus_instance: Optional[AgentBus] = None

# --- Orchestrator Logic --- #

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

AGENT_ID = "SocialTaskOrchestrator"
# TASK_LIST_PATH = Path(f"memory/{AGENT_ID}_tasks.json") # Use agent-specific task file <-- Old path
TASK_LIST_PATH = project_root / "../master_task_list.json" # Use the central master task list <-- New path
CURSOR_CHAT_AGENT_ID = "CursorChatCoordinator" # The agent responsible for executing social tasks

# Store task state locally for quick access
# In a robust system, this might be a shared DB or state manager
_local_tasks: List[Dict[str, Any]] = []
_local_tasks_lock = asyncio.Lock()

async def load_tasks() -> None:
    """Loads tasks from the JSON task list into local memory."""
    global _local_tasks
    async with _local_tasks_lock:
        if not TASK_LIST_PATH.exists():
            logger.warning(f"Task list not found at {TASK_LIST_PATH}. Initializing empty list.")
            _local_tasks = []
            return
        try:
            with open(TASK_LIST_PATH, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                     logger.info(f"Task file {TASK_LIST_PATH} is empty.")
                     _local_tasks = []
                     return
                tasks = json.loads(content)
            _local_tasks = tasks if isinstance(tasks, list) else []
            logger.info(f"Loaded {len(_local_tasks)} tasks from {TASK_LIST_PATH}")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from {TASK_LIST_PATH}. Using empty list.")
            _local_tasks = []
        except Exception as e:
            logger.error(f"Error loading tasks from {TASK_LIST_PATH}: {e}", exc_info=True)
            _local_tasks = []

async def save_tasks() -> None:
    """Saves the current local task list to the JSON file."""
    async with _local_tasks_lock:
        try:
            TASK_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(TASK_LIST_PATH, 'w', encoding='utf-8') as f:
                json.dump(_local_tasks, f, indent=2)
            logger.debug(f"Saved {len(_local_tasks)} tasks to {TASK_LIST_PATH}")
        except Exception as e:
            logger.error(f"Error saving tasks to {TASK_LIST_PATH}: {e}", exc_info=True)

async def find_next_task() -> Optional[Dict[str, Any]]:
    """Finds the next 'pending' task from local memory."""
    async with _local_tasks_lock:
        pending_tasks = [task for task in _local_tasks if task.get("status") == "pending"]
        if not pending_tasks:
            return None
        # Simple priority sorting (lower number = higher priority)
        pending_tasks.sort(key=lambda x: x.get("priority", float('inf')))
        return pending_tasks[0]

def validate_task(task: Dict[str, Any]) -> bool:
    """Validates the basic structure of a task."""
    required_fields = ["task_id", "type", "status", "details"]
    if not all(field in task for field in required_fields):
        logger.warning(f"Task {task.get('task_id', 'Unknown')} validation failed: Missing required fields ({required_fields}). Found: {list(task.keys())}")
        return False
    if task["status"] != "pending":
         logger.warning(f"Task {task.get('task_id')} validation failed: Status is '{task['status']}', not 'pending'.")
         return False
    # Add more specific validation based on task type if needed
    logger.debug(f"Task {task.get('task_id')} validated successfully.")
    return True

async def update_task_status(task_id: str, new_status: str, error: Optional[str] = None, result: Optional[Any] = None):
    """Updates the status of a task in local memory and saves."""
    async with _local_tasks_lock:
        task_updated = False
        for i, task in enumerate(_local_tasks):
            if task.get("task_id") == task_id:
                if task.get("status") == new_status:
                    logger.debug(f"Task {task_id} already has status '{new_status}'. No update needed.")
                    return # Avoid unnecessary updates
                
                _local_tasks[i]["status"] = new_status
                _local_tasks[i]["updated_at"] = datetime.now().isoformat()
                if error:
                     _local_tasks[i]["error"] = error
                else: # Clear error if status is no longer 'failed'
                     _local_tasks[i].pop("error", None)
                if result:
                     _local_tasks[i]["result"] = result # Store results if provided
                else:
                     # Clear previous result if task is being reset or failed
                     _local_tasks[i].pop("result", None)
                task_updated = True
                logger.info(f"Updated task {task_id} status to '{new_status}'.")
                break
        if not task_updated:
             logger.warning(f"Attempted to update status for non-existent or already updated task_id: {task_id}")

    if task_updated:
         await save_tasks() # Save after updating

async def handle_agent_event(event: Event):
    """Handles events received from the Agent Bus."""
    global agent_bus_instance # Ensure we can access the bus
    if not agent_bus_instance:
         logger.error("Agent bus instance not available in event handler.")
         return

    if event.type == EventType.TASK:
        event_data = event.data
        task_id = event_data.get("task_id")
        event_sub_type = event_data.get("type")
        source_agent = event.source_id

        logger.info(f"Received TASK event: Type='{event_sub_type}', TaskID='{task_id}', Source='{source_agent}'")

        if event_sub_type == "task_completed":
            # Task reported as completed by the executing agent
            result_data = event_data.get("result")
            await update_task_status(task_id, "complete", result=result_data)

        elif event_sub_type == "task_failed":
            # Task reported as failed by the executing agent
            error_message = event_data.get("error", "No error details provided.")
            await update_task_status(task_id, "failed", error=error_message)

        # Handle other potential task events if needed (e.g., progress updates)
        else:
             logger.debug(f"Ignoring TASK event subtype: {event_sub_type}")

    elif event.type == EventType.SYSTEM:
         # Handle system events if needed (e.g., shutdown directives)
         event_data = event.data
         event_sub_type = event_data.get("type")
         if event_sub_type == "shutdown_directive":
              logger.info(f"Received shutdown directive for phase: {event_data.get('phase')}. Preparing to shut down.")
              # Implement graceful shutdown logic here
              # For demo, just report ready
              try:
                  await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.SHUTDOWN_READY)
              except Exception as e:
                  logger.error(f"Failed to update status to SHUTDOWN_READY: {e}")
         else:
              logger.debug(f"Ignoring SYSTEM event subtype: {event_sub_type}")

async def orchestrate_next_task() -> bool:
    """Loads tasks, finds the next valid task, and dispatches it.
    Returns True if a task was processed (dispatched or failed validation), False otherwise.
    """
    global agent_bus_instance
    if not agent_bus_instance:
        logger.error("Agent Bus not initialized in orchestrate_next_task.")
        return False
        
    logger.debug(f"Running {AGENT_ID} orchestration cycle...")
    # Load tasks into local memory at start of cycle
    await load_tasks()

    next_task = await find_next_task()

    if not next_task:
        logger.debug("No pending tasks found.")
        return False # Indicate no task was processed

    logger.info(f"Found next task: {next_task.get('task_id')}")

    if not validate_task(next_task):
        await update_task_status(next_task["task_id"], "failed", error="Task validation failed")
        logger.error(f"Task {next_task.get('task_id')} failed validation. Marked as failed.")
        return True # Indicate a task was processed (failed)

    # Inject task into CursorChatCoordinator via AgentBus
    logger.info(f"Dispatching task {next_task.get('task_id')} to {CURSOR_CHAT_AGENT_ID}...")
    dispatch_payload = {
        "task_id": next_task["task_id"],
        "task_type": next_task["type"],
        "details": next_task["details"],
        "priority": next_task.get("priority")
    }

    try:
        response = await agent_bus_instance.dispatch(
             CURSOR_CHAT_AGENT_ID,
             "process_social_task", # Assumed command
             dispatch_payload
        )

        # NOTE: In a real system, we should NOT immediately assume success.
        # We should wait for a 'task_accepted' or 'task_started' event from the target agent.
        # For this demo, we optimistically mark as 'in_progress'.
        if response and response.get("status") == "success":
            await update_task_status(next_task["task_id"], "in_progress")
            logger.info(f"Task {next_task.get('task_id')} successfully dispatched to {CURSOR_CHAT_AGENT_ID}. Status updated to in_progress.")
        else:
            error_message = response.get("message", "Unknown dispatch error from bus")
            logger.error(f"Failed to dispatch task {next_task.get('task_id')} to {CURSOR_CHAT_AGENT_ID}: {error_message}")
            await update_task_status(next_task["task_id"], "failed", error=f"Dispatch failed: {error_message}")

    except Exception as e:
        logger.error(f"Exception during task dispatch for {next_task.get('task_id')}: {e}", exc_info=True)
        await update_task_status(next_task["task_id"], "failed", error=f"Dispatch exception: {str(e)}")

    return True # Indicate a task was processed (dispatched or failed)

async def main_loop(bus_instance: AgentBus):
    """Main loop for the orchestrator, including registration and event handling."""
    global agent_bus_instance # Allow loop to use the bus instance
    agent_bus_instance = bus_instance

    # Register with the Agent Bus
    try:
        await agent_bus_instance.register_agent(AGENT_ID, capabilities=["social_task_orchestration"])
        logger.info(f"{AGENT_ID} registered with Agent Bus.")
    except Exception as e:
        logger.error(f"Failed to register {AGENT_ID} with Agent Bus: {e}", exc_info=True)
        return # Cannot operate without registration

    # Register event handlers
    agent_bus_instance.register_handler(EventType.TASK, handle_agent_event)
    agent_bus_instance.register_handler(EventType.SYSTEM, handle_agent_event)
    logger.info("Registered event handlers for TASK and SYSTEM events.")

    # Initial task load
    await load_tasks()

    while True:
        if not agent_bus_instance or not getattr(agent_bus_instance, 'is_running', lambda: True)(): # Check if bus is running
            logger.warning("Agent bus is not running. Stopping orchestrator loop.")
            break
        try:
            processed_task = await orchestrate_next_task()
            sleep_time = 10 if processed_task else 30 # Shorter sleep if active, longer if idle
            logger.debug(f"Orchestration cycle complete. Sleeping for {sleep_time} seconds.")
            await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
             logger.info(f"{AGENT_ID} main loop cancelled.")
             break
        except Exception as loop_e:
             logger.error(f"Error in {AGENT_ID} main loop: {loop_e}", exc_info=True)
             await asyncio.sleep(60) # Longer sleep on error

    # Cleanup on exit
    logger.info(f"Shutting down {AGENT_ID}.")
    # Optionally unregister, update status, etc.
    try:
        if agent_bus_instance:
             # await agent_bus_instance.unregister_agent(AGENT_ID)
             await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.TERMINATED)
    except Exception as cleanup_e:
        logger.error(f"Error during {AGENT_ID} cleanup: {cleanup_e}")


if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
    print(f">>> Running module: {__file__}")

    parser = argparse.ArgumentParser(description='Social Task Orchestrator Demo')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.setLevel(logging.DEBUG)
    else:
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # --- Demo Setup --- #
    # In a standalone demo, we need to instantiate the bus if available
    # If BUS_AVAILABLE is False, it uses the PlaceholderAgentBus
    # If True, we instantiate the real one (assuming dependencies are met)
    bus = AgentBus() if BUS_AVAILABLE else PlaceholderAgentBus()
    # Set the global instance for the demo
    agent_bus_instance = bus

    async def run_orchestrator_demo():
        # Start the main loop as a background task
        orchestrator_task = asyncio.create_task(main_loop(bus))

        print("\n>>> Creating dummy task list: memory/SocialTaskOrchestrator_tasks.json")
        dummy_tasks = [
            {"task_id": f"task_soc_{uuid.uuid4().hex[:6]}", "type": "social_post", "status": "pending", "priority": 1, "details": {"platform": "twitter", "content": "Demo Post 1! #AI"}},
            {"task_id": f"task_soc_{uuid.uuid4().hex[:6]}", "type": "comment", "status": "pending", "priority": 2, "details": {"post_url": "http://example.com/post1", "comment": "Interesting take."}},
            {"task_id": f"task_soc_{uuid.uuid4().hex[:6]}", "type": "social_post", "status": "complete", "priority": 0, "details": {"platform": "linkedin", "content": "Already posted this."}, "result": "OK", "updated_at": "..."},
            {"task_id": f"task_soc_{uuid.uuid4().hex[:6]}", "type": "social_post", "status": "pending", "priority": 1, "details": {"platform": "bluesky", "content": "Testing the orchestrator."}},
            {"task_id": f"task_soc_{uuid.uuid4().hex[:6]}", "type": "invalid_task", "status": "pending", "priority": 3} # Missing details
        ]
        global _local_tasks
        _local_tasks = dummy_tasks # Initialize local memory for demo
        await save_tasks() # Save the dummy tasks
        print(f">>> Dummy tasks saved to {TASK_LIST_PATH}")

        print("\n>>> Running orchestration loop for a short duration (e.g., 25 seconds)... Press Ctrl+C to stop earlier.")
        print("(Watch console for task dispatch and status updates)")

        try:
            # Let it run a few cycles
            await asyncio.sleep(25)
        finally:
             print("\n>>> Stopping orchestrator loop...")
             orchestrator_task.cancel()
             try:
                 await orchestrator_task
             except asyncio.CancelledError:
                 logger.info("Orchestrator task successfully cancelled.")
             # Clean up dummy file
             if TASK_LIST_PATH.exists():
                 print(f"\n>>> Cleaning up dummy task list: {TASK_LIST_PATH}")
                 TASK_LIST_PATH.unlink(missing_ok=True)
             # Stop the bus if it was instantiated here
             if hasattr(bus, 'stop'):
                 await bus.stop()

    try:
        asyncio.run(run_orchestrator_demo())
    except KeyboardInterrupt:
        print("\n>>> Orchestrator demo stopped by user.")
    except Exception as e:
        print(f"\n>>> Error during demo execution: {e}")

    print(f">>> Module {__file__} execution finished.") 