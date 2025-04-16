import os
import time
import pytest
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY

# Import the module under test
from tools.cursor_result_listener import (
    update_execution_metrics,
    update_error_metrics,
    update_queue_metrics,
    track_processing_time,
    EXECUTION_COUNTER,
    ERROR_COUNTER,
    RETRY_COUNTER,
    QUEUE_SIZE
)

@pytest.fixture
def mock_directories():
    """Mock directory structure for testing queue metrics."""
    with patch('os.listdir') as mock_listdir:
        mock_listdir.return_value = ['file1.json', 'file2.json', 'not_json.txt']
        yield mock_listdir

@pytest.fixture
def clean_registry():
    """Clear prometheus registry between tests."""
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)
    yield
    for collector in list(REGISTRY._collector_to_names.keys()):
        REGISTRY.unregister(collector)

class TestCursorMetrics:
    """Test suite for cursor metrics functionality."""
    
    def test_execution_metrics_success(self, clean_registry):
        """Test execution metrics for successful operations."""
        update_execution_metrics("test_prompt", True, "TestAgent")
        
        # Get the metric value
        metric = EXECUTION_COUNTER.labels(status="success", source_agent="TestAgent")
        assert metric._value.get() == 1.0
        
        # Verify failure counter hasn't changed
        failure_metric = EXECUTION_COUNTER.labels(status="failure", source_agent="TestAgent")
        assert failure_metric._value.get() == 0.0

    def test_execution_metrics_failure(self, clean_registry):
        """Test execution metrics for failed operations."""
        update_execution_metrics("test_prompt", False, "TestAgent")
        
        # Get the metric value
        metric = EXECUTION_COUNTER.labels(status="failure", source_agent="TestAgent")
        assert metric._value.get() == 1.0
        
        # Verify success counter hasn't changed
        success_metric = EXECUTION_COUNTER.labels(status="success", source_agent="TestAgent")
        assert success_metric._value.get() == 0.0

    def test_error_metrics(self, clean_registry):
        """Test error metrics tracking."""
        error_type = "MalformedResponseError"
        update_error_metrics("test_prompt", error_type, "TestAgent")
        
        # Check error counter
        error_metric = ERROR_COUNTER.labels(error_type=error_type, source_agent="TestAgent")
        assert error_metric._value.get() == 1.0
        
        # Check retry counter
        retry_metric = RETRY_COUNTER.labels(source_agent="TestAgent")
        assert retry_metric._value.get() == 1.0

    def test_queue_metrics(self, mock_directories, clean_registry):
        """Test queue size metrics."""
        update_queue_metrics()
        
        # Should count only .json files (2 in mock data)
        for queue_type in ['pending', 'processing', 'archive', 'error', 'feedback']:
            metric = QUEUE_SIZE.labels(queue_type=queue_type)
            assert metric._value.get() == 2.0

    def test_processing_time_tracking(self, clean_registry):
        """Test the processing time context manager."""
        with track_processing_time("TestAgent"):
            time.sleep(0.1)  # Simulate some work
        
        # Get all samples for the processing time metric
        samples = list(REGISTRY.get_sample_value(
            'cursor_processing_duration_seconds',
            {'source_agent': 'TestAgent'}
        ))
        
        # Verify we have a non-zero processing time
        assert len(samples) > 0
        assert samples[0] > 0

    def test_multiple_error_types(self, clean_registry):
        """Test tracking of multiple error types."""
        error_types = ["RetryableError", "MalformedResponseError", "FileOriginError"]
        
        for error_type in error_types:
            update_error_metrics("test_prompt", error_type, "TestAgent")
        
        # Verify each error type was counted
        for error_type in error_types:
            metric = ERROR_COUNTER.labels(error_type=error_type, source_agent="TestAgent")
            assert metric._value.get() == 1.0

    def test_queue_metrics_error_handling(self, clean_registry):
        """Test queue metrics handles directory access errors gracefully."""
        with patch('os.listdir', side_effect=OSError("Permission denied")):
            # Should not raise an exception
            update_queue_metrics()
            
            # Verify metric was not updated
            for queue_type in ['pending', 'processing', 'archive', 'error', 'feedback']:
                metric = QUEUE_SIZE.labels(queue_type=queue_type)
                assert metric._value.get() == 0.0

    def test_execution_metrics_default_agent(self, clean_registry):
        """Test execution metrics with default agent name."""
        update_execution_metrics("test_prompt", True)
        
        metric = EXECUTION_COUNTER.labels(status="success", source_agent="UNKNOWN_AGENT")
        assert metric._value.get() == 1.0

    def test_concurrent_metric_updates(self, clean_registry):
        """Test concurrent updates to metrics."""
        from concurrent.futures import ThreadPoolExecutor
        import random
        
        def random_update():
            success = random.choice([True, False])
            update_execution_metrics(f"prompt_{random.randint(1,1000)}", success, "TestAgent")
        
        # Simulate concurrent updates
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(random_update) for _ in range(10)]
            
        # Verify total counts match expected updates
        success_metric = EXECUTION_COUNTER.labels(status="success", source_agent="TestAgent")
        failure_metric = EXECUTION_COUNTER.labels(status="failure", source_agent="TestAgent")
        total_updates = success_metric._value.get() + failure_metric._value.get()
        assert total_updates == 10.0 