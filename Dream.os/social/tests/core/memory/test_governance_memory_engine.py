import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
import time

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # core/memory
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Module to test
from core.memory import governance_memory_engine


class TestGovernanceMemoryEngine(unittest.TestCase):

    def setUp(self):
        """Create a temporary file for logging."""
        # Create a temporary file and get its path
        self.temp_log_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        self.temp_log_path = self.temp_log_file.name
        self.temp_log_file.close() # Close it so the module can open it
        
        # Patch the module-level constant to use our temp file
        self.log_path_patcher = patch.object(governance_memory_engine, 'GOVERNANCE_LOG_FILE', self.temp_log_path)
        self.log_path_patcher.start()
        
        # Also patch print within the module to suppress output
        self.print_patcher = patch('core.memory.governance_memory_engine.print')
        self.mock_print = self.print_patcher.start()

    def tearDown(self):
        """Stop patchers and remove the temporary file."""
        self.print_patcher.stop()
        self.log_path_patcher.stop()
        if os.path.exists(self.temp_log_path):
            os.remove(self.temp_log_path)

    def test_log_single_event(self):
        """Test logging a single event and verify file content."""
        event_type = "TEST_SINGLE"
        details = {"data": 123, "status": "ok"}
        
        success = governance_memory_engine.log_event(event_type, details)
        self.assertTrue(success)
        
        # Verify file content
        with open(self.temp_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        self.assertEqual(len(lines), 1)
        try:
            entry = json.loads(lines[0])
            self.assertEqual(entry['event_type'], event_type)
            self.assertEqual(entry['details'], details)
            self.assertTrue('timestamp' in entry)
            # Validate timestamp format (basic check)
            datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00')) 
        except json.JSONDecodeError:
            self.fail("Logged line is not valid JSON.")
        except Exception as e:
            self.fail(f"Error validating log entry: {e}")

    def test_log_multiple_events_consistency_and_order(self):
        """Test logging multiple events and check format, content, and time order."""
        events_to_log = [
            ("MULTI_TEST_1", {"seq": 1, "val": "a"}),
            ("MULTI_TEST_2", {"seq": 2, "active": True}),
            ("MULTI_TEST_3", {"seq": 3, "items": [1, 2]}),
        ]
        
        timestamps_logged = []
        for etype, dets in events_to_log:
            # Introduce a small delay to ensure timestamps are distinct
            time.sleep(0.01)
            success = governance_memory_engine.log_event(etype, dets)
            self.assertTrue(success)
            timestamps_logged.append(datetime.now(timezone.utc)) # Record approx time
            
        # Verify file content
        with open(self.temp_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        self.assertEqual(len(lines), len(events_to_log))
        
        last_timestamp = None
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
                expected_type, expected_details = events_to_log[i]
                
                self.assertEqual(entry['event_type'], expected_type)
                self.assertEqual(entry['details'], expected_details)
                self.assertTrue('timestamp' in entry)
                
                # Check timestamp format and order
                current_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                self.assertEqual(current_timestamp.tzinfo, timezone.utc) # Verify UTC
                if last_timestamp:
                    self.assertGreaterEqual(current_timestamp, last_timestamp)
                last_timestamp = current_timestamp
                
            except json.JSONDecodeError:
                self.fail(f"Logged line {i+1} is not valid JSON: {line.strip()}")
            except Exception as e:
                self.fail(f"Error validating log entry {i+1}: {e}")
                
    def test_log_event_write_failure(self):
        """Test behavior when writing to the log file fails."""
        # Arrange
        # Patch open specifically for the log_event call to simulate failure
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("Disk quota exceeded")
            
            event_type = "FAIL_WRITE"
            details = {"error_sim": True}
            
            # Act
            success = governance_memory_engine.log_event(event_type, details)
            
            # Assert
            self.assertFalse(success)
            # Verify that the error was printed (since we patched print)
            self.mock_print.assert_called_once()
            call_args = self.mock_print.call_args[0][0]
            self.assertIn("Failed to log event", call_args)
            self.assertIn("Disk quota exceeded", call_args)


if __name__ == '__main__':
    unittest.main() 