"""Dream.OS Agent Bus - Main Orchestration Module"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
import shutil
import argparse
import uuid

from core.config import config_service
from core.feedback import log_event
from core.utils.file_manager import FileManager
from core.utils.system import SystemUtils
from core.coordination.dispatcher import EventDispatcher, EventType, Event

# New modular components
from .bus_types import AgentStatus
from .agent_registry import AgentRegistry
from .system_diagnostics import SystemDiagnostics
from .shutdown_coordinator import ShutdownCoordinator

logger = logging.getLogger(__name__)

class AgentBus:
    """Centralized agent coordination hub, orchestrating modular components."""

    def __init__(self):
        logger.info("Initializing Agent Bus...")
        self.agents: Dict[str, Dict] = {}
        self.active_agents: Set[str] = set()
        self.shutdown_ready: Set[str] = set()
        self._lock = asyncio.Lock()
        self.file_mgr = FileManager()
        self.sys_utils = SystemUtils()
        self.shutdown_in_progress = False

        # Initialize Event Dispatcher first, as other components might need it or its callback
        self._dispatcher = EventDispatcher(self) # Dispatcher needs a reference? Or just use callback?
        # Using a callback approach might be cleaner to avoid circular deps
        # Let's define the callback here
        self._dispatch_callback = self._dispatch_system_event

        # Initialize modular components, passing dependencies
        self.registry = AgentRegistry(dispatch_event_callback=self._dispatch_callback)
        self.diagnostics = SystemDiagnostics(
            agent_registry=self.registry,
            event_dispatcher=self._dispatcher, # Diagnostics needs dispatcher to check its state
            sys_utils=self.sys_utils,
            dispatch_event_callback=self._dispatch_callback
        )
        self.coordinator = ShutdownCoordinator(
            agent_registry=self.registry,
            diagnostics=self.diagnostics,
            event_dispatcher=self._dispatcher, # Coordinator needs dispatcher to send directives
            sys_utils=self.sys_utils,
            dispatch_event_callback=self._dispatch_callback
        )

        # Start the event dispatcher background task
        self._dispatcher_task = asyncio.create_task(self._dispatcher.start())
        logger.info("Event Dispatcher started.")

        # Register signal handlers
        try:
            signal.signal(signal.SIGTERM, self.handle_shutdown_signal)
            signal.signal(signal.SIGINT, self.handle_shutdown_signal)
            logger.info("Signal handlers registered.")
        except ValueError as e:
            # Likely running in a thread where signals can't be set
            logger.warning(f"Could not set signal handlers: {e}. Shutdown might need external trigger.")

        self._load_shutdown_directive()

        logger.info("Agent Bus initialized successfully.")

    def _load_shutdown_directive(self):
        """Load shutdown directive template."""
        directive_path = Path("user_prompts/shutdown_directive.prompt.txt")
        self.shutdown_directive = directive_path.read_text()

    async def _dispatch_system_event(self, event_type: str, data: Dict[str, Any], priority: int = 0) -> None:
        """Callback function used by components to dispatch system events via the main dispatcher."""
        logger.debug(f"Dispatching system event: Type={event_type}, Priority={priority}")
        event = Event(
            type=EventType.SYSTEM,
            source_id="agent_bus", # Source is the bus itself
            priority=priority
        )
        # Ensure data is structured correctly, including the specific event type
        event.data = {"type": event_type, **data}
        try:
            await self._dispatcher.dispatch_event(event)
        except Exception as e:
            logger.error(f"Failed to dispatch system event {event_type}: {e}", exc_info=True)

    # --- Agent Management (Delegated to Registry) ---

    async def register_agent(self, agent_id: str, capabilities: List[str]) -> None:
        """Register a new agent. Delegates to AgentRegistry."""
        async with self._lock:
            if agent_id in self.agents:
                raise ValueError(f"Agent {agent_id} is already registered")
            
            self.agents[agent_id] = {
                "agent_id": agent_id,
                "status": AgentStatus.IDLE,
                "capabilities": capabilities,
                "current_task": None,
                "error_message": None
            }
            self.active_agents.add(agent_id)
            
            # Dispatch registration event
            await self._dispatch_system_event(
                "agent_registered",
                {"agent_id": agent_id, "capabilities": capabilities}
            )

    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent. Delegates to AgentRegistry."""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
            
            del self.agents[agent_id]
            self.active_agents.discard(agent_id)
            self.shutdown_ready.discard(agent_id)
            
            # Dispatch unregistration event
            await self._dispatch_system_event(
                "agent_unregistered",
                {"agent_id": agent_id}
            )

    async def update_agent_status(self, agent_id: str, status: AgentStatus,
                                task: Optional[str] = None,
                                error: Optional[str] = None) -> None:
        """Update an agent's status. Delegates to AgentRegistry."""
        # Ensure status is the Enum type before passing
        if not isinstance(status, AgentStatus):
            try:
                status = AgentStatus(status) # Attempt conversion if string
            except ValueError:
                 logger.error(f"Invalid status value '{status}' provided for agent {agent_id}. Use AgentStatus enum.")
                 raise ValueError(f"Invalid status value: {status}")
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
                
            agent = self.agents[agent_id]
            agent["status"] = status
            agent["current_task"] = task
            agent["error_message"] = error
            
            if status == AgentStatus.SHUTDOWN_READY:
                self.shutdown_ready.add(agent_id)
            
            # Dispatch status change event
            await self._dispatch_system_event(
                "status_change",
                {
                    "agent_id": agent_id,
                    "status": status,
                    "task": task,
                    "error": error
                }
            )

    async def get_available_agents(self, required_capabilities: List[str]) -> List[str]:
        """Get list of idle agents with required capabilities. Delegates to AgentRegistry."""
        async with self._lock:
            available = []
            for agent_id, info in self.agents.items():
                if (info["status"] == AgentStatus.IDLE and
                    all(cap in info["capabilities"] for cap in required_capabilities)):
                    available.append(agent_id)
            return available

    async def get_agent_info(self, agent_id: str) -> Dict:
        """Get information about a specific agent. Delegates to AgentRegistry."""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} is not registered")
            return self.agents[agent_id].copy()

    async def get_all_agents(self) -> Dict[str, Dict]:
        """Get information about all registered agents. Delegates to AgentRegistry."""
        async with self._lock:
            return self.agents.copy()

    # --- Event Handling (Delegated to Dispatcher) ---

    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register an event handler. Delegates to EventDispatcher."""
        self._dispatcher.register_handler(event_type, handler)

    # --- Shutdown Coordination (Delegated to Coordinator) ---

    async def broadcast_shutdown(self):
        """Initiate system-wide shutdown sequence. Delegates to ShutdownCoordinator."""
        if self.shutdown_in_progress:
            logger.warning("Shutdown broadcast requested, but already in progress.")
            return
        
        # Set flag immediately to prevent race conditions
        self.shutdown_in_progress = True 
        try:
            shutdown_result = await self.coordinator.broadcast_shutdown(shutdown_in_progress_flag=False) # Pass False as we just set the flag
            if not shutdown_result:
                 logger.error("Shutdown sequence initiated but did not complete successfully.")
                 # Reset flag only if shutdown failed critically and didn't exit?
                 # Emergency shutdown should handle exit. If it returns, maybe reset?
                 # self.shutdown_in_progress = False # Re-evaluate this based on coordinator logic
        except Exception as e:
            logger.critical(f"Critical error during broadcast_shutdown orchestration: {e}", exc_info=True)
            # Attempt emergency shutdown if the coordinator itself failed badly
            try:
                await self.coordinator._emergency_shutdown(f"Coordinator failed during broadcast: {e}")
            except Exception as emerg_e:
                 logger.critical(f"Failed to even trigger emergency shutdown: {emerg_e}")
                 sys.exit(1) # Last resort exit
        finally:
            # Should the flag be reset here? Only if shutdown allows retry?
            # For now, assume a shutdown attempt means it stays in progress or exits.
            pass
            
    def handle_shutdown_signal(self, signum, frame):
        """Handle system shutdown signals (SIGTERM, SIGINT)."""
        if not self.shutdown_in_progress:
            logger.info(f"Received shutdown signal: {signum}. Initiating broadcast...")
            # Use asyncio.create_task or similar if called from sync context?
            # Or ensure signal handler runs within the main loop context.
            # If running in main thread's loop:
            asyncio.ensure_future(self.broadcast_shutdown())
            # If potentially called from another thread, use run_coroutine_threadsafe
            # loop = asyncio.get_running_loop() # Get loop if possible
            # loop.call_soon_threadsafe(asyncio.create_task, self.broadcast_shutdown())
        else:
            logger.warning(f"Received shutdown signal {signum}, but shutdown already in progress.")

    async def stop(self): # Add a method to gracefully stop the bus itself
        """Gracefully stop the AgentBus and its components."""
        logger.info("Stopping Agent Bus...")
        # Ensure shutdown sequence is called if not already
        if not self.shutdown_in_progress:
             await self.broadcast_shutdown()
        # Stop the dispatcher task
        if self._dispatcher_task and not self._dispatcher_task.done():
            await self._dispatcher.stop()
            try:
                await self._dispatcher_task # Wait for it to finish
            except asyncio.CancelledError:
                logger.info("Dispatcher task cancelled.")
        logger.info("Agent Bus stopped.")


# Initialize global agent bus
agent_bus = AgentBus()

if __name__ == "__main__":
    """Example usage: AgentBus Capability & Coordination Demo
    
    🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
    
    This demo showcases:
    1. Agent registration and lifecycle
    2. Event handling and dispatch
    3. Status updates and capability queries
    4. Simulated autonomous task coordination kickoff
    5. Shutdown sequence with diagnostics
    6. Error handling and recovery
    
    Run with:
        python core/agent_bus.py                 # Normal demo
        python core/agent_bus.py --debug         # Debug output
        python core/agent_bus.py --error-cases   # Include error scenarios
    """
    import asyncio
    import argparse
    from datetime import datetime
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='AgentBus Capability & Coordination Demo')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--error-cases', action='store_true', help='Include error scenarios')
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    async def event_handler(event: Event):
        """Example event handler that prints events and simulates responses."""
        print(f"\n📢 Event Received [{datetime.now().isoformat()}]:")
        print(f"  Type: {event.type.value}")
        print(f"  Source: {event.source_id}")
        print(f"  Data: {event.data}")
        if args.debug:
            print(f"  Priority: {event.priority}")
            print(f"  Timestamp: {event.timestamp}")
            
        # Simulate basic response to task requests for demo
        if event.type == EventType.TASK and event.data.get("type") == "task_request":
            print("  ➡️ Simulating task acceptance...")
            await agent_bus.update_agent_status(
                event.source_id,
                AgentStatus.BUSY,
                task=event.data.get("task_id", "unknown_task")
            )
            # Simulate updating mailbox/board (represented by event dispatch)
            response_event = Event(
                type=EventType.TASK,
                source_id="agent_bus",
                priority=1
            )
            response_event.data = {
                "type": "task_accepted",
                "task_id": event.data.get("task_id"),
                "assigned_agent": event.source_id
            }
            await agent_bus._dispatcher.dispatch_event(response_event)
            print("  ✓ Task acceptance simulated.")

    async def demo_error_cases():
        """Demonstrate error handling and recovery."""
        print("\n⚠️ Starting Error Cases Demo...")
        
        try:
            # 1. Duplicate agent registration
            print("\nTesting duplicate registration:")
            await agent_bus.register_agent("error_agent", ["test"])
            try:
                await agent_bus.register_agent("error_agent", ["test"])
            except ValueError as e:
                print(f"✓ Caught expected error: {e}")
            
            # 2. Invalid agent operations
            print("\nTesting invalid agent operations:")
            try:
                await agent_bus.update_agent_status("nonexistent", AgentStatus.BUSY)
            except ValueError as e:
                print(f"✓ Caught expected error: {e}")
            
            # 3. Shutdown with agent in error state
            print("\nTesting shutdown with error state:")
            await agent_bus.update_agent_status(
                "error_agent",
                AgentStatus.ERROR,
                error="Simulated critical error"
            )
            try:
                await agent_bus.broadcast_shutdown()
            except RuntimeError as e:
                print(f"✓ Caught expected error: {e}")
            
            # 4. Resource cleanup verification
            print("\nTesting resource verification:")
            # Create a "stuck" temp file
            temp_path = Path("temp/stuck_file.txt")
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.write_text("stuck data")
            
            diagnostics = await agent_bus.run_pre_shutdown_diagnostics()
            print("\nResource Check Results:")
            print(json.dumps(diagnostics["checks"]["resources"], indent=2))
            
            # Cleanup
            temp_path.unlink()
            temp_path.parent.rmdir()
            
        except Exception as e:
            print(f"❌ Unexpected error in error cases demo: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    async def demo_agent_lifecycle():
        """Demonstrate agent registration, status updates, and queries."""
        print("\n🚀 Starting Agent Lifecycle Demo...")
        
        try:
            # Register event handler
            agent_bus.register_handler(EventType.SYSTEM, event_handler)
            print("✓ Registered event handler")
            
            # Register agents with capabilities
            await agent_bus.register_agent("agent1", ["nlp", "planning"])
            await agent_bus.register_agent("agent2", ["vision", "nlp"])
            await agent_bus.register_agent("agent3", ["planning", "execution"])
            print("✓ Registered 3 agents with capabilities")
            
            if args.debug:
                print("\n🔍 Internal Agent State:")
                print(json.dumps(agent_bus.agents, indent=2))
            
            # Query available agents
            nlp_agents = await agent_bus.get_available_agents(["nlp"])
            print(f"\n🔍 Agents with NLP capability: {nlp_agents}")
            
            # Update agent status
            await agent_bus.update_agent_status(
                "agent1",
                AgentStatus.BUSY,
                task="complex_planning_task"
            )
            print("✓ Updated agent1 status to BUSY")
            
            # Query again to show status effect
            nlp_agents = await agent_bus.get_available_agents(["nlp"])
            print(f"🔍 Available NLP agents after update: {nlp_agents}")
            
            # Show all agent info
            all_agents = await agent_bus.get_all_agents()
            print("\n📊 Current Agent Status:")
            for agent_id, info in all_agents.items():
                print(f"  {agent_id}:")
                print(f"    Status: {info['status']}")
                print(f"    Capabilities: {info['capabilities']}")
                print(f"    Current Task: {info['current_task']}")
                
        except Exception as e:
            print(f"❌ Error in agent lifecycle demo: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    async def demo_autonomous_coordination():
        """Demonstrate kicking off a task and coordinating via events."""
        print("\n🤖 Starting Autonomous Coordination Demo...")
        
        try:
            # Ensure an agent is ready
            if "agent1" not in agent_bus.agents:
                 await agent_bus.register_agent("agent1", ["planning"])
            await agent_bus.update_agent_status("agent1", AgentStatus.IDLE)
            print("✓ Agent 'agent1' ready for task.")
            
            # Register a handler specifically for TASK events if needed
            # (The main event_handler already covers this for the demo)
            # agent_bus.register_handler(EventType.TASK, task_event_handler)
            
            # Simulate agent1 initiating a task
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            print(f"\n🚀 Simulating 'agent1' requesting task: {task_id}")
            task_event = Event(
                type=EventType.TASK,
                source_id="agent1",
                priority=2 # Example priority
            )
            task_event.data = {
                "type": "task_request",
                "task_id": task_id,
                "description": "Plan a complex multi-step operation",
                "required_capabilities": ["planning"]
            }
            
            # Dispatch the event through the bus
            await agent_bus._dispatcher.dispatch_event(task_event)
            print(f"✓ Task request event dispatched for {task_id}.")
            
            # Allow time for event processing (in real scenario, this is async)
            await asyncio.sleep(0.1)
            
            # Check agent status after coordination
            agent1_info = await agent_bus.get_agent_info("agent1")
            print("\n📊 Agent 'agent1' status after task request:")
            print(f"  Status: {agent1_info['status']}")
            print(f"  Current Task: {agent1_info['current_task']}")
            
            # Simulate task completion
            print(f"\n✅ Simulating 'agent1' completing task: {task_id}")
            await agent_bus.update_agent_status("agent1", AgentStatus.IDLE)
            completion_event = Event(
                type=EventType.TASK,
                source_id="agent1",
                priority=1
            )
            completion_event.data = {
                "type": "task_completed",
                "task_id": task_id,
                "result": "Planning complete, steps generated."
            }
            await agent_bus._dispatcher.dispatch_event(completion_event)
            print("✓ Task completion event dispatched.")
            await asyncio.sleep(0.1) # Allow processing

        except Exception as e:
            print(f"❌ Error in autonomous coordination demo: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()

    async def demo_shutdown_sequence():
        """Demonstrate shutdown sequence with diagnostics."""
        print("\n🛑 Starting Shutdown Sequence Demo...")
        
        try:
            # Create required directories for diagnostics
            for dir_name in ["memory", "logs", "config", "temp"]:
                path = Path(dir_name)
                path.mkdir(parents=True, exist_ok=True)
                if args.debug:
                    print(f"✓ Created directory: {dir_name}")
            
            # Create agent state files
            memory_path = Path("memory/agents")
            memory_path.mkdir(parents=True, exist_ok=True)
            
            for agent_id in ["agent1", "agent2", "agent3"]:
                agent_dir = memory_path / agent_id
                agent_dir.mkdir(parents=True, exist_ok=True)
                
                # Create mailbox.json
                mailbox = {
                    "agent_id": agent_id,
                    "status": "idle",
                    "pending_operations": []
                }
                (agent_dir / "mailbox.json").write_text(json.dumps(mailbox))
                
                # Create task_list.json
                tasks = [{
                    "task_id": "task1",
                    "status": "completed",
                    "priority": 1
                }]
                (agent_dir / "task_list.json").write_text(json.dumps(tasks))
                
                if args.debug:
                    print(f"✓ Created state files for: {agent_id}")
            
            # Run pre-shutdown diagnostics
            print("\n📊 Running Pre-shutdown Diagnostics...")
            diagnostics = await agent_bus.run_pre_shutdown_diagnostics()
            
            if args.debug:
                print("\nDetailed Diagnostics:")
                print(json.dumps(diagnostics, indent=2))
            else:
                print("\nDiagnostic Results:")
                print(f"  Passed: {diagnostics['total_passed']}")
                print(f"  Failed: {diagnostics['total_failed']}")
                if diagnostics['critical_warnings']:
                    print("\n⚠️ Critical Warnings:")
                    for warning in diagnostics['critical_warnings']:
                        print(f"  - {warning}")
            
            # Prepare for shutdown
            print("\n🔄 Preparing for shutdown...")
            for agent_id in ["agent1", "agent2", "agent3"]:
                await agent_bus.update_agent_status(agent_id, AgentStatus.SHUTDOWN_READY)
            
            # Initiate shutdown
            print("\n⏳ Initiating shutdown sequence...")
            try:
                await agent_bus.broadcast_shutdown()
                print("✅ Shutdown completed successfully")
            except Exception as e:
                print(f"❌ Shutdown failed: {e}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
            
        except Exception as e:
            print(f"❌ Error in shutdown sequence demo: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        finally:
            # Clean up test directories
            for dir_name in ["memory", "logs", "config", "temp"]:
                path = Path(dir_name)
                if path.exists():
                    shutil.rmtree(path)
                    if args.debug:
                        print(f"✓ Cleaned up directory: {dir_name}")
    
    async def run_demo():
        """Run the complete AgentBus capability and coordination demo."""
        try:
            print("\n=== 🚀 AgentBus Capability & Coordination Demo ===")
            print("Debug mode:", "✅ Enabled" if args.debug else "❌ Disabled")
            print("Error cases:", "✅ Included" if args.error_cases else "❌ Excluded")
            print("=" * 50)
            
            # Demo 1: Agent Lifecycle
            await demo_agent_lifecycle()
            
            # Demo 2: Autonomous Coordination Kickoff
            await demo_autonomous_coordination()
            
            # Demo 3: Error Cases (if enabled)
            if args.error_cases:
                await demo_error_cases()
            
            # Demo 4: Shutdown Sequence
            await demo_shutdown_sequence()
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        finally:
            # Stop the event dispatcher
            await agent_bus._dispatcher.stop()
            if args.debug:
                print("\n✓ Event dispatcher stopped")
    
    # Run the demo
    asyncio.run(run_demo()) 