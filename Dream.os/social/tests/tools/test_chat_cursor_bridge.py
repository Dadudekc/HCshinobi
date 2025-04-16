import unittest
import os
import sys
import json
from unittest.mock import patch, mock_open, MagicMock

# --- Add project root to sys.path ---
script_dir = os.path.dirname(__file__) # tools/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# Module to test
from tools import chat_cursor_bridge

class TestChatCursorBridge(unittest.TestCase):

    # --- Tests for write_to_cursor_input ---

    @patch('tools.chat_cursor_bridge.os.makedirs') # Mock makedirs
    @patch("builtins.open", new_callable=mock_open) # Mock open
    @patch('tools.chat_cursor_bridge.print') # Mock print to suppress output
    def test_write_success(self, mock_print, mock_file_open, mock_makedirs):
        """Test successful write operation."""
        test_text = "This is a test prompt."
        expected_path = "temp/cursor_input.txt"
        
        success = chat_cursor_bridge.write_to_cursor_input(test_text)
        
        self.assertTrue(success)
        mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
        mock_file_open.assert_called_once_with(expected_path, "w", encoding="utf-8")
        mock_file_open().write.assert_called_once_with(test_text)
        # mock_print.assert_called_with(f"[Bridge 📤] Prompt written to {expected_path}")

    @patch('tools.chat_cursor_bridge.os.makedirs')
    @patch("builtins.open", new_callable=mock_open)
    @patch('tools.chat_cursor_bridge.print')
    def test_write_io_error(self, mock_print, mock_file_open, mock_makedirs):
        """Test write operation failure due to IO error."""
        test_text = "Another prompt."
        expected_path = "temp/cursor_input.txt"
        mock_file_open.side_effect = IOError("Permission denied") # Simulate error
        
        success = chat_cursor_bridge.write_to_cursor_input(test_text)
        
        self.assertFalse(success)
        mock_makedirs.assert_called_once_with(os.path.dirname(expected_path), exist_ok=True)
        mock_file_open.assert_called_once_with(expected_path, "w", encoding="utf-8")
        mock_print.assert_called_with(f"[Bridge Error ❌] Failed to write to {expected_path}: Permission denied")

    # --- Tests for read_from_cursor_output ---

    @patch('tools.chat_cursor_bridge.os.path.exists')
    @patch('tools.chat_cursor_bridge.print')
    def test_read_file_not_found(self, mock_print, mock_exists):
        """Test reading when the output file does not exist."""
        expected_path = "temp/cursor_output.json"
        mock_exists.return_value = False
        
        result = chat_cursor_bridge.read_from_cursor_output()
        
        self.assertIsNone(result)
        mock_exists.assert_called_once_with(expected_path)
        # mock_print was not called in this path in the original code

    @patch('tools.chat_cursor_bridge.os.path.exists')
    @patch("builtins.open", new_callable=mock_open, read_data='{"key": "value", "status": 123}')
    @patch('tools.chat_cursor_bridge.print')
    def test_read_success_valid_json(self, mock_print, mock_file_open, mock_exists):
        """Test successful read operation with valid JSON."""
        expected_path = "temp/cursor_output.json"
        expected_data = {"key": "value", "status": 123}
        mock_exists.return_value = True
        
        result = chat_cursor_bridge.read_from_cursor_output()
        
        self.assertEqual(result, expected_data)
        mock_exists.assert_called_once_with(expected_path)
        mock_file_open.assert_called_once_with(expected_path, "r", encoding="utf-8")
        # mock_print.assert_called_with(f"[Bridge 📥] Parsed JSON from {expected_path}")

    @patch('tools.chat_cursor_bridge.os.path.exists')
    @patch("builtins.open", new_callable=mock_open, read_data='invalid json string {')
    @patch('tools.chat_cursor_bridge.print')
    def test_read_invalid_json(self, mock_print, mock_file_open, mock_exists):
        """Test reading a file with invalid JSON content."""
        expected_path = "temp/cursor_output.json"
        mock_exists.return_value = True
        
        result = chat_cursor_bridge.read_from_cursor_output()
        
        self.assertIsNone(result)
        mock_exists.assert_called_once_with(expected_path)
        mock_file_open.assert_called_once_with(expected_path, "r", encoding="utf-8")
        # Check that the specific JSON decode error message was printed
        mock_print.assert_any_call(unittest.mock.ANY) # Print is called for the error
        # Example of more specific check if needed:
        # self.assertTrue(any("Failed to parse JSON" in call.args[0] for call in mock_print.call_args_list))

    @patch('tools.chat_cursor_bridge.os.path.exists')
    @patch("builtins.open", new_callable=mock_open)
    @patch('tools.chat_cursor_bridge.print')
    def test_read_io_error(self, mock_print, mock_file_open, mock_exists):
        """Test reading failure due to IO error."""
        expected_path = "temp/cursor_output.json"
        mock_exists.return_value = True
        mock_file_open.side_effect = IOError("Cannot read file") # Simulate error
        
        result = chat_cursor_bridge.read_from_cursor_output()
        
        self.assertIsNone(result)
        mock_exists.assert_called_once_with(expected_path)
        mock_file_open.assert_called_once_with(expected_path, "r", encoding="utf-8")
        mock_print.assert_called_with(f"[Bridge Error ❌] Error reading {expected_path}: Cannot read file")

    # --- Test Write then Read Simulation ---
    # This is more complex as mocks need careful management between calls
    # For now, the individual tests cover the core logic.

if __name__ == '__main__':
    unittest.main() 