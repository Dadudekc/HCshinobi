import asyncio
import logging
from typing import Dict, Any, Optional

# Attempt to import core components, fallback to placeholders if needed
try:
    # Assuming AgentBus and related types will eventually live in dreamforge.core
    from dreamforge.core.agent_bus import AgentBus, BaseAgent
    from dreamforge.core.bus_types import AgentStatus, Event, EventType
    BUS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Could not import core AgentBus components: {e}. AgentMonitorAgent will use placeholders.")
    BUS_AVAILABLE = False

    # Placeholder definitions
    class AgentStatus: IDLE = 'idle'; BUSY = 'busy'; ERROR = 'error'; SHUTDOWN_READY = 'shutdown_ready'; TERMINATED = 'terminated'
    class EventType: TASK = 'task'; SYSTEM = 'system'; AGENT_STATUS = 'agent_status' # Added status type
    class Event:
        def __init__(self, type: EventType, source_id: str, priority: int = 0, data: Optional[Dict] = None):
            self.type = type; self.source_id = source_id; self.priority = priority; self.data = data or {}
    class BaseAgent:
        def __init__(self, agent_id: str, agent_bus: Any, config: Optional[Dict] = None):
            self.agent_id = agent_id; self.agent_bus = agent_bus; self.config = config or {}; self.logger = logging.getLogger(agent_id)
        async def start(self): self.logger.info("Placeholder BaseAgent start."); pass
        async def stop(self): self.logger.info("Placeholder BaseAgent stop."); pass
        async def run(self): self.logger.info("Placeholder BaseAgent run."); pass
    class PlaceholderAgentBus:
        async def register_agent(self, *args, **kwargs): logging.info("[BUS_SIM][Monitor] Register..."); pass
        async def update_agent_status(self, *args, **kwargs): logging.info("[BUS_SIM][Monitor] Update Status..."); pass
        def register_handler(self, *args, **kwargs): logging.info("[BUS_SIM][Monitor] Register Handler..."); pass
        async def stop(self): logging.info("[BUS_SIM][Monitor] Stop Bus..."); pass
        def is_running(self): return True
    AgentBus = PlaceholderAgentBus

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentMonitorAgent")

AGENT_ID = "AgentMonitorAgent"

class AgentMonitorAgent(BaseAgent):
    """
    Monitors the status of other agents in the system.

    Listens for AGENT_STATUS events on the AgentBus and logs them.
    This is a basic stub implementation fulfilling the requirement from
    task 'fill_missing_placeholders_001'.
    """
    def __init__(self, agent_bus: AgentBus, config: Optional[Dict] = None):
        super().__init__(AGENT_ID, agent_bus, config)
        self.logger.info(f"{AGENT_ID} initialized.")
        # TODO: [MONITOR-1] Add persistent storage or dashboard integration for status history.

    async def start(self):
        """Registers the agent and its status event handler."""
        self.logger.info(f"Starting {AGENT_ID}...")
        try:
            # Use AGENT_STATUS event type if defined, otherwise fallback
            status_event_type = getattr(EventType, 'AGENT_STATUS', EventType.SYSTEM)
            
            await self.agent_bus.register_agent(self.agent_id, capabilities=["monitoring"])
            self.agent_bus.register_handler(status_event_type, self.handle_status_event)
            await self.agent_bus.update_agent_status(self.agent_id, AgentStatus.IDLE)
            self.logger.info(f"{AGENT_ID} registered and handlers set up.")
        except Exception as e:
            self.logger.error(f"Error during {AGENT_ID} startup: {e}", exc_info=True)
            await self.agent_bus.update_agent_status(self.agent_id, AgentStatus.ERROR, error=str(e))

    async def handle_status_event(self, event: Event):
        """Handles incoming agent status updates."""
        if not event.data:
            self.logger.warning("Received status event with no data.")
            return

        source_agent_id = event.source_id
        status = event.data.get('status')
        task_info = event.data.get('task')
        error_info = event.data.get('error')

        log_msg = f"Status Update: Agent '{source_agent_id}' is now {status}."
        if task_info:
            log_msg += f" (Task: {task_info})"
        if error_info:
            log_msg += f" (Error: {error_info})"

        self.logger.info(log_msg)
        # TODO: [MONITOR-2] Implement logic to trigger alerts or actions based on specific statuses (e.g., frequent errors).

    async def run(self):
        """Main agent loop (passive listener)."""
        self.logger.info(f"{AGENT_ID} running. Listening for status events...")
        while True:
            try:
                # Passive agent, just sleeps until stopped
                await asyncio.sleep(3600) # Sleep for a long time
            except asyncio.CancelledError:
                self.logger.info(f"{AGENT_ID} run loop cancelled.")
                break
            except Exception as e:
                self.logger.error(f"Error in {AGENT_ID} run loop: {e}", exc_info=True)
                # Avoid busy-looping on persistent errors
                await asyncio.sleep(60)

    async def stop(self):
        """Reports shutdown status."""
        self.logger.info(f"Stopping {AGENT_ID}...")
        try:
            await self.agent_bus.update_agent_status(self.agent_id, AgentStatus.TERMINATED)
        except Exception as e:
            self.logger.error(f"Error reporting TERMINATED status for {AGENT_ID}: {e}", exc_info=True)
        self.logger.info(f"{AGENT_ID} stopped.")

# Example of how to run this agent (for testing)
async def main():
    logger.info(f">>> Running {AGENT_ID} standalone demo...")
    bus = AgentBus() # Use real or placeholder bus based on imports
    monitor_agent = AgentMonitorAgent(bus)

    try:
        await monitor_agent.start()
        # In a real scenario, the bus would be running and dispatching events.
        # Here, we just keep the agent alive.
        await monitor_agent.run() # Will run until cancelled
    except asyncio.CancelledError:
        logger.info(f"{AGENT_ID} demo cancelled.")
    except Exception as e:
        logger.error(f"Error in {AGENT_ID} demo: {e}", exc_info=True)
    finally:
        await monitor_agent.stop()
        if hasattr(bus, 'stop'):
             # Ensure bus shutdown logic is called if it exists
             await bus.stop()
        logger.info(f"{AGENT_ID} demo finished.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"{AGENT_ID} demo interrupted by user.") 