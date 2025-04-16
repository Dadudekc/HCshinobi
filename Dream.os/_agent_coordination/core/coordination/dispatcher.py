"""Event dispatcher for Dream.OS agent coordination."""

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Callable, Optional
from datetime import datetime

from core.agent_bus import AgentBus

logger = logging.getLogger(__name__)

class EventType(Enum):
    CURSOR = "cursor"
    CHAT = "chat"
    SYSTEM = "system"

class Event:
    """Base event class for agent coordination."""
    
    def __init__(self, type: EventType, source_id: str, priority: int = 0):
        self.type = type
        self.source_id = source_id
        self.priority = priority
        self.timestamp: Optional[float] = None

class EventDispatcher:
    """Unified dispatcher for cursor and chat events."""
    
    def __init__(self, agent_bus: AgentBus):
        self._agent_bus = agent_bus
        self._handlers: Dict[EventType, List[Callable]] = {
            EventType.CURSOR: [],
            EventType.CHAT: [],
            EventType.SYSTEM: []
        }
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        
    def register_handler(self, event_type: EventType, handler: Callable) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            raise ValueError(f"Invalid event type: {event_type}")
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value} events")
        
    async def dispatch_event(self, event: Event) -> None:
        """Dispatch an event to the appropriate handlers."""
        if not event.timestamp:
            event.timestamp = asyncio.get_event_loop().time()
            
        # Add to priority queue (lower number = higher priority)
        await self._event_queue.put((event.priority, event.timestamp, event))
        logger.debug(f"Queued {event.type.value} event from {event.source_id}")
        
    async def start(self) -> None:
        """Start the event dispatcher."""
        if self._running:
            return
            
        self._running = True
        self._worker_task = asyncio.create_task(self._process_events())
        logger.info("Event dispatcher started")
        
    async def stop(self) -> None:
        """Stop the event dispatcher."""
        if not self._running:
            return
            
        self._running = False
        if self._worker_task:
            await self._worker_task
            self._worker_task = None
        logger.info("Event dispatcher stopped")
        
    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                # Get next event
                priority, timestamp, event = await self._event_queue.get()
                
                # Process event
                handlers = self._handlers[event.type]
                if not handlers:
                    logger.warning(f"No handlers for {event.type.value} events")
                    continue
                    
                # Execute handlers
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
                        
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                
        logger.info("Event processor stopped")
        
    async def get_queue_size(self) -> int:
        """Get the current size of the event queue."""
        return self._event_queue.qsize()
        
    async def get_handlers(self, event_type: Optional[EventType] = None) -> int:
        """Get count of registered handlers, optionally filtered by type."""
        if event_type:
            return len(self._handlers.get(event_type, []))
        return sum(len(handlers) for handlers in self._handlers.values()) 