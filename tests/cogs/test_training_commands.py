import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

# Assuming TrainingCommands is in HCshinobi.bot.cogs.training_commands
from HCshinobi.bot.cogs.training_commands import TrainingCommands 
# Assuming TrainingSystem/CharacterSystem are in HCshinobi.core
# from HCshinobi.core.training_system import TrainingSystem # Now mocked
from HCshinobi.core.character_system import CharacterSystem
# Assuming Character is in HCshinobi.core
from HCshinobi.core.character import Character 

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    return MagicMock()

@pytest.fixture
def mock_training_system():
    """Fixture for a mocked TrainingSystem."""
    mock = AsyncMock() # spec=TrainingSystem if class exists
    mock.cancel_training = AsyncMock()
    mock.get_training_status = AsyncMock(return_value=None) # Default: Not training
    mock.complete_training = AsyncMock() # Add mock for complete_training
    return mock

@pytest.fixture
def mock_character_system():
    """Fixture for a mocked CharacterSystem."""
    mock = AsyncMock(spec=CharacterSystem)
    mock.get_character = AsyncMock()
    sample_char = MagicMock(spec=Character)
    sample_char.id = 123456789
    sample_char.name = "TestCharacter"
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
def training_cog(mock_bot, mock_training_system, mock_character_system):
    """Fixture for the TrainingCommands cog instance."""
    # Use the actual cog class now
    cog = TrainingCommands(mock_bot, mock_training_system, mock_character_system)
    return cog

# --- Test Cases --- 

# --- /cancel_training Tests --- 

@pytest.mark.asyncio
async def test_cancel_training_success(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /cancel_training successfully cancels active training."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    success_message = "Training cancelled successfully."
    
    mock_training_system.get_training_status.return_value = {'skill': 'Ninjutsu', 'end_time': '...'} # Currently training
    mock_training_system.cancel_training.return_value = (True, success_message)

    # Call the actual command callback
    await training_cog.cancel_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character)
    mock_training_system.cancel_training.assert_awaited_once_with(character)
    mock_interaction.response.send_message.assert_awaited_once_with(success_message, ephemeral=True)

@pytest.mark.asyncio
async def test_cancel_training_no_character(training_cog, mock_interaction, mock_character_system, mock_training_system):
    """Test /cancel_training when the user has no character."""
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = None

    # Call the actual command callback
    await training_cog.cancel_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_not_awaited()
    mock_training_system.cancel_training.assert_not_awaited()
    # Check message was sent by the _check_character helper
    mock_interaction.response.send_message.assert_awaited_once_with("You need to create a character first using `/create`.", ephemeral=True)

@pytest.mark.asyncio
async def test_cancel_training_not_training(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /cancel_training when the user is not currently training."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    mock_training_system.get_training_status.return_value = None # Not training

    # Call the actual command callback
    await training_cog.cancel_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character)
    mock_training_system.cancel_training.assert_not_awaited()
    mock_interaction.response.send_message.assert_awaited_once_with("You are not currently training anything.", ephemeral=True)

@pytest.mark.asyncio
async def test_cancel_training_failure(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /cancel_training when the system fails to cancel."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    fail_message = "Failed to cancel training due to an error."
    
    mock_training_system.get_training_status.return_value = {'skill': 'Taijutsu', 'end_time': '...'} # Currently training
    mock_training_system.cancel_training.return_value = (False, fail_message)

    # Call the actual command callback
    await training_cog.cancel_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character)
    mock_training_system.cancel_training.assert_awaited_once_with(character)
    mock_interaction.response.send_message.assert_awaited_once_with(fail_message, ephemeral=True)

# --- /complete_training Tests --- 

@pytest.mark.asyncio
async def test_complete_training_success(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /complete_training successfully completes active training."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    skill_trained = "Ninjutsu"
    exp_gained = 100
    success_message = f"Training complete! You gained {exp_gained} EXP in {skill_trained}."
    
    mock_training_system.get_training_status.return_value = {'skill': skill_trained, 'end_time': '...'} # Currently training
    # Add complete_training mock to the system fixture if not already there
    mock_training_system.complete_training.return_value = (True, success_message, exp_gained) 

    # Call the actual command callback
    await training_cog.complete_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character) # Check if training first
    mock_training_system.complete_training.assert_awaited_once_with(character)
    mock_interaction.response.send_message.assert_awaited_once_with(success_message, ephemeral=True)

@pytest.mark.asyncio
async def test_complete_training_no_character(training_cog, mock_interaction, mock_character_system, mock_training_system):
    """Test /complete_training when the user has no character."""
    user_id = str(mock_interaction.user.id)
    mock_character_system.get_character.return_value = None

    # Call the actual command callback
    await training_cog.complete_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_not_awaited()
    mock_training_system.complete_training.assert_not_awaited()
    # Check message was sent by the _check_character helper
    mock_interaction.response.send_message.assert_awaited_once_with("You need to create a character first using `/create`.", ephemeral=True)

@pytest.mark.asyncio
async def test_complete_training_not_training(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /complete_training when the user is not currently training."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    mock_training_system.get_training_status.return_value = None # Not training

    # Call the actual command callback
    await training_cog.complete_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character)
    mock_training_system.complete_training.assert_not_awaited()
    mock_interaction.response.send_message.assert_awaited_once_with("You are not currently training anything.", ephemeral=True)

@pytest.mark.asyncio
async def test_complete_training_failure(training_cog, mock_interaction, mock_training_system, mock_character_system):
    """Test /complete_training when the system fails to complete."""
    user_id = str(mock_interaction.user.id)
    character = mock_character_system.get_character.return_value
    fail_message = "Failed to complete training. Still ongoing?"
    
    mock_training_system.get_training_status.return_value = {'skill': 'Genjutsu', 'end_time': '...'} # Currently training
    mock_training_system.complete_training.return_value = (False, fail_message, None)

    # Call the actual command callback
    await training_cog.complete_training.callback(training_cog, mock_interaction)

    mock_character_system.get_character.assert_awaited_once_with(user_id)
    mock_training_system.get_training_status.assert_awaited_once_with(character)
    mock_training_system.complete_training.assert_awaited_once_with(character)
    mock_interaction.response.send_message.assert_awaited_once_with(fail_message, ephemeral=True)

# TODO: Add tests for starting training, checking status etc. 