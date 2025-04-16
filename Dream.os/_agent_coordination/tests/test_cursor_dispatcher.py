import json
import pytest
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from tools.cursor_dispatcher import generate_cursor_prompt_from_context, dispatch_to_cursor

def log_event(event_type, agent_id, data):
    """Mock log_event function for test coverage reporting."""
    print(f"[{event_type}] Agent: {agent_id}, Data: {data}")

@pytest.fixture
def sample_context():
    """Fixture providing a sample context dictionary."""
    return {
        "stall_category": "CodeAnalysis",
        "suggested_action_keyword": "analyze_dependencies",
        "project_root": "/path/to/project",
        "relevant_files": ["file1.py", "file2.py"],
        "conversation_snippet": "User: Can you check the dependencies?\nAssistant: I'll analyze them."
    }

def test_generate_cursor_prompt_basic(sample_context):
    """Test basic prompt generation with all fields present."""
    prompt = generate_cursor_prompt_from_context(sample_context)
    
    # Check all components are present
    assert "Context Analysis:" in prompt
    assert "Stall Category: CodeAnalysis" in prompt
    assert "Suggested Action Keyword: analyze_dependencies" in prompt
    assert "Project Root: /path/to/project" in prompt
    assert "Relevant Files: file1.py, file2.py" in prompt
    assert "User: Can you check the dependencies?" in prompt
    assert "Assistant: I'll analyze them." in prompt
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_generate_cursor_prompt_basic"})

def test_generate_cursor_prompt_missing_fields():
    """Test prompt generation with missing fields."""
    minimal_context = {
        "stall_category": "Unknown",
        "conversation_snippet": "Test conversation"
    }
    
    prompt = generate_cursor_prompt_from_context(minimal_context)
    
    assert "Stall Category: Unknown" in prompt
    assert "Suggested Action Keyword: N/A" in prompt
    assert "Project Root: N/A" in prompt
    assert "Relevant Files:" not in prompt
    assert "Test conversation" in prompt
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_generate_cursor_prompt_missing_fields"})

def test_generate_cursor_prompt_empty_context():
    """Test prompt generation with empty context."""
    prompt = generate_cursor_prompt_from_context({})
    
    assert "Stall Category: Unknown" in prompt
    assert "Suggested Action Keyword: N/A" in prompt
    assert "Project Root: N/A" in prompt
    assert "N/A" in prompt
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_generate_cursor_prompt_empty_context"})

@pytest.fixture
def context_file(tmp_path, sample_context):
    """Fixture creating a temporary context file."""
    file_path = tmp_path / "test_context.json"
    file_path.write_text(json.dumps(sample_context))
    return file_path

def test_dispatch_to_cursor_file_not_found():
    """Test handling of non-existent context file."""
    with patch('builtins.print') as mock_print:
        dispatch_to_cursor(Path("nonexistent.json"))
        mock_print.assert_called_with("Error: Context JSON file not found: nonexistent.json")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_file_not_found"})

def test_dispatch_to_cursor_invalid_json(tmp_path):
    """Test handling of invalid JSON file."""
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("invalid json content")
    
    with patch('builtins.print') as mock_print:
        dispatch_to_cursor(invalid_json)
        mock_print.assert_any_call("Error reading context JSON file: Expecting value: line 1 column 1 (char 0)")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_invalid_json"})

@patch('subprocess.Popen')
@patch('time.sleep')
@patch('pyperclip.copy')
@patch('pyautogui.hotkey')
def test_dispatch_to_cursor_success(mock_hotkey, mock_copy, mock_sleep, mock_popen, context_file):
    """Test successful cursor dispatch process."""
    with patch('builtins.print') as mock_print:
        dispatch_to_cursor(context_file)
        
        # Verify subprocess call
        mock_popen.assert_called_once()
        
        # Verify clipboard operations
        mock_copy.assert_called_once()
        assert isinstance(mock_copy.call_args[0][0], str)
        assert "Context Analysis:" in mock_copy.call_args[0][0]
        
        # Verify GUI automation
        mock_hotkey.assert_called_once_with('ctrl', 'v')
        
        # Verify user prompts
        mock_print.assert_any_call("Cursor dispatch process initiated.")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_success"})

@patch('subprocess.Popen')
@patch('time.sleep')
@patch('pyperclip.copy')
def test_dispatch_to_cursor_cursor_not_found(mock_copy, mock_sleep, mock_popen, context_file):
    """Test handling of Cursor executable not found."""
    mock_popen.side_effect = FileNotFoundError()
    
    with patch('builtins.print') as mock_print:
        dispatch_to_cursor(context_file)
        mock_print.assert_any_call("Please update CURSOR_EXE_PATH in cursor_dispatcher.py")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_cursor_not_found"})

@patch('subprocess.Popen')
@patch('time.sleep')
def test_dispatch_to_cursor_pyperclip_import_error(mock_sleep, mock_popen, context_file):
    """Test handling of missing pyperclip module."""
    with patch('builtins.print') as mock_print, \
         patch('builtins.input') as mock_input, \
         patch.dict('sys.modules', {'pyperclip': None}):
        
        dispatch_to_cursor(context_file)
        mock_print.assert_any_call("Warning: pyperclip not found. Cannot copy prompt automatically.")
        mock_input.assert_called_once()
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_pyperclip_import_error"})

@patch('subprocess.Popen')
@patch('time.sleep')
@patch('pyperclip.copy')
@patch('pyautogui.hotkey')
def test_dispatch_to_cursor_gui_automation_error(mock_hotkey, mock_copy, mock_sleep, mock_popen, context_file):
    """Test handling of GUI automation errors."""
    mock_hotkey.side_effect = Exception("GUI automation error")
    
    with patch('builtins.print') as mock_print:
        dispatch_to_cursor(context_file)
        mock_print.assert_any_call("Error simulating paste: GUI automation error")
    log_event("TEST_PASSED", "CoverageAgent", {"test": "test_dispatch_to_cursor_gui_automation_error"})

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 