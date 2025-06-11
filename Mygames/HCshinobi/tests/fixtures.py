"""Test fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

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
    """Create a mock bot instance for testing."""
    bot = MagicMock(spec=commands.Bot)
    bot.command_prefix = "!"
    bot.intents = discord.Intents.default()
    return bot

@pytest.fixture
def mock_guild():
    """Create a mock guild for testing."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 987654321
    return guild

@pytest.fixture
def mock_member():
    """Create a mock member for testing."""
    member = MagicMock(spec=discord.Member)
    member.id = 123456789
    return member 