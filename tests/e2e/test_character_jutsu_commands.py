import pytest
import discord
from unittest.mock import MagicMock, AsyncMock
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine

pytestmark = pytest.mark.asyncio

@pytest.fixture
def integration_services():
    # Use the real ServiceContainer for integration
    return ServiceContainer()

@pytest.fixture
def mock_e2e_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 1234567890
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    return interaction

def get_char_cog_and_system(services):
    mock_bot = MagicMock()
    mock_bot.services = services
    char_cog = CharacterCommands(mock_bot)
    char_system = services.character_system
    return char_cog, char_system

async def test_create_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.delete_character(mock_e2e_interaction.user.id)
    await char_cog.create.callback(char_cog, mock_e2e_interaction, name="TestUser", clan=None)
    mock_e2e_interaction.response.send_message.assert_awaited()
    char = await char_system.get_character(mock_e2e_interaction.user.id)
    assert char is not None
    assert char.name == "TestUser"

async def test_create_already_exists(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.create.callback(char_cog, mock_e2e_interaction, name="TestUser", clan=None)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "already have a character" in kwargs["embed"].description

async def test_profile_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.view_profile.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Profile" in kwargs["embed"].title

async def test_profile_no_character(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.delete_character(mock_e2e_interaction.user.id)
    await char_cog.view_profile.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "don't have a character" in kwargs["embed"].description

async def test_jutsu_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    char = await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    char.jutsu = ["Basic Attack"]
    await char_system.save_character(char)
    await char_cog.view_jutsu.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Jutsu" in kwargs["embed"].title

async def test_jutsu_no_character(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.delete_character(mock_e2e_interaction.user.id)
    await char_cog.view_jutsu.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "don't have a character" in kwargs["embed"].description

async def test_jutsu_info_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    # Assume "Basic Attack" is a valid jutsu in the system
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.jutsu_info.callback(char_cog, mock_e2e_interaction, jutsu_name="Basic Attack")
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Basic Attack" in kwargs["embed"].title

async def test_jutsu_info_invalid(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.jutsu_info.callback(char_cog, mock_e2e_interaction, jutsu_name="NotARealJutsu")
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "not a valid jutsu" in kwargs["embed"].description

async def test_unlock_jutsu_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    char = await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    # Assume "Basic Attack" is always unlockable
    await char_cog.unlock_jutsu.callback(char_cog, mock_e2e_interaction, jutsu_name="Basic Attack")
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Successfully learned" in kwargs["embed"].description

async def test_unlock_jutsu_invalid(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.unlock_jutsu.callback(char_cog, mock_e2e_interaction, jutsu_name="NotARealJutsu")
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "not a valid jutsu" in kwargs["embed"].description

async def test_auto_unlock_jutsu_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    char = await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.auto_unlock_jutsu.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Auto-unlocked" in kwargs["embed"].description or "No jutsu" in kwargs["embed"].description

async def test_progression_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    char = await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.view_progression.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    args, kwargs = mock_e2e_interaction.response.send_message.call_args
    assert "Progression" in kwargs["embed"].title

async def test_delete_character_success(integration_services, mock_e2e_interaction):
    char_cog, char_system = get_char_cog_and_system(integration_services)
    await char_system.create_character(mock_e2e_interaction.user.id, "TestUser", "Uchiha")
    await char_cog.delete_character.callback(char_cog, mock_e2e_interaction)
    mock_e2e_interaction.response.send_message.assert_awaited()
    char = await char_system.get_character(mock_e2e_interaction.user.id)
    assert char is None 