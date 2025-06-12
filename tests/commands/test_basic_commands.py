"""Tests for basic commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.character_commands import CharacterCommands

@pytest.fixture
def mock_ctx():
    """Create a mock context with all required attributes."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.author = AsyncMock(spec=discord.Member)
    ctx.author.id = 123456789
    ctx.author.display_name = "Test User"
    ctx.user = AsyncMock(spec=discord.User)
    ctx.user.id = 123456789
    ctx.user.display_avatar = MagicMock(url="https://cdn.discordapp.com/avatar.png")
    ctx.send = AsyncMock()
    ctx.response = AsyncMock()
    ctx.response.send_message = AsyncMock()
    ctx.response.defer = AsyncMock()
    ctx.followup = AsyncMock()
    ctx.followup.send = AsyncMock()
    return ctx

@pytest.fixture
def character_commands_cog(mock_bot):
    """Create a CharacterCommands cog instance with mocked dependencies."""
    cog = CharacterCommands(mock_bot)
    cog.character_system = AsyncMock()
    cog.progression_engine = AsyncMock()
    cog.progression_engine.get_available_specializations.return_value = ["ninja", "samurai", "monk"]  # Set return value for specializations
    cog.clan_data = AsyncMock()
    return cog

@pytest.mark.asyncio
async def test_inventory_command(character_commands_cog, mock_ctx):
    """Test the inventory command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.inventory = {"item1": 1, "item2": 2}
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.inventory.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_jutsu_command(character_commands_cog, mock_ctx):
    """Test the jutsu command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.jutsu = ["jutsu1", "jutsu2"]
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.jutsu.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_status_command(character_commands_cog, mock_ctx):
    """Test the status command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.hp = 100
    mock_character.chakra = 100
    mock_character.stamina = 100
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.status.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_profile_command(character_commands_cog, mock_ctx):
    """Test the profile command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.level = 1
    mock_character.stats = {"strength": 10, "speed": 10}
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.profile.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True, thinking=True)

@pytest.mark.asyncio
async def test_stats_command(character_commands_cog, mock_ctx):
    """Test the stats command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.level = 1
    mock_character.stats = {"strength": 10, "speed": 10}
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.stats.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_achievements_command(character_commands_cog, mock_ctx):
    """Test the achievements command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.achievements = ["achievement1", "achievement2"]
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.achievements.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_titles_command(character_commands_cog, mock_ctx):
    """Test the titles command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.titles = ["title1", "title2"]
    character_commands_cog.character_system.get_character.return_value = mock_character

    # Call the command
    await character_commands_cog.titles.callback(character_commands_cog, mock_ctx)

    # Verify the response
    mock_ctx.response.defer.assert_called_once_with(ephemeral=True)

@pytest.mark.asyncio
async def test_specialize_command(character_commands_cog, mock_ctx):
    """Test the specialize command."""
    # Setup mock character
    mock_character = MagicMock()
    mock_character.name = "Test Character"
    mock_character.level = 10  # High enough level to specialize
    mock_character.specialization = None
    character_commands_cog.character_system.get_character.return_value = mock_character
    
    # Setup available specializations as an async mock
    available_specs = ["ninja", "samurai", "monk"]
    character_commands_cog.progression_engine.get_available_specializations = AsyncMock(return_value=available_specs)

    # Call the command
    await character_commands_cog.specialize.callback(character_commands_cog, mock_ctx)

    # Verify the response - only check for ephemeral=True
    mock_ctx.response.defer.assert_called_once()
    args, kwargs = mock_ctx.response.defer.call_args
    assert kwargs.get('ephemeral') is True

# Update the parametrized test
IMPLEMENTED_COMMAND_CASES = [
    ("profile", {}),
    ("stats", {}),
    ("inventory", {}),
    ("jutsu", {}),
    ("status", {}),
    ("achievements", {}),
    ("titles", {}),
    ("specialize", {})
]

@pytest.mark.asyncio
@pytest.mark.parametrize("command_name,params", IMPLEMENTED_COMMAND_CASES)
async def test_basic_commands(character_commands_cog, command_name, params):
    """Test all implemented commands using parametrized test cases."""
    # Create mock context
    mock_ctx = AsyncMock()
    mock_ctx.user = AsyncMock(spec=discord.User)
    mock_ctx.user.id = 123456789
    mock_ctx.user.display_avatar = MagicMock(url="https://cdn.discordapp.com/avatar.png")
    mock_ctx.response = AsyncMock()
    mock_ctx.followup = AsyncMock()

    # Get the command from the cog
    command = getattr(character_commands_cog, command_name)
    assert command is not None, f"{command_name} command not found"

    # Call the command with parameters
    await command.callback(character_commands_cog, mock_ctx, **params)

    # Verify interaction sequence - only check for ephemeral=True
    mock_ctx.response.defer.assert_called_once()
    args, kwargs = mock_ctx.response.defer.call_args
    assert kwargs.get('ephemeral') is True
    mock_ctx.followup.send.assert_called_once() 