import unittest
import os
import json
import shutil
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open, call
import sys
import pytest
import re
import time

# Updated import path
# from social.utils.mailbox_handler import MailboxHandler
from coordination.mailbox_handler import MailboxHandler # Assuming mailbox_handler is under coordination

# Add project root for imports
script_dir = os.path.dirname(__file__) # utils/
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Go up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock the logger used by MailboxHandler to avoid console output during tests
# and allow asserting log calls if needed in the future.
@patch('utils.mailbox_handler.log', MagicMock()) 
class TestMailboxHandler(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory structure for each test."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.inbox_dir = os.path.join(self.test_dir.name, 'inbox')
        self.outbox_dir = os.path.join(self.test_dir.name, 'outbox')
        # MailboxHandler creates its own subdirs, so we just need the base inbox/outbox
        os.makedirs(self.inbox_dir, exist_ok=True)
        os.makedirs(self.outbox_dir, exist_ok=True)
        
        self.handler = MailboxHandler(self.inbox_dir, self.outbox_dir)
        self.processed_dir = self.handler.processed_dir
        self.archive_dir = self.handler.archive_dir

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        self.test_dir.cleanup()

    def test_01_initialization_creates_directories(self):
        """Test if __init__ creates inbox, outbox, processed, and archive directories."""
        self.assertTrue(os.path.isdir(self.inbox_dir))
        self.assertTrue(os.path.isdir(self.outbox_dir))
        self.assertTrue(os.path.isdir(self.processed_dir))
        self.assertTrue(os.path.isdir(self.archive_dir))

    def test_02_send_message_creates_file(self):
        """Test if send_message creates a JSON file in the outbox."""
        message_data = {'command': 'test', 'status': 'ok'}
        success = self.handler.send_message(message_data, filename_prefix="test_msg")
        
        self.assertTrue(success)
        outbox_files = os.listdir(self.outbox_dir)
        self.assertEqual(len(outbox_files), 1)
        self.assertTrue(outbox_files[0].startswith('test_msg_'))
        self.assertTrue(outbox_files[0].endswith('.json'))

        # Verify content
        filepath = os.path.join(self.outbox_dir, outbox_files[0])
        with open(filepath, 'r') as f:
            read_data = json.load(f)
        self.assertEqual(read_data, message_data)
        
    def test_03_check_messages_empty_inbox(self):
        """Test check_for_messages with an empty inbox."""
        messages = self.handler.check_for_messages()
        self.assertEqual(messages, [])
        self.assertEqual(len(os.listdir(self.processed_dir)), 0)
        self.assertEqual(len(os.listdir(self.archive_dir)), 0)

    def test_04_check_messages_valid_json(self):
        """Test check_for_messages with a valid JSON file."""
        message_data = {'command': 'process', 'payload': 123}
        filepath = os.path.join(self.inbox_dir, 'valid_msg.json')
        with open(filepath, 'w') as f:
            json.dump(message_data, f)
            
        messages = self.handler.check_for_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], message_data)
        
        # Verify file moved
        self.assertEqual(len(os.listdir(self.inbox_dir)), 0)
        processed_files = os.listdir(self.processed_dir)
        self.assertEqual(len(processed_files), 1)
        self.assertTrue(processed_files[0].startswith('valid_msg_'))
        self.assertTrue(processed_files[0].endswith('_processed.json'))

    def test_05_check_messages_invalid_json(self):
        """Test check_for_messages with a file containing invalid JSON."""
        filepath = os.path.join(self.inbox_dir, 'invalid_msg.json')
        with open(filepath, 'w') as f:
            f.write("this is not valid json {")
            
        messages = self.handler.check_for_messages()
        self.assertEqual(messages, [])
        
        # Verify file moved
        self.assertEqual(len(os.listdir(self.inbox_dir)), 0)
        self.assertEqual(len(os.listdir(self.processed_dir)), 0)
        archived_files = os.listdir(self.archive_dir)
        self.assertEqual(len(archived_files), 1)
        self.assertTrue(archived_files[0].startswith('invalid_msg_'))
        self.assertTrue(archived_files[0].endswith('_archived_json_decode_error.json'))

    def test_06_check_messages_non_dict_json(self):
        """Test check_for_messages with valid JSON that is not a dictionary."""
        message_data = [1, 2, 3] # Valid JSON, but not a dict
        filepath = os.path.join(self.inbox_dir, 'list_msg.json')
        with open(filepath, 'w') as f:
            json.dump(message_data, f)
            
        messages = self.handler.check_for_messages()
        self.assertEqual(messages, [])
        
        # Verify file moved
        self.assertEqual(len(os.listdir(self.inbox_dir)), 0)
        self.assertEqual(len(os.listdir(self.processed_dir)), 0)
        archived_files = os.listdir(self.archive_dir)
        self.assertEqual(len(archived_files), 1)
        self.assertTrue(archived_files[0].startswith('list_msg_'))
        self.assertTrue(archived_files[0].endswith('_archived_invalid_format.json'))

    def test_07_check_messages_non_json_file(self):
        """Test check_for_messages ignores non-JSON files."""
        filepath = os.path.join(self.inbox_dir, 'ignore_me.txt')
        with open(filepath, 'w') as f:
            f.write("some text data")
            
        messages = self.handler.check_for_messages()
        self.assertEqual(messages, [])
        
        # Verify file NOT moved
        self.assertEqual(len(os.listdir(self.inbox_dir)), 1)
        self.assertEqual(os.listdir(self.inbox_dir)[0], 'ignore_me.txt')
        self.assertEqual(len(os.listdir(self.processed_dir)), 0)
        self.assertEqual(len(os.listdir(self.archive_dir)), 0)

    def test_08_check_messages_mixed_files(self):
        """Test check_for_messages with a mix of file types."""
        # Valid
        valid_data = {'id': 1, 'action': 'run'}
        with open(os.path.join(self.inbox_dir, 'msg_valid.json'), 'w') as f:
            json.dump(valid_data, f)
        # Invalid JSON
        with open(os.path.join(self.inbox_dir, 'msg_invalid.json'), 'w') as f:
            f.write("{bad json")
        # Non-JSON
        with open(os.path.join(self.inbox_dir, 'msg_text.txt'), 'w') as f:
            f.write("plain text")

        messages = self.handler.check_for_messages()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], valid_data)

        # Verify file movements
        inbox_files = os.listdir(self.inbox_dir)
        processed_files = os.listdir(self.processed_dir)
        archived_files = os.listdir(self.archive_dir)

        self.assertEqual(len(inbox_files), 1) # Only the .txt file remains
        self.assertEqual(inbox_files[0], 'msg_text.txt')
        
        self.assertEqual(len(processed_files), 1)
        self.assertTrue(processed_files[0].startswith('msg_valid_'))
        self.assertTrue(processed_files[0].endswith('_processed.json'))
        
        self.assertEqual(len(archived_files), 1)
        self.assertTrue(archived_files[0].startswith('msg_invalid_'))
        self.assertTrue(archived_files[0].endswith('_archived_json_decode_error.json'))

# --- Fixtures ---

@pytest.fixture
def mailbox_dirs(tmp_path):
    """Creates temporary directories for testing."""
    base_dir = tmp_path / "mailbox_test"
    inbox = base_dir / "inbox"
    outbox = base_dir / "outbox"
    # Let the handler create subdirs, just return paths
    # Ensure base dirs exist for setup
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    return {
        "inbox": str(inbox),
        "outbox": str(outbox),
        "processed": str(inbox / "processed"),
        "archive": str(inbox / "archive")
    }

# --- Test Cases ---

def test_mailbox_init_creates_dirs(mailbox_dirs):
    """Test that MailboxHandler creates necessary directories on init."""
    # Use patch to intercept os.makedirs calls
    with patch('os.makedirs') as mock_makedirs:
        handler = MailboxHandler(mailbox_dirs["inbox"], mailbox_dirs["outbox"])
        
        # Check if makedirs was called for all expected paths
        expected_calls = [
            call(mailbox_dirs["inbox"], exist_ok=True),
            call(mailbox_dirs["outbox"], exist_ok=True),
            call(mailbox_dirs["processed"], exist_ok=True),
            call(mailbox_dirs["archive"], exist_ok=True)
        ]
        mock_makedirs.assert_has_calls(expected_calls, any_order=True)
        assert mock_makedirs.call_count == 4

@patch('os.listdir')
def test_check_for_messages_empty_inbox(mock_listdir, mailbox_dirs):
    """Test checking an empty inbox."""
    mock_listdir.return_value = [] # Simulate empty directory
    handler = MailboxHandler(mailbox_dirs["inbox"], mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    assert messages == []
    mock_listdir.assert_called_once_with(mailbox_dirs["inbox"])

@patch('os.listdir')
@patch('os.path.isfile')
@patch('builtins.open', new_callable=mock_open)
@patch('shutil.move')
def test_check_for_messages_valid_message(mock_move, mock_file_open, mock_isfile, mock_listdir, mailbox_dirs):
    """Test reading a single valid JSON message."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "message1.json"
    filepath = os.path.join(inbox_dir, filename)
    valid_data = {"command": "test", "payload": 123}
    
    mock_listdir.return_value = [filename, "ignored.txt"] # Include non-json
    mock_isfile.side_effect = lambda path: path.endswith('.json') or path.endswith('.txt')
    # Configure mock_open to return the valid JSON content for the specific file
    mock_file_open.return_value.read.return_value = json.dumps(valid_data)
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [valid_data]
    mock_listdir.assert_called_once_with(inbox_dir)
    # Check isfile called for both files
    assert mock_isfile.call_count == 2
    # Check open called correctly
    mock_file_open.assert_called_once_with(filepath, 'r', encoding='utf-8')
    # Check file moved to processed
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == filepath
    assert args[1].startswith(mailbox_dirs["processed"])
    assert args[1].endswith("_processed.json")

@patch('os.listdir')
@patch('os.path.isfile')
@patch('builtins.open', new_callable=mock_open, read_data="invalid json data")
@patch('shutil.move')
def test_check_for_messages_invalid_json(mock_move, mock_file_open, mock_isfile, mock_listdir, mailbox_dirs):
    """Test handling a file with invalid JSON content."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "bad_message.json"
    filepath = os.path.join(inbox_dir, filename)
    
    mock_listdir.return_value = [filename]
    mock_isfile.return_value = True
    # mock_open is configured with invalid data
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [] # No valid messages returned
    mock_file_open.assert_called_once_with(filepath, 'r', encoding='utf-8')
    # Check file moved to archive with correct reason
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == filepath
    assert args[1].startswith(mailbox_dirs["archive"])
    assert "json_decode_error" in args[1]
    assert args[1].endswith(".json")

@patch('os.listdir')
@patch('os.path.isfile')
@patch('builtins.open', new_callable=mock_open)
@patch('shutil.move')
def test_check_for_messages_not_dict(mock_move, mock_file_open, mock_isfile, mock_listdir, mailbox_dirs):
    """Test handling a JSON file that doesn't contain a dictionary."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "list_message.json"
    filepath = os.path.join(inbox_dir, filename)
    list_data = [1, 2, 3]
    
    mock_listdir.return_value = [filename]
    mock_isfile.return_value = True
    mock_file_open.return_value.read.return_value = json.dumps(list_data)
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [] # No valid messages returned
    mock_file_open.assert_called_once_with(filepath, 'r', encoding='utf-8')
    # Check file moved to archive with correct reason
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == filepath
    assert args[1].startswith(mailbox_dirs["archive"])
    assert "invalid_format" in args[1]
    assert args[1].endswith(".json")

@patch('os.listdir', side_effect=FileNotFoundError("Inbox gone!"))
def test_check_for_messages_inbox_not_found(mock_listdir, mailbox_dirs):
    """Test handling when the inbox directory is missing."""
    handler = MailboxHandler(mailbox_dirs["inbox"], mailbox_dirs["outbox"])
    # Mock os.makedirs used inside _ensure_dirs_exist
    with patch('os.makedirs') as mock_makedirs:
        messages = handler.check_for_messages()
        assert messages == []
        # Check it attempted to recreate dirs
        mock_makedirs.assert_called()

@patch('builtins.open', new_callable=mock_open)
@patch('os.path.join') # Mock path join to control filename generation
def test_send_message_success(mock_path_join, mock_file_open, mailbox_dirs):
    """Test successfully sending (writing) a message to the outbox."""
    outbox_dir = mailbox_dirs["outbox"]
    # Define the expected filename components
    prefix = "test_response"
    timestamp_regex = r"\d{8}_\d{6}_\d{6}" # YYYYMMDD_HHMMSS_ffffff
    expected_filename = f"{prefix}_{timestamp_regex}.json"
    expected_filepath = os.path.join(outbox_dir, "dummy_filename.json") # Actual filename depends on time
    
    # Mock os.path.join to return a predictable path for assertion
    mock_path_join.return_value = expected_filepath
    
    handler = MailboxHandler(mailbox_dirs["inbox"], outbox_dir)
    message_data = {"status": "OK", "data": [1, 2]}
    
    result = handler.send_message(message_data, filename_prefix=prefix)
    
    assert result is True
    # Check os.path.join was called to create the path
    assert mock_path_join.call_args[0][0] == outbox_dir
    assert re.match(expected_filename, mock_path_join.call_args[0][1])
    
    # Check that open was called to write the file
    mock_file_open.assert_called_once_with(expected_filepath, 'w', encoding='utf-8')
    # Check the content written
    handle = mock_file_open()
    written_content = "".join(c[0][0] for c in handle.write.call_args_list)
    assert json.loads(written_content) == message_data

@patch('builtins.open', side_effect=IOError("Disk quota exceeded"))
def test_send_message_write_fails(mock_file_open, mailbox_dirs):
    """Test failure during writing the message file."""
    handler = MailboxHandler(mailbox_dirs["inbox"], mailbox_dirs["outbox"])
    message_data = {"status": "FAIL"}
    
    result = handler.send_message(message_data)
    
    assert result is False
    mock_file_open.assert_called_once() # Check that the write was attempted

# --- Mocks & Fixtures ---

# Mock log_event globally for all tests in this module
@pytest.fixture(autouse=True)
def mock_logging():
    with patch('social.utils.mailbox_handler.log_event') as mock_log:
        yield mock_log

# --- New Test Cases for Extended Scenarios (Task social-new-110) ---

@patch('os.makedirs', side_effect=OSError("Permission denied"))
def test_init_dir_creation_fails(mock_makedirs, mailbox_dirs):
    """Test __init__ when os.makedirs fails."""
    with pytest.raises(OSError, match="Permission denied"):
        # Expect the OSError to propagate if _ensure_dirs_exist fails critically
        MailboxHandler(mailbox_dirs["inbox"], mailbox_dirs["outbox"])
    # Ensure makedirs was called (at least for the first dir)
    mock_makedirs.assert_called()

@patch('os.listdir')
@patch('os.path.isfile', return_value=True)
@patch('builtins.open', side_effect=IOError("Cannot read file"))
@patch('shutil.move')
def test_check_messages_read_io_error(mock_move, mock_open_error, mock_isfile, mock_listdir, mailbox_dirs, mock_logging):
    """Test check_for_messages when opening a file raises IOError."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "unreadable.json"
    filepath = os.path.join(inbox_dir, filename)
    mock_listdir.return_value = [filename]
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [] # No message should be parsed
    mock_open_error.assert_called_once_with(filepath, 'r', encoding='utf-8')
    # Check file moved to archive with appropriate reason
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == filepath
    assert args[1].startswith(mailbox_dirs["archive"])
    assert "_archived_processing_error.json" in args[1]
    # Verify error logged
    mock_logging.assert_any_call("MAILBOX_ERROR", "MailboxHandler", 
                                  match=re.compile(r".*Error reading or processing message.*Cannot read file.*", re.IGNORECASE))

@patch('os.listdir')
@patch('os.path.isfile', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='{}') # Valid empty JSON
@patch('shutil.move', side_effect=OSError("Destination unwritable"))
def test_move_file_fails(mock_move_error, mock_file_open, mock_isfile, mock_listdir, mailbox_dirs, mock_logging):
    """Test behavior when shutil.move fails during processing."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "move_fail.json"
    filepath = os.path.join(inbox_dir, filename)
    mock_listdir.return_value = [filename]
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    # Expect check_for_messages to still return the message, but log error on move
    messages = handler.check_for_messages()
    
    assert messages == [{}] # Message was read successfully
    mock_file_open.assert_called_once_with(filepath, 'r', encoding='utf-8')
    mock_move_error.assert_called_once() # Move was attempted
    # Verify error logged for the move failure
    mock_logging.assert_any_call("MAILBOX_ERROR", "MailboxHandler", 
                                  match=re.compile(r".*Failed to move file.*Destination unwritable.*", re.IGNORECASE))

@patch('os.listdir')
@patch('os.path.isfile', return_value=True)
@patch('builtins.open', new_callable=mock_open, read_data='""') # Empty file, results in JSONDecodeError
@patch('shutil.move')
def test_check_messages_empty_file(mock_move, mock_file_open, mock_isfile, mock_listdir, mailbox_dirs, mock_logging):
    """Test reading an empty file (which is invalid JSON)."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "empty.json"
    filepath = os.path.join(inbox_dir, filename)
    mock_listdir.return_value = [filename]
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [] # No message should be parsed
    mock_file_open.assert_called_once_with(filepath, 'r', encoding='utf-8')
    # Check file moved to archive due to JSON decode error
    mock_move.assert_called_once()
    args, _ = mock_move.call_args
    assert args[0] == filepath
    assert args[1].startswith(mailbox_dirs["archive"])
    assert "_archived_json_decode_error.json" in args[1]
    mock_logging.assert_any_call("MAILBOX_ERROR", "MailboxHandler", 
                                  match=re.compile(r".*Failed to decode JSON.*Expecting value.*", re.IGNORECASE))


# Note: Testing true concurrency issues (race conditions on file move/delete)
# is very difficult in unit tests and often requires integration tests or 
# more sophisticated mocking/stress testing setups.
# This basic test simulates a file disappearing after listdir.
@patch('os.listdir')
@patch('os.path.isfile', return_value=True)
@patch('builtins.open', side_effect=FileNotFoundError("File disappeared"))
@patch('shutil.move')
def test_check_messages_file_disappears_before_open(mock_move, mock_open_disappears, mock_isfile, mock_listdir, mailbox_dirs, mock_logging):
    """Simulate file disappearing between listdir and open."""
    inbox_dir = mailbox_dirs["inbox"]
    filename = "ghost.json"
    filepath = os.path.join(inbox_dir, filename)
    mock_listdir.return_value = [filename]
    
    handler = MailboxHandler(inbox_dir, mailbox_dirs["outbox"])
    messages = handler.check_for_messages()
    
    assert messages == [] # No message parsed
    mock_open_disappears.assert_called_once_with(filepath, 'r', encoding='utf-8')
    mock_move.assert_not_called() # Move should not be attempted
    # Verify appropriate error logged
    mock_logging.assert_any_call("MAILBOX_ERROR", "MailboxHandler", 
                                  match=re.compile(r".*Error reading or processing message.*File disappeared.*", re.IGNORECASE))

# --- End New Test Cases --- 

# --- Existing Test Cases (unittest style) ---
# Keep existing unittest tests if they cover different aspects or are preferred.
# Ensure the patch decorator for logging is applied if they use logging.
@patch('social.utils.mailbox_handler.log_event', MagicMock())
class TestMailboxHandlerUnittestStyle(unittest.TestCase):
    # ... existing unittest test methods (test_01_... to test_08_...) ...
    pass # Keep the existing unittest cases

# If running directly, allow discovery by both pytest and unittest
if __name__ == '__main__':
    unittest.main() 