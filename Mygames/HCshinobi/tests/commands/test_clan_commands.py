"""Tests for clan commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.clans import ClanCommands

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
def clan_commands_cog(mock_bot):
    """Create a ClanCommands cog instance for testing."""
    return ClanCommands(mock_bot)

# Define test cases for clan commands
CLAN_COMMAND_CASES = [
    # (command_name, required_params)
    ("clan_info", {"clan_name": "Test Clan"}),
    ("clan_create", {"clan_name": "Test Clan", "description": "Test Description"}),
    ("clan_join", {"clan_name": "Test Clan"}),
    ("clan_leave", {}),
    ("clan_disband", {}),
    ("clan_members", {"clan_name": "Test Clan"}),
    ("clan_ranks", {"clan_name": "Test Clan"}),
    ("clan_promote", {"member": "user", "rank": "officer"}),
    ("clan_demote", {"member": "user", "rank": "member"}),
    ("clan_kick", {"member": "user"}),
    ("clan_invite", {"member": "user"}),
    ("clan_accept", {"clan_name": "Test Clan"}),
    ("clan_decline", {"clan_name": "Test Clan"}),
    ("clan_war", {"target_clan": "Enemy Clan"}),
    ("clan_peace", {"target_clan": "Enemy Clan"}),
    ("clan_alliance", {"target_clan": "Ally Clan"}),
    ("clan_break_alliance", {"target_clan": "Ally Clan"}),
    ("clan_treasury", {"clan_name": "Test Clan"}),
    ("clan_donate", {"amount": 1000}),
    ("clan_withdraw", {"amount": 1000}),
    ("clan_logs", {"clan_name": "Test Clan"}),
    ("clan_settings", {"clan_name": "Test Clan"}),
    ("clan_announce", {"clan_name": "Test Clan", "message": "Test Announcement"}),
    ("clan_motd", {"clan_name": "Test Clan", "message": "Test MOTD"}),
    ("clan_banner", {"clan_name": "Test Clan", "url": "https://example.com/banner.png"}),
    ("clan_tag", {"clan_name": "Test Clan", "tag": "TEST"}),
    ("clan_color", {"clan_name": "Test Clan", "color": "#FF0000"}),
    ("clan_rename", {"clan_name": "Test Clan", "new_name": "New Clan Name"}),
    ("clan_description", {"clan_name": "Test Clan", "description": "New Description"})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", CLAN_COMMAND_CASES)
async def test_clan_commands(clan_commands_cog, command_name, params):
    """Test all clan commands using parametrized test cases."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = getattr(clan_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"
    
    # Call the command with parameters
    await command.callback(clan_commands_cog, mock_ctx, **params)
    
    # Verify interaction sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": None}  # followup_send
    )

# Edge case tests
@pytest.mark.asyncio
async def test_clan_create_duplicate_name(clan_commands_cog):
    """Test clan_create with duplicate clan name."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = clan_commands_cog.clan_create
    assert command is not None, "Clan create command not found"
    
    # Mock existing clan
    clan_commands_cog.clan_exists = AsyncMock(return_value=True)
    
    # Call with duplicate name
    await command.callback(clan_commands_cog, mock_ctx, clan_name="Existing Clan", description="Test Description")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Clan name already exists: Existing Clan"}  # followup_send
    )

@pytest.mark.asyncio
async def test_clan_join_nonexistent(clan_commands_cog):
    """Test clan_join with nonexistent clan."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = clan_commands_cog.clan_join
    assert command is not None, "Clan join command not found"
    
    # Mock nonexistent clan
    clan_commands_cog.clan_exists = AsyncMock(return_value=False)
    
    # Call with nonexistent clan
    await command.callback(clan_commands_cog, mock_ctx, clan_name="Nonexistent Clan")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Clan not found: Nonexistent Clan"}  # followup_send
    )

@pytest.mark.asyncio
async def test_clan_promote_nonexistent_member(clan_commands_cog):
    """Test clan_promote with nonexistent member."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    command = clan_commands_cog.clan_promote
    assert command is not None, "Clan promote command not found"
    
    # Mock nonexistent member
    clan_commands_cog.get_member = AsyncMock(return_value=None)
    
    # Call with nonexistent member
    await command.callback(clan_commands_cog, mock_ctx, member="nonexistent_user", rank="officer")
    
    # Verify error response sequence
    trace.assert_interaction_sequence(
        {"ephemeral": True, "thinking": True},  # defer
        {"content": "Member not found: nonexistent_user"}  # followup_send
    ) 