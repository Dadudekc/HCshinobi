"""Tests for the HCshinobi command system."""
import pytest
import discord
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from HCshinobi.commands.character_commands_v2 import CharacterCommands
from HCshinobi.commands.announcement_commands import AnnouncementCommands
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.character import Character

@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction."""
    interaction = AsyncMock()
    interaction.user = Mock()
    interaction.user.id = 123456789
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_client():
    """Create a mock Discord client."""
    client = Mock(spec=discord.Client)
    client.announcement_channel_id = 987654321
    return client

@pytest.fixture
def character_system():
    """Create a character system instance."""
    return CharacterSystem()

@pytest.fixture
def clan_data():
    """Create a clan data instance."""
    return ClanData()

@pytest.fixture
def character_commands():
    """Create a character commands instance."""
    character_system = Mock()
    clan_data = Mock()
    return CharacterCommands(character_system=character_system, clan_data=clan_data)

@pytest.fixture
def announcement_commands():
    """Create an announcement commands instance."""
    client = Mock()
    return AnnouncementCommands(client=client)

def test_assign_clan_random(character_commands, mock_interaction):
    """Test random clan assignment."""
    # Mock the clan data
    clan_data = {
        'name': 'Uchiha',
        'rarity': 'Legendary',
        'bonuses': {
            'hp': 50,
            'chakra': 50,
            'strength': 10,
            'defense': 10,
            'speed': 10
        },
        'starting_jutsu': ['Fireball Jutsu']
    }
    character_commands.clan_data.get_random_clan = Mock(return_value=clan_data)
    character_commands.clan_data.get_clan = Mock(return_value=clan_data)

    # Mock character system
    character = Character(
        name='Test User',
        clan=None,
        level=1,
        exp=0,
        hp=100,
        chakra=100,
        strength=10,
        defense=10,
        speed=10,
        jutsu=[]
    )
    character_commands.character_system.get_character = Mock(return_value=character)
    character_commands.character_system.update_character = Mock(return_value=True)

    # Run the command
    asyncio.run(character_commands.assign_clan(mock_interaction))

    # Verify the response
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args[1]
    assert isinstance(call_args['embed'], discord.Embed)
    assert call_args['ephemeral'] is True
    assert "Uchiha" in call_args['embed'].description
    assert "Legendary" in call_args['embed'].title

def test_assign_clan_specific(character_commands, mock_interaction):
    """Test specific clan assignment."""
    # Mock the clan data
    clan_data = {
        'name': 'Hyuga',
        'rarity': 'Rare',
        'bonuses': {
            'hp': 30,
            'chakra': 30,
            'strength': 5,
            'defense': 5,
            'speed': 5
        },
        'starting_jutsu': ['Byakugan']
    }
    character_commands.clan_data.get_clan = Mock(return_value=clan_data)

    # Mock character system
    character = Character(
        name='Test User',
        clan=None,
        level=1,
        exp=0,
        hp=100,
        chakra=100,
        strength=10,
        defense=10,
        speed=10,
        jutsu=[]
    )
    character_commands.character_system.get_character = Mock(return_value=character)
    character_commands.character_system.update_character = Mock(return_value=True)

    # Run the command
    asyncio.run(character_commands.assign_clan(mock_interaction, clan="Hyuga"))

    # Verify the response
    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args[1]
    assert isinstance(call_args['embed'], discord.Embed)
    assert call_args['ephemeral'] is True
    assert "Hyuga" in call_args['embed'].description
    assert "Rare" in call_args['embed'].title

def test_assign_clan_no_character(character_commands, mock_interaction):
    """Test clan assignment when user has no character."""
    # Mock character system to return None
    character_commands.character_system.get_character = Mock(return_value=None)

    # Run the command
    asyncio.run(character_commands.assign_clan(mock_interaction))

    # Verify the error message
    mock_interaction.followup.send.assert_called_once_with(
        "❌ You don't have a character yet! Use `/create` to create one.",
        ephemeral=True
    )

def test_assign_clan_already_has_clan(character_commands, mock_interaction):
    """Test clan assignment when character already has a clan."""
    # Mock character system
    character = Character(
        name='Test User',
        clan='Uchiha',
        level=1,
        exp=0,
        hp=100,
        chakra=100,
        strength=10,
        defense=10,
        speed=10,
        jutsu=[]
    )
    character_commands.character_system.get_character = Mock(return_value=character)

    # Run the command
    asyncio.run(character_commands.assign_clan(mock_interaction))

    # Verify the error message
    mock_interaction.followup.send.assert_called_once_with(
        "❌ Your character already belongs to the Uchiha clan!",
        ephemeral=True
    )

def test_countdown_command(announcement_commands, mock_interaction):
    """Test the countdown command."""
    # Mock the guild and channel
    mock_guild = Mock()
    mock_channel = Mock()
    mock_interaction.guild = mock_guild
    mock_guild.get_channel.return_value = mock_channel

    # Run the command
    asyncio.run(announcement_commands.countdown(mock_interaction, minutes=5, reason="Test maintenance"))

    # Verify the response
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once() 