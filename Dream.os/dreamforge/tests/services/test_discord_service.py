import pytest
import os
import json
from unittest.mock import patch, MagicMock, AsyncMock
import discord
from datetime import datetime, timedelta

from dreamforge.services.discord_service import UnifiedDiscordService

@pytest.fixture
def mock_bot():
    """Mock Discord bot."""
    bot = MagicMock()
    bot.user = MagicMock(name="TestBot")
    bot.guilds = []
    bot.loop = AsyncMock()
    return bot

@pytest.fixture
def mock_channel():
    """Mock Discord channel."""
    channel = MagicMock()
    channel.id = 123456789
    channel.name = "test-channel"
    channel.send = AsyncMock()
    return channel

@pytest.fixture
def service(mock_bot, tmp_path):
    """Create UnifiedDiscordService instance with mocked components."""
    with patch('discord.ext.commands.Bot', return_value=mock_bot):
        service = UnifiedDiscordService(
            bot_token="test_token",
            default_channel_id=123456789,
            template_dir=str(tmp_path)
        )
        service.bot = mock_bot
        yield service

def test_init_with_config(tmp_path):
    """Test service initialization with config."""
    config = {
        "bot_token": "test_token",
        "default_channel_id": 123456789,
        "channel_mappings": {"test": 987654321},
        "allowed_roles": ["admin"],
        "auto_responses": {"123": "Hello!"}
    }
    
    config_file = tmp_path / "discord_service.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
        
    with patch('dreamforge.services.discord_service.UnifiedDiscordService.CONFIG_FILE', str(config_file)):
        service = UnifiedDiscordService()
        assert service.config["bot_token"] == "test_token"
        assert service.config["default_channel_id"] == 123456789
        assert service.config["channel_mappings"] == {"test": 987654321}

def test_run_bot_already_running(service):
    """Test attempting to run bot when already running."""
    service.is_running = True
    service.run()
    service.bot.start.assert_not_called()

def test_run_bot_no_token(service):
    """Test attempting to run bot without token."""
    service.config["bot_token"] = ""
    service.run()
    service.bot.start.assert_not_called()

@pytest.mark.asyncio
async def test_process_message_queue(service, mock_channel):
    """Test message queue processing."""
    service.bot.get_channel.return_value = mock_channel
    
    # Queue a test message
    await service.message_queue.put({
        "channel_id": mock_channel.id,
        "content": "Test message"
    })
    
    # Process one message
    await service._process_message_queue()
    
    mock_channel.send.assert_called_once_with(content="Test message")

@pytest.mark.asyncio
async def test_process_message_queue_with_file(service, mock_channel, tmp_path):
    """Test message queue processing with file attachment."""
    service.bot.get_channel.return_value = mock_channel
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Test content")
    
    # Queue a test message with file
    await service.message_queue.put({
        "channel_id": mock_channel.id,
        "content": "Test message",
        "file_path": str(test_file)
    })
    
    # Process one message
    await service._process_message_queue()
    
    # Verify file was sent
    call_kwargs = mock_channel.send.call_args[1]
    assert call_kwargs["content"] == "Test message"
    assert isinstance(call_kwargs["file"], discord.File)

@pytest.mark.asyncio
async def test_process_message_queue_with_embed(service, mock_channel):
    """Test message queue processing with embed."""
    service.bot.get_channel.return_value = mock_channel
    
    embed = discord.Embed(title="Test Embed")
    
    # Queue a test message with embed
    await service.message_queue.put({
        "channel_id": mock_channel.id,
        "content": "Test message",
        "embed": embed
    })
    
    # Process one message
    await service._process_message_queue()
    
    mock_channel.send.assert_called_once_with(content="Test message", embed=embed)

def test_send_message_not_running(service):
    """Test sending message when bot is not running."""
    service.is_running = False
    service.send_message("Test")
    assert service.message_queue.empty()

def test_send_file_not_found(service):
    """Test sending non-existent file."""
    service.is_running = True
    service.send_file("nonexistent.txt")
    assert service.message_queue.empty()

def test_send_template(service, tmp_path):
    """Test sending templated message."""
    service.is_running = True
    
    # Create test template
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    template_file = template_dir / "test.j2"
    template_file.write_text("Hello {{ name }}!")
    
    service.template_env.loader.searchpath = [str(template_dir)]
    
    service.send_template("test", {"name": "World"})
    
    msg_data = service.message_queue.get_nowait()
    assert msg_data["content"] == "Hello World!"

def test_get_status(service):
    """Test status information retrieval."""
    service.is_running = True
    service.start_time = datetime.utcnow() - timedelta(hours=1)
    
    # Mock guild and channels
    guild = MagicMock()
    channel = MagicMock()
    channel.id = 123
    channel.name = "test"
    channel.__class__ = discord.TextChannel
    guild.channels = [channel]
    service.bot.guilds = [guild]
    
    status = service.get_status()
    
    assert status["is_running"] is True
    assert status["uptime"] >= 3600  # 1 hour in seconds
    assert status["connected_servers"] == 1
    assert len(status["active_channels"]) == 1
    assert status["active_channels"][0]["id"] == 123

def test_logging_with_callback(service):
    """Test logging with external callback."""
    callback_called = False
    def callback(message):
        nonlocal callback_called
        callback_called = True
        assert "Test message" in message
    
    service.set_log_callback(callback)
    service._log("Test message")
    
    assert callback_called

def test_prompt_channel_mapping(service):
    """Test prompt type to channel mapping."""
    service.map_prompt_to_channel("story", 987654321)
    assert service.config["prompt_channel_map"]["story"] == 987654321
    
    channel_id = service.get_channel_for_prompt("story")
    assert channel_id == 987654321
    
    # Test unmapping
    service.unmap_prompt_channel("story")
    assert "story" not in service.config["prompt_channel_map"]
    
    # Test default fallback
    channel_id = service.get_channel_for_prompt("story")
    assert channel_id == service.config["default_channel_id"]

@pytest.mark.asyncio
async def test_send_dreamscape_episode(service, mock_channel, tmp_path):
    """Test sending a Dreamscape episode."""
    service.bot.get_channel.return_value = mock_channel
    service.is_running = True
    
    # Test short episode (direct message)
    await service.send_dreamscape_episode("Episode 1", "A short dream story")
    msg_data = service.message_queue.get_nowait()
    assert msg_data["content"].startswith("**Episode 1**")
    assert "A short dream story" in msg_data["content"]
    
    # Test long episode (file attachment)
    long_content = "A" * 2001  # Exceeds Discord's limit
    await service.send_dreamscape_episode("Episode 2", long_content)
    msg_data = service.message_queue.get_nowait()
    assert msg_data["content"].startswith("**Episode 2**")
    assert "file_path" in msg_data
    with open(msg_data["file_path"]) as f:
        assert f.read() == long_content

@pytest.mark.asyncio
async def test_send_prompt_response(service, mock_channel):
    """Test sending prompt responses."""
    service.bot.get_channel.return_value = mock_channel
    service.is_running = True
    
    # Test normal response
    await service.send_prompt_response("test_prompt", "A simple response")
    msg_data = service.message_queue.get_nowait()
    assert msg_data["content"] == "A simple response"
    
    # Test response with custom channel
    service.map_prompt_to_channel("test_prompt", 987654321)
    await service.send_prompt_response("test_prompt", "Channel specific")
    msg_data = service.message_queue.get_nowait()
    assert msg_data["channel_id"] == 987654321
    
    # Test response with embed
    await service.send_prompt_response("test_prompt", "Response with embed", 
                                     title="Test Title", color=0xFF0000)
    msg_data = service.message_queue.get_nowait()
    assert msg_data["embed"].title == "Test Title"
    assert msg_data["embed"].color == 0xFF0000

def test_status_management(service):
    """Test status data management."""
    # Test setting valid status
    service.update_status("processing_state", "active")
    assert service.get_status()["processing_state"] == "active"
    
    # Test setting multiple status fields
    service.update_status_fields({
        "current_task": "dream_analysis",
        "queue_size": 5
    })
    status = service.get_status()
    assert status["current_task"] == "dream_analysis"
    assert status["queue_size"] == 5
    
    # Test invalid status key
    with pytest.raises(ValueError):
        service.update_status("invalid_key", "value")
    
    # Test status history
    service.update_status("processing_state", "completed")
    history = service.get_status_history()
    assert len(history) > 0
    assert history[-1]["field"] == "processing_state"
    assert history[-1]["value"] == "completed"

def test_prompt_channel_mapping_extended(service):
    """Test extended prompt channel mapping functionality."""
    # Test mapping
    service.map_prompt_to_channel("story", 987654321)
    assert service.get_channel_for_prompt("story") == 987654321
    
    # Test unmapping
    service.unmap_prompt_channel("story")
    assert service.get_channel_for_prompt("story") == service.config["default_channel_id"]
    
    # Test multiple mappings
    mappings = {
        "dream": 111111,
        "nightmare": 222222,
        "analysis": 333333
    }
    service.update_prompt_mappings(mappings)
    for prompt_type, channel_id in mappings.items():
        assert service.get_channel_for_prompt(prompt_type) == channel_id
    
    # Test default fallback
    assert service.get_channel_for_prompt("nonexistent") == service.config["default_channel_id"] 