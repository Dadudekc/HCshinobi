"""Tests for announcement commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.announcements import AnnouncementCommands

@pytest.fixture
def mock_ctx():
    """Create a mock context for testing commands."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    ctx.author = MagicMock(spec=discord.Member)
    ctx.author.id = 123456789
    ctx.author.name = "TestUser"
    ctx.author.display_name = "Test User"
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 987654321
    
    # Add user attribute for interaction-based commands
    ctx.user = ctx.author
    ctx.interaction = AsyncMock()
    ctx.interaction.user = ctx.author
    ctx.interaction.guild = ctx.guild
    
    # Set up response methods
    ctx.response = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.followup = AsyncMock()
    ctx.followup.send = AsyncMock()
    ctx.interaction.response = ctx.response
    ctx.interaction.followup = ctx.followup
    
    return ctx

@pytest.fixture
def announcement_commands_cog(mock_bot):
    """Create an AnnouncementCommands cog instance for testing."""
    return AnnouncementCommands(mock_bot)

# Test cases for announcement commands
ANNOUNCEMENT_COMMAND_CASES = [
    ("announce", {"title": "Test Title", "message": "Test announcement"}),
    ("battle_announce", {"fighter_a": "Player1", "fighter_b": "Player2", "arena": "Test Arena", "time": "2024-01-01 12:00:00"}),
    ("lore_drop", {"title": "Test Lore", "snippet": "Test lore content"}),
    ("check_permissions", {}),
    ("check_bot_role", {}),
    ("send_system_alert", {"title": "Test Alert", "message": "Test alert message"}),
    ("broadcast_lore", {"trigger": "test_trigger"}),
    ("alert_clan", {"clan_name": "Test Clan", "title": "Test Alert", "message": "Test message"}),
    ("view_lore", {}),
    ("update", {"version": "1.0.0", "release_date": "2024-01-01", "changes": "Test changes"})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", ANNOUNCEMENT_COMMAND_CASES)
async def test_announcement_commands(announcement_commands_cog, command_name, params):
    """Test all announcement commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(announcement_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(announcement_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence based on command type
    if command_name in ["check_permissions", "check_bot_role"]:
        trace.assert_interaction_sequence(
            ("defer", {"ephemeral": True}),
            ("followup_send", {"embed": discord.Embed})
        )
    else:
        trace.assert_interaction_sequence(
            ("defer", {"ephemeral": True}),
            ("followup_send", {})
        )

# Edge case tests
@pytest.mark.asyncio
async def test_announce_empty_content(announcement_commands_cog):
    """Test announce with empty content."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = announcement_commands_cog.announce
    assert command is not None, "Announce command not found"
    
    # Call with empty message
    await command.callback(announcement_commands_cog, mock_ctx, title="Test Title", message="")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),
        ("followup_send", {"content": "Announcement message cannot be empty"})
    )

@pytest.mark.asyncio
async def test_announcement_schedule_invalid_time(announcement_commands_cog):
    """Test announcement_schedule with invalid time."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = announcement_commands_cog.update
    assert command is not None, "Update command not found"
    
    # Call with invalid release date
    await command.callback(announcement_commands_cog, mock_ctx, version="1.0.0", release_date="invalid_date", changes="Test changes")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),
        ("followup_send", {"content": "Invalid date format: invalid_date"})
    ) 