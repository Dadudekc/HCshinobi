import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Assuming ClanCommands is in HCshinobi.bot.cogs.clan_commands
from HCshinobi.bot.cogs.clan_commands import ClanCommands 
# Assuming ClanSystem/CharacterSystem are in HCshinobi.core
from HCshinobi.core.clan_system import ClanSystem # Adjust path if needed
from HCshinobi.core.character_system import CharacterSystem
# Assuming Character is in HCshinobi.core
from HCshinobi.core.character import Character 

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    return MagicMock()

@pytest.fixture
def mock_clan_system():
    """Fixture for a mocked ClanSystem."""
    mock = AsyncMock(spec=ClanSystem)
    mock.get_clan_info = AsyncMock()
    mock.get_player_clan = AsyncMock()
    mock.list_clans = AsyncMock()
    # Add mocks for create, join, leave, etc. if testing those commands
    return mock

@pytest.fixture
def mock_character_system():
    """Fixture for a mocked CharacterSystem."""
    mock = AsyncMock(spec=CharacterSystem)
    mock.get_character = AsyncMock()
    sample_char = MagicMock(spec=Character)
    sample_char.id = 123456789
    sample_char.name = "TestCharacter"
    sample_char.clan = None # Default to no clan
    mock.get_character.return_value = sample_char
    return mock

@pytest.fixture
def mock_interaction():
    """Fixture for a mocked discord.Interaction."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 123456789
    interaction.user.mention = "<@123456789>"
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    return interaction

@pytest.fixture
def clan_cog(mock_bot, mock_clan_system, mock_character_system):
    """Fixture for the ClanCommands cog instance."""
    # Use the actual cog class
    cog = ClanCommands(mock_bot, mock_clan_system, mock_character_system)
    return cog

# --- Test Cases --- 

# --- /clan Tests --- 

@pytest.mark.asyncio
async def test_clan_view_in_clan(clan_cog, mock_interaction, mock_clan_system, mock_character_system):
    """Test /clan when the user is in a clan."""
    user_id = str(mock_interaction.user.id)
    clan_name = "TestClan"
    clan_info_data = {'name': clan_name, 'members': [user_id], 'description': 'A test clan.', 'rarity': 'Common'}
    
    # Mock character being in the clan
    character = mock_character_system.get_character.return_value
    character.clan = clan_name 
    mock_clan_system.get_clan_info.return_value = clan_info_data

    # Call actual command callback (assuming /clan maps to view_clan)
    await clan_cog.view_clan.callback(clan_cog, mock_interaction, name=None)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_clan_system.get_clan_info.assert_awaited_once_with(clan_name)
    mock_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert clan_name in embed.title
    assert clan_info_data['description'] in embed.description
    assert str(len(clan_info_data['members'])) in embed.fields[0].value # Check member count
    # Add check for rarity field added in implementation
    assert clan_info_data['rarity'] in embed.fields[1].value

@pytest.mark.asyncio
async def test_clan_view_not_in_clan(clan_cog, mock_interaction, mock_character_system, mock_clan_system):
    """Test /clan when the user is not in a clan."""
    user_id = str(mock_interaction.user.id)
    # Mock character not being in a clan (default fixture state)
    character = mock_character_system.get_character.return_value
    character.clan = None 

    # Call actual command callback
    await clan_cog.view_clan.callback(clan_cog, mock_interaction, name=None)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_clan_system.get_clan_info.assert_not_awaited()
    # Check message sent by the command itself
    mock_interaction.response.send_message.assert_awaited_once_with("You are not currently in a clan.", ephemeral=True)

@pytest.mark.asyncio
async def test_clan_view_no_character(clan_cog, mock_interaction, mock_character_system, mock_clan_system):
    """Test /clan when the user has no character."""
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = None

    # Call actual command callback
    await clan_cog.view_clan.callback(clan_cog, mock_interaction, name=None)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    # Check message sent by the helper
    mock_interaction.response.send_message.assert_awaited_once_with("You need to create a character first using `/create`.", ephemeral=True)
    mock_clan_system.get_clan_info.assert_not_awaited()

# --- /clan_info Tests ---

@pytest.mark.asyncio
async def test_clan_info_success(clan_cog, mock_interaction, mock_clan_system):
    """Test /clan_info successfully retrieves and displays clan info."""
    target_clan_name = "TargetClan"
    clan_info_data = {'name': target_clan_name, 'members': ['1', '2'], 'description': 'Another test clan.', 'rarity': 'Rare'}
    mock_clan_system.get_clan_info.return_value = clan_info_data

    # Call actual command callback
    await clan_cog.clan_info.callback(clan_cog, mock_interaction, name=target_clan_name)

    mock_clan_system.get_clan_info.assert_awaited_once_with(target_clan_name)
    mock_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert target_clan_name in embed.title
    assert clan_info_data['description'] in embed.description
    assert str(len(clan_info_data['members'])) in embed.fields[0].value # Check member count
    assert clan_info_data['rarity'] in embed.fields[1].value # Check rarity

@pytest.mark.asyncio
async def test_clan_info_not_found(clan_cog, mock_interaction, mock_clan_system):
    """Test /clan_info when the specified clan does not exist."""
    target_clan_name = "NonExistentClan"
    mock_clan_system.get_clan_info.return_value = None # Clan not found

    # Call actual command callback
    await clan_cog.clan_info.callback(clan_cog, mock_interaction, name=target_clan_name)

    mock_clan_system.get_clan_info.assert_awaited_once_with(target_clan_name)
    mock_interaction.response.send_message.assert_awaited_once_with(f"Clan '{target_clan_name}' not found.", ephemeral=True)

# --- /clan_list Tests ---

@pytest.mark.asyncio
async def test_clan_list_success(clan_cog, mock_interaction, mock_clan_system):
    """Test /clan_list successfully displays a list of clans."""
    clan_list_data = [
        {'name': 'ClanA', 'rarity': 'Common', 'member_count': 5},
        {'name': 'ClanB', 'rarity': 'Rare', 'member_count': 10}
    ]
    mock_clan_system.list_clans.return_value = clan_list_data

    # Call actual command callback
    await clan_cog.list_clans.callback(clan_cog, mock_interaction)

    mock_clan_system.list_clans.assert_awaited_once()
    mock_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Clan List" in embed.title
    assert len(embed.fields) == len(clan_list_data)
    assert clan_list_data[0]['name'] in embed.fields[0].name
    assert clan_list_data[1]['name'] in embed.fields[1].name
    assert f"Rarity: {clan_list_data[0]['rarity']}" in embed.fields[0].value
    assert f"Members: {clan_list_data[1]['member_count']}" in embed.fields[1].value

@pytest.mark.asyncio
async def test_clan_list_empty(clan_cog, mock_interaction, mock_clan_system):
    """Test /clan_list when there are no clans."""
    mock_clan_system.list_clans.return_value = [] # No clans exist

    # Call actual command callback
    await clan_cog.list_clans.callback(clan_cog, mock_interaction)

    mock_clan_system.list_clans.assert_awaited_once()
    mock_interaction.response.send_message.assert_awaited_once_with("There are no clans formed yet.", ephemeral=True)

# TODO: Add tests for other clan commands (create, join, leave, etc.) if they exist 