"""Agent Worker Loop for Agent 4 (Task Orchestrator)."""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

# Ensure core modules are importable
try:
    from core.agent_bus import agent_bus, AgentStatus, Event, EventType
    from dreamos.coordinator import (AgentContext, AgentDomain, AgentState, AgentMessage,
                                     CoordinationEvent, CoordinationStatus)
    from core.utils.file_manager import FileManager
    from core.utils.system import SystemUtils
except ImportError as e:
    print(f"Error importing core modules: {e}. Ensure PYTHONPATH is set.")
    current_dir = Path(__file__).parent
    core_path = current_dir.parent.parent / 'core'
    dreamos_path = current_dir.parent.parent / 'dreamos'
    sys.path.insert(0, str(core_path.parent))
    sys.path.insert(0, str(dreamos_path.parent))
    
    try:
        from core.agent_bus import agent_bus, AgentStatus, Event, EventType
        from dreamos.coordinator import (AgentContext, AgentDomain, AgentState, AgentMessage,
                                         CoordinationEvent, CoordinationStatus)
        from core.utils.file_manager import FileManager
        from core.utils.system import SystemUtils
    except ImportError:
        print("Failed to import core modules even after path adjustment. Exiting.")
        sys.exit(1)

# --- Configuration ---
AGENT_ID = "agent_4"
AGENT_DOMAIN = AgentDomain.TASK_ORCHESTRATOR
AGENT_CAPABILITIES = ["task_dispatch", "state_monitoring", "agent_coordination", "priority_management"]
HEARTBEAT_INTERVAL = 5
TASK_CHECK_INTERVAL = 1 # Orchestrator needs to be responsive
MAX_TASK_RETRIES = 0 # Orchestration tasks shouldn't typically fail/retry
LOG_LEVEL = logging.INFO

# --- Setup Logging ---
log_path = Path(f"logs/agent_{AGENT_ID}.log")
log_path.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_path)
    ]
)
logger = logging.getLogger(f"AgentWorker_{AGENT_ID}")

class AgentWorker:
    """Manages the lifecycle and task execution for Agent 4 (Task Orchestrator)."""

    def __init__(self, agent_id: str, domain: AgentDomain, capabilities: List[str]):
        self.agent_id = agent_id
        self.domain = domain
        self.capabilities = capabilities
        self.running = False
        self.shutdown_requested = False
        self._lock = asyncio.Lock()

        # File/Directory Paths
        self.agent_dir = Path(f"agents/{self.agent_id}")
        self.memory_dir = self.agent_dir / "memory"
        self.mailbox_dir = self.agent_dir / "mailbox"
        self.inbox_dir = self.mailbox_dir / "inbox"
        self.outbox_dir = self.mailbox_dir / "outbox"
        self.task_list_path = self.agent_dir / "task_list.json" # Own tasks
        self.global_task_queue_path = Path("state/global_task_queue.json") # Example global queue
        self.context_path = self.memory_dir / "context.json"

        self._ensure_dirs()

        self.context: Optional[AgentContext] = None
        self.tasks: List[Dict] = [] # Tasks assigned TO the orchestrator itself
        self.global_tasks: List[Dict] = [] # Tasks TO BE orchestrated
        self.current_task_id: Optional[str] = None # For orchestrator's own tasks

        self.file_mgr = FileManager()
        self.sys_utils = SystemUtils()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _ensure_dirs(self):
        for path in [self.agent_dir, self.memory_dir, self.mailbox_dir, self.inbox_dir, self.outbox_dir, self.global_task_queue_path.parent]:
            path.mkdir(parents=True, exist_ok=True)

    async def _load_context(self) -> None:
        """Load agent context from file or create default."""
        async with self._lock:
            if self.context_path.exists():
                try:
                    content = await self.file_mgr.read_file(str(self.context_path))
                    data = json.loads(content)
                    self.context = AgentContext(
                        domain=AgentDomain(data.get("domain", self.domain.value)),
                        agent_id=data.get("agent_id", self.agent_id),
                        state=AgentState(data.get("state", AgentState.IDLE.value)),
                        current_task=data.get("current_task"),
                        memory=data.get("memory", {}),
                        last_update=datetime.fromisoformat(data.get("last_update")) if data.get("last_update") else datetime.utcnow(),
                        dependencies=data.get("dependencies", [])
                    )
                    logger.info(f"Loaded context from {self.context_path}")
                except Exception as e:
                    logger.error(f"Failed to load context: {e}. Creating default.")
                    self._create_default_context()
            else:
                logger.info("Context file not found. Creating default.")
                self._create_default_context()
            
            if self.context.state == AgentState.BUSY and not self.context.current_task:
                 self.context.state = AgentState.IDLE
            elif self.context.state in [AgentState.ERROR, AgentState.BLOCKED]:
                 self.context.state = AgentState.IDLE
            self.context.last_update = datetime.utcnow()

    def _create_default_context(self):
        self.context = AgentContext(
            domain=self.domain,
            agent_id=self.agent_id,
            state=AgentState.IDLE,
            current_task=None,
            memory={},
            last_update=datetime.utcnow(),
            dependencies=[]
        )

    async def _save_context(self) -> None:
        if not self.context: return
        async with self._lock:
            try:
                context_data = {
                    "domain": self.context.domain.value,
                    "agent_id": self.context.agent_id,
                    "state": self.context.state.value,
                    "current_task": self.context.current_task,
                    "memory": self.context.memory,
                    "last_update": self.context.last_update.isoformat(),
                    "dependencies": self.context.dependencies
                }
                await self.file_mgr.write_file(str(self.context_path), json.dumps(context_data, indent=2))
                logger.debug(f"Saved context to {self.context_path}")
            except Exception as e:
                logger.error(f"Failed to save context: {e}")

    async def _register_with_bus(self) -> None:
        if not self.context: await self._load_context()
        try:
            await agent_bus.register_agent(self.agent_id, self.capabilities)
            logger.info(f"Successfully registered with AgentBus.")
            await self._update_status_on_bus(self.context.state)
            # Orchestrator specific: Register handler for task requests/completions?
            agent_bus.register_handler(EventType.TASK, self.handle_task_event)
            agent_bus.register_handler(EventType.SYSTEM, self.handle_system_event)
            logger.info("Registered TASK and SYSTEM event handlers.")
        except ValueError:
             logger.warning(f"Agent {self.agent_id} already registered. Syncing state.")
             await self._update_status_on_bus(self.context.state)
        except Exception as e:
            logger.error(f"Failed to register with AgentBus: {e}")

    async def _update_status_on_bus(self, status: AgentState, task_id: Optional[str] = None, error: Optional[str] = None) -> None:
        async with self._lock:
            if not self.context: return
            self.context.state = status
            self.context.current_task = task_id if status == AgentState.BUSY else None
            self.context.last_update = datetime.utcnow()
            await self._save_context()
            try:
                await agent_bus.update_agent_status(
                    self.agent_id, AgentStatus[status.name], task=task_id, error=error
                )
                logger.info(f"Updated status on AgentBus: {status.value}" + (f" (Task: {task_id})" if task_id else ""))
            except Exception as e:
                logger.error(f"Failed to update status on AgentBus: {e}")

    async def _send_event(self, event_type: EventType, data: Dict[str, Any], priority: int = 1):
        try:
            event = Event(type=event_type, source_id=self.agent_id, priority=priority)
            event.data = data
            await agent_bus._dispatcher.dispatch_event(event)
            logger.debug(f"Sent event {event_type.name} with data: {data}")
        except Exception as e:
            logger.error(f"Failed to send event {event_type.name}: {e}")
            
    async def _send_message_to_agent(self, target_agent_id: str, message_type: str, content: Dict) -> None:
        """Send a message directly to an agent's mailbox file."""
        message = {
             "source": self.agent_id,
             "target": target_agent_id,
             "message_type": message_type,
             "content": content,
             "timestamp": datetime.utcnow().isoformat(),
             "message_id": f"msg_{uuid.uuid4().hex[:12]}" 
        }
        try:
            target_inbox = Path(f"agents/{target_agent_id}/mailbox/inbox")
            target_inbox.mkdir(parents=True, exist_ok=True) # Ensure dir exists
            msg_path = target_inbox / f"{message['message_id']}.json"
            await self.file_mgr.write_file(str(msg_path), json.dumps(message, indent=2))
            logger.info(f"Sent message type '{message_type}' to agent {target_agent_id}")
        except Exception as e:
            logger.error(f"Failed to send message to agent {target_agent_id}: {e}")

    async def _check_mailbox(self) -> None:
        """Check for messages specifically for the orchestrator."""
        try:
            for msg_file in self.inbox_dir.glob("*.json"):
                logger.info(f"Processing message file: {msg_file.name}")
                try:
                    content = await self.file_mgr.read_file(str(msg_file))
                    message_data = json.loads(content)
                    if not all(k in message_data for k in ["source", "message_type", "content"]):
                        logger.warning(f"Invalid message format: {msg_file.name}")
                        continue

                    await self._process_message(message_data)
                    await self.file_mgr.delete_file(str(msg_file))
                    logger.debug(f"Processed and deleted message: {msg_file.name}")
                except json.JSONDecodeError: logger.error(f"Invalid JSON: {msg_file.name}")
                except Exception as e: logger.error(f"Error processing message {msg_file.name}: {e}")
        except Exception as e: logger.error(f"Error checking mailbox: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Handle messages directed to the orchestrator."""
        msg_type = message.get("message_type")
        content = message.get("content", {})
        
        if msg_type == "shutdown_directive":
            phase = content.get("directive", {}).get("phase")
            logger.info(f"Received shutdown directive for phase: {phase}")
            if phase == "cleanup":
                self.shutdown_requested = True
                await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
        elif msg_type == "new_task_request": # External system adding a task
             task_data = content.get("task")
             if task_data:
                 logger.info(f"Received external task request: {task_data.get('task_id')}")
                 await self._add_global_task(task_data) 
        else:
            logger.debug(f"Received unhandled message type: {msg_type}")
            
    async def handle_task_event(self, event: Event):
        """Handle TASK events from the bus (e.g., requests from other agents)."""
        event_data = event.data
        event_subtype = event_data.get("type")
        
        logger.debug(f"Received TASK event: Type={event_subtype}, Source={event.source_id}")
        
        if event_subtype == "task_request":
            # Agent requesting a task to be done (needs orchestration)
            required_caps = event_data.get("required_capabilities", [])
            task_id = event_data.get("task_id", f"task_{uuid.uuid4().hex[:8]}")
            task_data = {
                "task_id": task_id,
                "description": event_data.get("description", "Task request from agent"),
                "status": "pending",
                "priority": event.priority,
                "params": event_data.get("params", {}),
                "required_capabilities": required_caps,
                "source_agent": event.source_id,
                "creation_time": event.timestamp.isoformat()
            }
            logger.info(f"Received task request '{task_id}' from {event.source_id} via event bus.")
            await self._add_global_task(task_data)
            
        elif event_subtype == "task_log_request":
             # Agent completed a self-assigned task (like usage block injection)
             # Log it to the global list/state
             task_payload = event_data.copy()
             task_payload.pop("type", None) # Remove internal type
             logger.info(f"Logging completed task from {event.source_id}: {task_payload.get('task_id')}")
             # TODO: Persist this to a global log or completed task list
             # For now, maybe add to orchestrator's memory?
             async with self._lock:
                 self.context.memory.setdefault("completed_tasks", []).append(task_payload)
             await self._save_context()
             
        elif event_subtype == "task_completion":
             # Agent finished an orchestrated task
             task_id = event_data.get("task_id")
             agent_id = event_data.get("agent_id")
             result = event_data.get("result")
             logger.info(f"Agent {agent_id} completed task {task_id}. Result: {str(result)[:100]}...")
             # Update global task status if tracked here
             await self._update_global_task_status(task_id, "complete", result=result)
             # Potentially trigger verification task
             await self._send_message_to_agent(
                 "agent_3", # Assuming agent_3 is the verifier
                 "task_completion_notification",
                 {"task_result": event_data}
             )

    async def handle_system_event(self, event: Event):
        """Handle SYSTEM events (e.g., agent status changes, board updates)."""
        event_data = event.data
        event_subtype = event_data.get("type")
        logger.debug(f"Received SYSTEM event: Type={event_subtype}, Source={event.source_id}")
        
        if event_subtype == "agent_registered":
             logger.info(f"Agent registered: {event_data.get('agent_id')} with caps: {event_data.get('capabilities')}")
        elif event_subtype == "status_change":
             agent_id = event_data.get('agent_id')
             new_status = event_data.get('status')
             logger.info(f"Agent {agent_id} status changed to {new_status}")
             # If agent becomes IDLE, check if we can assign a pending task
             if new_status == AgentStatus.IDLE:
                 await self.orchestrate_tasks() 
        elif event_subtype == "project_board_update":
             # Log or process project board updates
             component = event_data.get("component")
             agent = event_data.get("agent")
             logger.info(f"Project board update for {component} by {agent}: {event_data}")
             # TODO: Update actual project board state
        elif event_subtype == "usage_block_status":
            # Log the status reported by an agent after usage block injection
            file_path = event_data.get("file")
            status = event_data.get("status")
            logger.info(f"Usage block status for {file_path}: {status}")
            # TODO: Update global state / project board based on this

    async def _load_global_tasks(self) -> None:
        """Load tasks from the global task queue file."""
        async with self._lock:
            if not self.global_task_queue_path.exists():
                self.global_tasks = []
                return
            try:
                content = await self.file_mgr.read_file(str(self.global_task_queue_path))
                self.global_tasks = json.loads(content)
                # Filter for only pending tasks? Or keep all history?
                # self.global_tasks = [t for t in self.global_tasks if t.get("status") == "pending"]
                logger.debug(f"Loaded {len(self.global_tasks)} tasks from global queue {self.global_task_queue_path}")
            except json.JSONDecodeError: logger.error(f"Invalid JSON: {self.global_task_queue_path}"); self.global_tasks = []
            except Exception as e: logger.error(f"Failed to load global tasks: {e}"); self.global_tasks = []

    async def _save_global_tasks(self) -> None:
        """Save the current global task list to file."""
        async with self._lock:
            try:
                await self.file_mgr.write_file(str(self.global_task_queue_path), json.dumps(self.global_tasks, indent=2))
                logger.debug(f"Saved {len(self.global_tasks)} tasks to global queue {self.global_task_queue_path}")
            except Exception as e: logger.error(f"Failed to save global tasks: {e}")
            
    async def _add_global_task(self, task_data: Dict) -> None:
        """Add a task to the global queue."""
        # Basic validation
        required = ["task_id", "description", "status", "priority"]
        if not all(k in task_data for k in required): 
             logger.error(f"Attempted to add invalid global task: {task_data}"); return
             
        async with self._lock:
            task_id = task_data["task_id"]
            if any(t["task_id"] == task_id for t in self.global_tasks):
                logger.warning(f"Global task {task_id} already exists. Ignoring.")
                return
                
            task_data["status"] = "pending" # Ensure status is pending
            self.global_tasks.append(task_data)
            logger.info(f"Added task {task_id} to global queue.")
            await self._save_global_tasks()
            # Trigger orchestration attempt immediately
            await self.orchestrate_tasks()
            
    async def _update_global_task_status(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update status of a task in the global list."""
        updated = False
        async with self._lock:
            for task in self.global_tasks:
                if task["task_id"] == task_id:
                    task["status"] = status
                    task["last_update"] = datetime.utcnow().isoformat()
                    if result: task["result"] = result
                    if error: task["error"] = error
                    updated = True
                    logger.info(f"Updated global task {task_id} status to {status}")
                    break
            if updated:
                await self._save_global_tasks()
                # If task failed, maybe log or create a recovery task?
            else:
                 logger.warning(f"Global task {task_id} not found for status update.")

    async def orchestrate_tasks(self): 
        """Attempt to assign pending global tasks to available agents."""
        logger.debug("Running task orchestration cycle...")
        assigned_count = 0
        async with self._lock:
            # Get current agent statuses from AgentBus
            try:
                all_agents_info = await agent_bus.get_all_agents()
            except Exception as e:
                logger.error(f"Failed to get agent info from bus for orchestration: {e}")
                return
                
            idle_agents = { 
                agent_id: info for agent_id, info in all_agents_info.items() 
                if info["status"] == AgentStatus.IDLE
            }
            
            if not idle_agents:
                 logger.debug("No idle agents available for task assignment.")
                 return

            pending_global_tasks = sorted(
                [t for t in self.global_tasks if t.get("status") == "pending"],
                key=lambda t: t.get("priority", 5) # Sort by priority
            )

            if not pending_global_tasks:
                 logger.debug("No pending global tasks to orchestrate.")
                 return

            logger.info(f"Found {len(pending_global_tasks)} pending tasks and {len(idle_agents)} idle agents.")

            assigned_agent_ids = set() # Track agents assigned in this cycle
            
            for task in pending_global_tasks:
                task_id = task["task_id"]
                required_caps = task.get("required_capabilities", [])
                logger.debug(f"Attempting to assign task {task_id} requiring caps: {required_caps}")
                
                best_agent_id = None
                for agent_id, agent_info in idle_agents.items():
                    if agent_id in assigned_agent_ids: continue # Already assigned this cycle
                    
                    agent_caps = agent_info.get("capabilities", [])
                    if all(cap in agent_caps for cap in required_caps):
                        best_agent_id = agent_id
                        logger.debug(f"Found suitable agent {agent_id} for task {task_id}")
                        break # Assign to the first suitable idle agent
                        
                if best_agent_id:
                    logger.info(f"Assigning task {task_id} to agent {best_agent_id}")
                    # Update global task status to indicate assignment attempt
                    task["status"] = "assigning"
                    task["assigned_agent_id"] = best_agent_id
                    task["assignment_time"] = datetime.utcnow().isoformat()
                    
                    # Send assignment message directly to agent's mailbox
                    await self._send_message_to_agent(
                        best_agent_id,
                        "task_assignment",
                        {"task": task}
                    )
                    assigned_agent_ids.add(best_agent_id)
                    assigned_count += 1
                    # We expect the agent to update its status to BUSY via the bus
                else:
                    logger.warning(f"No suitable idle agent found for task {task_id} requiring caps: {required_caps}")

            if assigned_count > 0:
                 logger.info(f"Assigned {assigned_count} tasks in this orchestration cycle.")
                 await self._save_global_tasks() # Save status changes ('assigning')

    async def _execute_task(self, task: Dict) -> None:
        """Execute tasks assigned TO the orchestrator itself (e.g., monitoring)."""
        task_id = task["task_id"]
        description = task.get("description", "")
        task_type = task.get("task_type", "")
        
        self.current_task_id = task_id
        await self._update_status_on_bus(AgentState.BUSY, task_id=task_id)
        await self._update_task_status(task_id, "running") # Update orchestrator's own task list

        logger.info(f"Starting execution of orchestrator task: {task_id} - {description}")
        start_time = time.time()
        result_data = None
        error_msg = None
        
        try:
            if task_type == "monitor_agent_health":
                logger.info("Running agent health monitoring task...")
                all_agents = await agent_bus.get_all_agents()
                stuck_agents = []
                now = datetime.utcnow()
                for agent_id, info in all_agents.items():
                     last_update_str = info.get("last_update") # Assuming bus provides this
                     if last_update_str:
                         last_update = datetime.fromisoformat(last_update_str)
                         if (now - last_update).total_seconds() > 60 * 5: # Example: 5 minutes timeout
                             stuck_agents.append({"agent_id": agent_id, "status": info["status"], "last_update": last_update_str})
                
                if stuck_agents:
                     logger.warning(f"Found potentially stuck agents: {stuck_agents}")
                     # TODO: Trigger recovery actions
                result_data = {"status": "complete", "stuck_agents_found": len(stuck_agents), "details": stuck_agents}
                await self._update_task_status(task_id, "complete", result=result_data)
            else:
                 logger.warning(f"Orchestrator received unknown task type: {task_type}. Completing.")
                 result_data = {"status": "success", "message": f"Executed unknown task: {description}"}
                 await self._update_task_status(task_id, "complete", result=result_data)
                 
            duration = time.time() - start_time
            logger.info(f"Successfully completed orchestrator task: {task_id} in {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Orchestrator task {task_id} failed after {duration:.2f}s: {e}"
            logger.error(error_msg, exc_info=True)
            await self._update_task_status(task_id, "failed", error=error_msg)
            await self._update_status_on_bus(AgentState.ERROR, error=error_msg)
        finally:
             if self.current_task_id == task_id:
                 self.current_task_id = None
                 if self.context.state != AgentState.ERROR and not self.shutdown_requested:
                     await self._update_status_on_bus(AgentState.IDLE)

    def _handle_signal(self, signum, frame):
        logger.warning(f"Received signal {signum}. Initiating shutdown...")
        self.shutdown_requested = True

    async def _handle_shutdown(self) -> None:
        logger.info("Starting graceful shutdown...")
        if self.context.state == AgentState.BUSY and self.current_task_id:
            logger.warning(f"Shutdown requested while task {self.current_task_id} is running...")
            
        async with self._lock:
            self.context.state = AgentState.TERMINATED
            await self._save_context()
            # Save global tasks one last time?
            # await self._save_global_tasks()
            
        await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
        await self._send_event(EventType.SYSTEM, {"type": "agent_shutdown", "agent_id": self.agent_id})
        logger.info(f"Agent {self.agent_id} shutdown complete.")
        self.running = False

    async def run(self) -> None:
        logger.info(f"Starting Agent Worker for {self.agent_id} in domain {self.domain.value}")
        self.running = True
        await self._load_context()
        await self._register_with_bus() # This registers event handlers
        await self._load_global_tasks() # Load tasks needing orchestration
        # await self._load_tasks() # Load tasks for orchestrator itself (if any)
        last_heartbeat = time.time()
        last_orchestration = time.time()

        while self.running and not self.shutdown_requested:
            try:
                await self._check_mailbox()
                if self.shutdown_requested: break
                
                # Regularly try to orchestrate pending tasks
                now = time.time()
                if now - last_orchestration > TASK_CHECK_INTERVAL:
                    await self.orchestrate_tasks()
                    last_orchestration = now
                
                # Check for tasks assigned TO the orchestrator itself
                # (Could add _load_tasks() and _get_next_task() calls here if needed)
                # For now, primarily event-driven and periodic orchestration
                
                # Heartbeat
                if now - last_heartbeat > HEARTBEAT_INTERVAL:
                    async with self._lock:
                         if self.context.state != AgentState.BUSY:
                             await self._update_status_on_bus(self.context.state)
                    last_heartbeat = now

                await asyncio.sleep(0.5) # Short sleep to prevent busy-waiting

            except asyncio.CancelledError:
                logger.warning("Main loop cancelled.")
                self.shutdown_requested = True
            except Exception as e:
                logger.error(f"Unhandled error in main loop: {e}", exc_info=True)
                await self._update_status_on_bus(AgentState.ERROR, error=f"Unhandled loop error: {e}")
                await asyncio.sleep(10)

        await self._handle_shutdown()

if __name__ == "__main__":
    logger.info(f"Initializing Agent Worker {AGENT_ID}...")
    worker = AgentWorker(AGENT_ID, AGENT_DOMAIN, AGENT_CAPABILITIES)
    loop = asyncio.get_event_loop()
    main_task = None
    try:
        # Start agent bus dispatcher if not running (usually handled elsewhere)
        # if not agent_bus._dispatcher._running:
        #     loop.create_task(agent_bus._dispatcher.start())
            
        main_task = loop.create_task(worker.run())
        loop.run_until_complete(main_task)
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt received. Shutting down worker...")
        worker.shutdown_requested = True
        if main_task and not main_task.done():
             loop.run_until_complete(main_task)
    except Exception as e:
         logger.critical(f"Agent worker crashed: {e}", exc_info=True)
    finally:
        logger.info(f"Agent Worker {AGENT_ID} process finished.")
        # Avoid stopping dispatcher here if other agents are running
        # loop.run_until_complete(agent_bus._dispatcher.stop())
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)
        logging.shutdown() 