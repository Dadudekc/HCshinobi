"""Tests for the bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import BotConfig

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return BotConfig(
        token="test_token",
        guild_id=123456789,
        battle_channel_id=987654321,
        online_channel_id=123789456,
        announcement_channel_id=777888999,
        data_dir="test_data",
        command_prefix="!",
        webhook_url="https://discord.com/api/webhooks/test",
        log_level="INFO",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama2",
        openai_api_key="test_key",
        openai_target_url="https://api.openai.com/v1",
        openai_headless=True
    )

@pytest.fixture
def mock_services():
    """Create mock services."""
    services = MagicMock()
    services.character_system = AsyncMock()
    services.battle_system = AsyncMock()
    services.clan_system = AsyncMock()
    services.announcement_system = AsyncMock()
    services.ai_system = AsyncMock()
    return services

@pytest.fixture
def mock_bot(mock_config, mock_services):
    """Create a mock bot instance."""
    bot = HCBot(mock_config)
    bot.services = mock_services
    return bot

@pytest.mark.asyncio
async def test_bot_initialization(mock_config):
    """Test bot initialization."""
    bot = HCBot(mock_config)
    assert bot.config == mock_config
    assert bot.guild_id == mock_config.guild_id
    assert bot.battle_channel_id == mock_config.battle_channel_id
    assert bot.online_channel_id == mock_config.online_channel_id

@pytest.mark.asyncio
async def test_bot_setup(mock_bot):
    """Test bot setup."""
    # Mock the setup methods
    mock_bot.setup_services = AsyncMock()
    mock_bot.setup_commands = AsyncMock()
    mock_bot.setup_events = AsyncMock()
    
    # Call setup
    await mock_bot.setup()
    
    # Verify calls
    mock_bot.setup_services.assert_called_once()
    mock_bot.setup_commands.assert_called_once()
    mock_bot.setup_events.assert_called_once()

@pytest.mark.asyncio
async def test_bot_services_setup(mock_bot):
    """Test services setup."""
    # Call setup_services
    await mock_bot.setup_services()
    
    # Verify services are initialized
    assert mock_bot.services is not None
    assert mock_bot.services.character_system is not None
    assert mock_bot.services.battle_system is not None
    assert mock_bot.services.clan_system is not None
    assert mock_bot.services.notification_dispatcher is not None
    # Check AI clients (optional check, depends on test config)
    # assert mock_bot.services.ollama_client is not None 
    # assert mock_bot.services.openai_client is not None 

@pytest.mark.asyncio
async def test_bot_commands_setup(mock_bot):
    """Test commands setup."""
    # Call setup_commands
    await mock_bot.setup_commands()
    
    # Verify commands are loaded
    assert len(mock_bot.commands) > 0
    assert mock_bot.get_command("help") is not None

@pytest.mark.asyncio
async def test_bot_events_setup(mock_bot):
    """Test events setup."""
    # Call setup_events
    await mock_bot.setup_events()
    
    # Verify event listeners are registered
    assert len(mock_bot.extra_events) > 0

@pytest.mark.asyncio
async def test_bot_run(mock_bot):
    """Test bot run method."""
    # Mock the discord.py start method
    mock_bot.start = AsyncMock()
    
    # Call run
    await mock_bot.run()
    
    # Verify start was called with token
    mock_bot.start.assert_called_once_with(mock_bot.config.token)