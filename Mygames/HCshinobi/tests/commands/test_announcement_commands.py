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
    ctx.guild = MagicMock(spec=discord.Guild)
    ctx.guild.id = 987654321
    return ctx

@pytest.fixture
def announcement_commands_cog(mock_bot):
    """Create an AnnouncementCommands cog instance for testing."""
    return AnnouncementCommands(mock_bot)

# Define test cases for announcement commands
ANNOUNCEMENT_COMMAND_CASES = [
    # (command_name, required_params)
    ("announce", {"content": "Test announcement"}),
    ("announcement_list", {}),
    ("announcement_remove", {"announcement_id": 1}),
    ("announcement_edit", {"announcement_id": 1, "content": "Updated announcement"}),
    ("announcement_pin", {"announcement_id": 1}),
    ("announcement_unpin", {"announcement_id": 1}),
    ("announcement_schedule", {"content": "Test announcement", "time": "2023-01-01 12:00:00"}),
    ("announcement_cancel", {"announcement_id": 1}),
    ("announcement_repeat", {"announcement_id": 1, "interval": "daily"}),
    ("announcement_stop_repeat", {"announcement_id": 1}),
    ("announcement_priority", {"announcement_id": 1, "priority": "high"}),
    ("announcement_channel", {"announcement_id": 1, "channel": "general"}),
    ("announcement_role", {"announcement_id": 1, "role": "everyone"}),
    ("announcement_mention", {"announcement_id": 1, "mention": "here"}),
    ("announcement_embed", {"announcement_id": 1, "embed": True}),
    ("announcement_color", {"announcement_id": 1, "color": "#FF0000"}),
    ("announcement_title", {"announcement_id": 1, "title": "Test Title"}),
    ("announcement_description", {"announcement_id": 1, "description": "Test Description"}),
    ("announcement_footer", {"announcement_id": 1, "footer": "Test Footer"}),
    ("announcement_thumbnail", {"announcement_id": 1, "url": "https://example.com/thumb.png"})
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
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
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
    
    # Call with empty content
    await command.callback(announcement_commands_cog, mock_ctx, content="")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Announcement cannot be empty"}  # followup_send
    )

@pytest.mark.asyncio
async def test_announcement_remove_nonexistent(announcement_commands_cog):
    """Test announcement_remove with nonexistent announcement."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = announcement_commands_cog.announcement_remove
    assert command is not None, "Announcement remove command not found"
    
    # Mock nonexistent announcement
    announcement_commands_cog.announcement_exists = AsyncMock(return_value=False)
    
    # Call with nonexistent announcement
    await command.callback(announcement_commands_cog, mock_ctx, announcement_id=999)
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Announcement not found: 999"}  # followup_send
    )

@pytest.mark.asyncio
async def test_announcement_schedule_invalid_time(announcement_commands_cog):
    """Test announcement_schedule with invalid time."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = announcement_commands_cog.announcement_schedule
    assert command is not None, "Announcement schedule command not found"
    
    # Call with invalid time
    await command.callback(announcement_commands_cog, mock_ctx, content="Test", time="invalid_time")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Invalid time format: invalid_time"}  # followup_send
    ) 