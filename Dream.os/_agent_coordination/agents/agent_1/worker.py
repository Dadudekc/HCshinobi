"""Agent Worker Loop for Agent 1."""

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
                                     CoordinationEvent, CoordinationStatus) # Assuming coordinator structures are needed
    from core.utils.file_manager import FileManager
    from core.utils.system import SystemUtils
    from core.utils.agent_helpers import dispatch_usage_block_update
except ImportError as e:
    print(f"Error importing core modules: {e}. Ensure PYTHONPATH is set.")
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
        from core.utils.agent_helpers import dispatch_usage_block_update
    except ImportError:
        print("Failed to import core modules even after path adjustment. Exiting.")
        sys.exit(1)

# --- Configuration ---
AGENT_ID = "agent_1"
AGENT_DOMAIN = AgentDomain.PROMPT_PLANNER # Example: Assign a domain
AGENT_CAPABILITIES = ["planning", "text_generation", "usage_block_injection"]
HEARTBEAT_INTERVAL = 5  # Seconds between status checks/updates
TASK_CHECK_INTERVAL = 2 # Seconds between checking for new tasks
MAX_TASK_RETRIES = 3
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
    """Manages the lifecycle and task execution for a specific agent."""

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
            
            # Ensure state is consistent after load/init
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
            await self._load_context() # Ensure context exists
            
        try:
            await agent_bus.register_agent(self.agent_id, self.capabilities)
            logger.info(f"Successfully registered with AgentBus.")
            # Sync initial state with bus
            await self._update_status_on_bus(self.context.state)
        except ValueError:
             logger.warning(f"Agent {self.agent_id} already registered. Attempting to sync state.")
             await self._update_status_on_bus(self.context.state)
        except Exception as e:
            logger.error(f"Failed to register with AgentBus: {e}")
            # Consider retry logic or graceful exit

    async def _update_status_on_bus(self, status: AgentState, task_id: Optional[str] = None, error: Optional[str] = None) -> None:
        """Update the agent's status on the AgentBus and locally."""
        async with self._lock:
            if not self.context: return
            
            # Update local context
            self.context.state = status
            self.context.current_task = task_id if status == AgentState.BUSY else None
            self.context.last_update = datetime.utcnow()
            await self._save_context() # Persist local state change immediately

            # Update central bus
            try:
                await agent_bus.update_agent_status(
                    self.agent_id, 
                    AgentStatus[status.name], # Convert AgentState to AgentStatus
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
                    
                    # Basic validation
                    if not all(k in message_data for k in ["source", "message_type", "content"]):
                        logger.warning(f"Invalid message format in {msg_file.name}. Skipping.")
                        continue

                    # Process message (example: shutdown directive)
                    await self._process_message(message_data)
                    
                    # Move processed message to archive or delete
                    # For now, just delete
                    await self.file_mgr.delete_file(str(msg_file))
                    logger.debug(f"Processed and deleted message: {msg_file.name}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in message file {msg_file.name}. Moving to failed.")
                    failed_dir = self.inbox_dir / "failed_messages"
                    failed_dir.mkdir(exist_ok=True)
                    failed_path = failed_dir / msg_file.name
                    try:
                        await self.file_mgr.move_file(str(msg_file), str(failed_path))
                        logger.info(f"Moved invalid message {msg_file.name} to {failed_path}")
                    except Exception as move_err:
                        logger.error(f"Could not move failed message {msg_file.name} to {failed_dir}: {move_err}. Deleting instead.")
                        await self.file_mgr.delete_file(str(msg_file)) # Fallback to delete
                except Exception as e:
                    logger.error(f"Error processing message {msg_file.name}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking mailbox: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Handle specific message types."""
        msg_type = message.get("message_type")
        
        if msg_type == "shutdown_directive":
            phase = message.get("content", {}).get("directive", {}).get("phase")
            logger.info(f"Received shutdown directive for phase: {phase}")
            # Trigger phase-specific shutdown logic if needed
            # For now, just acknowledge readiness if the final phase approaches
            if phase == "cleanup": # Example: prepare for final shutdown
                self.shutdown_requested = True
                await self._update_status_on_bus(AgentState.SHUTDOWN_READY)
                
        elif msg_type == "task_assignment": # Example: direct task assignment
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
                # Ensure tasks have required fields
                self.tasks = [t for t in self.tasks if self._validate_task(t)]
                logger.debug(f"Loaded {len(self.tasks)} tasks from {self.task_list_path}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in task list file {self.task_list_path}. Clearing tasks.")
                self.tasks = []
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
                self.tasks = [] # Clear tasks on error to avoid processing bad data

    def _validate_task(self, task: Dict) -> bool:
        """Basic validation of task structure."""
        required_keys = ["task_id", "description", "status", "priority"]
        if not all(key in task for key in required_keys):
             logger.warning(f"Task missing required keys: {task.get('task_id', 'Unknown ID')}")
             return False
        if task.get("status") not in ["pending", "running", "complete", "failed"]:
             logger.warning(f"Task {task.get('task_id')} has invalid status: {task.get('status')}")
             return False
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
                
            task_data["retries"] = task_data.get("retries", 0) # Add retry counter
            self.tasks.append(task_data)
            logger.info(f"Added new task: {task_id}")
            await self._save_tasks()


    async def _get_next_task(self) -> Optional[Dict]:
        """Get the next pending task based on priority (simple FIFO for now)."""
        async with self._lock:
            pending_tasks = [t for t in self.tasks if t.get("status") == "pending"]
            if not pending_tasks:
                return None
            
            # Simple FIFO, could be enhanced with priority sorting
            # pending_tasks.sort(key=lambda t: t.get("priority", 5)) 
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
        """Execute a specific task based on its type."""
        task_id = task["task_id"]
        task_type = task["type"]
        logger.info(f"Executing task {task_id} of type {task_type}...")

        await self._update_status_on_bus(AgentState.BUSY, task_id)
        
        result = None
        error_msg = None
        status = "failed" # Default to failed unless success

        try:
            if task_type == "generate_text":
                # Placeholder for text generation logic
                logger.info("Simulating text generation...")
                await asyncio.sleep(2) # Simulate work
                result = {"generated_text": f"Generated text for task {task_id}"}
                status = "complete"

            elif task_type == "analyze_data":
                # Placeholder for data analysis logic
                logger.info("Simulating data analysis...")
                await asyncio.sleep(3) # Simulate work
                result = {"analysis_summary": f"Analysis complete for task {task_id}"}
                status = "complete"
                
            elif task_type == "inject_usage_block":
                target_file = task.get("target_file")
                if not target_file:
                    raise ValueError("Missing 'target_file' parameter for inject_usage_block task.")
                    
                logger.info(f"Injecting usage block into {target_file}...")
                # --- Placeholder for actual injection logic --- 
                # 1. Read file content
                # content = await self.file_mgr.read_file(target_file)
                # 2. Construct usage block
                # usage_block = "\nif __name__ == '__main__':\n    print('Usage block executed!')\n"
                # 3. Append block if not present
                # if "if __name__ == '__main__':" not in content:
                #    new_content = content + usage_block
                #    await self.file_mgr.write_file(target_file, new_content)
                #    logger.info(f"Usage block injected into {target_file}")
                # else:
                #    logger.info(f"Usage block already present in {target_file}")
                # --- End Placeholder --- 
                
                # Simulate execution/validation
                await asyncio.sleep(1)
                logger.info(f"Simulating execution/validation of usage block in {target_file}")
                # Assume success for now
                execution_status = "executed" # Could be 'failed' if validation fails
                result_summary = "Usage block injected and validated successfully."
                errors = None
                
                # --- Dispatch consolidated status using helper --- 
                await dispatch_usage_block_update(
                    agent_id=self.agent_id,
                    target_file=str(Path(target_file).resolve()), # Ensure absolute path
                    status=execution_status,
                    output_summary=result_summary,
                    errors=errors, # Pass actual errors if any occurred during injection/validation
                    task_id=task_id # Use the current task_id
                )
                logger.info(f"Dispatched consolidated status updates for task {task_id}")
                # We set the overall task status to complete here as the dispatch handles the details
                status = "complete"
                result = {"message": result_summary, "errors": errors}

            else:
                raise NotImplementedError(f"Task type '{task_type}' not implemented.")

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
            error_msg = str(e)
            status = "failed"
            result = {"error": error_msg} # Ensure result dict has error info

            # --- If error occurred during inject_usage_block, dispatch failure status --- 
            if task_type == "inject_usage_block":
                target_file = task.get("target_file", "unknown_file") # Get target_file even on error if possible
                logger.warning(f"Dispatching failure status updates for inject_usage_block task {task_id}")
                await dispatch_usage_block_update(
                    agent_id=self.agent_id,
                    target_file=str(Path(target_file).resolve()) if target_file != "unknown_file" else target_file,
                    status="failed",
                    output_summary="Failed during injection or validation.",
                    errors=error_msg,
                    task_id=task_id
                )
                # Ensure the main task status is also marked as failed
                status = "failed"

        finally:
            # Update local task list status, except for inject_usage_block 
            # as its status is primarily handled via the dispatched events
            if task_type != "inject_usage_block":
                await self._update_task_status(task_id, status, result=result, error=error_msg)
            else:
                # For inject_usage_block, just log completion/failure locally
                # The definitive status is in the events handled by Agent 5
                logger.info(f"Local completion/failure logged for inject_usage_block task {task_id}. Final status managed by StateSyncAgent.")
                # We might still update local task list minimally if needed, e.g., remove from active queue
                # This depends on task management strategy

            # Set agent back to IDLE
            await self._update_status_on_bus(AgentState.IDLE)

    def _handle_signal(self, signum, frame):
        """Handle OS signals for graceful shutdown."""
        logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
        self.shutdown_requested = True

    async def _handle_shutdown(self) -> None:
        """Perform graceful shutdown procedures."""
        logger.info("Starting graceful shutdown...")
        
        # 1. Stop accepting new tasks (already handled by loop exit)
        # 2. Wait for current task to complete (loop naturally waits)
        if self.context.state == AgentState.BUSY and self.current_task_id:
            logger.warning(f"Shutdown requested while task {self.current_task_id} is running. Allowing completion...")
            # The main loop structure should allow the current task to finish.
            # Add a timeout here if needed?
            
        # 3. Persist final state
        async with self._lock:
            self.context.state = AgentState.TERMINATED # Or SHUTDOWN_READY if coordinated
            await self._save_context()
            await self._save_tasks() # Save any status updates

        # 4. Notify AgentBus
        await self._update_status_on_bus(AgentState.SHUTDOWN_READY) # Use SHUTDOWN_READY for coordination
        await self._send_event(EventType.SYSTEM, {"type": "agent_shutdown", "agent_id": self.agent_id})

        # 5. Cleanup resources (if any specific to this agent)
        logger.info("Agent resource cleanup complete.")
        
        self.running = False
        logger.info(f"Agent {self.agent_id} shutdown complete.")

    async def run(self) -> None:
        """Main execution loop for the agent worker."""
        logger.info(f"Starting Agent Worker for {self.agent_id} in domain {self.domain.value}")
        self.running = True

        await self._load_context()
        await self._register_with_bus()
        await self._load_tasks() # Load initial tasks

        last_heartbeat = time.time()

        while self.running and not self.shutdown_requested:
            try:
                # 1. Check Mailbox for directives/messages
                await self._check_mailbox()
                
                # Exit immediately if shutdown was requested via message
                if self.shutdown_requested: break

                # 2. Check Agent State & Current Task
                async with self._lock:
                     current_state = self.context.state
                     is_busy = (current_state == AgentState.BUSY and self.current_task_id is not None)
                
                # 3. If Idle, find and execute next task
                if not is_busy and current_state == AgentState.IDLE:
                    await self._load_tasks() # Refresh task list
                    next_task = await self._get_next_task()
                    if next_task:
                        await self._execute_task(next_task)
                    else:
                        # No tasks, sleep a bit longer before checking again
                         await asyncio.sleep(TASK_CHECK_INTERVAL)
                elif is_busy:
                     # Already busy, just wait briefly
                     await asyncio.sleep(0.5)
                else: # ERROR, BLOCKED, etc.
                     logger.warning(f"Agent in state {current_state}. Waiting before checking tasks again.")
                     # Maybe clear ERROR state after a delay? Or require external intervention?
                     await asyncio.sleep(HEARTBEAT_INTERVAL) # Wait longer if blocked/error

                # 4. Heartbeat / Periodic Status Update
                now = time.time()
                if now - last_heartbeat > HEARTBEAT_INTERVAL:
                    async with self._lock:
                         # Send a simple heartbeat or resync status if needed
                         if self.context.state != AgentState.BUSY: # Avoid spamming while busy
                             await self._update_status_on_bus(self.context.state)
                    last_heartbeat = now

            except asyncio.CancelledError:
                logger.warning("Main loop cancelled.")
                self.shutdown_requested = True
            except Exception as e:
                logger.error(f"Unhandled error in main loop: {e}", exc_info=True)
                # Attempt to recover or enter error state
                await self._update_status_on_bus(AgentState.ERROR, error=f"Unhandled loop error: {e}")
                await asyncio.sleep(10) # Wait after a major error

        # --- Shutdown Sequence ---
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
        # Allow ongoing task and shutdown handler to complete
        if main_task and not main_task.done():
             # Wait gracefully for the main task (including shutdown) to finish
             loop.run_until_complete(main_task)
    except Exception as e:
         logger.critical(f"Agent worker crashed: {e}", exc_info=True)
    finally:
        # Ensure dispatcher stops if this is the main script (might be handled elsewhere)
        # loop.run_until_complete(agent_bus._dispatcher.stop())
        logger.info(f"Agent Worker {AGENT_ID} process finished.")
        # Ensure all handlers are closed
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)
        logging.shutdown() 