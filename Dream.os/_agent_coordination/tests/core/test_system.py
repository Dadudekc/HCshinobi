"""Tests for the system utilities module."""

import os
import pytest
import asyncio
import shutil
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock

from core.utils.system import (
    CommandExecutor, CommandResult,
    DirectoryMonitor, FileManager
)

@pytest.fixture
def temp_dir(tmp_path) -> Generator[Path, None, None]:
    """Fixture that provides a temporary directory."""
    yield tmp_path

@pytest.fixture
def command_executor() -> CommandExecutor:
    """Fixture that provides a CommandExecutor instance."""
    return CommandExecutor(max_retries=2, base_delay=0.1)

@pytest.fixture
def directory_monitor(temp_dir: Path) -> DirectoryMonitor:
    """Fixture that provides a DirectoryMonitor instance."""
    watch_dir = temp_dir / "watch"
    success_dir = temp_dir / "success"
    error_dir = temp_dir / "error"
    
    return DirectoryMonitor(
        watch_dir=watch_dir,
        success_dir=success_dir,
        error_dir=error_dir,
        poll_interval=0.1
    )

@pytest.fixture
def file_manager() -> FileManager:
    """Fixture that provides a FileManager instance."""
    return FileManager(max_retries=2)

@pytest.mark.asyncio
async def test_command_execution(command_executor: CommandExecutor):
    """Test basic command execution."""
    # Test successful command
    result = await command_executor.run_command(["echo", "test"])
    assert result.success
    assert result.return_code == 0
    assert "test" in result.stdout
    assert result.duration > 0
    
    # Test failed command
    with pytest.raises(subprocess.CalledProcessError):
        await command_executor.run_command(["nonexistent_command"])
    
    # Test command timeout
    with pytest.raises(asyncio.TimeoutError):
        await command_executor.run_command(
            ["sleep", "10"],
            timeout=0.1
        )

@pytest.mark.asyncio
async def test_command_retry(command_executor: CommandExecutor):
    """Test command retry logic."""
    # Mock a failing command that succeeds on second try
    attempt = 0
    async def mock_execute(*args, **kwargs):
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise Exception("First attempt failed")
        return CommandResult(
            success=True,
            return_code=0,
            stdout="success",
            stderr="",
            duration=0.1,
            command=["test"]
        )
    
    with patch.object(command_executor, 'run_command', side_effect=mock_execute):
        result = await command_executor.run_command(["test"])
        assert result.success
        assert attempt == 2

class TestDirectoryMonitor(DirectoryMonitor):
    """Test implementation of DirectoryMonitor."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_files = []
        
    async def process_file(self, file_path: Path) -> bool:
        self.processed_files.append(file_path)
        return True

@pytest.mark.asyncio
async def test_directory_monitor(temp_dir: Path):
    """Test directory monitoring functionality."""
    monitor = TestDirectoryMonitor(
        watch_dir=temp_dir / "watch",
        success_dir=temp_dir / "success",
        error_dir=temp_dir / "error",
        poll_interval=0.1
    )
    
    # Create test file
    test_file = monitor.watch_dir / "test.txt"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("test content")
    
    # Start monitor
    monitor_task = asyncio.create_task(monitor.start())
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Stop monitor
    await monitor.stop()
    await monitor_task
    
    # Verify file was processed
    assert test_file in monitor.processed_files
    assert not test_file.exists()  # Should be moved
    assert len(list(monitor.success_dir.glob("*.txt"))) == 1

@pytest.mark.asyncio
async def test_directory_monitor_error(temp_dir: Path):
    """Test directory monitor error handling."""
    class ErrorMonitor(DirectoryMonitor):
        async def process_file(self, file_path: Path) -> bool:
            raise Exception("Processing error")
    
    monitor = ErrorMonitor(
        watch_dir=temp_dir / "watch",
        success_dir=temp_dir / "success",
        error_dir=temp_dir / "error",
        poll_interval=0.1
    )
    
    # Create test file
    test_file = monitor.watch_dir / "test.txt"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("test content")
    
    # Start monitor
    monitor_task = asyncio.create_task(monitor.start())
    
    # Wait for processing
    await asyncio.sleep(0.2)
    
    # Stop monitor
    await monitor.stop()
    await monitor_task
    
    # Verify file was moved to error directory
    assert not test_file.exists()
    assert len(list(monitor.error_dir.glob("*.txt"))) == 1

@pytest.mark.asyncio
async def test_file_manager(file_manager: FileManager, temp_dir: Path):
    """Test file management operations."""
    # Test file creation
    test_file = temp_dir / "test.txt"
    await file_manager.safe_write(test_file, "test content")
    assert test_file.exists()
    assert test_file.read_text() == "test content"
    
    # Test file reading
    content = await file_manager.safe_read(test_file)
    assert content == "test content"
    
    # Test file copying
    copy_file = temp_dir / "test_copy.txt"
    await file_manager.safe_copy(test_file, copy_file)
    assert copy_file.exists()
    assert copy_file.read_text() == "test content"
    
    # Test file moving
    move_file = temp_dir / "test_move.txt"
    await file_manager.safe_move(copy_file, move_file)
    assert not copy_file.exists()
    assert move_file.exists()
    assert move_file.read_text() == "test content"
    
    # Test file deletion
    await file_manager.safe_delete(test_file)
    assert not test_file.exists()

@pytest.mark.asyncio
async def test_file_manager_retry(file_manager: FileManager, temp_dir: Path):
    """Test file operation retry logic."""
    test_file = temp_dir / "test.txt"
    
    # Mock a failing operation that succeeds on second try
    attempt = 0
    async def mock_write():
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            raise OSError("First attempt failed")
        test_file.write_text("test content")
    
    with patch.object(file_manager.retry_manager, 'execute',
                     side_effect=lambda f: mock_write()):
        await file_manager.safe_write(test_file, "test content")
        assert attempt == 2
        assert test_file.exists()
        assert test_file.read_text() == "test content" 