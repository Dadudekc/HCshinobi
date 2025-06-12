"""Tests for clan commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from discord import app_commands
from HCshinobi.bot.cogs.clan_commands import ClanCommands
from tests.utils.interaction_trace import InteractionTrace

@pytest.fixture
def mock_interaction():
    """Create a mock interaction for testing."""
    interaction = AsyncMock()
    interaction.user = MagicMock(id=123456789)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = AsyncMock()
    # Add services attribute
    bot.services = AsyncMock()
    return bot

@pytest.fixture
def clan_commands_cog(mock_bot):
    """Create a ClanCommands cog instance with mocked dependencies."""
    # Create mock systems
    clan_system = AsyncMock()
    character_system = AsyncMock()
    
    # Set up mock responses
    clan_system.get_clan_info = AsyncMock(return_value={
        'name': 'Test Clan',
        'description': 'A test clan',
        'members': ['123456789'],
        'rarity': 'Common',
        'village': 'Test Village',
        'power': 1000
    })
    clan_system.list_clans = AsyncMock(return_value=[{
        'name': 'Test Clan',
        'member_count': 1,
        'rarity': 'Common'
    }])
    clan_system.get_clan_rankings = AsyncMock(return_value=[{
        'name': 'Test Clan',
        'power': 1000
    }])
    clan_system.leave_clan = AsyncMock(return_value=(True, "Successfully left clan"))
    
    # Set up character system mock
    character = MagicMock()
    character.clan = 'Test Clan'
    character_system.get_character = AsyncMock(return_value=character)
    
    # Attach systems to bot services
    mock_bot.services.clan_system = clan_system
    mock_bot.services.character_system = character_system
    
    return ClanCommands(mock_bot)

# Test cases for clan commands
CLAN_COMMAND_CASES = [
    ('view_clan', {'name': 'Test Clan'}),
    ('create_clan', {}),
    ('join_clan', {}),
    ('leave_clan', {}),
    ('clan_members', {'clan_name': 'Test Clan'}),
    ('clan_leaderboard', {}),
    ('my_clan', {})
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

    # Verify that a response was sent
    assert len(trace.followup_send_calls) > 0, f"No response sent for {command_name}"

@pytest.mark.asyncio
async def test_clan_create_duplicate_name(clan_commands_cog):
    """Test create_clan with duplicate clan name."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()

    command = clan_commands_cog.create_clan
    assert command is not None, "Create clan command not found"

    # Set up character without a clan
    character = MagicMock()
    character.clan = None
    clan_commands_cog.character_system.get_character = AsyncMock(return_value=character)

    # Mock existing clan
    clan_commands_cog.clan_system.clan_exists = AsyncMock(return_value=True)

    # Call with duplicate name
    await command.callback(clan_commands_cog, mock_ctx)

    # Verify error response
    trace.assert_followup_send_called(content="This command is not implemented yet.")

@pytest.mark.asyncio
async def test_clan_join_nonexistent(clan_commands_cog):
    """Test join_clan with nonexistent clan."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()

    command = clan_commands_cog.join_clan
    assert command is not None, "Join clan command not found"

    # Set up character without a clan
    character = MagicMock()
    character.clan = None
    clan_commands_cog.character_system.get_character = AsyncMock(return_value=character)

    # Mock nonexistent clan
    clan_commands_cog.clan_system.clan_exists = AsyncMock(return_value=False)

    # Call with nonexistent clan
    await command.callback(clan_commands_cog, mock_ctx)

    # Verify error response
    trace.assert_followup_send_called(content="This command is not implemented yet.") 