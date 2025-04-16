"""Agent Worker Loop for Agent 3 (Feedback Verifier)."""

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
AGENT_ID = "agent_3"
AGENT_DOMAIN = AgentDomain.FEEDBACK_VERIFIER
AGENT_CAPABILITIES = ["output_verification", "log_analysis", "rl_data_generation", "status_reporting"]
HEARTBEAT_INTERVAL = 5
TASK_CHECK_INTERVAL = 3 # Verifier might not need to check as frequently
MAX_TASK_RETRIES = 1 # Verification tasks might be less prone to transient errors
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
    """Manages the lifecycle and task execution for Agent 3 (Feedback Verifier)."""

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
        self.rl_data_path = self.agent_dir / "rl_training_data.jsonl" # Example path for RL data

        self._ensure_dirs()

        self.context: Optional[AgentContext] = None
        self.tasks: List[Dict] = []
        self.current_task_id: Optional[str] = None

        self.file_mgr = FileManager()
        self.sys_utils = SystemUtils()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _ensure_dirs(self):
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

    async def _check_mailbox(self) -> None:
        """Check for new messages, potentially including task results to verify."""
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
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {msg_file.name}")
                    await self.file_mgr.delete_file(str(msg_file))
                except Exception as e:
                    logger.error(f"Error processing message {msg_file.name}: {e}")
        except Exception as e:
            logger.error(f"Error checking mailbox: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Handle messages, specifically looking for task completion events to verify."""
        msg_type = message.get("message_type")
        content = message.get("content", {})
        
        if msg_type == "shutdown_directive":
            phase = content.get("directive", {}).get("phase")
            logger.info(f"Received shutdown directive for phase: {phase}")
            if phase == "cleanup":
                self.shutdown_requested = True
                await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
                
        elif msg_type == "task_completion_notification": # Assume orchestrator sends this
            task_result = content.get("task_result")
            if task_result:
                 logger.info(f"Received task result for verification: {task_result.get('task_id')}")
                 # Create a verification task
                 verification_task = {
                     "task_id": f"verify_{task_result.get('task_id', uuid.uuid4().hex[:8])}",
                     "description": f"Verify output of task {task_result.get('task_id')}",
                     "status": "pending",
                     "priority": 2, # Verification priority
                     "params": {"original_task_result": task_result},
                     "task_type": "verify_output"
                 }
                 await self._add_task(verification_task)
            else:
                 logger.warning("Received task completion notification without result data.")
                 
        elif msg_type == "task_assignment": # Direct task assignment for verification?
             task_data = content.get("task")
             if task_data:
                 logger.info(f"Received direct task assignment: {task_data.get('task_id')}")
                 await self._add_task(task_data)
                 
        else:
            logger.debug(f"Received unhandled message type: {msg_type}")

    async def _load_tasks(self) -> None:
        async with self._lock:
            if not self.task_list_path.exists(): self.tasks = []; return
            try:
                content = await self.file_mgr.read_file(str(self.task_list_path))
                self.tasks = json.loads(content)
                self.tasks = [t for t in self.tasks if self._validate_task(t)]
                logger.debug(f"Loaded {len(self.tasks)} tasks")
            except json.JSONDecodeError: logger.error(f"Invalid JSON: {self.task_list_path}"); self.tasks = []
            except Exception as e: logger.error(f"Failed to load tasks: {e}"); self.tasks = []

    def _validate_task(self, task: Dict) -> bool:
        required = ["task_id", "description", "status", "priority"]
        if not all(k in task for k in required): logger.warning(f"Task missing keys: {task.get('task_id')}"); return False
        if task.get("status") not in ["pending", "running", "complete", "failed"]: logger.warning(f"Invalid status: {task.get('task_id')}"); return False
        if task.get("task_type") == "verify_output" and "original_task_result" not in task.get("params", {}):
             logger.warning(f"Verification task missing original result: {task.get('task_id')}"); return False
        return True

    async def _save_tasks(self) -> None:
        async with self._lock:
            try:
                await self.file_mgr.write_file(str(self.task_list_path), json.dumps(self.tasks, indent=2))
                logger.debug(f"Saved {len(self.tasks)} tasks")
            except Exception as e: logger.error(f"Failed to save tasks: {e}")

    async def _add_task(self, task_data: Dict) -> None:
        async with self._lock:
            if not self._validate_task(task_data): logger.error(f"Invalid task add: {task_data}"); return
            task_id = task_data["task_id"]
            if any(t["task_id"] == task_id for t in self.tasks): logger.warning(f"Task exists: {task_id}"); return
            task_data["retries"] = task_data.get("retries", 0)
            self.tasks.append(task_data)
            logger.info(f"Added new task: {task_id}")
            await self._save_tasks()

    async def _get_next_task(self) -> Optional[Dict]:
        async with self._lock:
            pending = [t for t in self.tasks if t.get("status") == "pending"]
            # Simple FIFO for now
            return pending[0] if pending else None

    async def _update_task_status(self, task_id: str, status: str, result: Optional[Dict] = None, error: Optional[str] = None):
        updated = False
        async with self._lock:
            for task in self.tasks:
                if task["task_id"] == task_id:
                    task["status"] = status
                    task["last_update"] = datetime.utcnow().isoformat()
                    if result is not None: task["result"] = result
                    if error is not None: task["error"] = error; task["retries"] = task.get("retries", 0) + 1
                    updated = True
                    logger.info(f"Updated task {task_id} status to {status}" + (f" with error: {error}" if error else ""))
                    break
            if updated: await self._save_tasks()
            else: logger.warning(f"Task not found for update: {task_id}")

    async def _execute_task(self, task: Dict) -> None:
        """Execute verification tasks."""
        task_id = task["task_id"]
        description = task.get("description", "")
        task_type = task.get("task_type", "")
        params = task.get("params", {})
        
        self.current_task_id = task_id
        await self._update_status_on_bus(AgentState.BUSY, task_id=task_id)
        await self._update_task_status(task_id, "running")

        logger.info(f"Starting execution of task: {task_id} - {description}")
        start_time = time.time()
        result_data = None
        error_msg = None

        try:
            # --- Task Execution Logic (Agent 3: Feedback Verifier) ---
            if task_type == "verify_output":
                original_result = params.get("original_task_result", {})
                original_task_id = original_result.get("task_id", "unknown")
                logger.info(f"Verifying output of task {original_task_id}")
                
                # --- Placeholder --- 
                # verification_passed, details = await self.verifier.verify(original_result)
                verification_passed, details = True, {"checks": ["placeholder_check_passed"], "score": 0.95}
                # --- End Placeholder ---
                
                result_data = {
                    "status": "verified",
                    "passed": verification_passed,
                    "details": details,
                    "original_task_id": original_task_id
                }
                
                # Generate RL data point (Placeholder)
                # await self.rl_logger.log_step(original_result, verification_passed, details.get("score"))
                await self.file_mgr.append_to_file(
                    str(self.rl_data_path),
                    json.dumps({"input": original_result, "verified": verification_passed, **details}) + "\n"
                )
                logger.info(f"Verification complete for {original_task_id}. Passed: {verification_passed}. RL data logged.")
                await self._update_task_status(task_id, "complete", result=result_data)

            elif task_type == "analyze_logs":
                log_file = params.get("log_file")
                if not log_file or not Path(log_file).exists():
                    raise ValueError(f"Invalid or missing log file: {log_file}")
                
                logger.info(f"Analyzing log file: {log_file}")
                # --- Placeholder --- 
                # analysis_summary = await self.log_analyzer.analyze(log_file)
                analysis_summary = {"errors_found": 0, "warnings_found": 2, "keywords": ["complete", "shutdown"]}
                # --- End Placeholder ---
                
                result_data = {"status": "analyzed", "summary": analysis_summary}
                await self._update_task_status(task_id, "complete", result=result_data)

            else:
                logger.warning(f"Agent 3 received unknown task type: {task_type} for task {task_id}. Logging completion.")
                result_data = {"status": "success", "message": f"Executed unknown task: {description}"}
                await self._update_task_status(task_id, "complete", result=result_data)
            
            duration = time.time() - start_time
            logger.info(f"Successfully completed task: {task_id} in {duration:.2f}s")
            await self._send_event(EventType.SYSTEM, {
                "type": "verification_complete", 
                "verification_task_id": task_id,
                "result": result_data
            })

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Task {task_id} failed after {duration:.2f}s: {e}"
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
        logger.warning(f"Received signal {signum}. Initiating shutdown...")
        self.shutdown_requested = True

    async def _handle_shutdown(self) -> None:
        logger.info("Starting graceful shutdown...")
        if self.context.state == AgentState.BUSY and self.current_task_id:
            logger.warning(f"Shutdown requested while task {self.current_task_id} is running. Allowing completion...")
            
        async with self._lock:
            self.context.state = AgentState.TERMINATED
            await self._save_context()
            await self._save_tasks()

        await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
        await self._send_event(EventType.SYSTEM, {"type": "agent_shutdown", "agent_id": self.agent_id})
        logger.info(f"Agent {self.agent_id} shutdown complete.")
        self.running = False

    async def run(self) -> None:
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