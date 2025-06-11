"""Tests for devlog commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.devlog import DevlogCommands

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
def devlog_commands_cog(mock_bot):
    """Create a DevlogCommands cog instance for testing."""
    return DevlogCommands(mock_bot)

# Define test cases for devlog commands
DEVLOG_COMMAND_CASES = [
    # (command_name, required_params)
    ("devlog", {}),
    ("devlog_add", {"content": "Test devlog entry"}),
    ("devlog_remove", {"entry_id": 1}),
    ("devlog_edit", {"entry_id": 1, "content": "Updated devlog entry"}),
    ("devlog_list", {}),
    ("devlog_search", {"query": "test"}),
    ("devlog_filter", {"category": "feature"}),
    ("devlog_sort", {"sort_by": "date"}),
    ("devlog_export", {}),
    ("devlog_import", {"file": "devlog.json"}),
    ("devlog_clear", {}),
    ("devlog_backup", {}),
    ("devlog_restore", {"backup_id": "2023-01-01"}),
    ("devlog_stats", {}),
    ("devlog_archive", {"entry_id": 1}),
    ("devlog_unarchive", {"entry_id": 1}),
    ("devlog_pin", {"entry_id": 1}),
    ("devlog_unpin", {"entry_id": 1}),
    ("devlog_tag", {"entry_id": 1, "tag": "bug"}),
    ("devlog_untag", {"entry_id": 1, "tag": "bug"})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", DEVLOG_COMMAND_CASES)
async def test_devlog_commands(devlog_commands_cog, command_name, params):
    """Test all devlog commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(devlog_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(devlog_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
    )

# Edge case tests
@pytest.mark.asyncio
async def test_devlog_add_empty_content(devlog_commands_cog):
    """Test devlog_add with empty content."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = devlog_commands_cog.devlog_add
    assert command is not None, "Devlog add command not found"
    
    # Call with empty content
    await command.callback(devlog_commands_cog, mock_ctx, content="")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Devlog entry cannot be empty"}  # followup_send
    )

@pytest.mark.asyncio
async def test_devlog_remove_nonexistent(devlog_commands_cog):
    """Test devlog_remove with nonexistent entry."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = devlog_commands_cog.devlog_remove
    assert command is not None, "Devlog remove command not found"
    
    # Mock nonexistent entry
    devlog_commands_cog.entry_exists = AsyncMock(return_value=False)
    
    # Call with nonexistent entry
    await command.callback(devlog_commands_cog, mock_ctx, entry_id=999)
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Devlog entry not found: 999"}  # followup_send
    )

@pytest.mark.asyncio
async def test_devlog_edit_nonexistent(devlog_commands_cog):
    """Test devlog_edit with nonexistent entry."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = devlog_commands_cog.devlog_edit
    assert command is not None, "Devlog edit command not found"
    
    # Mock nonexistent entry
    devlog_commands_cog.entry_exists = AsyncMock(return_value=False)
    
    # Call with nonexistent entry
    await command.callback(devlog_commands_cog, mock_ctx, entry_id=999, content="Updated content")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Devlog entry not found: 999"}  # followup_send
    ) 