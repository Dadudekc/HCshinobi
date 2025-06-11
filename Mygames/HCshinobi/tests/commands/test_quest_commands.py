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
def quest_commands_cog(mock_bot):
    """Create a MissionCommands cog instance for testing."""
    mission_system = MagicMock()
    character_system = MagicMock()
    return MissionCommands(mock_bot, mission_system, character_system)

# Define test cases for quest commands
QUEST_COMMAND_CASES = [
    # (command_name, required_params)
    ("quests", {}),
    ("accept_quest", {"quest_id": "test_quest"}),
    ("active_quests", {}),
    ("complete_quest", {"quest_id": "test_quest"}),
    ("abandon_quest", {"quest_id": "test_quest"}),
    ("quest_history", {}),
    ("quest_info", {"quest_id": "test_quest"}),
    ("quest_progress", {"quest_id": "test_quest"}),
    ("quest_rewards", {"quest_id": "test_quest"}),
    ("quest_requirements", {"quest_id": "test_quest"}),
    ("quest_difficulty", {"quest_id": "test_quest"}),
    ("quest_time", {"quest_id": "test_quest"}),
    ("quest_location", {"quest_id": "test_quest"}),
    ("quest_npc", {"quest_id": "test_quest"}),
    ("quest_items", {"quest_id": "test_quest"}),
    ("quest_skills", {"quest_id": "test_quest"}),
    ("quest_level", {"quest_id": "test_quest"}),
    ("quest_type", {"quest_id": "test_quest"}),
    ("quest_category", {"quest_id": "test_quest"}),
    ("quest_tags", {"quest_id": "test_quest"})
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
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
    )

# Edge case tests
@pytest.mark.asyncio
async def test_accept_quest_nonexistent(quest_commands_cog):
    """Test accept_quest with nonexistent quest."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.accept_quest
    assert command is not None, "Accept quest command not found"
    
    # Mock nonexistent quest
    quest_commands_cog.quest_exists = AsyncMock(return_value=False)
    
    # Call with nonexistent quest
    await command.callback(quest_commands_cog, mock_ctx, quest_id="nonexistent_quest")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Quest not found: nonexistent_quest"}  # followup_send
    )

@pytest.mark.asyncio
async def test_complete_quest_not_active(quest_commands_cog):
    """Test complete_quest when quest is not active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.complete_quest
    assert command is not None, "Complete quest command not found"
    
    # Mock quest not active
    quest_commands_cog.is_quest_active = AsyncMock(return_value=False)
    
    # Call with inactive quest
    await command.callback(quest_commands_cog, mock_ctx, quest_id="inactive_quest")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Quest is not active: inactive_quest"}  # followup_send
    )

@pytest.mark.asyncio
async def test_abandon_quest_not_active(quest_commands_cog):
    """Test abandon_quest when quest is not active."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = quest_commands_cog.abandon_quest
    assert command is not None, "Abandon quest command not found"
    
    # Mock quest not active
    quest_commands_cog.is_quest_active = AsyncMock(return_value=False)
    
    # Call with inactive quest
    await command.callback(quest_commands_cog, mock_ctx, quest_id="inactive_quest")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Quest is not active: inactive_quest"}  # followup_send
    ) 