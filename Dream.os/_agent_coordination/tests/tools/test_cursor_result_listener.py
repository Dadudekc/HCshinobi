"""Tests for the Cursor Result Listener service."""

import json
import pytest
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from prometheus_client import REGISTRY

from tools.cursor_result_listener import (
    CursorResultListener,
    CursorResultError,
    MalformedResponseError,
    RetryableError,
    FileOriginError,
    LISTENER_AGENT_ID
)

# --- Test Fixtures ---

@pytest.fixture
def mock_config_service():
    """Mock configuration service."""
    with patch('tools.cursor_result_listener.config_service') as mock:
        mock.get.side_effect = lambda key, default: {
            "cursor.poll_interval": 0.1,
            "cursor.metrics_port": 8000,
            "cursor.pending_dir": "/tmp/pending",
            "cursor.processing_dir": "/tmp/processing",
            "cursor.archive_dir": "/tmp/archive",
            "cursor.error_dir": "/tmp/error",
            "cursor.feedback_dir": "/tmp/feedback",
            "cursor.context_file": "/tmp/context.json",
            "cursor.log_file": "/tmp/cursor.log"
        }.get(key, default)
        yield mock

@pytest.fixture
def mock_log_event():
    """Mock log_event function."""
    with patch('tools.cursor_result_listener.log_event') as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def test_dirs(tmp_path):
    """Create test directories structure."""
    dirs = {
        "pending": tmp_path / "pending",
        "processing": tmp_path / "processing",
        "archive": tmp_path / "archive",
        "error": tmp_path / "error",
        "feedback": tmp_path / "feedback"
    }
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True)
    return dirs

@pytest.fixture
def listener(test_dirs, mock_config_service, mock_log_event):
    """Create CursorResultListener instance with test configuration."""
    with patch('tools.cursor_result_listener.Path') as mock_path:
        mock_path.return_value = Path("/tmp")
        listener = CursorResultListener()
        # Override paths with test directories
        listener.pending_dir = test_dirs["pending"]
        listener.processing_dir = test_dirs["processing"]
        listener.archive_dir = test_dirs["archive"]
        listener.error_dir = test_dirs["error"]
        listener.feedback_dir = test_dirs["feedback"]
        listener.context_file = test_dirs["pending"].parent / "context.json"
        yield listener

@pytest.fixture
def sample_prompt_file(test_dirs):
    """Create a sample prompt file."""
    prompt_data = {
        "prompt_id": "test_prompt_123",
        "prompt_text": "Test prompt content",
        "source_agent": "TestAgent",
        "target_context": {"key": "value"},
        "metadata": {
            "originating_request_id": "req_456"
        }
    }
    file_path = test_dirs["pending"] / "test_prompt.json"
    file_path.write_text(json.dumps(prompt_data))
    return file_path

# --- Test Configuration and Initialization ---

def test_listener_initialization(listener, test_dirs):
    """Test that CursorResultListener initializes correctly."""
    assert listener.pending_dir == test_dirs["pending"]
    assert listener.processing_dir == test_dirs["processing"]
    assert listener.archive_dir == test_dirs["archive"]
    assert listener.error_dir == test_dirs["error"]
    assert listener.feedback_dir == test_dirs["feedback"]
    assert isinstance(listener.file_manager, object)  # FileManager instance
    assert isinstance(listener.command_executor, object)  # CommandExecutor instance

def test_metrics_registration():
    """Test that Prometheus metrics are registered."""
    metrics = [metric.name for metric in REGISTRY.collect()]
    assert "cursor_execution_results" in metrics
    assert "cursor_error_types" in metrics
    assert "cursor_retry_attempts" in metrics
    assert "cursor_processing_duration_seconds" in metrics
    assert "cursor_queue_size" in metrics

# --- Test Context File Operations ---

@pytest.mark.asyncio
async def test_read_context_file_empty(listener):
    """Test reading empty context file."""
    listener.context_file.write_text("")
    context = await listener.read_context_file()
    assert context == {"last_updated": None, "cursor_results": {}}

@pytest.mark.asyncio
async def test_read_context_file_invalid_json(listener):
    """Test reading invalid JSON context file."""
    listener.context_file.write_text("invalid json")
    context = await listener.read_context_file()
    assert context == {"last_updated": None, "cursor_results": {}}

@pytest.mark.asyncio
async def test_write_context_file_success(listener):
    """Test successful context file writing."""
    test_data = {"cursor_results": {"test": "data"}}
    success = await listener.write_context_file(test_data)
    assert success
    written_data = json.loads(listener.context_file.read_text())
    assert "last_updated" in written_data
    assert written_data["cursor_results"] == {"test": "data"}

# --- Test File Processing ---

@pytest.mark.asyncio
async def test_process_file_success(listener, sample_prompt_file, mock_log_event):
    """Test successful prompt file processing."""
    success = await listener.process_file(sample_prompt_file)
    assert success
    
    # Check file movement
    assert not sample_prompt_file.exists()
    assert len(list(listener.archive_dir.glob("*.json"))) == 1
    
    # Check context update
    context = await listener.read_context_file()
    assert "test_prompt_123" in context["cursor_results"]
    assert context["cursor_results"]["test_prompt_123"]["status"] == "success"
    
    # Check feedback file
    feedback_files = list(listener.feedback_dir.glob("*.json"))
    assert len(feedback_files) == 1
    feedback_data = json.loads(feedback_files[0].read_text())
    assert feedback_data["prompt_id"] == "test_prompt_123"
    assert feedback_data["target_agent"] == "TestAgent"

@pytest.mark.asyncio
async def test_process_file_invalid_json(listener, test_dirs):
    """Test processing file with invalid JSON."""
    invalid_file = test_dirs["pending"] / "invalid.json"
    invalid_file.write_text("invalid json")
    
    success = await listener.process_file(invalid_file)
    assert not success
    assert len(list(listener.error_dir.glob("*.json"))) == 1

@pytest.mark.asyncio
async def test_process_file_missing_required_fields(listener, test_dirs):
    """Test processing file with missing required fields."""
    incomplete_file = test_dirs["pending"] / "incomplete.json"
    incomplete_file.write_text("{}")
    
    success = await listener.process_file(incomplete_file)
    assert success  # Should still succeed with defaults
    
    # Check context has default values
    context = await listener.read_context_file()
    result = list(context["cursor_results"].values())[0]
    assert result["status"] == "success"

# --- Test Metrics Updates ---

def test_update_queue_metrics(listener, test_dirs):
    """Test queue size metrics updates."""
    # Create test files
    (test_dirs["pending"] / "test1.json").touch()
    (test_dirs["processing"] / "test2.json").touch()
    (test_dirs["archive"] / "test3.json").touch()
    
    listener.update_queue_metrics()
    
    # Get metric values
    metrics = {
        metric.name: {label["queue_type"]: value 
                     for label, value, _ in metric.samples}
        for metric in REGISTRY.collect()
        if metric.name == "cursor_queue_size"
    }
    
    assert metrics["cursor_queue_size"]["pending"] == 1
    assert metrics["cursor_queue_size"]["processing"] == 1
    assert metrics["cursor_queue_size"]["archive"] == 1
    assert metrics["cursor_queue_size"]["error"] == 0

# --- Test Error Handling ---

@pytest.mark.asyncio
async def test_process_file_move_error(listener, sample_prompt_file):
    """Test handling of file move errors."""
    with patch.object(listener.file_manager, 'safe_move', 
                     side_effect=FileOriginError("Move failed")):
        success = await listener.process_file(sample_prompt_file)
        assert not success
        assert sample_prompt_file.exists()

@pytest.mark.asyncio
async def test_process_file_cursor_error(listener, sample_prompt_file):
    """Test handling of Cursor API errors."""
    with patch.object(listener.command_executor, 'run_command',
                     side_effect=RetryableError("API timeout")):
        success = await listener.process_file(sample_prompt_file)
        assert not success
        assert len(list(listener.error_dir.glob("*.json"))) == 1

# --- Test Main Loop ---

@pytest.mark.asyncio
async def test_main_loop_startup_shutdown(listener):
    """Test main loop startup and graceful shutdown."""
    with patch('tools.cursor_result_listener.start_http_server'):
        # Start listener in background task
        listener_task = asyncio.create_task(listener.start())
        
        # Allow some startup time
        await asyncio.sleep(0.1)
        
        # Trigger shutdown
        await listener.stop()
        
        # Wait for shutdown
        await listener_task
        
        # Verify cleanup
        assert listener._stop_event.is_set()

@pytest.mark.asyncio
async def test_main_loop_file_processing(listener, test_dirs):
    """Test main loop processes files in sequence."""
    # Create multiple test files
    files = []
    for i in range(3):
        file_path = test_dirs["pending"] / f"test{i}.json"
        file_path.write_text(json.dumps({
            "prompt_id": f"test_{i}",
            "source_agent": "TestAgent"
        }))
        files.append(file_path)
    
    with patch('tools.cursor_result_listener.start_http_server'):
        # Start listener in background
        listener_task = asyncio.create_task(listener.start())
        
        # Allow processing time
        await asyncio.sleep(0.3)
        
        # Stop listener
        await listener.stop()
        await listener_task
        
        # Verify all files processed
        assert len(list(test_dirs["pending"].glob("*.json"))) == 0
        assert len(list(test_dirs["archive"].glob("*.json"))) == 3

# --- Integration Tests ---

@pytest.mark.asyncio
async def test_full_processing_cycle(listener, sample_prompt_file, mock_log_event):
    """Test complete file processing cycle with all components."""
    # Start listener
    listener_task = asyncio.create_task(listener.start())
    
    # Allow processing time
    await asyncio.sleep(0.2)
    
    # Stop listener
    await listener.stop()
    await listener_task
    
    # Verify file movement
    assert not sample_prompt_file.exists()
    assert len(list(listener.archive_dir.glob("*.json"))) == 1
    
    # Verify context update
    context = await listener.read_context_file()
    assert "test_prompt_123" in context["cursor_results"]
    
    # Verify feedback
    feedback_files = list(listener.feedback_dir.glob("*.json"))
    assert len(feedback_files) == 1
    
    # Verify metrics
    metrics = {
        metric.name: {label["source_agent"]: value 
                     for label, value, _ in metric.samples}
        for metric in REGISTRY.collect()
        if metric.name == "cursor_processing_duration_seconds"
    }
    assert "TestAgent" in metrics["cursor_processing_duration_seconds"]
    
    # Verify events logged
    mock_log_event.assert_any_call(
        "FEEDBACK_SENT",
        LISTENER_AGENT_ID,
        {"feedback_id": mock_log_event.call_args_list[0][0][2]["feedback_id"],
         "prompt_id": "test_prompt_123",
         "target_agent": "TestAgent"}
    ) 

# --- Production Readiness Tests ---

@pytest.mark.asyncio
async def test_resource_cleanup_on_crash(listener, test_dirs):
    """Test that resources are properly cleaned up even if the listener crashes."""
    # Create files in processing state
    processing_file = test_dirs["processing"] / "stuck.json"
    processing_file.write_text(json.dumps({"prompt_id": "stuck_123"}))
    
    # Simulate crash during startup
    with patch.object(listener, 'process_file', side_effect=Exception("Simulated crash")):
        listener_task = asyncio.create_task(listener.start())
        await asyncio.sleep(0.1)
        
        # Force stop
        await listener.stop()
        await listener_task
        
        # Verify cleanup occurred
        assert not processing_file.exists()
        assert len(list(test_dirs["error"].glob("*.json"))) == 1

@pytest.mark.asyncio
async def test_concurrent_file_processing(listener, test_dirs):
    """Test that multiple files can be processed concurrently."""
    # Create multiple files
    file_count = 5
    files = []
    for i in range(file_count):
        file_path = test_dirs["pending"] / f"concurrent_{i}.json"
        file_path.write_text(json.dumps({
            "prompt_id": f"concurrent_{i}",
            "source_agent": "TestAgent"
        }))
        files.append(file_path)
    
    # Process files concurrently
    tasks = [listener.process_file(file) for file in files]
    results = await asyncio.gather(*tasks)
    
    # Verify all files processed successfully
    assert all(results)
    assert len(list(test_dirs["archive"].glob("*.json"))) == file_count

@pytest.mark.asyncio
async def test_system_resilience(listener, test_dirs, mock_log_event):
    """Test system resilience against various failure scenarios."""
    # Prepare test file
    file_path = test_dirs["pending"] / "resilience_test.json"
    file_path.write_text(json.dumps({
        "prompt_id": "resilience_123",
        "source_agent": "TestAgent"
    }))
    
    # Test scenarios that should be handled gracefully
    scenarios = [
        (FileOriginError("File locked"), True),  # Retryable
        (PermissionError("Access denied"), True),  # Retryable
        (MalformedResponseError("Bad response"), False),  # Non-retryable
        (asyncio.TimeoutError(), True),  # Retryable
    ]
    
    for error, should_retry in scenarios:
        with patch.object(listener.command_executor, 'run_command', side_effect=error):
            success = await listener.process_file(file_path)
            if should_retry:
                mock_log_event.assert_any_call(
                    "PROCESSING_RETRY",
                    LISTENER_AGENT_ID,
                    {"prompt_id": "resilience_123", "error": str(error)}
                )

@pytest.mark.asyncio
async def test_memory_cleanup(listener):
    """Test that memory is properly cleaned up during processing."""
    import psutil
    import gc
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Process a large number of files
    for i in range(100):
        await listener.process_file(None)  # Mock processing
        gc.collect()  # Force garbage collection
    
    # Check memory hasn't grown significantly (allow 10% growth)
    final_memory = process.memory_info().rss
    assert final_memory <= initial_memory * 1.1

def test_production_config_validation(mock_config_service):
    """Validate production configuration settings."""
    required_settings = [
        "cursor.poll_interval",
        "cursor.metrics_port",
        "cursor.pending_dir",
        "cursor.processing_dir",
        "cursor.archive_dir",
        "cursor.error_dir",
        "cursor.feedback_dir",
        "cursor.context_file",
        "cursor.log_file"
    ]
    
    for setting in required_settings:
        value = mock_config_service.get(setting, None)
        assert value is not None, f"Missing required production setting: {setting}"

if __name__ == '__main__':
    pytest.main(['-v', '--cov=tools.cursor_result_listener', '--cov-report=html']) 