import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from core.utils.base import (
    Singleton, AsyncLockManager, Cache, RetryManager,
    generate_id, load_json_file, save_json_file,
    ValidationError, validate_required_fields, validate_field_type
)

# Test Singleton
class TestSingleton(metaclass=Singleton):
    def __init__(self, value: str = "test"):
        self.value = value

def test_singleton():
    # Create multiple instances
    instance1 = TestSingleton()
    instance2 = TestSingleton("other")
    
    # Should be the same instance
    assert instance1 is instance2
    assert instance1.value == instance2.value
    assert instance1.value == "test"  # Second init args ignored

@pytest.mark.asyncio
async def test_async_lock_manager():
    lock = asyncio.Lock()
    
    # Test normal operation
    async with AsyncLockManager(lock):
        assert lock.locked()
    assert not lock.locked()
    
    # Test timeout
    async with AsyncLockManager(lock):
        with pytest.raises(TimeoutError):
            async with AsyncLockManager(lock, timeout=0.1):
                pass

@pytest.mark.asyncio
async def test_cache():
    cache = Cache[str](ttl=0.1)  # 100ms TTL
    
    # Test set and get
    await cache.set("key1", "value1")
    assert await cache.get("key1") == "value1"
    
    # Test TTL expiration
    await asyncio.sleep(0.2)  # Wait for TTL
    assert await cache.get("key1") is None
    
    # Test delete
    await cache.set("key2", "value2")
    await cache.delete("key2")
    assert await cache.get("key2") is None
    
    # Test clear
    await cache.set("key3", "value3")
    await cache.clear()
    assert await cache.get("key3") is None

@pytest.mark.asyncio
async def test_retry_manager():
    retry_manager = RetryManager(
        max_retries=3,
        base_delay=0.1,
        max_delay=0.3
    )
    
    # Test successful execution
    async def success():
        return "success"
    
    result = await retry_manager.execute(success)
    assert result == "success"
    
    # Test retry on failure
    attempt = 0
    async def fail_twice():
        nonlocal attempt
        attempt += 1
        if attempt <= 2:
            raise ValueError("Temporary error")
        return "success"
    
    result = await retry_manager.execute(fail_twice)
    assert result == "success"
    assert attempt == 3
    
    # Test max retries exceeded
    async def always_fail():
        raise ValueError("Permanent error")
    
    with pytest.raises(ValueError, match="Permanent error"):
        await retry_manager.execute(always_fail)

def test_generate_id():
    # Test basic ID generation
    id1 = generate_id()
    id2 = generate_id()
    assert len(id1) == 12
    assert id1 != id2
    
    # Test with prefix
    prefixed = generate_id("test_")
    assert prefixed.startswith("test_")
    assert len(prefixed) == 17  # prefix + 12 chars

def test_json_file_operations():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.json"
        
        # Test save
        data = {"key": "value", "number": 42}
        save_json_file(data, file_path)
        assert file_path.exists()
        
        # Test load
        loaded = load_json_file(file_path)
        assert loaded == data
        
        # Test error handling
        with pytest.raises(Exception):
            load_json_file(Path(tmpdir) / "nonexistent.json")

def test_validation():
    # Test required fields
    data = {"field1": "value1", "field2": 42}
    validate_required_fields(data, ["field1", "field2"])
    
    with pytest.raises(ValidationError) as exc:
        validate_required_fields(data, ["field1", "field3"])
    assert "field3" in str(exc.value)
    
    # Test field type
    validate_field_type("test", str, "string_field")
    validate_field_type(42, int, "int_field")
    
    with pytest.raises(ValidationError) as exc:
        validate_field_type("test", int, "number_field")
    assert "number_field" in str(exc.value)
    assert "int" in str(exc.value) 