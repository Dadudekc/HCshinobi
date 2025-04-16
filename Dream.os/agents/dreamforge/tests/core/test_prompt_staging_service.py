"""Tests for prompt staging service."""
import pytest
import os
import json
import asyncio
from unittest.mock import patch, mock_open
from dreamforge.core.prompt_staging_service import (
    render_prompt,
    stage_prompt_for_cursor,
    write_to_cursor_input,
    read_from_cursor_output,
    stage_and_execute_prompt
)
from dreamforge.core.memory.governance_memory_engine import log_event

@pytest.fixture
def mock_template_engine():
    with patch('dreamforge.core.prompt_staging_service.TemplateEngine') as mock:
        engine_instance = mock.return_value
        engine_instance.render.return_value = "Rendered template"
        yield mock

@pytest.fixture
def mock_config():
    with patch('dreamforge.core.prompt_staging_service.config') as mock:
        mock.CURSOR_INPUT_FILE = "/tmp/cursor_input.json"
        mock.CURSOR_OUTPUT_FILE = "/tmp/cursor_output.json"
        yield mock

def test_render_prompt_success(mock_template_engine):
    """Test successful prompt rendering."""
    template_name = "test_template.j2"
    context = {"key": "value"}
    
    result = render_prompt(template_name, context)
    log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_render_prompt_success"})
    
    assert result == "Rendered template"
    mock_template_engine.return_value.render.assert_called_once_with(template_name, context)

def test_render_prompt_failure(mock_template_engine):
    """Test handling of prompt rendering failure."""
    mock_template_engine.return_value.render.side_effect = Exception("Render error")
    
    result = render_prompt("template.j2", {})
    log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_render_prompt_failure"})
    
    assert result == ""

def test_stage_prompt_for_cursor_success(mock_template_engine, mock_config):
    """Test successful prompt staging."""
    with patch('dreamforge.core.prompt_staging_service.write_to_cursor_input') as mock_write:
        mock_write.return_value = True
        
        result = stage_prompt_for_cursor("template.j2", {"key": "value"})
        log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_stage_prompt_for_cursor_success"})
        
        assert result is True
        mock_write.assert_called_once_with("Rendered template")

def test_stage_prompt_for_cursor_render_failure(mock_template_engine):
    """Test prompt staging with render failure."""
    mock_template_engine.return_value.render.return_value = ""
    
    result = stage_prompt_for_cursor("template.j2", {})
    log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_stage_prompt_for_cursor_render_failure"})
    
    assert result is False

def test_write_to_cursor_input_success(mock_config):
    """Test successful write to cursor input file."""
    content = "Test content"
    mock_file = mock_open()
    
    with patch('builtins.open', mock_file):
        result = write_to_cursor_input(content)
        log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_write_to_cursor_input_success"})
        
        assert result is True
        mock_file.assert_called_once_with(mock_config.CURSOR_INPUT_FILE, 'w')
        mock_file().write.assert_called_once_with(content)

def test_write_to_cursor_input_failure(mock_config):
    """Test handling of write failure."""
    with patch('builtins.open', side_effect=Exception("Write error")):
        result = write_to_cursor_input("content")
        log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_write_to_cursor_input_failure"})
        
        assert result is False

def test_read_from_cursor_output_success(mock_config):
    """Test successful read from cursor output file."""
    expected_data = {"key": "value"}
    mock_file = mock_open(read_data=json.dumps(expected_data))
    
    with patch('builtins.open', mock_file):
        with patch('os.path.exists', return_value=True):
            result = read_from_cursor_output()
            log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_read_from_cursor_output_success"})
            
            assert result == expected_data
            mock_file.assert_called_once_with(mock_config.CURSOR_OUTPUT_FILE, 'r')

def test_read_from_cursor_output_file_not_exists(mock_config):
    """Test reading when output file doesn't exist."""
    with patch('os.path.exists', return_value=False):
        result = read_from_cursor_output()
        log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_read_from_cursor_output_file_not_exists"})
        
        assert result is None

def test_read_from_cursor_output_empty_file(mock_config):
    """Test reading from empty output file."""
    mock_file = mock_open(read_data="")
    
    with patch('builtins.open', mock_file):
        with patch('os.path.exists', return_value=True):
            result = read_from_cursor_output()
            log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_read_from_cursor_output_empty_file"})
            
            assert result is None

def test_read_from_cursor_output_invalid_json(mock_config):
    """Test reading invalid JSON from output file."""
    mock_file = mock_open(read_data="invalid json")
    
    with patch('builtins.open', mock_file):
        with patch('os.path.exists', return_value=True):
            result = read_from_cursor_output()
            log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_read_from_cursor_output_invalid_json"})
            
            assert result is None

@pytest.mark.asyncio
async def test_stage_and_execute_prompt_success(mock_template_engine, mock_config):
    """Test successful prompt staging and execution."""
    expected_response = {"status": "success"}
    
    with patch('dreamforge.core.prompt_staging_service.stage_prompt_for_cursor', return_value=True):
        with patch('dreamforge.core.prompt_staging_service.read_from_cursor_output', return_value=expected_response):
            result = await stage_and_execute_prompt("template.j2", {"key": "value"}, timeout_seconds=1)
            log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_stage_and_execute_prompt_success"})
            
            assert result == expected_response

@pytest.mark.asyncio
async def test_stage_and_execute_prompt_staging_failure(mock_template_engine, mock_config):
    """Test handling of staging failure."""
    with patch('dreamforge.core.prompt_staging_service.stage_prompt_for_cursor', return_value=False):
        result = await stage_and_execute_prompt("template.j2", {}, timeout_seconds=1)
        log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_stage_and_execute_prompt_staging_failure"})
        
        assert result is None

@pytest.mark.asyncio
async def test_stage_and_execute_prompt_timeout(mock_template_engine, mock_config):
    """Test handling of execution timeout."""
    with patch('dreamforge.core.prompt_staging_service.stage_prompt_for_cursor', return_value=True):
        with patch('dreamforge.core.prompt_staging_service.read_from_cursor_output', return_value=None):
            result = await stage_and_execute_prompt("template.j2", {}, timeout_seconds=1)
            log_event("TEST_ADDED", "TestPromptStaging", {"test": "test_stage_and_execute_prompt_timeout"})
            
            assert result is None 