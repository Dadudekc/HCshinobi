import os
import sys
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, mock_open, MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dreamforge.core.governance_memory_engine import (
    log_event,
    get_events,
    GOVERNANCE_LOG_FILE,
    _SOURCE_ID
)

@pytest.fixture
def mock_file_ops():
    """Mock file operations."""
    mock_open_fn = mock_open()
    with patch('builtins.open', mock_open_fn):
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists', return_value=True):
                yield {
                    'open': mock_open_fn,
                    'makedirs': mock_makedirs
                }

def test_log_event_success(mock_file_ops):
    """Test successful event logging."""
    event_type = "TEST_EVENT"
    data = {"test_key": "test_value"}
    source = "TestSource"
    
    result = log_event(event_type, data, source)
    
    assert result is True
    mock_file_ops['makedirs'].assert_called_once()
    mock_file_ops['open'].assert_called_once_with(GOVERNANCE_LOG_FILE, "a")
    
    # Verify written event structure
    handle = mock_file_ops['open']()
    written_data = handle.write.call_args[0][0]
    event = json.loads(written_data)
    assert_event_structure(event, event_type, source, data)

def test_log_event_makedirs_error(mock_file_ops):
    """Test logging when directory creation fails."""
    mock_file_ops['makedirs'].side_effect = PermissionError()
    
    result = log_event("TEST", {"data": "test"})
    
    assert result is False
    mock_file_ops['open'].assert_not_called()

def test_log_event_write_error(mock_file_ops):
    """Test logging when file write fails."""
    mock_file_ops['open'].side_effect = PermissionError()
    
    result = log_event("TEST", {"data": "test"})
    
    assert result is False

@pytest.mark.parametrize("event_type,data,source", [
    (None, {"data": "test"}, "source"),
    ("TEST", None, "source"),
    ("TEST", {"data": "test"}, None),
    ("", {"data": "test"}, "source"),
    ("TEST", {}, "source"),
])
def test_log_event_invalid_params(event_type, data, source, mock_file_ops):
    """Test logging with invalid parameters."""
    result = log_event(event_type, data, source)
    assert result is False
    mock_file_ops['open'].assert_not_called()

def test_get_events_empty_file(mock_file_ops):
    """Test getting events from empty log file."""
    mock_file_ops['open'].return_value.__enter__().readlines.return_value = []
    
    events = get_events()
    
    assert events == []
    mock_file_ops['open'].assert_called_once_with(GOVERNANCE_LOG_FILE, "r")

def test_get_events_with_filter():
    """Test getting events with type and source filters."""
    test_events = [
        {"type": "TEST1", "source": "SRC1", "data": {"val": 1}},
        {"type": "TEST2", "source": "SRC1", "data": {"val": 2}},
        {"type": "TEST1", "source": "SRC2", "data": {"val": 3}},
    ]
    
    events_str = "\n".join(json.dumps(e) for e in test_events)
    
    with patch('builtins.open', mock_open(read_data=events_str)):
        with patch('os.path.exists', return_value=True):
            # Filter by type
            events = get_events(event_type="TEST1")
            assert len(events) == 2
            assert all(e["type"] == "TEST1" for e in events)
            
            # Filter by source
            events = get_events(source="SRC1")
            assert len(events) == 2
            assert all(e["source"] == "SRC1" for e in events)
            
            # Filter by both
            events = get_events(event_type="TEST1", source="SRC1")
            assert len(events) == 1
            assert events[0]["type"] == "TEST1"
            assert events[0]["source"] == "SRC1"

def test_get_events_with_limit():
    """Test event retrieval with limit."""
    test_events = [{"type": "TEST", "data": {"val": i}} for i in range(10)]
    events_str = "\n".join(json.dumps(e) for e in test_events)
    
    with patch('builtins.open', mock_open(read_data=events_str)):
        with patch('os.path.exists', return_value=True):
            events = get_events(limit=5)
            assert len(events) == 5

def test_get_events_invalid_json():
    """Test handling of invalid JSON in log file."""
    invalid_data = "valid_json\ninvalid}{json\nvalid_json"
    
    with patch('builtins.open', mock_open(read_data=invalid_data)):
        with patch('os.path.exists', return_value=True):
            events = get_events()
            assert len(events) == 0

def test_get_events_file_not_found():
    """Test getting events when log file doesn't exist."""
    with patch('os.path.exists', return_value=False):
        events = get_events()
        assert events == []

def test_source_id_constant():
    """Test _SOURCE_ID constant."""
    assert _SOURCE_ID == "GovernanceEngine"
    assert isinstance(_SOURCE_ID, str)

def test_governance_log_file_path():
    """Test GOVERNANCE_LOG_FILE path construction."""
    assert GOVERNANCE_LOG_FILE.endswith("runtime/governance_memory.jsonl") 