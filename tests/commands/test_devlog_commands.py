"""Test cases for devlog commands."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from tests.utils.interaction_trace import InteractionTrace
import os
import aiofiles
from datetime import datetime
import discord
from discord import app_commands

@pytest.fixture
def mock_bot():
    """Create a mock bot with configured channels."""
    bot = AsyncMock()
    bot.config = AsyncMock()
    bot.config.bug_report_channel_id = 123456789
    bot.config.suggestion_channel_id = 987654321
    
    # Create mock channels
    bug_channel = AsyncMock()
    suggest_channel = AsyncMock()
    
    # Set up get_channel to return appropriate channels (sync, not async)
    bot.get_channel = Mock(side_effect=lambda channel_id: 
        bug_channel if channel_id == 123456789 else 
        suggest_channel if channel_id == 987654321 else 
        None
    )
    
    return bot

@pytest.fixture
def devlog_commands_cog(mock_bot):
    """Create a DevlogCommands cog instance with mocked bot."""
    from HCshinobi.bot.cogs.devlog import DevlogCommands
    return DevlogCommands(mock_bot)

@pytest.fixture
def mock_devlog_file(tmp_path):
    """Create a temporary devlog file for testing."""
    devlog_path = tmp_path / "devlog.md"
    devlog_content = """# HCShinobi Development Log

## Test Entry 1 (update)
*Added by TestUser on 2024-01-01 12:00:00*

This is a test entry.

## Test Entry 2 (feature)
*Added by TestUser on 2024-01-02 12:00:00*

This is another test entry.
"""
    with open(devlog_path, 'w', encoding='utf-8') as f:
        f.write(devlog_content)
    return devlog_path

@pytest.fixture
def mock_interaction():
    """Create a mock interaction for testing app commands."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 123456789
    interaction.user.name = "TestUser"
    interaction.user.display_name = "Test User"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 987654321
    
    # Set up response methods
    interaction.response = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    
    return interaction

# Define test cases for devlog commands
DEVLOG_COMMAND_CASES = [
    # (command_name, required_params)
    ("devlog", {}),
    ("bug_report", {"description": "Test bug report"}),
    ("suggest", {"suggestion": "Test suggestion"})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", DEVLOG_COMMAND_CASES)
async def test_devlog_commands(devlog_commands_cog, mock_bot, command_name, params):
    """Test all devlog commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(devlog_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Patch send for bug_report and suggest
    if command_name == "bug_report":
        # Get the channel that will be returned by get_channel
        bug_channel = mock_bot.get_channel(123456789)
        with patch.object(bug_channel, "send", new=AsyncMock(return_value=None)):
            await command.callback(devlog_commands_cog, mock_ctx, **params)
    elif command_name == "suggest":
        # Get the channel that will be returned by get_channel
        suggest_channel = mock_bot.get_channel(987654321)
        with patch.object(suggest_channel, "send", new=AsyncMock(return_value=None)):
            await command.callback(devlog_commands_cog, mock_ctx, **params)
    else:
        await command.callback(devlog_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    if command_name == "devlog":
        trace.assert_interaction_sequence(
            ("defer", {"ephemeral": True}),  # defer
            ("followup_send", {"content": None, "embed": discord.Embed, "ephemeral": True})  # followup_send with embed
        )
    elif command_name == "bug_report":
        trace.assert_interaction_sequence(
            ("defer", {"ephemeral": True}),
            ("followup_send", {"content": "✅ Your bug report has been submitted. Thank you for helping improve the bot!", "ephemeral": True})
        )
    else:  # suggest
        trace.assert_interaction_sequence(
            ("defer", {"ephemeral": True}),
            ("followup_send", {"content": "✅ Your suggestion has been submitted. Thank you for your input!", "ephemeral": True})
        )

@pytest.mark.asyncio
async def test_bug_report_no_channel(devlog_commands_cog):
    """Test bug_report when bug report channel is not configured."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Mock bot.config to return None for bug_report_channel_id
    devlog_commands_cog.bot.config.bug_report_channel_id = None
    
    # Call the command
    await devlog_commands_cog.bug_report.callback(devlog_commands_cog, mock_ctx, description="Test bug")
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),  # defer
        ("followup_send", {"content": "❌ Bug reporting is currently unavailable. Please try again later.", "ephemeral": True})  # followup_send
    )

@pytest.mark.asyncio
async def test_suggest_no_channel(devlog_commands_cog):
    """Test suggest when suggestion channel is not configured."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Mock bot.config to return None for suggestion_channel_id
    devlog_commands_cog.bot.config.suggestion_channel_id = None
    
    # Call the command
    await devlog_commands_cog.suggest.callback(devlog_commands_cog, mock_ctx, suggestion="Test suggestion")
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),  # defer
        ("followup_send", {"content": "❌ Suggestion submission is currently unavailable. Please try again later.", "ephemeral": True})  # followup_send
    )

@pytest.mark.asyncio
async def test_devlog_add(devlog_commands_cog, mock_devlog_file):
    """Test adding a new devlog entry."""
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    mock_ctx.user.guild_permissions.administrator = True
    
    # Patch the devlog file path
    with patch('HCshinobi.bot.cogs.devlog.DEVLOG_FILE_PATH', str(mock_devlog_file)):
        await devlog_commands_cog.devlog_add.callback(
            devlog_commands_cog,
            mock_ctx,
            title="New Test Entry",
            content="This is a new test entry.",
            category="feature"
        )
    
    # Verify the interaction sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),
        ("followup_send", {"content": "✅ Devlog entry added successfully!", "ephemeral": True})
    )
    
    # Verify the file was updated correctly
    with open(mock_devlog_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "## New Test Entry (feature)" in content
        assert "This is a new test entry." in content

@pytest.mark.asyncio
async def test_devlog_remove(devlog_commands_cog, mock_devlog_file):
    """Test removing a devlog entry."""
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    mock_ctx.user.guild_permissions.administrator = True
    
    # Patch the devlog file path
    with patch('HCshinobi.bot.cogs.devlog.DEVLOG_FILE_PATH', str(mock_devlog_file)):
        await devlog_commands_cog.devlog_remove.callback(
            devlog_commands_cog,
            mock_ctx,
            entry_number=1
        )
    
    # Verify the interaction sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),
        ("followup_send", {"content": "✅ Devlog entry removed successfully!", "ephemeral": True})
    )
    
    # Verify the file was updated correctly
    with open(mock_devlog_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "Test Entry 1" not in content  # Entry should be removed
        assert "Test Entry 2" in content  # Other entries should remain

@pytest.mark.asyncio
async def test_devlog_edit(devlog_commands_cog, mock_devlog_file):
    """Test editing a devlog entry."""
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    mock_ctx.user.guild_permissions.administrator = True
    
    # Patch the devlog file path
    with patch('HCshinobi.bot.cogs.devlog.DEVLOG_FILE_PATH', str(mock_devlog_file)):
        await devlog_commands_cog.devlog_edit.callback(
            devlog_commands_cog,
            mock_ctx,
            entry_number=1,
            new_title="Updated Entry",
            new_content="This is an updated entry.",
            new_category="bugfix"
        )
    
    # Verify the interaction sequence
    trace.assert_interaction_sequence(
        ("defer", {"ephemeral": True}),
        ("followup_send", {"content": "✅ Devlog entry edited successfully!", "ephemeral": True})
    )
    
    # Verify the file was updated correctly
    with open(mock_devlog_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "## Updated Entry (bugfix)" in content
        assert "This is an updated entry." in content
        assert "Test Entry 1" not in content

@pytest.mark.asyncio
async def test_devlog_commands_no_permission(devlog_commands_cog, mock_interaction):
    """Test that non-administrators cannot use admin commands."""
    mock_interaction.user.guild_permissions.administrator = False

    # Test devlog_add
    await devlog_commands_cog.devlog_add.callback(
        devlog_commands_cog,
        mock_interaction,
        title="Test",
        content="Test"
    )

    # Verify response
    mock_interaction.response.send_message.assert_awaited_once_with(
        "❌ You don't have permission to use this command.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_devlog_commands(devlog_commands_cog, mock_interaction):
    """Test the devlog command."""
    # Get the command from the cog
    command = devlog_commands_cog.devlog
    assert command is not None, "Devlog command not found"

    # Call the command
    await command.callback(devlog_commands_cog, mock_interaction)

    # Verify interaction sequence
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_awaited_once() 