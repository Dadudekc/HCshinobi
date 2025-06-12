import pytest
import discord
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from enum import Enum

# Import necessary classes from the application
from HCshinobi.bot.cogs.training import TrainingCommands, TrainingView, TrainingIntensity, TRAINING_ATTRIBUTES
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.training_system import TrainingSystem

pytestmark = pytest.mark.asyncio

# Use the actual TrainingIntensity enum if possible, otherwise mock it
# class TrainingIntensity(Enum): ...

# --- Mock Enum --- 
class TrainingType(Enum):
    PHYSICAL = "Physical"
    MENTAL = "Mental"
    SOCIAL = "Social"

# --- Fixtures --- 
@pytest.fixture
def mock_bot_training():
    bot = MagicMock(spec=["services"])
    bot.services = MagicMock()
    # Mock services as AsyncMock or MagicMock based on sync/async
    bot.services.character_system = AsyncMock(spec=CharacterSystem)
    # Training system itself is likely not async, but its methods might be
    bot.services.training_system = MagicMock(spec=TrainingSystem) 
    # Explicitly mock methods that are called
    bot.services.training_system.get_training_status = MagicMock()
    bot.services.training_system.get_training_status_embed = MagicMock()
    return bot

@pytest.fixture
def training_cog(mock_bot_training):
    # Cog only takes bot
    return TrainingCommands(bot=mock_bot_training)

@pytest.fixture
def mock_interaction_training():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User, id="7777777777", display_name="TrainingTester")
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()
    return interaction

@pytest.fixture
def mock_character():
    char = MagicMock()
    # Add attributes expected by TrainingView
    for attr in TRAINING_ATTRIBUTES.keys():
        setattr(char, attr, 10) # Default stats
    return char

# --- Tests --- 
class TestTrainingCommands:

    async def test_train_command_sends_view(self, training_cog, mock_interaction_training, mock_bot_training, mock_character):
        # Arrange
        player_id = mock_interaction_training.user.id
        mock_character_system_instance = mock_bot_training.services.character_system
        mock_training_system_instance = mock_bot_training.services.training_system

        # Patch methods on the INSTANCES using a context manager
        # Note: train command calls get_character (async) and get_training_status (sync)
        with patch.object(mock_character_system_instance, 'get_character', new_callable=AsyncMock) as mock_get_character_instance, \
             patch.object(mock_training_system_instance, 'get_training_status', new_callable=MagicMock) as mock_get_training_status_instance:

            mock_get_character_instance.return_value = mock_character
            mock_get_training_status_instance.return_value = None # User is not currently training

            # Act
            await training_cog.train.callback(training_cog, mock_interaction_training)

            # Assert
            mock_get_character_instance.assert_awaited_once_with(player_id)
            # Assert the sync method was called
            mock_get_training_status_instance.assert_called_once_with(player_id)

            # Check followup.send since we deferred
            mock_interaction_training.followup.send.assert_awaited_once()
            args, kwargs = mock_interaction_training.followup.send.call_args
            assert 'view' in kwargs
            assert isinstance(kwargs['view'], TrainingView)
            assert 'embed' in kwargs
            assert kwargs['view'].character == mock_character
            assert kwargs.get('ephemeral') == True

    async def test_train_command_no_character(self, training_cog, mock_interaction_training, mock_bot_training):
        # Arrange
        player_id = mock_interaction_training.user.id
        mock_character_system_instance = mock_bot_training.services.character_system

        # Patch only get_character
        with patch.object(mock_character_system_instance, 'get_character', new_callable=AsyncMock) as mock_get_character_instance:
            mock_get_character_instance.return_value = None

            # Act
            await training_cog.train.callback(training_cog, mock_interaction_training)

            # Assert
            mock_get_character_instance.assert_awaited_once_with(player_id)
            mock_interaction_training.followup.send.assert_awaited_once_with(
                "You must create a character first using `/create`.",
                ephemeral=True
            )

    async def test_training_status_active(self, training_cog, mock_interaction_training, mock_bot_training):
        # Arrange
        player_id = mock_interaction_training.user.id
        mock_training_system_instance = mock_bot_training.services.training_system
        
        # Create the expected embed
        status_embed = discord.Embed(title="🏋️ Training Status", color=discord.Color.blue())
        status_embed.description = "⏳ Training in progress... 7 hours remaining"
        status_embed.add_field(name="Attribute", value="Taijutsu", inline=True)
        status_embed.add_field(name="Intensity", value="Moderate", inline=True)
        status_embed.add_field(name="Progress", value="`██████████░░░░░░░░░░` 50%", inline=False)

        # Patch only get_training_status_embed (sync) using context manager
        with patch.object(mock_training_system_instance, 'get_training_status_embed', new_callable=MagicMock) as mock_get_training_status_embed_instance:
            mock_get_training_status_embed_instance.return_value = status_embed

            # Act
            await training_cog.training_status.callback(training_cog, mock_interaction_training)

            # Assert
            # Check the call to the sync method
            mock_get_training_status_embed_instance.assert_called_once_with(player_id)
            
            mock_interaction_training.followup.send.assert_awaited_once()
            args, kwargs = mock_interaction_training.followup.send.call_args
            assert 'embed' in kwargs
            assert kwargs['embed'] == status_embed # Check the correct embed was sent
            assert kwargs.get('ephemeral') == True

    async def test_training_status_inactive(self, training_cog, mock_interaction_training, mock_bot_training):
        # Arrange
        player_id = mock_interaction_training.user.id
        mock_training_system_instance = mock_bot_training.services.training_system

        # Patch only get_training_status_embed (sync) using context manager
        with patch.object(mock_training_system_instance, 'get_training_status_embed', new_callable=MagicMock) as mock_get_training_status_embed_instance:
            mock_get_training_status_embed_instance.return_value = None # No active training

            # Act
            await training_cog.training_status.callback(training_cog, mock_interaction_training)

            # Assert
            # Check the call to the sync method
            mock_get_training_status_embed_instance.assert_called_once_with(player_id)
            
            # Correct the expected message text
            mock_interaction_training.followup.send.assert_awaited_once_with(
                "You are not currently training and have no active cooldown.",
                ephemeral=True
            )

    # TODO: Add tests for view interactions (selecting attribute, intensity, duration, starting)
    # TODO: Add tests for /complete command
    # TODO: Add tests for /cancel_training command

# Remove the trailing </rewritten_file> 