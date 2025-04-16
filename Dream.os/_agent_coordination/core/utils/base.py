"""
Base utilities for DreamOS agent coordination.
"""

import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Callable
from pathlib import Path
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

T = TypeVar('T')

class Singleton(type):
    """Metaclass for creating singleton classes."""
    _instances: Dict[type, Any] = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class AsyncLockManager:
    """Context manager for async locks with timeout."""
    
    def __init__(self, lock: asyncio.Lock, timeout: Optional[float] = None):
        self.lock = lock
        self.timeout = timeout
        
    async def __aenter__(self):
        try:
            await asyncio.wait_for(self.lock.acquire(), self.timeout)
            return self
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to acquire lock within {self.timeout} seconds")
            
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

class Cache(Generic[T]):
    """Generic cache with TTL support."""
    
    def __init__(self, ttl: Optional[float] = None):
        self._data: Dict[str, tuple[T, float]] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[T]:
        """Get value from cache."""
        async with AsyncLockManager(self._lock):
            if key not in self._data:
                return None
                
            value, timestamp = self._data[key]
            if self._ttl and (datetime.now().timestamp() - timestamp) > self._ttl:
                del self._data[key]
                return None
                
            return value
            
    async def set(self, key: str, value: T) -> None:
        """Set value in cache."""
        async with AsyncLockManager(self._lock):
            self._data[key] = (value, datetime.now().timestamp())
            
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        async with AsyncLockManager(self._lock):
            self._data.pop(key, None)
            
    async def clear(self) -> None:
        """Clear all values from cache."""
        async with AsyncLockManager(self._lock):
            self._data.clear()

class RetryManager:
    """Utility for handling retries with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0,
                 max_delay: float = 10.0, exponential_base: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )
                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    
        raise last_error

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"

def load_json_file(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse JSON file."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {path}: {e}")
        raise

def save_json_file(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """Save data to JSON file."""
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=indent)
    except Exception as e:
        logger.error(f"Error saving JSON file {path}: {e}")
        raise

class ValidationError(Exception):
    """Base exception for validation errors."""
    pass

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that dictionary contains all required fields."""
    missing = [field for field in required_fields if field not in data]
    if missing:
        raise ValidationError(f"Missing required fields: {', '.join(missing)}")

def validate_field_type(value: Any, expected_type: type, field_name: str) -> None:
    """Validate that a value is of the expected type."""
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"Field '{field_name}' must be of type {expected_type.__name__}, "
            f"got {type(value).__name__}"
        ) 