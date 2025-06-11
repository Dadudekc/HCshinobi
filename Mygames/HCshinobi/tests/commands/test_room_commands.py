"""Tests for room commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

from HCshinobi.bot.cogs.room import RoomCommands

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
def room_commands_cog(mock_bot):
    """Create a RoomCommands cog instance for testing."""
    return RoomCommands(mock_bot)

@pytest.mark.asyncio
async def test_room_info_command(room_commands_cog, mock_ctx):
    """Test the room_info command."""
    # Get the command from the cog
    command = room_commands_cog.room_info
    assert command is not None, "Room info command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_room_enter_command(room_commands_cog, mock_ctx):
    """Test the room_enter command."""
    # Get the command from the cog
    command = room_commands_cog.room_enter
    assert command is not None, "Room enter command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx, room_name="Test Room")
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_room_leave_command(room_commands_cog, mock_ctx):
    """Test the room_leave command."""
    # Get the command from the cog
    command = room_commands_cog.room_leave
    assert command is not None, "Room leave command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()
    # TODO: Add specific assertions for room_leave command output 