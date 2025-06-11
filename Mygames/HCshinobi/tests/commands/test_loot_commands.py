"""Tests for loot commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

from HCshinobi.bot.cogs.loot_commands import LootCommands

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
def loot_commands_cog(mock_bot):
    """Create a LootCommands cog instance for testing."""
    return LootCommands(mock_bot)

@pytest.mark.asyncio
async def test_loot_command(loot_commands_cog, mock_ctx):
    """Test the loot command."""
    # Get the command from the cog
    command = loot_commands_cog.loot
    assert command is not None, "Loot command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_loot_history_command(loot_commands_cog, mock_ctx):
    """Test the loot_history command."""
    # Get the command from the cog
    command = loot_commands_cog.loot_history
    assert command is not None, "Loot history command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_loot_sell_command(loot_commands_cog, mock_ctx):
    """Test the loot_sell command."""
    # Get the command from the cog
    command = loot_commands_cog.loot_sell
    assert command is not None, "Loot sell command not found"
    
    # Call the command
    await command.callback(loot_commands_cog, mock_ctx, item_id="test_item")
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()
    # TODO: Add specific assertions for loot_sell command output 