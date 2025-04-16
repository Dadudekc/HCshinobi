import os
import sys
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dreamforge.core.feedback_engine import FeedbackEngine
from dreamforge.core.exceptions import FeedbackProcessingError, MaxRetriesExceededError

@pytest.fixture
def feedback_engine():
    """Provides a fresh FeedbackEngine instance for each test."""
    engine = FeedbackEngine()
    yield engine
    # Cleanup any test data
    engine.clear_feedback()

def test_process_feedback_success(feedback_engine):
    """Test successful feedback processing."""
    feedback_data = {
        "task_id": "TEST-001",
        "status": "success",
        "message": "Task completed successfully",
        "timestamp": datetime.now().isoformat()
    }
    
    result = feedback_engine.process_feedback(feedback_data)
    assert result is True
    stored_feedback = feedback_engine.get_feedback("TEST-001")
    assert stored_feedback["status"] == "success"
    assert stored_feedback["message"] == "Task completed successfully"
    assert "timestamp" in stored_feedback
    assert stored_feedback.get("retry_count", 0) == 0

def test_process_feedback_failure_with_retry(feedback_engine):
    """Test feedback processing with failure and retry."""
    feedback_data = {
        "task_id": "TEST-002",
        "status": "failure",
        "message": "Task failed, retrying",
        "timestamp": datetime.now().isoformat()
    }
    
    # First attempt
    result = feedback_engine.process_feedback(feedback_data)
    assert result is False
    stored_feedback = feedback_engine.get_feedback("TEST-002")
    assert stored_feedback["retry_count"] == 1
    
    # Second attempt
    result = feedback_engine.process_feedback(feedback_data)
    stored_feedback = feedback_engine.get_feedback("TEST-002")
    assert stored_feedback["retry_count"] == 2

def test_max_retries_exceeded(feedback_engine):
    """Test that maximum retry limit is enforced."""
    feedback_data = {
        "task_id": "TEST-003",
        "status": "failure",
        "message": "Task failed",
        "timestamp": datetime.now().isoformat()
    }
    
    # Simulate multiple failures up to max retries
    for _ in range(FeedbackEngine.MAX_RETRIES):
        result = feedback_engine.process_feedback(feedback_data)
        assert result is False
    
    # Next attempt should raise MaxRetriesExceededError
    with pytest.raises(MaxRetriesExceededError):
        feedback_engine.process_feedback(feedback_data)

def test_process_multiple_feedback_entries(feedback_engine):
    """Test processing multiple feedback entries for different tasks."""
    tasks = ["TEST-004", "TEST-005", "TEST-006"]
    for task_id in tasks:
        feedback_data = {
            "task_id": task_id,
            "status": "success",
            "message": f"Task {task_id} completed",
            "timestamp": datetime.now().isoformat()
        }
        feedback_engine.process_feedback(feedback_data)
    
    # Verify all feedback entries are stored correctly
    for task_id in tasks:
        stored_feedback = feedback_engine.get_feedback(task_id)
        assert stored_feedback["task_id"] == task_id
        assert stored_feedback["status"] == "success"

def test_get_nonexistent_feedback(feedback_engine):
    """Test attempting to get feedback for a nonexistent task."""
    assert feedback_engine.get_feedback("NONEXISTENT-TASK") is None

def test_clear_feedback(feedback_engine):
    """Test clearing all feedback entries."""
    feedback_data = {
        "task_id": "TEST-007",
        "status": "success",
        "message": "Task completed",
        "timestamp": datetime.now().isoformat()
    }
    feedback_engine.process_feedback(feedback_data)
    
    feedback_engine.clear_feedback()
    assert feedback_engine.get_feedback("TEST-007") is None

def test_invalid_feedback_data(feedback_engine):
    """Test processing invalid feedback data."""
    invalid_data = {
        "task_id": "TEST-008"
        # Missing required fields
    }
    
    with pytest.raises(FeedbackProcessingError):
        feedback_engine.process_feedback(invalid_data)

def test_feedback_timestamp_tracking(feedback_engine):
    """Test that feedback timestamps are properly tracked."""
    current_time = datetime.now()
    feedback_data = {
        "task_id": "TEST-009",
        "status": "success",
        "message": "Task completed",
        "timestamp": current_time.isoformat()
    }
    
    feedback_engine.process_feedback(feedback_data)
    stored_feedback = feedback_engine.get_feedback("TEST-009")
    stored_time = datetime.fromisoformat(stored_feedback["timestamp"])
    
    # Verify timestamp is within 1 second of original
    assert abs((stored_time - current_time).total_seconds()) < 1 