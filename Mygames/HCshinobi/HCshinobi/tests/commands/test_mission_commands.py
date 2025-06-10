"""Tests for mission commands."""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import discord
from discord import app_commands
from datetime import datetime, timedelta

from HCshinobi.commands.mission_commands import MissionCommands
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.character import Character

@pytest.fixture
def mission_system(character_system):
    """Create a mission system instance with a character system dependency."""
    # Pass the (mocked) character_system to the constructor
    # Assuming mission data is loaded separately or mocked within MissionSystem itself
    # for these command-level tests.
    return MissionSystem(character_system=character_system)

@pytest.fixture
def character_system():
    """Create a mocked character system for testing mission commands."""
    # CharacterSystem's get_character is sync, so the mock should be too.
    # Return MagicMock, not AsyncMock.
    mock_cs = MagicMock(spec=CharacterSystem)
    # get_character should return the mock character/None directly.
    mock_cs.get_character.return_value = None # Default to no character
    # If mission commands *also* call async methods like save/load/create,
    # those specific methods on the mock can be made AsyncMocks:
    mock_cs.save_character = AsyncMock(return_value=True)
    # mock_cs.load_characters = AsyncMock(return_value=[]) # If needed
    # mock_cs.create_character = AsyncMock(return_value=None) # If needed
    # Add mocks for other methods if needed by MissionCommands, e.g.:
    mock_cs.update_character = AsyncMock(return_value=True) # Assuming this might be needed later
    return mock_cs

@pytest.fixture
def mission_commands(mission_system, character_system):
    """Create mission commands cog instance for testing."""
    # Instantiate the Cog directly with its dependencies
    cog = MissionCommands(mission_system=mission_system, character_system=character_system)
    # Add a mock bot attribute if the cog methods expect self.bot
    cog.bot = AsyncMock()
    # Add mock services to the bot attribute if methods expect self.bot.services
    cog.bot.services = AsyncMock()
    cog.bot.services.mission_system = mission_system
    cog.bot.services.character_system = character_system
    # Mock other bot attributes if needed (e.g., get_cog, client)
    cog.bot.get_cog = Mock(return_value=None)
    cog.bot.client = MagicMock() # Added client mock based on usage in mission_board
    # Ensure the get_clan method on the mocked clan_data is an AsyncMock
    cog.bot.client.clan_data = MagicMock()
    cog.bot.client.clan_data.get_clan = AsyncMock(return_value=None) # Default to None, make it awaitable
    return cog

@pytest.mark.asyncio
async def test_mission_board_no_character(mission_commands):
    """Test mission board command when user has no character."""
    # Mock interaction
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock() # Mock the client attribute
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    # Mock character system (already mocked in fixture to return None by default)
    # mission_commands.character_system.get_character.return_value = None

    # Call command
    await mission_commands.mission_board(interaction=interaction)

    # Verify response
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "need a character" in kwargs.get("content", "") or "need a character" in args[0]
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_mission_board_with_character(mission_commands):
    """Test mission board command with an existing character."""
    # Mock interaction
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock() # Mock the client attribute
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    # Mock character
    character = MagicMock(spec=Character)
    character.name = "Test Character"
    character.level = 1
    character.clan = "Test Clan"
    mission_commands.character_system.get_character.return_value = character

    # Mock clan data retrieval (assuming it comes via interaction.client)
    mock_clan_info = {"rarity": "Common", "name": "Test Clan", "color": discord.Color.blue()} # Example data
    interaction.client.clan_data = MagicMock()
    # Ensure get_clan is an AsyncMock returning the desired info
    interaction.client.clan_data.get_clan = AsyncMock(return_value=mock_clan_info)

    # Mock mission system response
    mission_commands.mission_system.get_available_missions = Mock(return_value={}) # Return empty dict for simplicity

    # Call command
    await mission_commands.mission_board(interaction=interaction)

    # Verify response
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "Mission Board" in embed.title
    assert character.name in embed.description

@pytest.mark.asyncio
async def test_mission_accept_no_character(mission_commands):
    """Test mission accept command when user has no character."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    mission_commands.character_system.get_character.return_value = None

    await mission_commands.mission_accept(interaction=interaction, mission_id="D001")

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "need a character" in kwargs.get("content", "") or "need a character" in args[0]
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_mission_accept_success(mission_commands):
    """Test successful mission acceptance."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    # Ensure get_clan is an AsyncMock (returning None is fine if clan info isn't used for accept logic)
    interaction.client.clan_data = MagicMock()
    interaction.client.clan_data.get_clan = AsyncMock(return_value=None)

    character = MagicMock(spec=Character)
    character.id = str(interaction.user.id) # Ensure ID matches
    character.name = "Test Character"
    character.level = 1
    character.clan = "Test Clan"
    mission_commands.character_system.get_character.return_value = character

    # Mock mission system accept call - Use Mock, not AsyncMock, as the real method is sync
    mission_commands.mission_system.accept_mission = Mock(return_value=(True, "Mission D001 accepted!"))

    await mission_commands.mission_accept(interaction=interaction, mission_id="D001")

    # Verify accept_mission was called correctly - Use assert_called_once_with for sync mock
    mission_commands.mission_system.accept_mission.assert_called_once_with(str(interaction.user.id), "D001")

    # Verify response
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "Mission Accepted" in embed.title

@pytest.mark.asyncio
async def test_mission_progress_no_character(mission_commands):
    """Test mission progress command when user has no character."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    mission_commands.character_system.get_character.return_value = None

    await mission_commands.mission_progress(interaction=interaction)

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "need a character" in kwargs.get("content", "") or "need a character" in args[0]
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_mission_progress_with_character(mission_commands):
    """Test mission progress command with an existing character."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    # Ensure get_clan is an AsyncMock (returning None is fine if clan info isn't used for progress logic beyond display)
    interaction.client.clan_data = MagicMock()
    interaction.client.clan_data.get_clan = AsyncMock(return_value=None)

    character = MagicMock(spec=Character)
    character.name = "Test Character"
    character.level = 1
    character.clan = "Test Clan"
    mission_commands.character_system.get_character.return_value = character

    # Mock mission system get_active_missions
    mock_active_mission = MagicMock() # Mock a mission object if needed
    mock_active_mission.mission_id = "D001"
    mock_active_mission.title = "Lost Cat"
    mock_active_mission.time_remaining = timedelta(minutes=30) 
    mission_commands.mission_system.get_active_missions = Mock(return_value=[mock_active_mission])

    await mission_commands.mission_progress(interaction=interaction)

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "Active Missions" in embed.title
    assert character.name in embed.description

@pytest.mark.asyncio
async def test_mission_complete_no_character(mission_commands):
    """Test mission complete command when user has no character."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    mission_commands.character_system.get_character.return_value = None

    # Need mission_autocomplete fixture/mock if using autocomplete
    await mission_commands.mission_complete(interaction=interaction, mission_id="D001")

    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "need a character" in kwargs.get("content", "") or "need a character" in args[0]
    assert kwargs.get("ephemeral") is True

@pytest.mark.asyncio
async def test_mission_complete_success(mission_commands):
    """Test successful mission completion."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(id=12345)
    interaction.client = MagicMock()
    interaction.response = AsyncMock(spec=discord.InteractionResponse)

    # Ensure get_clan is an AsyncMock (returning None is fine if clan info isn't used for complete logic beyond display)
    interaction.client.clan_data = MagicMock()
    interaction.client.clan_data.get_clan = AsyncMock(return_value=None)

    character = MagicMock(spec=Character)
    character.id=str(interaction.user.id)
    character.name = "Test Character"
    character.level = 1
    character.clan = "Test Clan"
    mission_commands.character_system.get_character.return_value = character

    # Mock mission system complete_mission call - Use Mock, not AsyncMock
    rewards = {"exp": 100, "ryo": 500}
    mission_commands.mission_system.complete_mission = Mock(return_value=(True, "Mission D001 complete!", rewards))
    # Mock character update
    mission_commands.character_system.update_character = AsyncMock(return_value=True)

    await mission_commands.mission_complete(interaction=interaction, mission_id="D001")

    # Verify complete_mission was called correctly - Use assert_called_once_with for sync mock
    mission_commands.mission_system.complete_mission.assert_called_once_with(str(interaction.user.id), "D001")

    # Verify character update was called - REMOVED: Command doesn't call this directly
    # mission_commands.character_system.update_character.assert_awaited_once()

    # Verify response was sent with the correct embed
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "embed" in kwargs
    embed = kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert "Mission Complete" in embed.title 