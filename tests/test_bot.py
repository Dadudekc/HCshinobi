"""Tests for the main bot module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
import logging

from HCshinobi.bot.bot import HCBot

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

@pytest.mark.asyncio
async def test_commands_command(mock_ctx):
    """Test the commands command."""
    # Create a minimal config for the bot
    config = MagicMock()
    config.command_prefix = "!"
    config.application_id = 123456789
    config.guild_id = 987654321
    config.battle_channel_id = 111111111
    config.online_channel_id = 222222222
    config.log_level = logging.INFO
    
    # Initialize the bot with the config
    bot = HCBot(config)
    
    # Register a test command
    @bot.command(name="test")
    async def test_command(ctx):
        await ctx.send("Test command")
    
    # Get the commands command
    commands_cmd = bot.get_command("commands")
    assert commands_cmd is not None, "Commands command not found"
    
    # Call the command
    await commands_cmd.callback(bot, mock_ctx)
    
    # Verify a message was sent
    mock_ctx.send.assert_awaited_once()
    args, kwargs = mock_ctx.send.call_args
    assert "Available commands:" in args[0]
    assert "test" in args[0] 