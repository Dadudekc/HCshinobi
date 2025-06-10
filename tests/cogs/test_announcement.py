"""Test suite for announcement commands."""
import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch
from HCshinobi.bot.cogs.announcement import AnnouncementCommands

@pytest.fixture
async def announcement_cog(mock_bot):
    """Create an AnnouncementCommands instance with mocked dependencies."""
    cog = AnnouncementCommands(mock_bot)
    return cog

@pytest.fixture
def mock_interaction():
    """Create a mock interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(
        id=123456789,
        display_name="Test User",
        guild_permissions=MagicMock(administrator=True)
    )
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_channel():
    """Create a mock text channel."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.id = 987654321
    channel.mention = "#test-channel"
    return channel

@pytest.mark.asyncio
async def test_announce_command_success(announcement_cog, mock_interaction, mock_channel):
    """Test successful announcement."""
    # Setup
    message = "Test announcement message"

    # Execute
    await announcement_cog.announce(mock_interaction, mock_channel, message)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_channel.send.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with(
        f"✅ Announcement sent to {mock_channel.mention}!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_announce_command_no_permission(announcement_cog, mock_interaction, mock_channel):
    """Test announcement without admin permission."""
    # Setup
    mock_interaction.user.guild_permissions.administrator = False
    message = "Test announcement message"

    # Execute
    await announcement_cog.announce(mock_interaction, mock_channel, message)

    # Verify
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You don't have permission to use this command!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_broadcast_command_success(announcement_cog, mock_interaction):
    """Test successful broadcast."""
    # Setup
    channel_ids = "123,456,789"
    message = "Test broadcast message"
    mock_channel1 = AsyncMock(spec=discord.TextChannel)
    mock_channel1.mention = "#channel1"
    mock_channel2 = AsyncMock(spec=discord.TextChannel)
    mock_channel2.mention = "#channel2"
    announcement_cog.bot.get_channel.side_effect = [mock_channel1, mock_channel2, None]

    # Execute
    await announcement_cog.broadcast(mock_interaction, channel_ids, message)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    assert mock_channel1.send.call_count == 1
    assert mock_channel2.send.call_count == 1
    mock_interaction.followup.send.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_command_no_permission(announcement_cog, mock_interaction):
    """Test broadcast without admin permission."""
    # Setup
    mock_interaction.user.guild_permissions.administrator = False
    channel_ids = "123,456,789"
    message = "Test broadcast message"

    # Execute
    await announcement_cog.broadcast(mock_interaction, channel_ids, message)

    # Verify
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You don't have permission to use this command!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_alert_command_success(announcement_cog, mock_interaction, mock_channel):
    """Test successful alert."""
    # Setup
    message = "Test alert message"

    # Execute
    await announcement_cog.alert(mock_interaction, mock_channel, message)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_channel.send.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with(
        f"✅ Alert sent to {mock_channel.mention}!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_alert_command_no_permission(announcement_cog, mock_interaction, mock_channel):
    """Test alert without admin permission."""
    # Setup
    mock_interaction.user.guild_permissions.administrator = False
    message = "Test alert message"

    # Execute
    await announcement_cog.alert(mock_interaction, mock_channel, message)

    # Verify
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You don't have permission to use this command!",
        ephemeral=True
    ) 