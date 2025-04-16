"""Tests for the logging utilities module."""

import json
import logging
import os
import pytest
from pathlib import Path
from typing import Generator

from core.utils.logging import LogManager, LogFormatter, get_logger

@pytest.fixture
def log_dir(tmp_path) -> Generator[Path, None, None]:
    """Fixture that provides a temporary directory for log files."""
    log_path = tmp_path / "logs"
    log_path.mkdir()
    yield log_path

@pytest.fixture
def log_manager(log_dir: Path) -> LogManager:
    """Fixture that provides a configured LogManager instance."""
    manager = LogManager()
    manager.configure(log_dir)
    return manager

def test_log_formatter():
    """Test that LogFormatter correctly formats log records."""
    formatter = LogFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Add component info
    setattr(record, 'component', 'test_component')
    
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data['level'] == 'INFO'
    assert data['message'] == 'Test message'
    assert data['component'] == 'test_component'
    assert data['logger'] == 'test_logger'
    assert 'timestamp' in data

def test_log_formatter_with_exception():
    """Test that LogFormatter correctly handles exceptions."""
    formatter = LogFormatter()
    try:
        raise ValueError("Test error")
    except ValueError:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=True
        )
        
    formatted = formatter.format(record)
    data = json.loads(formatted)
    
    assert data['level'] == 'ERROR'
    assert 'exception' in data
    assert data['exception']['type'] == 'ValueError'
    assert data['exception']['message'] == 'Test error'

def test_log_manager_configuration(log_dir: Path):
    """Test that LogManager configures logging correctly."""
    manager = LogManager()
    manager.configure(log_dir)
    
    # Verify log directory was created
    assert log_dir.exists()
    
    # Verify handlers were created
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) == 2
    
    # Verify log levels
    console_handler = root_logger.handlers[0]
    file_handler = root_logger.handlers[1]
    
    assert console_handler.level == logging.INFO
    assert file_handler.level == logging.DEBUG

def test_get_logger_with_component():
    """Test that get_logger creates loggers with component context."""
    logger = get_logger("test_module", "test_component")
    assert isinstance(logger, logging.LoggerAdapter)
    assert logger.extra['component'] == 'test_component'

def test_get_logger_without_component():
    """Test that get_logger creates basic loggers without component."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)

def test_log_manager_singleton():
    """Test that LogManager maintains singleton state."""
    manager1 = LogManager()
    manager2 = LogManager()
    assert manager1 is manager2

def test_logging_output(log_dir: Path, caplog):
    """Test that logging actually produces expected output."""
    manager = LogManager()
    manager.configure(log_dir)
    
    logger = get_logger("test_module", "test_component")
    test_message = "Test log message"
    logger.info(test_message)
    
    # Check console output
    assert test_message in caplog.text
    
    # Check file output
    log_file = log_dir / 'agent.log'
    assert log_file.exists()
    
    with open(log_file) as f:
        log_entry = json.loads(f.readline())
        assert log_entry['message'] == test_message
        assert log_entry['component'] == 'test_component'
        assert log_entry['level'] == 'INFO'

def test_set_level(log_manager: LogManager):
    """Test that set_level changes log levels correctly."""
    # Test with string level
    log_manager.set_level('DEBUG')
    for handler in logging.getLogger().handlers:
        assert handler.level == logging.DEBUG
        
    # Test with integer level
    log_manager.set_level(logging.WARNING)
    for handler in logging.getLogger().handlers:
        assert handler.level == logging.WARNING

def test_log_rotation(log_dir: Path):
    """Test that log rotation works correctly."""
    manager = LogManager()
    manager.configure(
        log_dir,
        max_size=100,  # Small size to trigger rotation
        backup_count=2
    )
    
    logger = get_logger("test_module")
    
    # Write enough data to trigger rotation
    for i in range(100):
        logger.info("X" * 10)
    
    # Check that backup files were created
    log_files = list(log_dir.glob('agent.log*'))
    assert len(log_files) > 1  # Original + at least one backup 