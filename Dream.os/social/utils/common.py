"""
Common, generic utilities for the Dream.OS project.
Includes retry logic and potentially other cross-cutting concerns.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from utils.logging_utils import get_logger

# Configure logging for this utility module
logger = get_logger(__name__)

# Type variables for generic functions
ReturnType = TypeVar('ReturnType')

# Kept retry_on_exception as a generic utility
def retry_on_exception(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator for functions that may fail temporarily.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function that implements retry logic
    """
    def decorator(func: Callable[..., ReturnType]) -> Callable[..., ReturnType]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ReturnType:
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        # Log final failure before raising
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts. Final error: {e}",
                            exc_info=True # Include stack trace for the final error
                        )
                        raise
                    # Log retry attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {current_delay:.2f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            # This line should theoretically not be reached if max_attempts >= 1
            raise RuntimeError(f"Retry logic failed unexpectedly after {max_attempts} attempts for {func.__name__}")
        return wrapper
    return decorator

# Removed log_event (duplicate of utils.logging_utils.log_event)
# Removed wait_and_find_element (duplicate of utils.selenium_utils.wait_for_element)
# Removed wait_and_click (duplicate of utils.selenium_utils.safe_click)
# Removed wait_and_send_keys (duplicate of utils.selenium_utils.safe_send_keys)
# Removed is_element_present (similar logic possible via wait_for_element) 