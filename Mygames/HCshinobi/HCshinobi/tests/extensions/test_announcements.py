"""Test suite for announcements cog."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from discord.ext import commands
from HCshinobi.bot.cogs.announcements import AnnouncementCommands
from HCshinobi.bot.cogs.rolling import Rolling
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer
import discord
from discord import Color

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
async def test_announcement_commands_initialization(mock_bot):
    """Test announcement commands initialization."""
    cog = AnnouncementCommands(mock_bot)
    assert cog.bot == mock_bot
    assert isinstance(cog, commands.Cog)

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.user = Mock()
    interaction.user.guild_permissions = Mock()
    interaction.user.guild_permissions.administrator = False
    return interaction

@pytest.fixture
def cog(mock_bot):
    return AnnouncementCommands(mock_bot)

@pytest.mark.asyncio
async def test_toggle_announcements(cog, mock_interaction):
    """Test toggling announcements on and off."""
    # Test turning announcements on
    mock_interaction.user.guild_permissions.administrator = True
    await cog.toggle_announcements.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
    assert "enabled" in mock_interaction.response.send_message.call_args[0][0].lower()
    
    # Test turning announcements off
    mock_interaction.response.send_message.reset_mock()
    await cog.toggle_announcements.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
    assert "disabled" in mock_interaction.response.send_message.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_announce_without_admin_permission(cog, mock_interaction):
    """Test that non-admins cannot use the announce command."""
    await cog.announce_message.callback(cog, mock_interaction, "Test announcement")
    mock_interaction.response.send_message.assert_called_once()
    assert "administrator" in mock_interaction.response.send_message.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_announce_with_admin_plain_text(cog, mock_interaction):
    """Test that admins can send plain text announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement plain"
    await cog.announce_message.callback(cog, mock_interaction, test_message)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for content
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "content" in kwargs
    assert kwargs["content"] == test_message

@pytest.mark.asyncio
async def test_announce_with_admin_embed(cog, mock_interaction):
    """Test that admins can send embedded announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement embed"
    await cog.announce_message.callback(cog, mock_interaction, test_message, embed=True)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for embed
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    assert isinstance(kwargs["embed"], discord.Embed)
    assert kwargs["embed"].description == test_message

@pytest.mark.asyncio
async def test_announce_with_everyone_ping(cog, mock_interaction):
    """Test that @everyone ping is included when requested."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement ping"
    await cog.announce_message.callback(cog, mock_interaction, test_message, ping_everyone=True)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for content with @everyone
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "content" in kwargs
    assert "@everyone" in kwargs["content"]
    assert test_message in kwargs["content"]

@pytest.mark.asyncio
async def test_announce_forbidden_error(cog, mock_interaction):
    """Test handling of forbidden errors when sending announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    forbidden_error = discord.Forbidden(Mock(), "Missing permissions")
    mock_interaction.response.send_message.side_effect = forbidden_error

    # Expect the command to raise discord.Forbidden
    with pytest.raises(discord.Forbidden) as excinfo:
        await cog.announce_message.callback(cog, mock_interaction, "Test announcement forbidden")

    assert excinfo.value is forbidden_error
    # Check the ephemeral response sent by the error handler
    mock_interaction.response.send_message.assert_called_once_with(
        f"Failed to send announcement: {forbidden_error}", ephemeral=True
    )

@pytest.mark.asyncio
async def test_announce_generic_error(cog, mock_interaction):
    """Test handling of generic errors when sending announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_exception = Exception("Unexpected error")
    mock_interaction.response.send_message.side_effect = test_exception

    # Expect the command to raise a generic Exception
    with pytest.raises(Exception) as excinfo:
        await cog.announce_message.callback(cog, mock_interaction, "Test announcement generic error")

    assert excinfo.value is test_exception
    # Check the ephemeral response sent by the error handler
    mock_interaction.response.send_message.assert_called_once_with(
        "An unexpected error occurred while sending the announcement.", ephemeral=True
    )
    # Verify logger was called as well for generic errors
    cog.logger.error.assert_called_once()

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