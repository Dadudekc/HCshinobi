import unittest
import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # utils/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Module to test
from utils.performance_logger import PerformanceLogger

# Need to know the log path defined in the module to patch open correctly
# (Assuming it's imported or defined in performance_logger)
# If LOG_PATH is dynamic, this approach might need adjustment
# For now, assume we patch open globally within the test scope
LOG_PATH_IN_MODULE = "memory/performance_log.jsonl"

class TestPerformanceLogger(unittest.TestCase):

    @patch('utils.performance_logger.print') # Mock print to suppress error messages during test
    @patch("builtins.open", new_callable=mock_open)
    def test_log_successful_outcome(self, mock_file_open, mock_print):
        """Test logging a successful task outcome."""
        # Arrange
        task_id = "task-123"
        agent_id = "Agent-007"
        task_type = "analysis"
        status = "success"
        start_time = datetime.utcnow() - timedelta(seconds=5)
        end_time = datetime.utcnow()
        input_summary = {"input_files": 1}
        output_summary = {"output_files": 1, "result": "ok"}
        
        # Act
        PerformanceLogger.log_outcome(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
            input_summary=input_summary,
            output_summary=output_summary
        )
        
        # Assert
        # Verify open was called correctly
        mock_file_open.assert_called_once_with(LOG_PATH_IN_MODULE, "a", encoding="utf-8")
        
        # Verify write was called
        mock_file_open().write.assert_called_once()
        
        # Get the written content and parse it
        written_content = mock_file_open().write.call_args[0][0]
        self.assertTrue(written_content.endswith("\n"))
        logged_entry = json.loads(written_content.strip()) # Remove trailing newline before parsing
        
        # Verify structure and content
        self.assertEqual(logged_entry["task_id"], task_id)
        self.assertEqual(logged_entry["agent_id"], agent_id)
        self.assertEqual(logged_entry["task_type"], task_type)
        self.assertEqual(logged_entry["status"], status.upper())
        self.assertEqual(logged_entry["start_time"], start_time.isoformat() + "Z")
        self.assertEqual(logged_entry["end_time"], end_time.isoformat() + "Z")
        self.assertAlmostEqual(logged_entry["duration_ms"], 5000, delta=50) # Allow small delta for timing
        self.assertIsNone(logged_entry["error_message"])
        self.assertEqual(logged_entry["input_summary"], input_summary)
        self.assertEqual(logged_entry["output_summary"], output_summary)
        self.assertTrue("log_timestamp" in logged_entry)
        mock_print.assert_not_called() # No error print expected

    @patch('utils.performance_logger.print')
    @patch("builtins.open", new_callable=mock_open)
    def test_log_failed_outcome(self, mock_file_open, mock_print):
        """Test logging a failed task outcome with an error message."""
        # Arrange
        task_id = "task-456"
        agent_id = "Agent-008"
        task_type = "execution"
        status = "failed"
        start_time = datetime.utcnow() - timedelta(seconds=2)
        end_time = datetime.utcnow()
        error_message = "Something went wrong"
        
        # Act
        PerformanceLogger.log_outcome(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            status=status,
            start_time=start_time,
            end_time=end_time,
            error_message=error_message
        )
        
        # Assert
        mock_file_open.assert_called_once_with(LOG_PATH_IN_MODULE, "a", encoding="utf-8")
        mock_file_open().write.assert_called_once()
        logged_entry = json.loads(mock_file_open().write.call_args[0][0].strip())
        
        self.assertEqual(logged_entry["task_id"], task_id)
        self.assertEqual(logged_entry["agent_id"], agent_id)
        self.assertEqual(logged_entry["status"], status.upper())
        self.assertAlmostEqual(logged_entry["duration_ms"], 2000, delta=50)
        self.assertEqual(logged_entry["error_message"], error_message)
        self.assertIsNone(logged_entry["input_summary"])
        self.assertIsNone(logged_entry["output_summary"])
        mock_print.assert_not_called()

    @patch('utils.performance_logger.print')
    @patch("builtins.open", new_callable=mock_open)
    def test_log_file_write_error(self, mock_file_open, mock_print):
        """Test that an error during file writing is caught and printed."""
        # Arrange
        mock_file_open.side_effect = IOError("Disk full") # Simulate write error
        task_id = "task-789"
        agent_id = "Agent-009"
        task_type = "logging_test"
        status = "error"
        start_time = datetime.utcnow()
        end_time = datetime.utcnow()

        # Act
        PerformanceLogger.log_outcome(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            status=status,
            start_time=start_time,
            end_time=end_time
        )

        # Assert
        mock_file_open.assert_called_once_with(LOG_PATH_IN_MODULE, "a", encoding="utf-8")
        # Check that print was called with the error message
        mock_print.assert_called_once()
        self.assertIn("Failed to write to performance log", mock_print.call_args[0][0])
        self.assertIn("Disk full", mock_print.call_args[0][0])


if __name__ == '__main__':
    unittest.main() 