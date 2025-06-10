"""Tests for the bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer

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
    """Create a fully mocked ServiceContainer instance."""
    services = MagicMock(spec=ServiceContainer)
    services.initialize = AsyncMock()
    services.shutdown = AsyncMock()
    services.currency_system = MagicMock()
    services.character_system = MagicMock()
    services.battle_system = MagicMock()
    services.training_system = MagicMock()
    services.quest_system = MagicMock()
    services.clan_system = MagicMock()
    services.clan_missions = MagicMock()
    services.loot_system = MagicMock()
    services.room_system = MagicMock()
    services.clan_data = MagicMock()
    services.webhook = MagicMock()
    return services

@pytest.fixture
def mock_bot(mock_config):
    """Create a mock bot instance."""
    bot = HCBot(mock_config)
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
async def test_bot_setup(mock_bot, mock_services):
    """Test bot setup, replacing the internally created ServiceContainer."""
    mock_bot.setup_commands = AsyncMock()
    mock_bot.setup_events = AsyncMock()

    with patch('HCshinobi.bot.bot.ServiceContainer', return_value=mock_services) as mock_sc_constructor:
        await mock_bot.setup()

    mock_sc_constructor.assert_called_once_with(mock_bot.config)
    mock_services.initialize.assert_called_once()
    mock_bot.setup_commands.assert_called_once()
    mock_bot.setup_events.assert_called_once()
    assert mock_bot.services is mock_services

@pytest.mark.asyncio
async def test_bot_commands_setup(mock_bot):
    """Test commands setup."""
    await mock_bot.setup_commands()
    
    assert len(mock_bot.commands) > 0
    assert mock_bot.get_command("help") is not None

@pytest.mark.asyncio
async def test_bot_events_setup(mock_bot):
    """Test events setup."""
    await mock_bot.setup_events()
    
    assert len(mock_bot.extra_events) > 0

@pytest.mark.asyncio
async def test_bot_run(mock_bot):
    """Test bot run method."""
    mock_bot.start = AsyncMock()
    
    await mock_bot.run()
    
    mock_bot.start.assert_called_once_with(mock_bot.config.token)