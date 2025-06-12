"""Tests for clan mission commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
from HCshinobi.bot.cogs.missions import MissionCommands
from HCshinobi.bot.cogs.clan_mission_commands import ClanMissionCommands
from HCshinobi.core.mission_system import MissionSystem
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from tests.utils.interaction_trace import InteractionTrace
from discord import app_commands

@pytest.fixture
def mock_clan_data_service():
    """Create a mock clan data service."""
    service = AsyncMock()
    service.get_clan = AsyncMock(return_value=MagicMock(name="Test Clan"))
    service.get_clan_missions = AsyncMock(return_value=[
        {"id": "1", "title": "Test Mission", "description": "Test Description"}
    ])
    return service

@pytest.fixture
def mock_character_system(mock_clan_data_service):
    """Create a mock character system."""
    system = CharacterSystem("test_data", mock_clan_data_service)
    system.get_character = AsyncMock(return_value=MagicMock(name="Test Character"))
    return system

@pytest.fixture
def mock_mission_system(mock_character_system):
    """Create a mock mission system."""
    system = MissionSystem(mock_character_system, "test_data")
    system.get_available_missions = AsyncMock(return_value=[
        {"id": "1", "title": "Test Mission", "description": "Test Description"}
    ])
    system.accept_mission = AsyncMock(return_value=True)
    system.complete_mission = AsyncMock(return_value=True)
    return system

@pytest.fixture
def mock_currency_system():
    """Create a mock currency system."""
    system = CurrencySystem("test_data")
    system.get_player_balance = AsyncMock(return_value=1000)
    system.set_player_balance = AsyncMock()
    system.add_balance_and_save = AsyncMock()
    return system

@pytest.fixture
async def character_system(mock_clan_data_service):
    """Create a mock character system."""
    system = CharacterSystem("test_data", mock_clan_data_service)
    system.get_character = AsyncMock(return_value={
        "name": "Test User",
        "rank": "Genin",
        "level": 5,
        "exp": 100,
        "ryo": 1000,
        "clan": "Uchiha"
    })
    return system

@pytest.fixture
async def currency_system():
    """Create a mock currency system."""
    system = CurrencySystem("test_data")
    system.add_currency = AsyncMock()
    return system

@pytest.fixture
async def mission_system(character_system, currency_system):
    """Create a mock mission system."""
    system = MissionSystem(character_system, "test_data", currency_system)
    await system.initialize()
    return system

@pytest.fixture
async def interaction_trace():
    """Create an interaction trace for testing."""
    return InteractionTrace()

@pytest.fixture
async def mock_ctx(interaction_trace):
    """Create a mock context."""
    return interaction_trace.create_mock_ctx()

@pytest.fixture
async def mock_bot(mock_character_system, mock_mission_system, mock_currency_system):
    """Create a mock bot with services."""
    bot = MagicMock()
    bot.services = MagicMock()
    bot.services.character_system = mock_character_system
    bot.services.mission_system = mock_mission_system
    bot.services.currency_system = mock_currency_system
    return bot

@pytest.fixture
async def mission_commands(mock_bot):
    """Create a MissionCommands cog with mocked dependencies."""
    cog = MissionCommands(mock_bot)
    return cog

@pytest.fixture
async def clan_mission_commands_cog(mock_bot):
    """Create a ClanMissionCommands cog with mocked dependencies."""
    # Create cog with bot
    cog = ClanMissionCommands(mock_bot)
    
    # Patch system initialization to use our mocks
    with patch('HCshinobi.bot.cogs.clan_mission_commands.CharacterSystem', return_value=mock_bot.services.character_system), \
         patch('HCshinobi.bot.cogs.clan_mission_commands.MissionSystem', return_value=mock_bot.services.mission_system):
        return cog

@pytest.fixture
async def mock_interaction():
    """Create a mock interaction object."""
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 123456789
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.mark.asyncio
async def test_clan_mission_board(clan_mission_commands_cog, mock_interaction):
    """Test the clan mission board command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.mission_board
    assert command is not None, "Mission board command not found"

    # Call the command
    await command.callback(clan_mission_commands_cog, mock_interaction)

    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_accept_clan_mission(clan_mission_commands_cog, mock_interaction):
    """Test the accept clan mission command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.accept_mission
    assert command is not None, "Accept mission command not found"

    # Call the command
    await command.callback(clan_mission_commands_cog, mock_interaction, mission_id="1")

    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_complete_clan_mission(clan_mission_commands_cog, mock_interaction):
    """Test the complete clan mission command."""
    # Get the command from the cog
    command = clan_mission_commands_cog.complete_mission
    assert command is not None, "Complete mission command not found"

    # Call the command
    await command.callback(clan_mission_commands_cog, mock_interaction)

    # Verify response
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_awaited_once() 