# Tests for core services (e.g., prompt staging, template engine)

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import json
import tempfile

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import services
from core.template_engine import render_template, TemplateEngine
from core.prompt_staging_service import stage_and_execute_prompt, PromptStagingService

# --- Template Engine Tests ---

# Fixture to manage temporary template files
@pytest.fixture
def temp_template_dir(tmp_path):
    """Create a temporary directory for templates."""
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    return template_dir

@pytest.fixture
def setup_template_engine(temp_template_dir):
    """Initialize TemplateEngine pointing to the temp directory."""
    # Temporarily patch TEMPLATE_DIR used in template_engine module
    with patch('core.template_engine.TEMPLATE_DIR', str(temp_template_dir)):
        engine = TemplateEngine() # Re-initialize with patched path
        yield engine # Provide the engine instance to the test

def test_template_rendering_simple(setup_template_engine, temp_template_dir):
    """Test basic template rendering with variables."""
    engine = setup_template_engine
    template_path = temp_template_dir / "simple.j2"
    template_path.write_text("Hello, {{ name }}!")

    rendered = engine.render("simple.j2", {"name": "World"})
    assert rendered == "Hello, World!"

def test_template_rendering_missing_variable(setup_template_engine, temp_template_dir):
    """Test rendering when a variable is missing (should default to empty string)."""
    engine = setup_template_engine
    template_path = temp_template_dir / "missing.j2"
    template_path.write_text("Value: {{ missing_var }}")

    rendered = engine.render("missing.j2", {})
    assert rendered == "Value: " # Jinja's default behavior for undefined

def test_template_rendering_with_filter(setup_template_engine, temp_template_dir):
    """Test rendering using the custom 'tojson' filter."""
    engine = setup_template_engine
    template_path = temp_template_dir / "filter.j2"
    template_path.write_text("{{ data | tojson }}")

    data_dict = {"key": "value", "number": 123}
    expected_json = json.dumps(data_dict)
    rendered = engine.render("filter.j2", {"data": data_dict})
    assert rendered == expected_json

def test_template_rendering_file_not_found(setup_template_engine):
    """Test rendering a non-existent template file."""
    engine = setup_template_engine
    rendered = engine.render("non_existent.j2", {})
    assert rendered is None # Expect None on failure

def test_render_template_module_function(setup_template_engine, temp_template_dir):
    """Test the standalone render_template function."""
    template_path = temp_template_dir / "module_func.j2"
    template_path.write_text("Standalone: {{ value }}")

    # Need to ensure the module-level function uses the patched path
    # The fixture `setup_template_engine` already patches TEMPLATE_DIR
    rendered = render_template("module_func.j2", {"value": 123})
    assert rendered == "Standalone: 123"

# --- Prompt Staging Service Tests ---

# Mock the ChatCursorBridge interaction
@patch('core.prompt_staging_service.write_to_input')
@patch('core.prompt_staging_service.read_from_output')
@patch('core.prompt_staging_service.log_event') # Also mock logging
def test_prompt_staging_success(mock_log_event, mock_read_output, mock_write_input):
    """Test successful staging and execution flow."""
    # Setup Mocks
    mock_write_input.return_value = True
    mock_read_output.return_value = {"type": "response", "data": "Mock LLM Response"}

    prompt_text = "This is the prompt text."
    agent_id = "TestAgent"
    purpose = "test_purpose"

    result = stage_and_execute_prompt(prompt_text, agent_id, purpose)

    assert result == "Mock LLM Response"
    # Verify write_to_input was called correctly
    mock_write_input.assert_called_once()
    args, kwargs = mock_write_input.call_args
    # args[0] is the filename, args[1] is the data dict
    assert args[0].endswith("_prompt_input.json")
    assert args[1]["prompt"] == prompt_text
    assert args[1]["agent_id"] == agent_id
    assert args[1]["purpose"] == purpose
    assert "supervisor_state" in args[1] # Check state injection (even if empty)

    # Verify read_from_output was called
    mock_read_output.assert_called_once()

    # Verify logging calls (basic checks)
    mock_log_event.assert_any_call("PROMPT_STAGING_START", "PromptStagingService", pytest.approx({"agent_id": agent_id, "purpose": purpose}))
    mock_log_event.assert_any_call("PROMPT_SENT_TO_BRIDGE", "PromptStagingService", pytest.approx({"agent_id": agent_id, "purpose": purpose}))
    mock_log_event.assert_any_call("PROMPT_RESPONSE_RECEIVED", "PromptStagingService", pytest.approx({"agent_id": agent_id, "purpose": purpose}))

@patch('core.prompt_staging_service.write_to_input')
@patch('core.prompt_staging_service.read_from_output')
@patch('core.prompt_staging_service.log_event')
def test_prompt_staging_write_fails(mock_log_event, mock_read_output, mock_write_input):
    """Test failure during writing to the bridge input file."""
    mock_write_input.return_value = False # Simulate write failure

    result = stage_and_execute_prompt("prompt", "AgentFail", "purposeFail")

    assert result is None
    mock_write_input.assert_called_once()
    mock_read_output.assert_not_called()
    mock_log_event.assert_any_call("PROMPT_STAGING_ERROR", "PromptStagingService", pytest.approx({"error": "Failed to write prompt to bridge input file"}))

@patch('core.prompt_staging_service.write_to_input')
@patch('core.prompt_staging_service.read_from_output')
@patch('core.prompt_staging_service.log_event')
def test_prompt_staging_read_timeout(mock_log_event, mock_read_output, mock_write_input):
    """Test failure due to timeout while reading from bridge output."""
    mock_write_input.return_value = True
    mock_read_output.return_value = None # Simulate read timeout/failure

    result = stage_and_execute_prompt("prompt", "AgentTimeout", "purposeTimeout")

    assert result is None
    mock_write_input.assert_called_once()
    mock_read_output.assert_called_once()
    mock_log_event.assert_any_call("PROMPT_STAGING_ERROR", "PromptStagingService", pytest.approx({"error": "Failed to read prompt response from bridge output file (timeout or error)"}))

@patch('core.prompt_staging_service.write_to_input')
@patch('core.prompt_staging_service.read_from_output')
@patch('core.prompt_staging_service.log_event')
def test_prompt_staging_read_malformed(mock_log_event, mock_read_output, mock_write_input):
    """Test receiving malformed (non-dictionary) data from bridge."""
    mock_write_input.return_value = True
    mock_read_output.return_value = "This is not a dictionary" # Simulate malformed read

    result = stage_and_execute_prompt("prompt", "AgentMalformed", "purposeMalformed")

    assert result is None
    mock_write_input.assert_called_once()
    mock_read_output.assert_called_once()
    mock_log_event.assert_any_call("PROMPT_STAGING_ERROR", "PromptStagingService", pytest.approx({"error": "Malformed response received from bridge"}))

@patch('core.prompt_staging_service.write_to_input')
@patch('core.prompt_staging_service.read_from_output')
@patch('core.prompt_staging_service.log_event')
@patch('core.prompt_staging_service.load_state') # Mock supervisor state loading
def test_prompt_staging_with_supervisor_state(mock_load_state, mock_log_event, mock_read_output, mock_write_input):
    """Test that supervisor state is loaded and injected."""
    mock_write_input.return_value = True
    mock_read_output.return_value = {"type": "response", "data": "Response with State"}
    mock_supervisor_state = {"current_focus": "testing", "mode": "autonomous"}
    mock_load_state.return_value = mock_supervisor_state

    result = stage_and_execute_prompt("prompt", "AgentWithState", "purposeState")

    assert result == "Response with State"
    mock_load_state.assert_called_once()
    mock_write_input.assert_called_once()
    args, kwargs = mock_write_input.call_args
    assert args[1]["supervisor_state"] == mock_supervisor_state # Verify injected state 