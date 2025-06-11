import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta, timezone
import re

# Assume necessary imports from the project
from HCshinobi.bot.bot import HCBot
# from HCshinobi.bot.config import BotConfig
# from HCshinobi.bot.services import ServiceContainer
# from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.training_system import TrainingSystem, TrainingSession, TrainingIntensity
# from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.bot.cogs.training import TrainingCommands, TrainingView
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.bot.services import ServiceContainer # Correct path
from tests.utils.time_utils import get_mock_now, get_past_hours, get_past_seconds

# Fixtures integration_bot, mock_e2e_interaction are loaded from conftest.py

# Helper to create mock interaction
def create_mock_interaction(user_id: int, user_name: str, guild_id: int):
    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = user_id
    mock_user.name = user_name
    mock_user.display_name = user_name

    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.id = guild_id

    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.user = mock_user
    mock_interaction.guild = mock_guild
    mock_interaction.response = AsyncMock(spec=discord.InteractionResponse)
    mock_interaction.followup = AsyncMock(spec=discord.Webhook)
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    return mock_interaction

# Helper to create a character for tests
async def create_test_character(char_system: CharacterSystem, user_id: int, name: str, clan: str) -> Character:
    char = await char_system.create_character(user_id=user_id, name=name, clan=clan)
    assert char is not None, f"Failed to create test character {name}"
    return char

# --- Tests for /train ---

@pytest.mark.asyncio
async def test_train_command_shows_view(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test that the /train command initially shows the TrainingView."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None
    
    # Ensure character exists
    char_system: CharacterSystem = services.character_system
    await char_system.create_character(user_id, interaction.user.display_name, "TestClan") # Simplified creation

    # --- Execute Command ---
    train_cmd = getattr(training_cog, 'train')
    await train_cmd.callback(training_cog, interaction)

    # --- Assertions ---
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    
    args, kwargs = interaction.followup.send.call_args
    assert isinstance(kwargs.get('view'), TrainingView)
    assert isinstance(kwargs.get('embed'), discord.Embed)
    assert kwargs.get('ephemeral') is True
    sent_embed = kwargs.get('embed')
    assert sent_embed.title == "🎯 Training Setup"

@pytest.mark.asyncio
# async def test_start_training_success(integration_bot):
async def test_start_training_success(integration_services: ServiceContainer):
    """Test successfully starting training via the view interaction."""
    services = integration_services
    char_system: CharacterSystem = services.character_system
    training_system: TrainingSystem = services.training_system

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None

    user_id = 67890
    user_name = "Trainee"
    guild_id = 98765
    character_name = "RockLee"
    character_clan = "Might"

    # 1. PREPARE: Create character, add funds & mock interaction
    character = await create_test_character(char_system, user_id, character_name, character_clan)
    services.currency_system.add_balance_and_save(character.id, 10000) # Call synchronously
    interaction = create_mock_interaction(user_id, user_name, guild_id)

    # Ensure not currently training and no cooldown
    assert user_id not in training_system.active_sessions
    assert user_id not in training_system.cooldowns

    # 2. Execute the /train command to get the view
    await training_cog.train.callback(training_cog, interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    call_args, call_kwargs = interaction.followup.send.call_args
    view = call_kwargs.get('view')
    assert isinstance(view, TrainingView)

    # --- Assert View and Children --- 
    assert view is not None, "View was not sent in the interaction response"
    assert isinstance(view, TrainingView), "Sent view is not a TrainingView"
    # Make sure the view has components added in its __init__
    assert len(view.children) > 0, "TrainingView has no UI components (children)"
    
    # --- Debug: Print children before asserting --- 
    print("\n--- [DEBUG] test_start_training_success: View Children --- ")
    for i, child in enumerate(view.children):
        child_info = f"Child {i}: Type={type(child)}, CustomID={getattr(child, 'custom_id', 'N/A')}, Placeholder/Label={getattr(child, 'placeholder', getattr(child, 'label', 'N/A'))}"
        print(child_info)
    print("--------------------------------------------------------")
    # --- End Debug ---
    
    # Specifically check for the intensity select using its custom_id
    intensity_select = discord.utils.get(view.children, custom_id="training_intensity_select")
    assert intensity_select is not None, "Intensity select dropdown (custom_id='training_intensity_select') not found in view children"
    # Also check for the button
    start_button_check = discord.utils.get(
        [child for child in view.children if isinstance(child, discord.ui.Button)],
        label="Start Training"
    )
    assert start_button_check is not None, "Start Training button not found in view children"

    # Add a small delay before accessing view children, just in case
    await asyncio.sleep(0.05)
    
    # --- Check if children exist at all --- 
    assert view.children, "TrainingView has no children! View object might be incomplete or uninitialized."
    # --- Debug: Print children types ---
    print("\n--- TrainingView Children --- ")
    for i, child in enumerate(view.children):
        print(f"Child {i}: {type(child)} - {getattr(child, 'placeholder', getattr(child, 'label', 'N/A'))} - ID: {getattr(child, 'custom_id', 'N/A')}")
    print("-----------------------------")
    # --- End Debug --- 

    # 3. Simulate View Interaction
    # Select attribute, intensity, duration
    test_attribute = "taijutsu"
    test_intensity = TrainingIntensity.MODERATE
    test_duration = 8
    
    # Revert to using discord.utils.get and check each individually
    intensity_select = discord.utils.get(view.children, custom_id="training_intensity_select")
    assert intensity_select is not None, "Intensity select not found"
    attribute_select = discord.utils.get(view.children, custom_id="training_attribute_select")
    assert attribute_select is not None, "Attribute select not found"
    duration_select = discord.utils.get(view.children, custom_id="training_duration_select")
    assert duration_select is not None, "Duration select not found"
    start_button = discord.utils.get(
        [child for child in view.children if isinstance(child, discord.ui.Button)],
        label="Start Training"
    )
    assert start_button is not None, "Start button not found"

    # Simulate selections
    # Need to mock the interaction for the select callbacks
    select_interaction = create_mock_interaction(user_id, user_name, guild_id)
    # Set the selected value on the component
    attribute_select.values = [test_attribute]
    # Call the view's handler method
    await view.select_attribute_callback(select_interaction)
    
    select_interaction_2 = create_mock_interaction(user_id, user_name, guild_id)
    # Set the selected value on the component
    intensity_select.values = [test_intensity]
    # Call the view's handler method
    await view.select_intensity_callback(select_interaction_2)
    
    select_interaction_3 = create_mock_interaction(user_id, user_name, guild_id)
    # Set the selected value on the component
    duration_select.values = [str(test_duration)]
    # Call the view's handler method
    await view.select_duration_callback(select_interaction_3)
    
    # Button should now be enabled (check internal state if possible or assume)
    # view.start_training_button.disabled should be False now ideally

    # Reset interaction mock for the button click
    button_interaction = create_mock_interaction(user_id, user_name, guild_id)

    # 4. Simulate Button Click
    # We need to capture the result of the callback indirectly
    # The callback sends a followup message based on success/failure
    await start_button.callback(button_interaction)

    # 5. Assertions
    # Check button interaction response (defer + followup)
    button_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    button_interaction.followup.send.assert_awaited_once()
    final_args, final_kwargs = button_interaction.followup.send.call_args
    # Assert the SUCCESS message was sent by the callback
    assert "✅ Training session started!" in final_args[0]
    assert final_kwargs.get('ephemeral') is True

    # Verify training session was created in the system *after* confirming success message
    assert user_id in training_system.active_sessions
    session = training_system.active_sessions.get(str(user_id))
    assert session is not None, "Training session missing after start_training call"
    # Prepare a past timestamp to force training completion
    mock_now = get_mock_now()
    past_time = get_past_hours(test_duration + 1)
    session.start_time = past_time  # Update the datetime object
    assert session.attribute == test_attribute
    assert session.duration_hours == test_duration
    assert session.intensity == test_intensity
    assert session.user_id == str(user_id)

@pytest.mark.asyncio
# async def test_full_training_cycle(integration_bot, mocker):
async def test_full_training_cycle(integration_services: ServiceContainer):
    """Test the full cycle: start training, wait, complete training."""
    services = integration_services
    char_system: CharacterSystem = services.character_system
    training_system: TrainingSystem = services.training_system
    currency_system: CurrencySystem = services.currency_system # Added currency system

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services
    # Mock bot.get_user needed by complete_training's send_completion_message
    mock_bot.get_user = MagicMock()
    mock_user_obj = MagicMock(spec=discord.User)
    mock_user_obj.id = 11223
    mock_user_obj.send = AsyncMock() # Mock the DM send method
    mock_bot.get_user.return_value = mock_user_obj

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None

    user_id = 11223
    user_name = "CycleTester"
    guild_id = 32211
    character_name = "Shino"
    character_clan = "Aburame"

    # 1. PREPARE: Create character and add funds
    original_char = await create_test_character(char_system, user_id, character_name, character_clan)
    await asyncio.to_thread(currency_system.set_player_balance, user_id, 1000) # Add sufficient funds
    await asyncio.to_thread(currency_system.save_currency_data) # Save balance
    original_xp = original_char.exp
    original_level = original_char.level

    # Mock interaction for starting training
    start_interaction = create_mock_interaction(user_id, user_name, guild_id)

    # 2. START TRAINING
    # We need to call the actual start_training method for the cycle
    # Define training parameters
    test_attribute = "intelligence"
    test_intensity = TrainingIntensity.LIGHT
    test_duration = 1 # Keep duration short for testing

    # Mock interaction for the view interaction part
    # Assuming the view selection logic is tested elsewhere, we directly call the system
    # Alternatively, could simulate the view interaction like in test_start_training_success
    success, start_msg = await training_system.start_training(user_id, test_attribute, test_duration, test_intensity)
    assert success, f"Failed to start training: {start_msg}" # Now this should pass
    
    # ADD SMALL DELAY to allow async save to potentially complete
    await asyncio.sleep(0.01)
    
    assert user_id in training_system.active_sessions
    session = training_system.active_sessions.get(str(user_id))
    assert session is not None, "Training session missing after start_training call"
    # Prepare a past timestamp to force training completion
    mock_now = get_mock_now()
    past_time = get_past_hours(test_duration + 1)
    session.start_time = past_time  # Update the datetime object

    # Mock interaction for completing training
    complete_interaction = create_mock_interaction(user_id, user_name, guild_id)

    # 4. COMPLETE TRAINING (Call /train again)
    # Patch datetime here for the completion logic
    with patch('HCshinobi.core.training_system.datetime') as core_dt, \
         patch('HCshinobi.bot.cogs.training.datetime') as cog_dt:
        core_dt.now.return_value = mock_now # Use the same mocked 'now' for consistency
        cog_dt.now.return_value = mock_now
        
        await training_cog.train.callback(training_cog, complete_interaction)

        # Verify training session is removed
        assert str(user_id) not in training_system.active_sessions

        # Verify cooldown is now set
        assert str(user_id) in training_system.cooldowns
        # assert training_system.cooldowns[user_id] > asyncio.get_running_loop().time()

        # Verify character gained XP/levels
        updated_char = await char_system.get_character(str(user_id))
        assert updated_char is not None
        assert updated_char.exp > original_xp or updated_char.level > original_level

        # Verify completion message was sent via followup
        complete_interaction.followup.send.assert_awaited_once()
        args, kwargs = complete_interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None
        assert "Training Complete!" in sent_embed.title
        # Use re.search with raw string for proper regex matching
        assert re.search(r"Gained \d+ XP", sent_embed.description), "Embed description should contain XP gain message"

        # Verify DM was attempted (mocked bot.get_user was called)
        mock_bot.get_user.assert_called_once_with(user_id)
        # And check the DM send method on the mocked user obj
        mock_user_obj.send.assert_called_once()
        dm_args, dm_kwargs = mock_user_obj.send.call_args
        dm_embed = dm_kwargs.get('embed')
        assert dm_embed is not None
        assert "Training Complete!" in dm_embed.title

# Test underlying system logic directly for specific cases
@pytest.mark.asyncio
async def test_start_training_insufficient_funds(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test starting training when the character lacks sufficient funds."""
    services = integration_services
    _ = mock_e2e_interaction
    user_id = _.user.id

    training_system: TrainingSystem = services.training_system
    char_system: CharacterSystem = services.character_system
    currency_system: CurrencySystem = services.currency_system

    # Ensure character exists but has NO funds
    await char_system.create_character(user_id, "Poor User", "NoClan") # Simplified creation
    await asyncio.to_thread(currency_system.set_player_balance, user_id, 0)
    await asyncio.to_thread(currency_system.save_currency_data) # Ensure save after set

    # Reset active sessions for this test
    training_system.active_sessions = {}
    training_system.cooldowns = {}

    attribute_to_train = "ninjutsu"
    duration_hours = 1
    intensity = TrainingIntensity.MODERATE
    cost = training_system._get_training_cost(attribute_to_train) 
    cost_multiplier, _ = TrainingIntensity.get_multipliers(intensity)
    expected_cost = int(cost * duration_hours * cost_multiplier)

    # --- Call System Method --- 
    success, message = await training_system.start_training(user_id, attribute_to_train, duration_hours, intensity)

    # --- Assertions ---
    assert success is False
    # Adjust assertion to match actual message format
    assert f"Insufficient Ryō! Cost: {expected_cost}" in message
    assert user_id not in training_system.active_sessions
    final_balance = await asyncio.to_thread(currency_system.get_player_balance, user_id)
    assert final_balance == 0

# --- Tests for /training_status ---

@pytest.mark.asyncio
async def test_training_status_active(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test /training_status when training is active."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id

    training_system: TrainingSystem = services.training_system
    char_system: CharacterSystem = services.character_system
    currency_system: CurrencySystem = services.currency_system

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services
    # Mock datetime.now for consistent time checks
    mock_now = get_mock_now()
    # Use unittest.mock.patch context manager
    with patch('HCshinobi.core.training_system.datetime') as core_dt, \
         patch('HCshinobi.bot.cogs.training.datetime') as cog_dt:
        core_dt.now.return_value = mock_now
        cog_dt.now.return_value = mock_now

        # Instantiate the Cog directly
        training_cog = TrainingCommands(mock_bot)
        assert training_cog is not None

        # Ensure character exists
        character = await char_system.create_character(user_id, interaction.user.display_name, "TestClan")
        assert character is not None

        # --- Setup: Manually start a training session --- 
        start_time = get_past_hours(1)  # Started 1 hour ago
        session_data = {
            'user_id': str(user_id),
            'character_id': str(user_id), # Assuming character_id is same as user_id
            'attribute': 'taijutsu',
            'intensity': TrainingIntensity.MODERATE,
            'start_time': start_time.isoformat(), # Store as ISO string
            'end_time': (start_time + timedelta(hours=8)).isoformat(),
            'duration_hours': 8,
            'cost': 50, # Example cost
            'xp_gain': 0, # Not calculated yet
            'attribute_gain': 0, # Not calculated yet
            'injury_chance': 0.1, # Example
            'progress_check_interval': timedelta(minutes=60).total_seconds(), # Example
            'last_progress_check': start_time.isoformat()
        }
        session = TrainingSession.from_dict(session_data)
        # Add to the system's active sessions
        training_system.active_sessions[str(user_id)] = session
        # Set character state
        character.is_active = True
        character.training_details = session.to_dict() # Update character data
        await char_system.save_character(character) # Save changes
        # Brief delay after setup
        await asyncio.sleep(0.1)
        # ------------------------------------------------- 

        # --- Execute Command --- (Code needs to be inside the with block)
        status_cmd = getattr(training_cog, 'training_status')
        await status_cmd.callback(training_cog, interaction)

        # --- Assertions --- (Code needs to be inside the with block)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        interaction.followup.send.assert_awaited_once()
        
        args, kwargs = interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None, "No embed sent for active training status"
        assert kwargs.get('ephemeral') is True
        # Check for the active training status title
        assert "🏋️ Training Status" in sent_embed.title, f"Embed title was '{sent_embed.title}' instead of containing '🏋️ Training Status'"
        # Optionally, assert specific fields matching the session data
        assert f"**Attribute:** {session.attribute.title()}\n" in sent_embed.description
        assert f"**Intensity:** {session.intensity.title()}\n" in sent_embed.description

@pytest.mark.asyncio
async def test_training_status_inactive(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test /training_status when training is not active."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id

    training_system: TrainingSystem = services.training_system
    char_system: CharacterSystem = services.character_system

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None

    # Ensure character exists
    await char_system.create_character(user_id, interaction.user.display_name, "InactiveClan")

    # Make sure no active training
    if user_id in training_system.active_sessions:
        del training_system.active_sessions[user_id]

    # Execute /train status
    await training_cog.train.callback(training_cog, interaction)

    # Assert: Check that the interaction response shows the training view (not active)
    interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    assert isinstance(kwargs.get('embed'), discord.Embed)
    assert kwargs.get('ephemeral') is True
    sent_embed = kwargs.get('embed')
    assert sent_embed.title == "🎯 Training Setup"
    assert isinstance(kwargs.get('view'), TrainingView)

@pytest.mark.asyncio
async def test_complete_training_success(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test completing training successfully via /train command when duration passed."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id

    training_system: TrainingSystem = services.training_system
    char_system: CharacterSystem = services.character_system

    # Create minimal mock bot needed for Cog init + DM mocking
    mock_bot = MagicMock()
    mock_bot.services = services
    mock_bot.get_user = MagicMock()
    mock_user_obj = MagicMock(spec=discord.User)
    mock_user_obj.id = user_id
    mock_user_obj.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user_obj

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None

    # Ensure character exists
    char = await char_system.create_character(user_id, interaction.user.display_name, "CompleteClan")
    original_xp = char.exp

    # Manually start a session - ADDED INTENSITY
    test_intensity = TrainingIntensity.LIGHT # Choose an intensity
    await training_system.start_training(char.id, "Taijutsu", 1, test_intensity) # Provide intensity
    
    # ADD SMALL DELAY to allow async save to potentially complete
    await asyncio.sleep(0.01)

    # Simulate time passing: Set start time far in the past
    # Use unittest.mock.patch for datetime within this operation
    mock_now = get_mock_now()
    training_duration_hours = 1
    training_duration_seconds = timedelta(hours=training_duration_hours).total_seconds()
    # training_duration = training_system.config.get('training_duration_seconds', 60)
    past_time = get_past_seconds((training_duration_hours * 3600) + 5)  # 5s buffer

    # Assuming the session stores start time as isoformat string
    # We need to update the session data directly
    session = training_system.active_sessions.get(str(user_id))
    assert session is not None, "Training session missing after start_training call"
    session.start_time = past_time # Update the datetime object

    # Ensure cooldown not set yet
    if user_id in training_system.cooldowns:
        del training_system.cooldowns[user_id]

    # Execute /train command (should trigger completion)
    # Patch datetime here as well for the completion logic
    with patch('HCshinobi.core.training_system.datetime') as core_dt_comp, \
         patch('HCshinobi.bot.cogs.training.datetime') as cog_dt_comp:
        core_dt_comp.now.return_value = mock_now # Use the same mocked 'now'
        cog_dt_comp.now.return_value = mock_now

        await training_cog.train.callback(training_cog, interaction)

        # Assert: Training completed (assertions need to be inside the patch block)
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        assert str(user_id) not in training_system.active_sessions
        assert str(user_id) in training_system.cooldowns

        # Check XP gain
        updated_char = await char_system.get_character(str(user_id))
        assert updated_char is not None, "Character not found after completion"
        assert updated_char.exp > original_xp

        # Verify completion message was sent via followup
        # The mock_e2e_interaction fixture might need adjustment if followup is not captured correctly
        interaction.followup.send.assert_awaited_once()
        args, kwargs = interaction.followup.send.call_args
        sent_embed = kwargs.get('embed')
        assert sent_embed is not None, "No embed sent on training completion"
        assert "Training Complete!" in sent_embed.title

        # Verify DM attempt
        mock_bot.get_user.assert_called_once_with(user_id)
        mock_user_obj.send.assert_called_once()
        dm_args, dm_kwargs = mock_user_obj.send.call_args
        dm_embed = dm_kwargs.get('embed')
        assert dm_embed is not None
        assert "Training Complete!" in dm_embed.title

@pytest.mark.asyncio
async def test_complete_training_not_active(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test trying to complete training via /train when none is active."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id

    training_system: TrainingSystem = services.training_system
    char_system: CharacterSystem = services.character_system

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    training_cog = TrainingCommands(mock_bot)
    assert training_cog is not None

    # Ensure character exists
    await char_system.create_character(user_id, interaction.user.display_name, "NoTrainClan")

    # Make sure no active training
    if user_id in training_system.active_sessions:
        del training_system.active_sessions[user_id]

    # Execute /train command
    await training_cog.train.callback(training_cog, interaction)

    # Assert: Should show the training setup view
    interaction.response.defer.assert_called_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_called_once()
    args, kwargs = interaction.followup.send.call_args
    assert isinstance(kwargs.get('embed'), discord.Embed)
    assert kwargs.get('ephemeral') is True
    sent_embed = kwargs.get('embed')
    assert sent_embed.title == "🎯 Training Setup"
    assert isinstance(kwargs.get('view'), TrainingView)

# TODO: Add test for cooldown
# TODO: Add test for trying to start training while already active
# TODO: Add test for trying to start training while on cooldown
# TODO: Add tests for different training intensities (if applicable)

# No newline at end of file 