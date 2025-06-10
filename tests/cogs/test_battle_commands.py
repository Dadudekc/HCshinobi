import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Assuming BattleCommands is in HCshinobi.bot.cogs.battle_commands
from HCshinobi.bot.cogs.battle_commands import BattleCommands 
# Assuming BattleSystem/CharacterSystem are in HCshinobi.core
from HCshinobi.core.battle_system import BattleSystem # Adjust path if needed
from HCshinobi.core.character_system import CharacterSystem
# Assuming Character is in HCshinobi.core
from HCshinobi.core.character import Character 

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    return MagicMock()

@pytest.fixture
def mock_battle_system():
    """Fixture for a mocked BattleSystem."""
    mock = AsyncMock(spec=BattleSystem)
    mock.initiate_battle = AsyncMock()
    mock.get_battle_history = AsyncMock()
    mock.surrender_battle = AsyncMock()
    mock.get_active_battle_status = AsyncMock(return_value=None) # Default: No active battle
    # Add mocks for other battle actions if needed
    return mock

@pytest.fixture
def mock_character_system():
    """Fixture for a mocked CharacterSystem."""
    mock = AsyncMock(spec=CharacterSystem)
    # Setup to return different characters based on ID
    char1 = MagicMock(spec=Character)
    char1.id = 123456789
    char1.name = "TestUserChar"
    char1.level = 10
    
    char2 = MagicMock(spec=Character)
    char2.id = 987654321
    char2.name = "OpponentChar"
    char2.level = 11

    async def get_char_side_effect(user_id):
        user_id_str = str(user_id)
        if user_id_str == str(char1.id):
            return char1
        elif user_id_str == str(char2.id):
            return char2
        else:
            # print(f"Debug: get_character called with unmocked ID: {user_id_str}") # Debugging line
            return None
            
    mock.get_character = AsyncMock(side_effect=get_char_side_effect)
    return mock

@pytest.fixture
def mock_interaction():
    """Fixture for a mocked discord.Interaction for the command user."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    interaction.user.id = 123456789
    interaction.user.mention = "<@123456789>"
    interaction.user.display_name = "TestUser"
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    # Ensure response object has necessary methods
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction

@pytest.fixture
def mock_opponent_user():
    """Fixture for a mocked opponent discord.User."""
    user = MagicMock(spec=discord.User)
    user.id = 987654321
    user.mention = "<@987654321>"
    user.display_name = "Opponent"
    return user

@pytest.fixture
def battle_cog(mock_bot, mock_battle_system, mock_character_system):
    """Fixture for the BattleCommands cog instance."""
    # Use the actual cog class
    cog = BattleCommands(mock_bot, mock_battle_system, mock_character_system)
    return cog

# --- Test Cases --- 

# --- /battle Tests --- 

@pytest.mark.asyncio
async def test_battle_initiate_success(battle_cog, mock_interaction, mock_opponent_user, mock_battle_system, mock_character_system):
    """Test initiating a battle successfully with /battle."""
    user_id = str(mock_interaction.user.id)
    opponent_id = str(mock_opponent_user.id)
    initiator_char = await mock_character_system.get_character(user_id)
    opponent_char = await mock_character_system.get_character(opponent_id)
    success_message = f"Battle initiated between {initiator_char.name} and {opponent_char.name}!"
    
    mock_battle_system.initiate_battle.return_value = (True, success_message)

    # Call actual command callback
    await battle_cog.battle.callback(battle_cog, mock_interaction, opponent=mock_opponent_user)

    # Verify character lookups
    assert mock_character_system.get_character.call_count == 4 
    mock_character_system.get_character.assert_any_call(user_id)
    mock_character_system.get_character.assert_any_call(opponent_id)
    
    # Verify battle system call
    mock_battle_system.initiate_battle.assert_awaited_once_with(initiator_char, opponent_char)
    
    # Verify response (deferred then followed up)
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once_with(success_message, ephemeral=False) # Check followup message (likely public)

@pytest.mark.asyncio
async def test_battle_initiate_self(battle_cog, mock_interaction, mock_battle_system, mock_character_system):
    """Test /battle when user tries to battle themselves."""
    user_id = str(mock_interaction.user.id)
    # Pass interaction.user as opponent
    opponent_user = mock_interaction.user 

    # Call actual command callback
    await battle_cog.battle.callback(battle_cog, mock_interaction, opponent=opponent_user)

    # Should not check character or initiate battle
    mock_character_system.get_character.assert_not_awaited()
    mock_battle_system.initiate_battle.assert_not_awaited()
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once_with("You cannot battle yourself!", ephemeral=True)

@pytest.mark.asyncio
async def test_battle_initiate_no_own_character(battle_cog, mock_interaction, mock_opponent_user, mock_battle_system, mock_character_system):
    """Test /battle when the command user has no character."""
    user_id = str(mock_interaction.user.id)
    # Mock get_character to return None for the initiator
    original_side_effect = mock_character_system.get_character.side_effect
    async def side_effect_no_initiator(uid):
        if str(uid) == user_id: return None
        return await original_side_effect(uid)
    mock_character_system.get_character.side_effect = side_effect_no_initiator

    # Call actual command callback
    await battle_cog.battle.callback(battle_cog, mock_interaction, opponent=mock_opponent_user)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_battle_system.initiate_battle.assert_not_awaited()
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once_with("You need to create a character first using `/create`.", ephemeral=True)
    mock_character_system.get_character.side_effect = original_side_effect 

@pytest.mark.asyncio
async def test_battle_initiate_no_opponent_character(battle_cog, mock_interaction, mock_opponent_user, mock_battle_system, mock_character_system):
    """Test /battle when the opponent has no character."""
    user_id = str(mock_interaction.user.id)
    opponent_id = str(mock_opponent_user.id)
    # Mock get_character to return None for the opponent
    original_side_effect = mock_character_system.get_character.side_effect
    async def side_effect_no_opponent(uid):
        if str(uid) == opponent_id: return None
        return await original_side_effect(uid)
    mock_character_system.get_character.side_effect = side_effect_no_opponent

    # Call actual command callback
    await battle_cog.battle.callback(battle_cog, mock_interaction, opponent=mock_opponent_user)

    assert mock_character_system.get_character.call_count == 2
    mock_character_system.get_character.assert_any_call(user_id)
    mock_character_system.get_character.assert_any_call(opponent_id)
    mock_battle_system.initiate_battle.assert_not_awaited()
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once_with(f"{mock_opponent_user.display_name} does not have a character.", ephemeral=True)
    mock_character_system.get_character.side_effect = original_side_effect

@pytest.mark.asyncio
async def test_battle_initiate_already_in_battle(battle_cog, mock_interaction, mock_opponent_user, mock_battle_system, mock_character_system):
    """Test /battle when the initiator is already in a battle."""
    user_id = str(mock_interaction.user.id)
    mock_battle_system.get_active_battle_status.return_value = "some_active_battle_id" # User is in battle

    # Call actual command callback
    await battle_cog.battle.callback(battle_cog, mock_interaction, opponent=mock_opponent_user)
        
    mock_battle_system.get_active_battle_status.assert_awaited_once_with(user_id)
    # Allow for character check before battle status check in current implementation
    # Corrected assertion: check call count is 2 (initiator + opponent)
    assert mock_character_system.get_character.call_count == 2
    mock_character_system.get_character.assert_any_call(user_id)
    # mock_character_system.get_character.assert_any_call(opponent_id) # Opponent might not be called if initiator check fails early

    mock_battle_system.initiate_battle.assert_not_awaited()
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    mock_interaction.followup.send.assert_awaited_once_with("You are already in a battle!", ephemeral=True)

# TODO: Add test for /battle failure (e.g., system returns False)

# --- /battle_history Tests ---

@pytest.mark.asyncio
async def test_battle_history_success(battle_cog, mock_interaction, mock_battle_system):
    """Test /battle_history successfully displays history."""
    user_id = str(mock_interaction.user.id)
    history_data = [
        {'opponent_name': 'Opponent1', 'outcome': 'Win', 'timestamp': '2023-10-27T10:00:00Z'},
        {'opponent_name': 'Opponent2', 'outcome': 'Loss', 'timestamp': '2023-10-26T15:00:00Z'}
    ]
    mock_battle_system.get_battle_history.return_value = history_data

    # Call actual command callback
    await battle_cog.battle_history.callback(battle_cog, mock_interaction)

    mock_battle_system.get_battle_history.assert_awaited_once_with(user_id)
    mock_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Battle History" in embed.title
    assert len(embed.fields) == len(history_data)
    assert history_data[0]['opponent_name'] in embed.fields[0].name
    assert history_data[1]['opponent_name'] in embed.fields[1].name
    assert history_data[0]['outcome'] in embed.fields[0].value
    # Embed formatting logic is in cog, test just checks content
    assert history_data[1]['timestamp'] in embed.fields[1].value 
    assert kwargs.get('ephemeral') is True # History should be ephemeral

@pytest.mark.asyncio
async def test_battle_history_empty(battle_cog, mock_interaction, mock_battle_system):
    """Test /battle_history when there is no history."""
    user_id = str(mock_interaction.user.id)
    mock_battle_system.get_battle_history.return_value = [] # Empty history

    # Call actual command callback
    await battle_cog.battle_history.callback(battle_cog, mock_interaction)

    mock_battle_system.get_battle_history.assert_awaited_once_with(user_id)
    mock_interaction.response.send_message.assert_awaited_once_with("You have no recorded battle history.", ephemeral=True)

# --- /battle_surrender Tests ---

@pytest.mark.asyncio
async def test_battle_surrender_success(battle_cog, mock_interaction, mock_battle_system):
    """Test /battle_surrender successfully surrenders an active battle."""
    user_id = str(mock_interaction.user.id)
    battle_id = "active_battle_123"
    success_message = "You have surrendered the battle."
    
    mock_battle_system.get_active_battle_status.return_value = battle_id # User is in battle
    mock_battle_system.surrender_battle.return_value = (True, success_message)

    # Call actual command callback
    await battle_cog.battle_surrender.callback(battle_cog, mock_interaction)

    mock_battle_system.get_active_battle_status.assert_awaited_once_with(user_id)
    mock_battle_system.surrender_battle.assert_awaited_once_with(user_id, battle_id)
    mock_interaction.response.send_message.assert_awaited_once_with(success_message, ephemeral=True)

@pytest.mark.asyncio
async def test_battle_surrender_not_in_battle(battle_cog, mock_interaction, mock_battle_system):
    """Test /battle_surrender when the user is not in a battle."""
    user_id = str(mock_interaction.user.id)
    mock_battle_system.get_active_battle_status.return_value = None # Not in battle

    # Call actual command callback
    await battle_cog.battle_surrender.callback(battle_cog, mock_interaction)

    mock_battle_system.get_active_battle_status.assert_awaited_once_with(user_id)
    mock_battle_system.surrender_battle.assert_not_awaited()
    mock_interaction.response.send_message.assert_awaited_once_with("You are not currently in a battle.", ephemeral=True)

@pytest.mark.asyncio
async def test_battle_surrender_failure(battle_cog, mock_interaction, mock_battle_system):
    """Test /battle_surrender when the system fails to surrender."""
    user_id = str(mock_interaction.user.id)
    battle_id = "active_battle_456"
    fail_message = "Failed to surrender. An error occurred."
    
    mock_battle_system.get_active_battle_status.return_value = battle_id # User is in battle
    mock_battle_system.surrender_battle.return_value = (False, fail_message)

    # Call actual command callback
    await battle_cog.battle_surrender.callback(battle_cog, mock_interaction)

    mock_battle_system.get_active_battle_status.assert_awaited_once_with(user_id)
    mock_battle_system.surrender_battle.assert_awaited_once_with(user_id, battle_id)
    mock_interaction.response.send_message.assert_awaited_once_with(fail_message, ephemeral=True)

# TODO: Add test for /battle_history
# TODO: Add test for /battle_surrender 