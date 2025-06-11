"""Tests for mission commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

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
def mission_commands_cog(mock_bot):
    """Create a MissionCommands cog instance for testing."""
    mission_system = MagicMock()
    character_system = MagicMock()
    return MissionCommands(mock_bot, mission_system, character_system)

# Define test cases for mission commands
MISSION_COMMAND_CASES = [
    # (command_name, required_params)
    ("mission_board", {}),
    ("mission_accept", {"mission_number": 1}),
    ("mission_progress", {}),
    ("mission_roll", {}),
    ("mission_complete", {}),
    ("mission_abandon", {}),
    ("mission_history", {}),
    ("mission_simulate", {})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", MISSION_COMMAND_CASES)
async def test_mission_commands(mission_commands_cog, command_name, params):
    """Test all mission commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(mission_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(mission_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
    )

# Edge case tests
@pytest.mark.asyncio
async def test_mission_accept_invalid_number(mission_commands_cog):
    """Test mission_accept with invalid mission number."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = mission_commands_cog.mission_accept
    assert command is not None, "Mission accept command not found"
    
    # Call with invalid mission number
    await command.callback(mission_commands_cog, mock_ctx, mission_number=999)
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Invalid mission number"}  # followup_send
    )

@pytest.mark.asyncio
async def test_mission_accept_no_missions(mission_commands_cog):
    """Test mission_accept when no missions are available."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = mission_commands_cog.mission_accept
    assert command is not None, "Mission accept command not found"
    
    # Mock empty mission board
    mission_commands_cog.mission_board = []
    
    # Call command
    await command.callback(mission_commands_cog, mock_ctx, mission_number=1)
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "No missions available"}  # followup_send
    )

@pytest.mark.asyncio
async def test_mission_complete_no_active_mission(mission_commands_cog):
    """Test mission_complete when no mission is active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = mission_commands_cog.mission_complete
    assert command is not None, "Mission complete command not found"
    
    # Mock no active mission
    mission_commands_cog.active_mission = None
    
    # Call command
    await command.callback(mission_commands_cog, mock_ctx)
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "No active mission"}  # followup_send
    ) 