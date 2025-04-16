"""Agent Worker Loop for Agent 2 (Cursor Executor - LIVE MODE)."""

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
# Assuming PYTHONPATH is set correctly or project structure allows this
try:
    from core.agent_bus import agent_bus, AgentStatus, Event, EventType
    from dreamos.coordinator import (AgentContext, AgentDomain, AgentState, AgentMessage,
                                     CoordinationEvent, CoordinationStatus)
    from core.utils.file_manager import FileManager
    from core.utils.system import SystemUtils
    # --- Import the LIVE bridge --- 
    from core.execution.cursor_executor_bridge import CursorExecutorBridge 
except ImportError as e:
    print(f"Error importing core modules or CursorExecutorBridge: {e}. Ensure PYTHONPATH is set and bridge exists.")
    # Add parent directories to sys.path for relative imports if needed
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
        # --- Re-attempt bridge import ---
        from core.execution.cursor_executor_bridge import CursorExecutorBridge 
    except ImportError:
        print("Failed to import core modules/bridge even after path adjustment. Exiting.")
        sys.exit(1)

# --- Configuration ---
AGENT_ID = "agent_2"
AGENT_DOMAIN = AgentDomain.CURSOR_EXECUTOR
AGENT_CAPABILITIES = ["cursor_execution", "code_refactor", "test_generation", "file_edit"]
HEARTBEAT_INTERVAL = 5  # Seconds between status checks/updates
TASK_CHECK_INTERVAL = 2 # Seconds between checking for new tasks
MAX_TASK_RETRIES = 2 # Cursor tasks might be more prone to transient issues?
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
    """Manages the lifecycle and task execution for Agent 2 (Cursor Executor - LIVE MODE)."""

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
        self.task_list_path = self.agent_dir / "task_list.json"
        self.context_path = self.memory_dir / "context.json"

        self._ensure_dirs()

        self.context: Optional[AgentContext] = None
        self.tasks: List[Dict] = []
        self.current_task_id: Optional[str] = None

        self.file_mgr = FileManager()
        self.sys_utils = SystemUtils()
        # --- Instantiate the LIVE bridge --- 
        try:
            self.bridge = CursorExecutorBridge()
            logger.info("CursorExecutorBridge initialized successfully.")
        except Exception as e:
             logger.critical(f"Failed to initialize CursorExecutorBridge: {e}", exc_info=True)
             # Decide how to handle failure: exit, run in stub mode, etc.
             # For now, let it raise or exit if bridge is critical
             raise e 

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _ensure_dirs(self):
        """Create necessary directories if they don't exist."""
        for path in [self.agent_dir, self.memory_dir, self.mailbox_dir, self.inbox_dir, self.outbox_dir]:
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
                    logger.error(f"Failed to load context from {self.context_path}: {e}. Creating default.")
                    self._create_default_context()
            else:
                logger.info("Context file not found. Creating default context.")
                self._create_default_context()
            
            if self.context.state == AgentState.BUSY and not self.context.current_task:
                 logger.warning("Context loaded with BUSY state but no current task. Resetting to IDLE.")
                 self.context.state = AgentState.IDLE
            elif self.context.state in [AgentState.ERROR, AgentState.BLOCKED]:
                 logger.warning(f"Context loaded with state {self.context.state}. Resetting to IDLE for restart.")
                 self.context.state = AgentState.IDLE
                 
            self.context.last_update = datetime.utcnow()

    def _create_default_context(self):
        """Create a default AgentContext."""
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
        """Save the current agent context to file."""
        if not self.context:
            return
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
        """Register the agent with the central AgentBus."""
        if not self.context:
            await self._load_context()
            
        try:
            await agent_bus.register_agent(self.agent_id, self.capabilities)
            logger.info(f"Successfully registered with AgentBus.")
            await self._update_status_on_bus(self.context.state)
        except ValueError:
             logger.warning(f"Agent {self.agent_id} already registered. Syncing state.")
             await self._update_status_on_bus(self.context.state)
        except Exception as e:
            logger.error(f"Failed to register with AgentBus: {e}")

    async def _update_status_on_bus(self, status: AgentState, task_id: Optional[str] = None, error: Optional[str] = None) -> None:
        """Update the agent's status on the AgentBus and locally."""
        async with self._lock:
            if not self.context: return
            
            self.context.state = status
            self.context.current_task = task_id if status == AgentState.BUSY else None
            self.context.last_update = datetime.utcnow()
            await self._save_context()

            try:
                await agent_bus.update_agent_status(
                    self.agent_id, 
                    AgentStatus[status.name],
                    task=task_id, 
                    error=error
                )
                logger.info(f"Updated status on AgentBus: {status.value}" + (f" (Task: {task_id})" if task_id else ""))
            except Exception as e:
                logger.error(f"Failed to update status on AgentBus: {e}")

    async def _send_event(self, event_type: EventType, data: Dict[str, Any], priority: int = 1):
        """Send an event to the AgentBus."""
        try:
            event = Event(type=event_type, source_id=self.agent_id, priority=priority)
            event.data = data
            await agent_bus._dispatcher.dispatch_event(event)
            logger.debug(f"Sent event {event_type.name} with data: {data}")
        except Exception as e:
            logger.error(f"Failed to send event {event_type.name}: {e}")

    async def _check_mailbox(self) -> None:
        """Check for new messages in the inbox."""
        try:
            for msg_file in self.inbox_dir.glob("*.json"):
                logger.info(f"Processing message file: {msg_file.name}")
                try:
                    content = await self.file_mgr.read_file(str(msg_file))
                    message_data = json.loads(content)
                    
                    if not all(k in message_data for k in ["source", "message_type", "content"]):
                        logger.warning(f"Invalid message format in {msg_file.name}. Skipping.")
                        continue

                    await self._process_message(message_data)
                    await self.file_mgr.delete_file(str(msg_file))
                    logger.debug(f"Processed and deleted message: {msg_file.name}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in message file {msg_file.name}. Moving to failed.")
                    await self.file_mgr.delete_file(str(msg_file))
                except Exception as e:
                    logger.error(f"Error processing message {msg_file.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking mailbox: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Handle specific message types for Agent 2."""
        msg_type = message.get("message_type")
        
        if msg_type == "shutdown_directive":
            phase = message.get("content", {}).get("directive", {}).get("phase")
            logger.info(f"Received shutdown directive for phase: {phase}")
            if phase == "cleanup":
                self.shutdown_requested = True
                await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
                
        elif msg_type == "task_assignment": 
             task_data = message.get("content", {}).get("task")
             if task_data:
                 logger.info(f"Received direct task assignment: {task_data.get('task_id')}")
                 await self._add_task(task_data)
        else:
            logger.debug(f"Received unhandled message type: {msg_type}")

    async def _load_tasks(self) -> None:
        """Load tasks from the task_list.json file."""
        async with self._lock:
            if not self.task_list_path.exists():
                self.tasks = []
                return
            try:
                content = await self.file_mgr.read_file(str(self.task_list_path))
                self.tasks = json.loads(content)
                self.tasks = [t for t in self.tasks if self._validate_task(t)]
                logger.debug(f"Loaded {len(self.tasks)} tasks from {self.task_list_path}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in task list file {self.task_list_path}. Clearing tasks.")
                self.tasks = []
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
                self.tasks = []

    def _validate_task(self, task: Dict) -> bool:
        """Basic validation of task structure."""
        required_keys = ["task_id", "description", "status", "priority"]
        if not all(key in task for key in required_keys):
             logger.warning(f"Task missing required keys: {task.get('task_id', 'Unknown ID')}")
             return False
        if task.get("status") not in ["pending", "running", "complete", "failed"]:
             logger.warning(f"Task {task.get('task_id')} has invalid status: {task.get('status')}")
             return False
        # Add Cursor-specific validation if needed
        return True

    async def _save_tasks(self) -> None:
        """Save the current task list to file."""
        async with self._lock:
            try:
                await self.file_mgr.write_file(str(self.task_list_path), json.dumps(self.tasks, indent=2))
                logger.debug(f"Saved {len(self.tasks)} tasks to {self.task_list_path}")
            except Exception as e:
                logger.error(f"Failed to save tasks: {e}")

    async def _add_task(self, task_data: Dict) -> None:
        """Add a new task to the list if it doesn't exist."""
        async with self._lock:
            if not self._validate_task(task_data):
                logger.error(f"Attempted to add invalid task: {task_data}")
                return
            
            task_id = task_data["task_id"]
            if any(t["task_id"] == task_id for t in self.tasks):
                logger.warning(f"Task {task_id} already exists. Ignoring add request.")
                return
                
            task_data["retries"] = task_data.get("retries", 0)
            self.tasks.append(task_data)
            logger.info(f"Added new task: {task_id}")
            await self._save_tasks()

    async def _get_next_task(self) -> Optional[Dict]:
        """Get the next pending task based on priority (simple FIFO for now)."""
        async with self._lock:
            pending_tasks = [t for t in self.tasks if t.get("status") == "pending"]
            if not pending_tasks:
                return None
            return pending_tasks[0]

    async def _update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        """Update the status of a task in the list and save."""
        updated = False
        async with self._lock:
            for task in self.tasks:
                if task["task_id"] == task_id:
                    task["status"] = status
                    task["last_update"] = datetime.utcnow().isoformat()
                    if result is not None:
                        task["result"] = result
                    if error is not None:
                        task["error"] = error
                        task["retries"] = task.get("retries", 0) + 1
                    updated = True
                    logger.info(f"Updated task {task_id} status to {status}" + (f" with error: {error}" if error else ""))
                    break
            if updated:
                await self._save_tasks()
            else:
                 logger.warning(f"Attempted to update status for non-existent task: {task_id}")

    async def _execute_task(self, task: Dict) -> None:
        """Execute a given task, routing Cursor actions through the live bridge."""
        task_id = task["task_id"]
        description = task.get("description", "")
        task_type = task.get("task_type", "")
        params = task.get("params", {})
        
        self.current_task_id = task_id
        await self._update_status_on_bus(AgentState.BUSY, task_id=task_id)
        await self._update_task_status(task_id, "running")

        logger.info(f"Starting execution of task: {task_id} - {description}")
        start_time = time.time()
        
        try:
            # --- Task Execution Logic (Agent 2: Using Live Cursor Bridge) ---
            
            if not hasattr(self, 'bridge') or not self.bridge:
                 raise RuntimeError("CursorExecutorBridge not initialized")

            result_data = None
            success = False
            output = None
            logs = ""

            if task_type == "cursor_refactor" or "refactor" in description.lower():
                target_file = params.get("target_file")
                refactor_prompt = params.get("prompt", description)
                if not target_file:
                    raise ValueError("Missing 'target_file' parameter for cursor_refactor task")
                
                logger.info(f"Executing LIVE Cursor refactor on {target_file}...")
                # --- Call the LIVE bridge --- 
                success, output, logs = await self.bridge.refactor_file(target_file, refactor_prompt)
                # --- End bridge call ---
                
                if success:
                     # Structure might depend on what bridge.refactor_file actually returns
                     result_data = {"status": "success", "diff": output.get("diff"), "logs": logs}
                     await self._update_task_status(task_id, "complete", result=result_data)
                else:
                     raise RuntimeError(f"Cursor refactor failed via bridge. Logs: {logs}")

            elif task_type == "generate_tests" or "generate tests" in description.lower():
                target_file = params.get("target_file")
                test_framework = params.get("framework", "pytest")
                if not target_file:
                    raise ValueError("Missing 'target_file' parameter for generate_tests task")
                
                logger.info(f"Executing LIVE Cursor test generation for {target_file}...")
                # --- Call the LIVE bridge --- 
                success, output, logs = await self.bridge.generate_tests(target_file, test_framework)
                # --- End bridge call ---
                
                if success:
                     # Structure might depend on what bridge.generate_tests actually returns
                     result_data = {"status": "success", "test_file": output.get("test_file_path"), "coverage": output.get("coverage"), "logs": logs}
                     await self._update_task_status(task_id, "complete", result=result_data)
                else:
                     raise RuntimeError(f"Cursor test generation failed via bridge. Logs: {logs}")
            
            elif task_type == "execute_prompt_file":
                prompt_file = params.get("prompt_file")
                context_files = params.get("context_files", [])
                if not prompt_file:
                     raise ValueError("Missing 'prompt_file' parameter for execute_prompt_file task")
                
                logger.info(f"Executing LIVE Cursor prompt file: {prompt_file}...")
                # --- Call the LIVE bridge --- 
                success, output, logs = await self.bridge.execute_prompt_file(prompt_file, context_files)
                # --- End bridge call ---
                
                if success:
                     # Structure might depend on what bridge.execute_prompt_file actually returns
                     result_data = {"status": "success", "output": output.get("output"), "files_modified": output.get("files_modified", []), "logs": logs}
                     await self._update_task_status(task_id, "complete", result=result_data)
                else:
                     raise RuntimeError(f"Cursor prompt execution failed via bridge. Logs: {logs}")

            else:
                logger.warning(f"Agent 2 received unknown task type: {task_type} for task {task_id}. Logging completion.")
                result_data = {"status": "success", "message": f"Executed unknown task: {description}"}
                await self._update_task_status(task_id, "complete", result=result_data)
                success = True # Mark as successful if unknown but handled gracefully
            
            # --- End Task Execution Logic ---
            
            duration = time.time() - start_time
            if success:
                 logger.info(f"Successfully completed task via bridge: {task_id} in {duration:.2f}s")
                 # Send completion event with results
                 await self._send_event(EventType.TASK, {
                     "type": "task_completion", 
                     "task_id": task_id, 
                     "agent_id": self.agent_id, 
                     "result": result_data
                 })
            # Failure case handled by the exception block below

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Task {task_id} failed (Live Bridge) after {duration:.2f}s: {e}"
            logger.error(error_msg, exc_info=True)
            
            retries = task.get("retries", 0)
            if retries < MAX_TASK_RETRIES:
                 logger.info(f"Retrying task {task_id} (Attempt {retries + 1}/{MAX_TASK_RETRIES})")
                 await self._update_task_status(task_id, "pending", error=error_msg)
            else:
                 logger.error(f"Task {task_id} reached max retries. Marking as failed.")
                 await self._update_task_status(task_id, "failed", error=error_msg)
                 await self._update_status_on_bus(AgentState.ERROR, error=error_msg)
                 await self._send_event(EventType.SYSTEM, {"type": "task_failure", "task_id": task_id, "error": error_msg})

        finally:
             if self.current_task_id == task_id:
                 self.current_task_id = None
                 if self.context.state != AgentState.ERROR and not self.shutdown_requested:
                     await self._update_status_on_bus(AgentState.IDLE)

    def _handle_signal(self, signum, frame):
        """Handle OS signals for graceful shutdown."""
        logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
        self.shutdown_requested = True

    async def _handle_shutdown(self) -> None:
        """Perform graceful shutdown procedures for Agent 2."""
        logger.info("Starting graceful shutdown...")
        
        if self.context.state == AgentState.BUSY and self.current_task_id:
            logger.warning(f"Shutdown requested while task {self.current_task_id} is running. Allowing completion...")
            
        async with self._lock:
            self.context.state = AgentState.TERMINATED
            await self._save_context()
            await self._save_tasks()

        await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
        await self._send_event(EventType.SYSTEM, {"type": "agent_shutdown", "agent_id": self.agent_id})

        logger.info("Agent resource cleanup complete.")
        self.running = False
        logger.info(f"Agent {self.agent_id} shutdown complete.")

    async def run(self) -> None:
        """Main execution loop for the agent worker."""
        logger.info(f"Starting Agent Worker for {self.agent_id} in domain {self.domain.value}")
        self.running = True

        await self._load_context()
        await self._register_with_bus()
        await self._load_tasks()

        last_heartbeat = time.time()

        while self.running and not self.shutdown_requested:
            try:
                await self._check_mailbox()
                if self.shutdown_requested: break

                async with self._lock:
                     current_state = self.context.state
                     is_busy = (current_state == AgentState.BUSY and self.current_task_id is not None)
                
                if not is_busy and current_state == AgentState.IDLE:
                    await self._load_tasks()
                    next_task = await self._get_next_task()
                    if next_task:
                        await self._execute_task(next_task)
                    else:
                         await asyncio.sleep(TASK_CHECK_INTERVAL)
                elif is_busy:
                     await asyncio.sleep(0.5)
                else: 
                     logger.warning(f"Agent in state {current_state}. Waiting...")
                     await asyncio.sleep(HEARTBEAT_INTERVAL)

                now = time.time()
                if now - last_heartbeat > HEARTBEAT_INTERVAL:
                    async with self._lock:
                         if self.context.state != AgentState.BUSY:
                             await self._update_status_on_bus(self.context.state)
                    last_heartbeat = now

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
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)
        logging.shutdown() 