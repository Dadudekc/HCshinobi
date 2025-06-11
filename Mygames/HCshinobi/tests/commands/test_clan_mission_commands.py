"""Tests for clan mission commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

from HCshinobi.bot.cogs.missions import MissionCommands

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
def mock_bot():
    """Create a mock bot for testing."""
    bot = MagicMock()
    bot.services = MagicMock()
    bot.services.mission_system = MagicMock()
    bot.services.character_system = MagicMock()
    return bot

@pytest.fixture
def clan_mission_commands_cog(mock_bot):
    """Create a MissionCommands cog instance for testing."""
    return MissionCommands(mock_bot)

@pytest.mark.asyncio
async def test_clan_mission_board_command(clan_mission_commands_cog, mock_ctx):
    """Test the clan_mission_board command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.clan_mission_board
    assert command is not None, "Clan mission board command not found"
    
    # Call the command
    await command.callback(clan_mission_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_clan_mission_accept_command(clan_mission_commands_cog, mock_ctx):
    """Test the clan_mission_accept command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.clan_mission_accept
    assert command is not None, "Clan mission accept command not found"
    
    # Call the command
    await command.callback(clan_mission_commands_cog, mock_ctx, mission_number=1)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_clan_mission_complete_command(clan_mission_commands_cog, mock_ctx):
    """Test the clan_mission_complete command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.clan_mission_complete
    assert command is not None, "Clan mission complete command not found"
    
    # Call the command
    await command.callback(clan_mission_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()
    # TODO: Add specific assertions for clan_mission_complete command output 