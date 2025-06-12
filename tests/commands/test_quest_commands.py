"""Tests for quest commands module."""

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
def quest_commands_cog(mock_bot):
    """Create a MissionCommands cog instance for testing."""
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
    mock_bot.services = MagicMock()
    mock_bot.services.mission_system = mission_system
    mock_bot.services.character_system = character_system
    
    # Create and return the cog
    cog = MissionCommands(mock_bot)
    cog.mission_system = mission_system
    cog.character_system = character_system
    return cog

# Define test cases for quest commands
QUEST_COMMAND_CASES = [
    # (command_name, required_params)
    ("mission_board", {}),
    ("mission_accept", {"mission_number": 1}),
    ("mission_progress", {}),
    ("mission_roll", {}),
    ("mission_complete", {}),
    ("mission_abandon", {}),
    ("mission_history", {})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", QUEST_COMMAND_CASES)
async def test_quest_commands(quest_commands_cog, command_name, params):
    """Test all quest commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(quest_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(quest_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    expected_messages = {
        "mission_board": "No missions are available for you right now. Try ranking up or leveling up!",
        "mission_accept": "No missions are available for you right now.",
        "mission_progress": "You don't have an active mission!",
        "mission_roll": "You don't have an active mission!",
        "mission_complete": "You don't have an active mission!",
        "mission_abandon": "You don't have an active mission!",
        "mission_history": "You haven't completed any missions yet!",
    }
    
    # First verify defer was called
    trace.assert_defer_called(ephemeral=True, thinking=True)
    
    # Then verify the response
    trace.assert_followup_send_called(content=expected_messages[command_name])

@pytest.mark.asyncio
async def test_accept_quest_nonexistent(quest_commands_cog):
    """Test mission_accept with nonexistent quest."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.mission_accept
    assert command is not None, "Mission accept command not found"
    
    # Mock nonexistent quest
    quest_commands_cog.mission_system.get_available_missions = AsyncMock(return_value=[])
    
    # Call with nonexistent quest
    await command.callback(quest_commands_cog, mock_ctx, mission_number=1)
    
    # Verify error response sequence
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="No missions are available for you right now.")

@pytest.mark.asyncio
async def test_complete_quest_not_active(quest_commands_cog):
    """Test mission_complete when quest is not active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.mission_complete
    assert command is not None, "Mission complete command not found"
    
    # Mock quest not active
    quest_commands_cog.mission_system.get_active_mission = AsyncMock(return_value=None)
    
    # Call with inactive quest
    await command.callback(quest_commands_cog, mock_ctx)
    
    # Verify error response sequence
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="You don't have an active mission!")

@pytest.mark.asyncio
async def test_abandon_quest_not_active(quest_commands_cog):
    """Test mission_abandon when quest is not active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.mission_abandon
    assert command is not None, "Mission abandon command not found"
    
    # Mock quest not active
    quest_commands_cog.mission_system.get_active_mission = AsyncMock(return_value=None)
    
    # Call with inactive quest
    await command.callback(quest_commands_cog, mock_ctx)
    
    # Verify error response sequence
    trace.assert_defer_called(ephemeral=True, thinking=True)
    trace.assert_followup_send_called(content="You don't have an active mission!") 