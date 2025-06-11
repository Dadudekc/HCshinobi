import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import os

# Assume necessary imports from the project
from HCshinobi.bot.bot import HCBot
from HCshinobi.core.training_system import TrainingIntensity

# Fixtures test_config, temp_data_dir, integration_bot, mock_e2e_interaction 
# are now expected to be loaded from tests/e2e/conftest.py

# --- The Test ---

@pytest.mark.asyncio
async def test_full_training_cycle(integration_bot, mock_e2e_interaction):
    """Test the full flow: /create -> /train -> /training_status -> /complete -> /profile"""
    # bot = await integration_bot # Don't await fixture
    bot = integration_bot 
    interaction = mock_e2e_interaction 
    user_id = interaction.user.id

    # Get Cogs and Systems for easier access
    char_cog = bot.get_cog('CharacterCommands')
    training_cog = bot.get_cog('TrainingCommands')
    assert char_cog is not None
    assert training_cog is not None

    char_system = bot.services.character_system
    training_system = bot.services.training_system
    currency_system = bot.services.currency_system

    # --- Step 1: Create Character ---
    print("\n--- E2E Step: Create Character ---")
    create_cmd = getattr(char_cog, 'create')
    await create_cmd.callback(char_cog, interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    await asyncio.sleep(0.01) # Give I/O time
    created_char = await char_system.get_character(user_id)
    assert created_char is not None
    assert created_char.id == user_id
    assert created_char.name == interaction.user.display_name

    # --- Grant Starting Currency ---
    starting_ryo = 100
    print(f"--- E2E Step: Granting {starting_ryo} Ryo ---")
    # Use the correct method and check the returned balance
    new_balance = await asyncio.to_thread( # Run sync method in executor
        currency_system.add_balance_and_save, 
        user_id, 
        starting_ryo
        # No reason/source argument in this method
    )
    assert new_balance == starting_ryo
    print(f"--- E2E Step: Balance is now {new_balance} Ryo ---")

    # Reset interaction mocks for next step
    interaction.response.reset_mock()
    interaction.followup.reset_mock()

    # --- Step 2: Start Training ---
    print("--- E2E Step: Start Training --- ")
    # For simplicity, let's directly interact with the system after ensuring /train runs
    # Call /train to check initial path
    train_cmd = getattr(training_cog, 'train')
    await train_cmd.callback(training_cog, interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once() # Expects the view
    # TODO: Verify the view was sent, maybe mock view interaction or call system directly

    # Simplified: Call system directly to start training
    print("--- E2E Step: (Simplified) Directly starting training via system ---")
    attribute_to_train = "ninjutsu"
    duration_hours = 1
    intensity = TrainingIntensity.MODERATE
    success, message = await training_system.start_training(user_id, attribute_to_train, duration_hours, intensity)
    assert success is True
    print(f"Start training message: {message}")

    # Verify training is active by checking the status embed
    status_embed = training_system.get_training_status_embed(user_id) # Sync call returns Embed or None
    assert status_embed is not None
    assert isinstance(status_embed, discord.Embed)
    assert status_embed.title == "🏋️ Training Status"
    # Find the attribute field to check its value
    attribute_field = discord.utils.get(status_embed.fields, name="Attribute")
    assert attribute_field is not None
    assert attribute_field.value == attribute_to_train.title()

    # Reset mocks
    interaction.response.reset_mock()
    interaction.followup.reset_mock()
    # Store baseline stat before completion
    char_before_complete = await char_system.get_character(user_id)
    base_stat_value = getattr(char_before_complete, attribute_to_train, 0)

    # --- Step 4: Complete Training ---
    print("--- E2E Step: Complete Training (using force_complete=True) --- ")
    # Call system method directly for reliable completion in test
    completion_results = await training_system.complete_training(user_id, force_complete=True)
    success = completion_results[0]
    completion_message = completion_results[1]
    assert success is True
    print(f"Completion message: {completion_message}")
    
    # --- Assertions based on system call results --- 
    # Assert stat gain in the message (adjust based on actual message format)
    # Since force_complete=True is used immediately, duration/gain is ~0
    expected_gain = 0.0 
    assert f"Points Gained: **{expected_gain:.2f}**" in completion_message 
    assert "completed early" in completion_message # Ensure early completion is noted

    # Assert training is no longer active using system call
    status_after = training_system.get_training_status_embed(user_id) # Sync call
    assert status_after is None

    # Assert character stat changed (or didn't change, since gain is 0)
    char_after_complete = await char_system.get_character(user_id)
    new_stat_value = getattr(char_after_complete, attribute_to_train, 0)
    assert new_stat_value == pytest.approx(base_stat_value + expected_gain)
    print(f"Stat {attribute_to_train}: {base_stat_value} -> {new_stat_value} (Expected Gain: {expected_gain})")

    # Reset mocks for the next command test (/profile)
    interaction.response.reset_mock()
    interaction.followup.reset_mock()

    # --- Step 5: Check Profile ---
    print("--- E2E Step: Check Profile --- ")
    profile_cmd = getattr(char_cog, 'profile')
    await profile_cmd.callback(char_cog, interaction)
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    args, kwargs = interaction.followup.send.call_args
    sent_profile_embed = kwargs.get('embed')
    assert sent_profile_embed is not None
    assert sent_profile_embed.title == f"{interaction.user.display_name}'s Shinobi Profile"

    # Print field names for debugging
    print(f"DEBUG: Embed fields received: {[f.name for f in sent_profile_embed.fields]}")

    # Check specific field for the stat
    combat_stats_field = discord.utils.get(sent_profile_embed.fields, name="Combat Stats")
    assert combat_stats_field is not None, "Combat Stats field not found in profile embed"
    
    # Check the stat value within the field
    # Value should be 0 because force_complete resulted in 0 gain
    expected_profile_line = f"**{attribute_to_train.title()}:** {int(round(new_stat_value))}"
    assert expected_profile_line in combat_stats_field.value, f"Expected stat line '{expected_profile_line}' not found in Combat Stats field value: {combat_stats_field.value}"
    print(f"Found stat in profile field '{combat_stats_field.name}': {combat_stats_field.value}")
    
    # --- Remove old loop check ---
    # field_found = False
    # for field in sent_profile_embed.fields:
    #     if field.value and f"{attribute_to_train.title()}" in field.value:
    #          expected_profile_line = f"**{attribute_to_train.title()}:** {int(round(new_stat_value))}" 
    #          assert expected_profile_line in field.value
    #          print(f"Found stat in profile field '{field.name}': {field.value}")
    #          field_found = True
    #          break
    # assert field_found is True, f"Stat {attribute_to_train} not found or incorrect in profile embed fields."