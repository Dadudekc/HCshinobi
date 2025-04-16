import pytest
import asyncio
from unittest.mock import Mock, patch
from dreamforge.core.cursor_dispatcher import CursorListener

@pytest.fixture
def cursor_listener():
    return CursorListener()

@pytest.fixture
def mock_message_queue():
    return asyncio.Queue()

@pytest.mark.asyncio
async def test_cursor_listener_initialization(cursor_listener):
    """Test CursorListener initializes correctly"""
    assert cursor_listener is not None
    assert hasattr(cursor_listener, 'process_message')
    assert hasattr(cursor_listener, 'start')

@pytest.mark.asyncio
async def test_message_processing(cursor_listener, mock_message_queue):
    """Test message processing functionality"""
    test_message = {"type": "command", "content": "test"}
    
    with patch.object(cursor_listener, '_handle_command') as mock_handler:
        await cursor_listener.process_message(test_message, mock_message_queue)
        mock_handler.assert_called_once_with(test_message, mock_message_queue)

@pytest.mark.asyncio
async def test_invalid_message_handling(cursor_listener, mock_message_queue):
    """Test handling of invalid messages"""
    invalid_message = {"type": "invalid", "content": "test"}
    
    with pytest.raises(ValueError):
        await cursor_listener.process_message(invalid_message, mock_message_queue)

@pytest.mark.asyncio
async def test_command_execution(cursor_listener, mock_message_queue):
    """Test command execution flow"""
    command = {
        "type": "command",
        "command": "test_command",
        "args": ["arg1", "arg2"]
    }
    
    with patch.object(cursor_listener, '_execute_command') as mock_execute:
        mock_execute.return_value = {"status": "success"}
        result = await cursor_listener._handle_command(command, mock_message_queue)
        assert result["status"] == "success"
        mock_execute.assert_called_once_with("test_command", ["arg1", "arg2"])

@pytest.mark.asyncio
async def test_error_handling(cursor_listener, mock_message_queue):
    """Test error handling during command execution"""
    command = {
        "type": "command",
        "command": "failing_command",
        "args": []
    }
    
    with patch.object(cursor_listener, '_execute_command') as mock_execute:
        mock_execute.side_effect = Exception("Test error")
        result = await cursor_listener._handle_command(command, mock_message_queue)
        assert result["status"] == "error"
        assert "Test error" in result["error"]

@pytest.mark.asyncio
async def test_queue_management(cursor_listener):
    """Test message queue management"""
    queue = asyncio.Queue()
    test_message = {"type": "command", "content": "test"}
    
    await queue.put(test_message)
    assert queue.qsize() == 1
    
    with patch.object(cursor_listener, 'process_message'):
        await cursor_listener._process_queue(queue)
        assert queue.empty()

@pytest.mark.asyncio
async def test_listener_start_stop(cursor_listener):
    """Test listener start and stop functionality"""
    with patch.object(cursor_listener, '_process_queue') as mock_process:
        # Start the listener
        task = asyncio.create_task(cursor_listener.start())
        await asyncio.sleep(0.1)  # Give it time to start
        
        # Verify it's running
        assert not task.done()
        
        # Stop the listener
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        assert task.done() 