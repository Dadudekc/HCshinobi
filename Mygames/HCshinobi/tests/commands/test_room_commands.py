"""Tests for room commands module."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands
from tests.utils.interaction_trace import InteractionTrace

from HCshinobi.bot.cogs.room import RoomCommands

class MockRoom:
    """Mock room object with required attributes."""
    def __init__(self, room_id, name, description, exits=None, contents=None, details=None):
        self.id = room_id
        self.name = name
        self.description = description
        self.exits = exits or []
        self.contents = contents or []
        self.details = details

    def get_available_exits(self):
        """Return available exits."""
        return self.exits

@pytest.fixture
def mock_bot():
    """Create a mock bot with required services."""
    bot = MagicMock()
    
    # Create async mocks for room system methods
    room_system = AsyncMock()
    mock_room = MockRoom(
        room_id="test_room",
        name="Test Room",
        description="A test room",
        exits=["north", "south"],
        contents=[],
        details="This is a test room for testing purposes."
    )
    room_system.get_current_room = AsyncMock(return_value=mock_room)
    room_system.get_room = AsyncMock(return_value=mock_room)
    room_system.move_character = AsyncMock(return_value=(True, "Moved successfully"))
    room_system.enter_room = AsyncMock(return_value=(True, "Entered room successfully"))
    room_system.leave_room = AsyncMock(return_value=(True, "Left room successfully"))
    room_system.get_room_contents = AsyncMock(return_value=[])
    room_system.get_characters_in_room = AsyncMock(return_value=[])

    # Create async mocks for character system methods
    character_system = AsyncMock()
    character_system.get_character = AsyncMock(return_value=MagicMock())

    # Set up bot services
    bot.services = MagicMock()
    bot.services.room_system = room_system
    bot.services.character_system = character_system
    
    return bot

@pytest.fixture
def room_commands_cog(mock_bot):
    """Create a RoomCommands cog instance for testing."""
    return RoomCommands(mock_bot)

@pytest.mark.asyncio
async def test_look_command(room_commands_cog):
    """Test the look command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.look
    assert command is not None, "Look command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx)
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True)

@pytest.mark.asyncio
async def test_move_command(room_commands_cog):
    """Test the move command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.move
    assert command is not None, "Move command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx, direction="north")
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True)

@pytest.mark.asyncio
async def test_enter_command(room_commands_cog):
    """Test the enter command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.enter
    assert command is not None, "Enter command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx, room_id="test_room")
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True)

@pytest.mark.asyncio
async def test_room_info_command(room_commands_cog):
    """Test the room_info command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.room_info
    assert command is not None, "Room info command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx, room_id="test_room")
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True)

@pytest.mark.asyncio
async def test_room_enter_command(room_commands_cog):
    """Test the room_enter command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.room_enter
    assert command is not None, "Room enter command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx, room_id="test_room")
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True)

@pytest.mark.asyncio
async def test_room_leave_command(room_commands_cog):
    """Test the room_leave command."""
    # Create interaction trace
    trace = InteractionTrace()
    mock_ctx = trace.create_mock_ctx()
    
    # Get the command from the cog
    command = room_commands_cog.room_leave
    assert command is not None, "Room leave command not found"
    
    # Call the command
    await command.callback(room_commands_cog, mock_ctx)
    
    # Verify interaction sequence
    trace.assert_defer_called(ephemeral=True)
    trace.assert_followup_send_called(embed=discord.Embed, ephemeral=True) 