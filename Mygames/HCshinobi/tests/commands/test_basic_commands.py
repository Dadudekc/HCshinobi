"""Tests for basic commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.character_commands import CharacterCommands

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
def basic_commands_cog(mock_bot):
    """Create a CharacterCommands cog instance for testing."""
    return CharacterCommands(mock_bot)

@pytest.mark.asyncio
async def test_inventory_command(basic_commands_cog, mock_ctx):
    """Test the inventory command."""
    await basic_commands_cog.inventory.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for inventory command output

@pytest.mark.asyncio
async def test_jutsu_command(basic_commands_cog, mock_ctx):
    """Test the jutsu command."""
    await basic_commands_cog.jutsu.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for jutsu command output

@pytest.mark.asyncio
async def test_status_command(basic_commands_cog, mock_ctx):
    """Test the status command."""
    await basic_commands_cog.status.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for status command output

@pytest.mark.asyncio
async def test_missions_command(basic_commands_cog, mock_ctx):
    """Test the missions command."""
    await basic_commands_cog.missions.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for missions command output

@pytest.mark.asyncio
async def test_team_command(basic_commands_cog, mock_ctx):
    """Test the team command."""
    await basic_commands_cog.team.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for team command output

@pytest.mark.asyncio
async def test_clan_command(basic_commands_cog, mock_ctx):
    """Test the clan command."""
    await basic_commands_cog.clan.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for clan command output

@pytest.mark.asyncio
async def test_shop_command(basic_commands_cog, mock_ctx):
    """Test the shop command."""
    await basic_commands_cog.shop.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for shop command output

@pytest.mark.asyncio
async def test_balance_command(basic_commands_cog, mock_ctx):
    """Test the balance command."""
    await basic_commands_cog.balance.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for balance command output

@pytest.mark.asyncio
async def test_train_command(basic_commands_cog, mock_ctx):
    """Test the train command."""
    await basic_commands_cog.train.callback(basic_commands_cog, mock_ctx)
    mock_ctx.send.assert_awaited_once()
    # TODO: Add specific assertions for train command output

@pytest.mark.asyncio
async def test_ping_command(basic_commands_cog, mock_ctx):
    """Test the ping command."""
    # Get the command from the cog
    command = basic_commands_cog.ping
    assert command is not None, "Ping command not found"
    
    # Call the command
    await command.callback(basic_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_help_command(basic_commands_cog, mock_ctx):
    """Test the help command."""
    # Get the command from the cog
    command = basic_commands_cog.help
    assert command is not None, "Help command not found"
    
    # Call the command
    await command.callback(basic_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_about_command(basic_commands_cog, mock_ctx):
    """Test the about command."""
    # Get the command from the cog
    command = basic_commands_cog.about
    assert command is not None, "About command not found"
    
    # Call the command
    await command.callback(basic_commands_cog, mock_ctx)
    
    # Verify response
    mock_ctx.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_ctx.followup.send.assert_awaited_once()

# Define test cases for basic commands
BASIC_COMMAND_CASES = [
    # (command_name, required_params)
    ("ping", {}),
    ("help", {}),
    ("about", {}),
    ("status", {}),
    ("profile", {}),
    ("inventory", {}),
    ("equipment", {}),
    ("stats", {}),
    ("train", {"stat": "strength"}),
    ("rest", {}),
    ("shop", {}),
    ("buy", {"item": "potion"}),
    ("sell", {"item": "potion"}),
    ("use", {"item": "potion"}),
    ("drop", {"item": "potion"}),
    ("give", {"item": "potion", "target": "user"}),
    ("trade", {"target": "user"}),
    ("duel", {"target": "user"}),
    ("challenge", {"target": "user"}),
    ("accept", {}),
    ("decline", {}),
    ("forfeit", {}),
    ("leaderboard", {}),
    ("rank", {}),
    ("achievements", {}),
    ("daily", {}),
    ("weekly", {}),
    ("monthly", {}),
    ("rewards", {}),
    ("settings", {}),
    ("language", {"lang": "en"}),
    ("timezone", {"tz": "UTC"}),
    ("notifications", {}),
    ("privacy", {}),
    ("report", {"target": "user", "reason": "spam"}),
    ("feedback", {"content": "test feedback"}),
    ("bug", {"description": "test bug"}),
    ("suggestion", {"content": "test suggestion"}),
    ("rules", {}),
    ("terms", {}),
    ("privacy_policy", {}),
    ("support", {}),
    ("invite", {}),
    ("vote", {}),
    ("patreon", {}),
    ("discord", {}),
    ("github", {}),
    ("website", {}),
    ("social", {}),
    ("credits", {})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", BASIC_COMMAND_CASES)
async def test_basic_commands(basic_commands_cog, command_name, params):
    """Test all basic commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(basic_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(basic_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
    )

# Edge case tests
@pytest.mark.asyncio
async def test_train_invalid_stat(basic_commands_cog):
    """Test train command with invalid stat."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = basic_commands_cog.train
    assert command is not None, "Train command not found"
    
    # Call with invalid stat
    await command.callback(basic_commands_cog, mock_ctx, stat="invalid_stat")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Invalid stat: invalid_stat"}  # followup_send
    )

@pytest.mark.asyncio
async def test_buy_nonexistent_item(basic_commands_cog):
    """Test buy command with nonexistent item."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = basic_commands_cog.buy
    assert command is not None, "Buy command not found"
    
    # Call with nonexistent item
    await command.callback(basic_commands_cog, mock_ctx, item="nonexistent_item")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Item not found: nonexistent_item"}  # followup_send
    )

@pytest.mark.asyncio
async def test_duel_self(basic_commands_cog):
    """Test duel command with self as target."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = basic_commands_cog.duel
    assert command is not None, "Duel command not found"
    
    # Call with self as target
    await command.callback(basic_commands_cog, mock_ctx, target="self")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "You cannot duel yourself"}  # followup_send
    ) 