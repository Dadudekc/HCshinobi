"""Base agent class with consolidated message handling."""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime

from ..utils.performance_logger import PerformanceLogger
from ..memory.governance_memory_engine import log_event

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Base message class for agent communication."""
    id: str
    type: str
    sender: str
    receiver: str
    content: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: datetime = datetime.utcnow()

class AgentError(Exception):
    """Base exception for agent-related errors."""
    pass

class MessageHandlingError(AgentError):
    """Error during message handling."""
    pass

class BaseAgent:
    """Base class for all agents providing common functionality."""
    
    def __init__(self, agent_id: str):
        """Initialize the base agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
        """
        self.agent_id = agent_id
        self._message_handlers: Dict[str, Callable[[Message], Awaitable[None]]] = {}
        self._running = False
        self._message_queue = asyncio.Queue()
        self.perf_logger = PerformanceLogger(agent_id)
        
    def register_message_handler(
        self, 
        message_type: str, 
        handler: Callable[[Message], Awaitable[None]]
    ) -> None:
        """Register a handler for a specific message type.
        
        Args:
            message_type: Type of message this handler processes
            handler: Async function that processes the message
        """
        self._message_handlers[message_type] = handler
        
    async def start(self) -> None:
        """Start the agent."""
        try:
            self._running = True
            log_event("AGENT_START", self.agent_id, {"version": "1.0.0"})
            
            # Start message processor
            asyncio.create_task(self._process_messages())
            
            # Call agent-specific startup
            await self._on_start()
            
        except Exception as e:
            logger.error(f"Error starting agent {self.agent_id}: {e}")
            raise AgentError(f"Failed to start agent: {e}")
            
    async def stop(self) -> None:
        """Stop the agent."""
        try:
            self._running = False
            
            # Call agent-specific shutdown
            await self._on_stop()
            
            log_event("AGENT_STOP", self.agent_id, {"reason": "Shutdown requested"})
            
        except Exception as e:
            logger.error(f"Error stopping agent {self.agent_id}: {e}")
            raise AgentError(f"Failed to stop agent: {e}")
            
    async def send_message(self, message: Message) -> None:
        """Send a message to another agent.
        
        Args:
            message: Message to send
        """
        try:
            with self.perf_logger.track_operation("send_message"):
                await self._message_queue.put(message)
                log_event("MESSAGE_SENT", self.agent_id, {
                    "message_id": message.id,
                    "message_type": message.type,
                    "receiver": message.receiver
                })
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise MessageHandlingError(f"Failed to send message: {e}")
            
    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                message = await self._message_queue.get()
                
                with self.perf_logger.track_operation("process_message"):
                    handler = self._message_handlers.get(message.type)
                    if handler:
                        try:
                            await handler(message)
                            log_event("MESSAGE_PROCESSED", self.agent_id, {
                                "message_id": message.id,
                                "message_type": message.type
                            })
                        except Exception as e:
                            logger.error(f"Error in message handler: {e}")
                            log_event("MESSAGE_HANDLER_ERROR", self.agent_id, {
                                "message_id": message.id,
                                "error": str(e)
                            })
                    else:
                        logger.warning(f"No handler for message type: {message.type}")
                        
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on error
                
    async def _on_start(self) -> None:
        """Hook for agent-specific startup logic. Override in subclasses."""
        pass
        
    async def _on_stop(self) -> None:
        """Hook for agent-specific shutdown logic. Override in subclasses.""" 