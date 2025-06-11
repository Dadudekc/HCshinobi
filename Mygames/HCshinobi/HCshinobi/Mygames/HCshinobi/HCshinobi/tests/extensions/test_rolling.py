"""Test suite for rolling cog."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from discord.ext import commands
from HCshinobi.bot.cogs.rolling import Rolling
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return BotConfig(
        token="test_token",
        guild_id=123456789,
        battle_channel_id=987654321,
        online_channel_id=987654322,
        data_dir="test_data",
        ollama_base_url="http://localhost:11434",
        ollama_model="mistral",
        openai_api_key="test_key",
        openai_target_url="http://localhost:8000",
        openai_headless=True
    )

@pytest.fixture
def mock_services():
    """Create a mock service container."""
    services = Mock(spec=ServiceContainer)
    services.initialize = AsyncMock()
    services.shutdown = AsyncMock()
    return services

@pytest.fixture
def mock_bot(mock_config, mock_services):
    """Create a mock bot."""
    bot = Mock(spec=commands.Bot)
    bot.config = mock_config
    bot.services = mock_services
    return bot

@pytest.mark.asyncio
async def test_rolling_initialization(mock_bot):
    """Test rolling cog initialization."""
    cog = Rolling(mock_bot)
    assert cog.bot == mock_bot
    assert isinstance(cog, commands.Cog)

@pytest.mark.asyncio
async def test_roll_command(mock_bot):
    """Test roll command."""
    cog = Rolling(mock_bot)
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()

    # Test rolling with default values
    await cog.roll.callback(cog, interaction)
    interaction.response.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_create_roll_animation(mock_bot):
    """Test create_roll_animation method."""
    cog = Rolling(mock_bot)
    message = AsyncMock()
    
    await cog.create_roll_animation(message)
    
    # Verify that edit was called multiple times with different animation frames
    assert message.edit.call_count > 1
    # Verify the animation frames
    calls = message.edit.call_args_list
    assert all("Rolling clan" in call[1]["content"] for call in calls) 