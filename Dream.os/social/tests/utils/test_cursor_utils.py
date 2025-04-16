import os
import json
import uuid
import pytest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime, timezone
from utils.cursor_utils import export_prompt_for_cursor, CURSOR_QUEUE_DIR

@pytest.fixture
def valid_prompt_payload():
    """Fixture providing a valid prompt payload."""
    return {
        "prompt_id": "test_prompt_123",
        "objective": "Test objective",
        "prompt_instruction": "Test instruction",
        "context_files": ["file1.py", "file2.py"],
        "target_file": "target.py",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec='seconds') + 'Z'
    }

@pytest.fixture
def temp_cursor_dir(tmp_path):
    """Fixture providing a temporary cursor queue directory."""
    cursor_dir = tmp_path / ".cursor" / "social_queued_prompts"
    cursor_dir.mkdir(parents=True)
    with patch('utils.cursor_utils.CURSOR_QUEUE_DIR', str(cursor_dir)):
        yield cursor_dir

class TestCursorUtils:
    def test_export_prompt_success(self, valid_prompt_payload, temp_cursor_dir):
        """Test successful prompt export."""
        result = export_prompt_for_cursor(valid_prompt_payload)
        
        assert result is not None
        assert os.path.exists(result)
        
        # Verify file contents
        with open(result, 'r') as f:
            saved_payload = json.load(f)
            assert saved_payload == valid_prompt_payload
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_success"})

    def test_export_prompt_invalid_payload(self):
        """Test export with invalid payload structure."""
        invalid_payload = {"not_objective": "missing required field"}
        
        result = export_prompt_for_cursor(invalid_payload)
        
        assert result is None
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_invalid_payload"})

    def test_export_prompt_none_payload(self):
        """Test export with None payload."""
        result = export_prompt_for_cursor(None)
        
        assert result is None
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_none_payload"})

    def test_export_prompt_directory_creation(self, valid_prompt_payload, tmp_path):
        """Test directory creation during export."""
        new_dir = tmp_path / "new_cursor_dir"
        with patch('utils.cursor_utils.CURSOR_QUEUE_DIR', str(new_dir)):
            result = export_prompt_for_cursor(valid_prompt_payload)
            
            assert result is not None
            assert os.path.exists(new_dir)
            assert os.path.exists(result)
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_directory_creation"})

    def test_export_prompt_os_error(self, valid_prompt_payload):
        """Test handling of OS errors during export."""
        with patch('os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = OSError("Permission denied")
            
            result = export_prompt_for_cursor(valid_prompt_payload)
            
            assert result is None
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_os_error"})

    def test_export_prompt_json_error(self, valid_prompt_payload, temp_cursor_dir):
        """Test handling of JSON serialization errors."""
        # Create an object that can't be JSON serialized
        valid_prompt_payload['bad_field'] = object()
        
        result = export_prompt_for_cursor(valid_prompt_payload)
        
        assert result is None
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_json_error"})

    def test_export_prompt_write_error(self, valid_prompt_payload, temp_cursor_dir):
        """Test handling of file write errors."""
        mock_file = mock_open()
        mock_file.side_effect = IOError("Write error")
        
        with patch('builtins.open', mock_file):
            result = export_prompt_for_cursor(valid_prompt_payload)
            
            assert result is None
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_write_error"})

    def test_export_prompt_filename_generation(self, valid_prompt_payload, temp_cursor_dir):
        """Test proper filename generation with timestamp and prompt_id."""
        result = export_prompt_for_cursor(valid_prompt_payload)
        
        assert result is not None
        filename = os.path.basename(result)
        assert filename.startswith("prompt_")
        assert valid_prompt_payload['prompt_id'] in filename
        assert filename.endswith(".json")
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_filename_generation"})

    def test_export_prompt_special_chars_in_id(self, valid_prompt_payload, temp_cursor_dir):
        """Test handling of special characters in prompt_id."""
        valid_prompt_payload['prompt_id'] = "test/with@special#chars"
        
        result = export_prompt_for_cursor(valid_prompt_payload)
        
        assert result is not None
        filename = os.path.basename(result)
        assert "test_with_special_chars" in filename
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_special_chars_in_id"})

    def test_export_prompt_no_prompt_id(self, valid_prompt_payload, temp_cursor_dir):
        """Test export when prompt_id is not provided."""
        del valid_prompt_payload['prompt_id']
        
        result = export_prompt_for_cursor(valid_prompt_payload)
        
        assert result is not None
        filename = os.path.basename(result)
        # Should contain a UUID
        assert any(part for part in filename.split('_') if len(part) == 32)
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_export_prompt_no_prompt_id"})

    @pytest.mark.integration
    def test_integration_file_persistence(self, valid_prompt_payload, temp_cursor_dir):
        """Integration test for file persistence and cleanup."""
        # Export the prompt
        result = export_prompt_for_cursor(valid_prompt_payload)
        assert result is not None
        
        # Verify file exists and content is correct
        assert os.path.exists(result)
        with open(result, 'r') as f:
            saved_payload = json.load(f)
            assert saved_payload == valid_prompt_payload
        
        # Clean up
        os.remove(result)
        assert not os.path.exists(result)
        
        log_event("TEST_ADDED", "CoverageAgent", {"test": "test_integration_file_persistence"})

if __name__ == '__main__':
    pytest.main([__file__]) 