import pytest
import os
import sys
from unittest.mock import patch, mock_open, MagicMock

from jinja2 import TemplateNotFound, UndefinedError, Environment

# --- Path Setup --- 
# Add project root to sys.path to allow importing dreamforge modules
script_dir = os.path.dirname(__file__) # dreamforge/tests/core
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..')) # Up three levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# -----------------

# Module to test
from dreamforge.core import template_engine # Assuming template_engine.py is in dreamforge/core
from dreamforge.core.governance_memory_engine import log_event # Needed for log checks

# --- Mock Functions & Data --- 

MOCKED_LOGS = []

def mock_log_event(event_type, agent_source, details):
    print(f"Mock Log Event: {event_type} | {agent_source} | {details}") # For test visibility
    MOCKED_LOGS.append({
        "event_type": event_type,
        "agent_source": agent_source,
        "details": details
    })
    return True # Assume logging success

# Mock templates
MOCK_TEMPLATES = {
    "valid/simple.j2": "Hello, {{ name }}!",
    "valid/complex.j2": "Data: {{ data.key }} Number: {{ number }}",
    "error/undefined.j2": "Value: {{ undefined_variable }}",
}

# --- Test Fixture --- 

@pytest.fixture(autouse=True)
def setup_mocks(monkeypatch):
    """Apply mocks for log_event before each test."""
    MOCKED_LOGS.clear() # Clear logs before each test
    # Mock log_event within the template_engine module specifically
    monkeypatch.setattr(template_engine, "log_event", mock_log_event)
    yield
    # Teardown (if any) happens after yield

# --- Test Cases --- 

@patch("builtins.open", new_callable=mock_open, read_data="Default content - should be overridden")
@patch("os.path.exists")
def test_render_template_success(mock_exists, mock_open_file):
    """Test successful rendering of a template with valid context."""
    mock_exists.return_value = True
    template_name = "valid/simple.j2"
    context = {"name": "Dreamer"}
    expected_output = "Hello, Dreamer!"
    
    # Configure mock_open to return specific template content based on path
    # Note: This basic mock_open doesn't handle multiple file opens well without more logic
    # We'll assume it opens the correct template path implicitly
    mock_open_file.return_value.read.return_value = MOCK_TEMPLATES[template_name]
    
    result = template_engine.render_template(template_name, context)
    
    assert result == expected_output
    # Verify os.path.exists was called (part of Jinja's FileSystemLoader usually)
    # mock_exists.assert_called_once() # Difficult to assert path precisely without deeper mocking
    # Check logs (should only be DEBUG if logging level allows)
    assert any(log['event_type'] == "TEMPLATE_RENDER_SUCCESS" for log in MOCKED_LOGS)
    assert any(log['details']['template_name'] == template_name for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_SUCCESS")

@patch("os.path.exists")
def test_render_template_not_found(mock_exists):
    """Test handling when the template file does not exist."""
    mock_exists.return_value = False # Simulate file not existing
    template_name = "invalid/nonexistent.j2"
    context = {"name": "Test"}
    
    # Jinja2's FileSystemLoader raises TemplateNotFound *before* trying to open
    # So we don't need to mock open here, just the check
    result = template_engine.render_template(template_name, context)
    
    assert result is None
    mock_exists.assert_called() # Check that it at least tried to find the template
    assert any(log['event_type'] == "TEMPLATE_RENDER_ERROR" for log in MOCKED_LOGS)
    assert any("TemplateNotFound" in log['details']['error'] for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")
    assert any(log['details']['template_name'] == template_name for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")

@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
def test_render_template_render_error(mock_exists, mock_open_file):
    """Test handling when rendering fails due to context issues (e.g., UndefinedError)."""
    mock_exists.return_value = True
    template_name = "error/undefined.j2"
    context = {"some_other_key": "value"} # Missing 'undefined_variable'
    
    mock_open_file.return_value.read.return_value = MOCK_TEMPLATES[template_name]
    
    result = template_engine.render_template(template_name, context)
    
    assert result is None
    assert any(log['event_type'] == "TEMPLATE_RENDER_ERROR" for log in MOCKED_LOGS)
    assert any("UndefinedError" in log['details']['error'] for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")
    assert any(log['details']['template_name'] == template_name for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")

@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
def test_render_template_complex_context(mock_exists, mock_open_file):
    """Test successful rendering with a more complex context object."""
    mock_exists.return_value = True
    template_name = "valid/complex.j2"
    context = {"data": {"key": "value123"}, "number": 42}
    expected_output = "Data: value123 Number: 42"
    
    mock_open_file.return_value.read.return_value = MOCK_TEMPLATES[template_name]
    
    result = template_engine.render_template(template_name, context)
    
    assert result == expected_output
    assert any(log['event_type'] == "TEMPLATE_RENDER_SUCCESS" for log in MOCKED_LOGS)

@patch("builtins.open", side_effect=IOError("Disk read error simulation"))
@patch("os.path.exists")
def test_render_template_io_error(mock_exists, mock_open_file):
    """Test handling when opening the template file raises an IOError."""
    mock_exists.return_value = True # Simulate file exists
    template_name = "valid/simple.j2"
    context = {"name": "IOErrorTest"}
    
    # The side_effect on mock_open will raise the IOError when called
    result = template_engine.render_template(template_name, context)
    
    assert result is None
    assert any(log['event_type'] == "TEMPLATE_RENDER_ERROR" for log in MOCKED_LOGS)
    # Check if the specific IOError is mentioned, or a general file access error
    assert any("Error accessing template file" in log['details']['error'] or "Disk read error simulation" in log['details']['error'] for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")
    assert any(log['details']['template_name'] == template_name for log in MOCKED_LOGS if log['event_type'] == "TEMPLATE_RENDER_ERROR")

# --- Additional Test Cases ---

def test_gme_ready_fallback():
    """Test the fallback logging when governance_memory_engine is not available."""
    # Save original _gme_ready and log_event
    original_gme_ready = template_engine._gme_ready
    original_log_event = template_engine.log_event
    
    try:
        # Simulate GME import failure
        template_engine._gme_ready = False
        template_engine.log_event = template_engine.__dict__['log_event']
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            template_engine.log_event("TEST_EVENT", "TEST_SOURCE", {"test": "data"})
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Dummy Logger" in call_args
            assert "TEST_EVENT" in call_args
    finally:
        # Restore original values
        template_engine._gme_ready = original_gme_ready
        template_engine.log_event = original_log_event

def test_environment_configuration():
    """Test that Jinja2 environment is configured correctly."""
    env = template_engine.env
    assert isinstance(env, Environment)
    assert env.trim_blocks is True
    assert env.lstrip_blocks is True
    assert 'html' in env.autoescape
    assert 'xml' in env.autoescape

@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
def test_render_empty_context(mock_exists, mock_open_file):
    """Test rendering with an empty context dictionary."""
    mock_exists.return_value = True
    template_name = "valid/simple.j2"
    context = {}
    
    mock_open_file.return_value.read.return_value = "Static content with no variables"
    
    result = template_engine.render_template(template_name, context)
    
    assert result == "Static content with no variables"
    assert any(log['event_type'] == "TEMPLATE_RENDER_SUCCESS" for log in MOCKED_LOGS)

@patch('json.load')
@patch("builtins.open", new_callable=mock_open)
@patch("os.path.exists")
def test_main_execution_with_sample_data(mock_exists, mock_open_file, mock_json_load):
    """Test the main() function execution path with sample data."""
    mock_exists.return_value = True
    mock_json_load.return_value = {"test_key": "test_value"}
    
    # Mock template rendering
    with patch.object(template_engine, 'render') as mock_render:
        mock_render.return_value = "Rendered test output"
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            template_engine.main()
            
            # Verify main() behavior
            mock_exists.assert_called_once()
            mock_json_load.assert_called_once()
            mock_render.assert_called_once()
            assert mock_print.call_count >= 2  # Should print template name and output

@patch("os.path.exists")
def test_main_execution_fallback_context(mock_exists):
    """Test main() function with fallback to default context."""
    mock_exists.return_value = False
    
    # Mock template rendering
    with patch.object(template_engine, 'render') as mock_render:
        mock_render.return_value = "Rendered with default context"
        
        # Capture print output
        with patch('builtins.print') as mock_print:
            template_engine.main()
            
            # Verify fallback behavior
            mock_render.assert_called_once_with(
                "test_template.j2",
                {"example_key": "example_value"}
            )
            assert mock_print.call_count >= 2

@patch("os.path.exists")
def test_main_execution_json_error(mock_exists):
    """Test main() function when JSON loading fails."""
    mock_exists.return_value = True
    
    # Mock open to raise JSONDecodeError
    mock_open_cm = mock_open(read_data="invalid json")
    with patch("builtins.open", mock_open_cm):
        # Mock template rendering
        with patch.object(template_engine, 'render') as mock_render:
            mock_render.return_value = "Rendered with default context"
            
            # Capture print output
            with patch('builtins.print') as mock_print:
                template_engine.main()
                
                # Verify error handling
                mock_render.assert_called_once_with(
                    "test_template.j2",
                    {"example_key": "example_value"}
                )
                assert mock_print.call_count >= 2 