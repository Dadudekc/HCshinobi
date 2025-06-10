"""Utility functions for agent functionality."""
import asyncio
import functools
import logging
import uuid
from typing import Any, Callable, Dict, Optional, TypeVar, Awaitable
from datetime import datetime

from .base_agent import Message, AgentError, MessageHandlingError
from ..utils.performance_logger import PerformanceLogger
from ..memory.governance_memory_engine import log_event

logger = logging.getLogger(__name__)

T = TypeVar('T')

def with_error_handling(error_class: type = AgentError):
    """Decorator for functions that need standardized error handling.
    
    Args:
        error_class: Exception class to use for errors
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                error_details = {
                    "error": error_msg,
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs)
                }
                log_event("AGENT_ERROR", "agent_utils", error_details)
                raise error_class(error_msg) from e
        return wrapper
    return decorator

def with_performance_tracking(operation_name: str):
    """Decorator for tracking operation performance.
    
    Args:
        operation_name: Name of the operation to track
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> T:
            with self.perf_logger.track_operation(operation_name):
                return await func(self, *args, **kwargs)
        return wrapper
    return decorator

def create_message(
    sender: str,
    receiver: str,
    message_type: str,
    content: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> Message:
    """Create a new message with a unique ID.
    
    Args:
        sender: ID of sending agent
        receiver: ID of receiving agent
        message_type: Type of message
        content: Message content
        correlation_id: Optional correlation ID for message chains
        
    Returns:
        Message object
    """
    return Message(
        id=str(uuid.uuid4()),
        type=message_type,
        sender=sender,
        receiver=receiver,
        content=content,
        correlation_id=correlation_id,
        timestamp=datetime.utcnow()
    )

async def broadcast_message(
    sender: str,
    receivers: list[str],
    message_type: str,
    content: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> None:
    """Broadcast a message to multiple receivers.
    
    Args:
        sender: ID of sending agent
        receivers: List of receiving agent IDs
        message_type: Type of message
        content: Message content
        correlation_id: Optional correlation ID for message chains
    """
    base_message = create_message(
        sender=sender,
        receiver="",  # Will be set per receiver
        message_type=message_type,
        content=content,
        correlation_id=correlation_id
    )
    
    for receiver in receivers:
        message = base_message.copy()
        message.receiver = receiver
        try:
            # Send message to each receiver
            # Note: This assumes some kind of message bus/broker is available
            # Implementation would need to be customized based on actual message routing
            pass
        except Exception as e:
            logger.error(f"Error broadcasting to {receiver}: {e}")
            log_event("BROADCAST_ERROR", sender, {
                "error": str(e),
                "receiver": receiver,
                "message_id": message.id
            })

async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    **kwargs
) -> T:
    """Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_retries: Maximum number of retries
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from successful function call
        
    Raises:
        AgentError: If all retries fail
    """
    delay = initial_delay
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == max_retries:
                break
                
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                f"Retrying in {delay:.1f}s"
            )
            
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)
            
    raise AgentError(f"Function failed after {max_retries + 1} attempts: {last_error}")

def log_agent_metrics(
    agent_id: str,
    perf_logger: PerformanceLogger,
    metrics: Dict[str, Any]
) -> None:
    """Log agent performance metrics.
    
    Args:
        agent_id: ID of the agent
        perf_logger: Performance logger instance
        metrics: Dictionary of metrics to log
    """
    try:
        perf_logger.log_metrics(metrics)
        log_event("METRICS_LOGGED", agent_id, metrics)
    except Exception as e:
        logger.error(f"Error logging metrics: {e}")
        log_event("METRICS_ERROR", agent_id, {
            "error": str(e),
            "metrics": metrics
        }) 