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
def mock_bot():
    """Create a mock bot with required services."""
    bot = MagicMock()
    
    # Create async mocks for mission system methods
    mission_system = AsyncMock()
    mission_system.get_available_missions = AsyncMock(return_value=[])
    mission_system.get_active_mission = AsyncMock(return_value=None)
    mission_system.get_mission_progress = AsyncMock(return_value="Progress: 0%")
    mission_system.roll_mission = AsyncMock(return_value="Roll result: Success")
    mission_system.complete_mission = AsyncMock(return_value=True)
    mission_system.abandon_mission = AsyncMock(return_value=True)
    mission_system.get_mission_history = AsyncMock(return_value=[])
    mission_system.simulate_mission = AsyncMock(return_value="Simulation result: Success")
    mission_system.accept_mission = AsyncMock(return_value=True)

    # Create async mocks for character system methods
    character_system = AsyncMock()
    character_system.get_character = AsyncMock(return_value=MagicMock())

    # Set up bot services
    bot.services = MagicMock()
    bot.services.mission_system = mission_system
    bot.services.character_system = character_system
    
    return bot

@pytest.fixture
def mission_commands_cog(mock_bot):
    """Create a MissionCommands cog instance for testing."""
    return MissionCommands(mock_bot)

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
    expected_messages = {
        "mission_board": "No missions are available for you right now. Try ranking up or leveling up!",
        "mission_accept": "No missions are available for you right now.",
        "mission_progress": "You don't have an active mission!",
        "mission_roll": "You don't have an active mission!",
        "mission_complete": "You don't have an active mission!",
        "mission_abandon": "You don't have an active mission!",
        "mission_history": "You haven't completed any missions yet!",
        "mission_simulate": "You don't have an active mission!",
    }
    
    # First verify defer was called
    trace.assert_defer_called(ephemeral=True, thinking=True)
    
    # Then verify the response
    trace.assert_followup_send_called(content=expected_messages[command_name])

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
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="No missions are available for you right now.")

@pytest.mark.asyncio
async def test_mission_accept_no_missions(mission_commands_cog):
    """Test mission_accept when no missions are available."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = mission_commands_cog.mission_accept
    assert command is not None, "Mission accept command not found"
    
    # Mock empty mission board
    mission_commands_cog.mission_system.get_available_missions.return_value = []
    
    # Call command
    await command.callback(mission_commands_cog, mock_ctx, mission_number=1)
    
    # Verify error response sequence
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="No missions are available for you right now.")

@pytest.mark.asyncio
async def test_mission_complete_no_active_mission(mission_commands_cog):
    """Test mission_complete when no mission is active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = mission_commands_cog.mission_complete
    assert command is not None, "Mission complete command not found"
    
    # Mock no active mission
    mission_commands_cog.mission_system.get_active_mission.return_value = None
    
    # Call command
    await command.callback(mission_commands_cog, mock_ctx)
    
    # Verify error response sequence
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="You don't have an active mission!") 