"""Test suite for room commands."""
import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch
from HCshinobi.bot.cogs.room import RoomCommands

@pytest.fixture
async def room_cog(mock_bot, mock_room_system, mock_character_system):
    """Create a RoomCommands instance with mocked dependencies."""
    cog = RoomCommands(mock_bot)
    cog.room_system = mock_room_system
    cog.character_system = mock_character_system
    return cog

@pytest.fixture
def mock_interaction():
    """Create a mock interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=123456789)
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_move_command_success(room_cog, mock_interaction, mock_room_system, mock_character_system):
    """Test successful room movement."""
    # Setup
    mock_character_system.get_character.return_value = MagicMock()
    mock_room_system.move_character.return_value = (True, "Moved successfully")
    mock_room_system.get_current_room.return_value = MagicMock(
        description="Test room",
        get_available_exits=lambda: ["north", "south"]
    )

    # Execute
    await room_cog.move(mock_interaction, "north")

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_room_system.move_character.assert_called_once_with("123456789", "north")
    mock_interaction.followup.send.assert_called_once()

@pytest.mark.asyncio
async def test_move_command_no_character(room_cog, mock_interaction, mock_character_system):
    """Test move command when user has no character."""
    # Setup
    mock_character_system.get_character.return_value = None

    # Execute
    await room_cog.move(mock_interaction, "north")

    # Verify
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You need a character to move around!",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_look_command_success(room_cog, mock_interaction, mock_room_system, mock_character_system):
    """Test successful room look command."""
    # Setup
    mock_character_system.get_character.return_value = MagicMock(name="Test Character")
    mock_room_system.get_current_room.return_value = MagicMock(
        name="Test Room",
        description="Test room description",
        details="Test room details",
        get_available_exits=lambda: ["north", "south"]
    )
    mock_room_system.get_room_contents.return_value = ["Item 1", "Item 2"]
    mock_room_system.get_characters_in_room.return_value = ["Other Character"]

    # Execute
    await room_cog.look(mock_interaction)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()

@pytest.mark.asyncio
async def test_whereami_command_success(room_cog, mock_interaction, mock_room_system, mock_character_system):
    """Test successful whereami command."""
    # Setup
    mock_character_system.get_character.return_value = MagicMock()
    mock_room_system.get_current_room.return_value = MagicMock(
        name="Test Room",
        description="Test room description",
        get_available_exits=lambda: ["north", "south"]
    )

    # Execute
    await room_cog.whereami(mock_interaction)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()

@pytest.mark.asyncio
async def test_enter_command_success(room_cog, mock_interaction, mock_room_system, mock_character_system):
    """Test successful room entry."""
    # Setup
    mock_character_system.get_character.return_value = MagicMock()
    mock_room_system.enter_room.return_value = (True, "Entered successfully")
    mock_room_system.get_current_room.return_value = MagicMock(
        description="Test room",
        get_available_exits=lambda: ["north", "south"]
    )

    # Execute
    await room_cog.enter(mock_interaction, "room123")

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_room_system.enter_room.assert_called_once_with("123456789", "room123")
    mock_interaction.followup.send.assert_called_once()

@pytest.mark.asyncio
async def test_exit_command_success(room_cog, mock_interaction, mock_room_system, mock_character_system):
    """Test successful room exit."""
    # Setup
    mock_character_system.get_character.return_value = MagicMock()
    mock_room_system.exit_room.return_value = (True, "Exited successfully")
    mock_room_system.get_current_room.return_value = MagicMock(
        description="Test room",
        get_available_exits=lambda: ["north", "south"]
    )

    # Execute
    await room_cog.exit(mock_interaction)

    # Verify
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_room_system.exit_room.assert_called_once_with("123456789")
    mock_interaction.followup.send.assert_called_once() 