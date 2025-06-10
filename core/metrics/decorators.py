"""Decorators for command metrics logging."""
import time
import functools
from typing import Callable, Any
from .command_logger import CommandLogger

command_logger = CommandLogger()

def track_command_usage(func: Callable) -> Callable:
    """
    Decorator to track command usage metrics.
    
    Args:
        func: The command function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = True
        error = None
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Get interaction from args (first arg is self, second is interaction)
            if len(args) >= 2 and hasattr(args[1], 'user'):
                user_id = str(args[1].user.id)
                command_name = func.__name__
                
                # Log command usage
                command_logger.log_command_usage(
                    user_id=user_id,
                    command_name=command_name,
                    success=success,
                    duration_ms=duration_ms,
                    error=error
                )
                
    return wrapper 