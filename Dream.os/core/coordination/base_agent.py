"""Base agent class providing common functionality for all Dream.OS agents."""
import asyncio
import traceback
import logging # Added for standard logger
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

# Update imports to use 'core' or relative paths
# from dreamforge.core.coordination.agent_bus import AgentBus, Message, MessageType, BusError
from core.coordination.agent_bus import AgentBus, Message, BusError # Removed MessageType
# from dreamforge.core.coordination.message_patterns import (
#     TaskMessage, TaskStatus, TaskPriority,
#     create_task_message, update_task_status
# )
from core.coordination.message_patterns import (
    TaskMessage, TaskStatus, TaskPriority,
    create_task_message, update_task_status
)
# from dreamforge.core.utils.performance_logger import PerformanceLogger
from core.utils.performance_logger import PerformanceLogger
# from dreamforge.core.memory.governance_memory_engine import log_event
from core.memory.governance_memory_engine import log_event
# from dreamforge.core.utils.agent_utils import (
#     with_error_handling,
#     with_performance_tracking,
#     publish_task_update,
#     publish_error,
#     handle_task_cancellation,
#     log_task_performance,
#     AgentError,
#     TaskProcessingError,
#     MessageHandlingError
# )
# Assuming agent_utils is now in core/utils
from core.utils.agent_utils import (
    with_error_handling,
    with_performance_tracking,
    publish_task_update,
    publish_error,
    handle_task_cancellation,
    log_task_performance,
    AgentError,
    TaskProcessingError,
    MessageHandlingError
)

class BaseAgent:
    """Base class for all Dream.OS agents providing common functionality."""

    # Update __init__ signature and logic
    # def __init__(self, agent_id: str):
    def __init__(self, agent_id: str, agent_bus: AgentBus):
        """Initialize the base agent.

        Args:
            agent_id: Unique identifier for this agent instance.
            agent_bus: The shared AgentBus instance.
        """
        self.agent_id = agent_id
        # self.agent_bus = AgentBus() # Remove internal instantiation
        self.agent_bus = agent_bus # Use injected bus
        self._subscription_id = None # Maybe manage subscriptions differently?
        self._running = False
        self._active_tasks = {}  # task_id -> asyncio.Task
        self._task_queue = asyncio.PriorityQueue()
        self._command_handlers: Dict[str, Callable[[TaskMessage], Awaitable[Dict[str, Any]]]] = {}
        self.perf_logger = PerformanceLogger(agent_id)
        # Add standard logger
        self.logger = logging.getLogger(agent_id)
        # Configure logger (basic example, could be more sophisticated)
        # TODO: Centralize logger configuration
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers: # Avoid adding handlers multiple times
             self.logger.addHandler(handler)
             self.logger.setLevel(logging.INFO) # Default level


    @with_error_handling(AgentError)
    async def start(self):
        """Start the agent, subscribe to topics, and launch task processor."""
        self.logger.info(f"Starting agent {self.agent_id}...")
        log_event("AGENT_START", self.agent_id, {"version": "1.0.0"})
        self._running = True

        # Subscribe to command messages using topic string
        # Topic should likely be specific to the agent_id
        command_topic = f"agent.{self.agent_id}.command"
        # self._subscription_id = await self.agent_bus.subscribe(
        #     MessageType.COMMAND,
        #     self._handle_command
        # )
        # Assuming subscribe now returns a subscription object or ID for unsubscribing
        self._subscription_id = await self.agent_bus.subscribe(command_topic, self._handle_command)
        self.logger.info(f"Subscribed to command topic: {command_topic}")

        # Start task processor
        self._task_processor_task = asyncio.create_task(self._process_task_queue())
        self.logger.info("Task processor started.")

        # Start the message bus (if BaseAgent is responsible for its lifecycle)
        # NOTE: Typically, AgentBus lifecycle is managed externally.
        # Consider removing this if the bus is started elsewhere.
        # await self.agent_bus.start()
        # self.logger.info("AgentBus start requested (if managed internally)." )

        # Call agent-specific startup
        await self._on_start()
        self.logger.info(f"Agent {self.agent_id} started successfully.")

    @with_error_handling(AgentError)
    async def stop(self):
        """Stop the agent, cancel tasks, unsubscribe, and shutdown."""
        self.logger.info(f"Stopping agent {self.agent_id}...")
        self._running = False

        # Cancel the task processor first
        if hasattr(self, '_task_processor_task') and self._task_processor_task:
            self._task_processor_task.cancel()
            try:
                await self._task_processor_task
            except asyncio.CancelledError:
                self.logger.info("Task processor stopped.")

        # Cancel all active tasks managed by the queue processing
        self.logger.info(f"Cancelling {len(self._active_tasks)} active task(s)...")
        for task_id, task in list(self._active_tasks.items()): # Iterate over copy
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    self.logger.info(f"Cancelled active task {task_id}.")
                    log_event("AGENT_TASK_CANCELLED", self.agent_id, {"task_id": task_id})
                # Ensure removal even if await fails
                self._active_tasks.pop(task_id, None)

        # Clear the queue (optional, prevents processing stale tasks on restart)
        while not self._task_queue.empty():
             try:
                 self._task_queue.get_nowait()
             except asyncio.QueueEmpty:
                 break
        self.logger.info("Task queue cleared.")

        # Unsubscribe from bus
        if self._subscription_id:
            try:
                # Assuming unsubscribe takes the ID returned by subscribe
                await self.agent_bus.unsubscribe(self._subscription_id)
                self.logger.info("Unsubscribed from command topic.")
            except Exception as e:
                self.logger.error(f"Error unsubscribing from agent bus: {e}")

        # Shutdown the message bus (if BaseAgent is responsible)
        # NOTE: Typically, AgentBus lifecycle is managed externally.
        # Consider removing this if the bus is shutdown elsewhere.
        # await self.agent_bus.shutdown()
        # self.logger.info("AgentBus shutdown requested (if managed internally)." )

        # Call agent-specific shutdown
        await self._on_stop()

        log_event("AGENT_STOP", self.agent_id, {"reason": "Shutdown requested"})
        self.logger.info(f"Agent {self.agent_id} stopped successfully.")

    def register_command_handler(self, command_type: str, handler: Callable[[TaskMessage], Awaitable[Dict[str, Any]]]):
        """Register a handler for a specific command type (task_type)."""
        self.logger.debug(f"Registering command handler for type: {command_type}")
        self._command_handlers[command_type] = handler

    @with_error_handling(MessageHandlingError)
    @with_performance_tracking("handle_command")
    # Handler signature might change depending on AgentBus implementation
    # Assuming handler receives topic and message dictionary
    async def _handle_command(self, topic: str, message: Dict[str, Any]):
        """Handle incoming command messages from the subscribed topic."""
        self.logger.debug(f"Received message on topic '{topic}': {message}")
        # Extract task data, assuming it's in message['data']
        task_data = message.get('data')
        if not task_data or not isinstance(task_data, dict):
            self.logger.error(f"Invalid message format on topic {topic}: missing or invalid 'data' field.")
            return

        try:
            # task = TaskMessage.from_message_content(message.content)
            task = TaskMessage.from_dict(task_data)
            correlation_id = message.get('correlation_id') # Get correlation_id if available
        except Exception as e:
            self.logger.error(f"Failed to parse TaskMessage from message data: {e}", exc_info=True)
            # Potentially publish an error back if possible
            return

        self.logger.info(f"Received task {task.task_id} ({task.task_type}) via bus.")

        if task.task_type == "cancel_task":
            await self._handle_cancel_task(task)
            return

        # Update task status to pending
        task = update_task_status(task, TaskStatus.PENDING)
        # publish_task_update might need agent_bus passed if it doesn't use a global one
        await publish_task_update(self.agent_bus, task, self.agent_id)

        # Add task to priority queue
        priority_value = self._get_priority_value(task.priority)
        await self._task_queue.put((priority_value, task, correlation_id))
        self.logger.debug(f"Added task {task.task_id} to queue with priority {priority_value}.")

    def _get_priority_value(self, priority: TaskPriority) -> int:
        """Convert TaskPriority to numeric value for queue ordering."""
        priority_map = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3
        }
        # Default to NORMAL priority if not found or invalid
        return priority_map.get(priority, priority_map[TaskPriority.NORMAL])

    @with_error_handling(TaskProcessingError)
    async def _process_task_queue(self):
        """Process tasks from the priority queue continuously."""
        self.logger.info("Task processing queue started.")
        while self._running:
            try:
                # Get next task from queue
                priority, task, correlation_id = await self._task_queue.get()
                self.logger.info(f"Processing task {task.task_id} ({task.task_type}) with priority {priority}.")

                # Check if task is already active (should not happen with proper queue logic)
                if task.task_id in self._active_tasks:
                    self.logger.warning(f"Task {task.task_id} is already active. Skipping.")
                    self._task_queue.task_done()
                    continue

                # Update task status to running
                task = update_task_status(task, TaskStatus.RUNNING)
                await publish_task_update(self.agent_bus, task, self.agent_id)

                # Create and track the task
                # Pass correlation_id if needed by _process_single_task
                process_task = asyncio.create_task(self._process_single_task(task, correlation_id))
                self._active_tasks[task.task_id] = process_task

                try:
                    await process_task # Wait for the task processing to complete
                except asyncio.CancelledError:
                    self.logger.warning(f"Task {task.task_id} was cancelled during execution.")
                    # Status already updated within _process_single_task or _handle_cancel_task
                except Exception as exec_e:
                    # Catch errors from within _process_single_task if not handled internally
                    self.logger.error(f"Unhandled exception during task {task.task_id} execution: {exec_e}", exc_info=True)
                    # Ensure task status is marked as FAILED
                    if task.status != TaskStatus.FAILED:
                         task = update_task_status(task, TaskStatus.FAILED, error=str(exec_e))
                         await publish_task_update(self.agent_bus, task, self.agent_id)
                         # Publish error to bus
                         await publish_error(
                             self.agent_bus, str(exec_e), self.agent_id, correlation_id,
                             details={"traceback": traceback.format_exc()}
                         )
                finally:
                    # Remove task from active tasks once completed, cancelled, or failed
                    self._active_tasks.pop(task.task_id, None)
                    self._task_queue.task_done()
                    self.logger.debug(f"Finished processing task {task.task_id}. Queue size: {self._task_queue.qsize()}")

            except asyncio.CancelledError:
                self.logger.info("Task processing queue stopping due to cancellation.")
                break # Exit the loop if the processor task itself is cancelled
            except Exception as e:
                # Log errors in the queue loop itself
                self.logger.error(f"Error in task queue processing loop: {e}", exc_info=True)
                log_event("AGENT_ERROR", self.agent_id, {
                    "error": "Task queue processing loop failed",
                    "details": str(e)
                })
                # Avoid tight loop on persistent errors
                await asyncio.sleep(1)
        self.logger.info("Task processing queue finished.")

    @with_error_handling(TaskProcessingError)
    @with_performance_tracking("process_single_task")
    async def _process_single_task(self, task: TaskMessage, correlation_id: Optional[str]):
        """Process a single task by calling its registered handler."""
        self.logger.info(f"Executing handler for task {task.task_id} ({task.task_type}).")
        try:
            # Get the appropriate handler for this task type
            handler = self._command_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler registered for task type: {task.task_type}")

            # Execute the handler
            result = await handler(task)
            self.logger.debug(f"Handler for task {task.task_id} returned: {result}")

            # Process result and update task status
            if isinstance(result, dict) and result.get("status") == "success":
                task = update_task_status(task, TaskStatus.COMPLETED, result=result.get('data')) # Store actual result data
                await publish_task_update(self.agent_bus, task, self.agent_id)
                self.logger.info(f"Task {task.task_id} completed successfully.")

                # Send success response using topic string
                response_topic = f"system.response.{correlation_id or task.task_id}"
                response_message = {
                     "sender_id": self.agent_id,
                     "correlation_id": correlation_id,
                     "data": task.to_dict() # Send full task details back
                }
                # await self.agent_bus.publish(Message(
                #     type=MessageType.RESPONSE,
                #     sender=self.agent_id,
                #     content=task.to_message_content(),
                #     correlation_id=correlation_id
                # ))
                await self.agent_bus.publish(response_topic, response_message)
                self.logger.debug(f"Published success response to {response_topic}")

            elif isinstance(result, dict) and result.get("status") == "error":
                error_msg = result.get("error", "Task execution failed")
                task = update_task_status(task, TaskStatus.FAILED, error=error_msg)
                await publish_task_update(self.agent_bus, task, self.agent_id)
                self.logger.error(f"Task {task.task_id} failed: {error_msg}")

                # Send error response using topic string
                await publish_error(
                    self.agent_bus, error_msg, self.agent_id, correlation_id,
                    details=result
                )

            else:
                # Handle unexpected result format
                error_msg = f"Task {task.task_id} handler returned unexpected result format: {type(result)}"
                self.logger.error(error_msg)
                task = update_task_status(task, TaskStatus.FAILED, error=error_msg)
                await publish_task_update(self.agent_bus, task, self.agent_id)

                await publish_error(self.agent_bus, error_msg, self.agent_id, correlation_id)

        except asyncio.CancelledError:
            # Handle task cancellation specifically
            self.logger.warning(f"Execution of task {task.task_id} was cancelled.")
            task = update_task_status(task, TaskStatus.CANCELLED, error="Task execution cancelled")
            await publish_task_update(self.agent_bus, task, self.agent_id)
            # Optionally publish a specific cancellation confirmation message?
            raise # Re-raise cancellation error to be caught by the queue processor

        except Exception as e:
            # Handle other exceptions during handler execution
            error_msg = f"Exception during task {task.task_id} execution: {e}"
            self.logger.error(error_msg, exc_info=True)
            task = update_task_status(task, TaskStatus.FAILED, error=str(e))
            await publish_task_update(self.agent_bus, task, self.agent_id)

            await publish_error(
                self.agent_bus, str(e), self.agent_id, correlation_id,
                details={"traceback": traceback.format_exc()}
            )
            # Do not re-raise, let the queue processor log completion/failure status

        finally:
            # Log performance metrics regardless of outcome
            log_task_performance(task, self.agent_id, self.perf_logger)

    async def _handle_cancel_task(self, cancel_request: TaskMessage):
        """Handle task cancellation request by cancelling the corresponding asyncio Task."""
        target_task_id = cancel_request.input_data.get("target_task_id")
        correlation_id = cancel_request.correlation_id
        self.logger.info(f"Received cancellation request for task {target_task_id}.")

        if not target_task_id:
            error_msg = "No target_task_id provided for cancellation request."
            self.logger.error(error_msg)
            await publish_error(self.agent_bus, error_msg, self.agent_id, correlation_id)
            return

        # Use the helper function, passing necessary context
        await handle_task_cancellation(
            target_task_id=target_task_id,
            active_tasks=self._active_tasks,
            agent_bus=self.agent_bus,
            agent_id=self.agent_id,
            correlation_id=correlation_id
        )
        # Note: handle_task_cancellation should ideally handle publishing success/failure responses

    # --- Lifecycle Hooks ---
    async def _on_start(self):
        """Placeholder for agent-specific startup logic. Called after core start logic."""
        self.logger.debug("Executing _on_start hook.")
        pass # Subclasses should override this

    async def _on_stop(self):
        """Placeholder for agent-specific shutdown logic. Called before core stop logic."""
        self.logger.debug("Executing _on_stop hook.")
        pass # Subclasses should override this 