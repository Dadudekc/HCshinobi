# agents/sim_cursor_chat_coordinator.py
import asyncio
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

# --- Core Agent Bus Integration ---
import sys
# Add the coordination core directory to sys.path if not standard
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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
        TERMINATED = "terminated"
    class EventType:
        TASK = "task"
        SYSTEM = "system"
    class Event:
        def __init__(self, type, source_id, priority):
            self.type=type; self.source_id=source_id; self.priority=priority; self.data={}
    class PlaceholderAgentBus:
        async def register_agent(self, *args, **kwargs): logger.info("[BUS_SIM][CCC] Registering agent...")
        async def update_agent_status(self, *args, **kwargs): logger.info("[BUS_SIM][CCC] Updating status...")
        async def dispatch(self, target_agent_id: str, command: str, payload: Dict[str, Any]):
             logger.info(f"[BUS_SIM][CCC] Dispatch called but not implemented for target {target_agent_id}")
             return {"status": "success", "message": "Dispatch called (simulated)."}
        def register_handler(self, *args, **kwargs): logger.info("[BUS_SIM][CCC] Registering handler...")
        async def _dispatch_system_event(self, event_type: str, data: Dict[str, Any], priority: int = 0):
             logger.info(f"[BUS_SIM][CCC] Dispatching event '{event_type}': {data}")
        async def stop(self): logger.info("[BUS_SIM][CCC] Stopping bus...")
        async def broadcast_shutdown(self): logger.info("[BUS_SIM][CCC] Broadcasting shutdown...")
        def is_running(self): return True
    AgentBus = PlaceholderAgentBus

# Global variable to hold the bus instance (either real or placeholder)
agent_bus_instance: Optional[AgentBus] = None

# --- Simulated Agent Logic --- #

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

AGENT_ID = "CursorChatCoordinator"

async def handle_bus_event(event: Event):
    """Handles events received from the Agent Bus."""
    global agent_bus_instance # Ensure we can access the bus
    if not agent_bus_instance:
         logger.error(f"[{AGENT_ID}] Agent bus instance not available in event handler.")
         return

    if event.type == EventType.TASK and event.data.get("type") == "process_social_task":
        # Received a task from the orchestrator
        task_details = event.data
        task_id = task_details.get("task_id", "unknown_task")
        logger.info(f"[{AGENT_ID}] Received task {task_id}. Simulating execution...")

        try:
            # Update status to BUSY
            await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.BUSY, task=task_id)

            # Simulate doing the work (e.g., interacting with Cursor or social API)
            await asyncio.sleep(random.uniform(1, 4)) # Simulate variable work time

            # Simulate success or failure randomly
            if random.random() < 0.9: # 90% success rate
                logger.info(f"[{AGENT_ID}] Task {task_id} completed successfully (simulated).")
                result_payload = {"status": "posted", "url": f"http://simulated.social/{task_id}"}
                # Report completion back to the bus (orchestrator will handle this)
                completion_event = Event(
                    type=EventType.TASK,
                    source_id=AGENT_ID,
                    priority=1
                )
                completion_event.data = {
                    "type": "task_completed",
                    "task_id": task_id,
                    "result": result_payload
                }
                # Need the _dispatch_system_event or equivalent on the bus instance
                if hasattr(agent_bus_instance, '_dispatch_system_event'):
                     await agent_bus_instance._dispatch_system_event("task_completed", completion_event.data, priority=1)
                else: # Fallback for placeholder
                     await agent_bus_instance.dispatch(AGENT_ID, "task_completed", completion_event.data)

                await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
            else:
                logger.warning(f"[{AGENT_ID}] Task {task_id} failed (simulated).")
                error_message = "Simulated API error or content rejection."
                # Report failure back to the bus
                failure_event = Event(
                    type=EventType.TASK,
                    source_id=AGENT_ID,
                    priority=1
                )
                failure_event.data = {
                    "type": "task_failed",
                    "task_id": task_id,
                    "error": error_message
                }
                if hasattr(agent_bus_instance, '_dispatch_system_event'):
                     await agent_bus_instance._dispatch_system_event("task_failed", failure_event.data, priority=1)
                else:
                     await agent_bus_instance.dispatch(AGENT_ID, "task_failed", failure_event.data)

                await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.ERROR, error=error_message)
                # Go back to IDLE after reporting error for demo simplicity
                await asyncio.sleep(0.5)
                await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)

        except Exception as e:
            logger.error(f"[{AGENT_ID}] Error processing task {task_id}: {e}", exc_info=True)
            # Report failure if an exception occurs
            error_event = Event(type=EventType.TASK, source_id=AGENT_ID, priority=1)
            error_event.data = {"type": "task_failed", "task_id": task_id, "error": str(e)}
            try:
                 if hasattr(agent_bus_instance, '_dispatch_system_event'):
                     await agent_bus_instance._dispatch_system_event("task_failed", error_event.data, priority=1)
                 else:
                     await agent_bus_instance.dispatch(AGENT_ID, "task_failed", error_event.data)
                 await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.ERROR, error=str(e))
                 await asyncio.sleep(0.5)
                 await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
            except Exception as report_e:
                 logger.error(f"[{AGENT_ID}] Failed to report task failure for {task_id}: {report_e}")

    elif event.type == EventType.SYSTEM:
         # Handle system events if needed (e.g., shutdown directives)
         event_data = event.data
         event_sub_type = event_data.get("type")
         if event_sub_type == "shutdown_directive":
              logger.info(f"[{AGENT_ID}] Received shutdown directive for phase: {event_data.get('phase')}. Preparing.")
              # Simulate getting ready for shutdown
              await asyncio.sleep(0.2)
              try:
                  await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.SHUTDOWN_READY)
                  logger.info(f"[{AGENT_ID}] Reported SHUTDOWN_READY.")
              except Exception as e:
                  logger.error(f"[{AGENT_ID}] Failed to update status to SHUTDOWN_READY: {e}")
         else:
              logger.debug(f"[{AGENT_ID}] Ignoring SYSTEM event subtype: {event_sub_type}")

async def main_loop(bus_instance: AgentBus):
    """Main loop for the simulated agent."""
    global agent_bus_instance # Allow loop to use the bus instance
    agent_bus_instance = bus_instance

    # Register with the Agent Bus
    try:
        await agent_bus_instance.register_agent(AGENT_ID, capabilities=["social_interaction", "cursor_chat"])
        logger.info(f"{AGENT_ID} registered with Agent Bus.")
        await agent_bus_instance.update_agent_status(AGENT_ID, AgentStatus.IDLE)
    except Exception as e:
        logger.error(f"Failed to register {AGENT_ID} with Agent Bus: {e}", exc_info=True)
        return # Cannot operate without registration

    # Register event handlers to receive tasks and system messages
    agent_bus_instance.register_handler(EventType.TASK, handle_bus_event)
    agent_bus_instance.register_handler(EventType.SYSTEM, handle_bus_event)
    logger.info(f"[{AGENT_ID}] Registered event handlers.")

    # Keep agent alive, waiting for events
    while True:
         if not agent_bus_instance or not getattr(agent_bus_instance, 'is_running', lambda: True)():
             logger.warning(f"[{AGENT_ID}] Agent bus is not running. Stopping agent loop.")
             break
         try:
            await asyncio.sleep(1) # Keep running, listening for events
         except asyncio.CancelledError:
             logger.info(f"[{AGENT_ID}] main loop cancelled.")
             break
         except Exception as loop_e:
             logger.error(f"Error in [{AGENT_ID}] main loop: {loop_e}", exc_info=True)
             await asyncio.sleep(5) # Pause briefly after an error

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

    parser = argparse.ArgumentParser(description='Simulated Cursor Chat Coordinator Agent Demo')
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
        # Start the agent's main loop
        agent_task = asyncio.create_task(main_loop(bus))

        print(f"\n>>> {AGENT_ID} simulation started. Waiting for tasks via Agent Bus...")
        print("(Run social_task_orchestrator.py in another terminal to send tasks)")
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
        asyncio.run(run_agent_demo())
    except KeyboardInterrupt:
        print(f"\n>>> {AGENT_ID} demo stopped by user.")
    except Exception as e:
        print(f"\n>>> Error during {AGENT_ID} demo execution: {e}")

    print(f">>> Module {__file__} execution finished.") 