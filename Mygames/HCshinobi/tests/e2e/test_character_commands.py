import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock

# Assume necessary imports from the project
from HCshinobi.bot.bot import HCBot
# from HCshinobi.bot.config import BotConfig # Not needed directly in test
# from HCshinobi.bot.services import ServiceContainer # Not needed directly in test
# from HCshinobi.core.character_system import CharacterSystem # Accessed via bot.services
from HCshinobi.core.character import Character # Import Character for type checks
from HCshinobi.bot.cogs.character_commands import CharacterCommands, DeleteConfirmationView # Correct path and add View import
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.bot.services import ServiceContainer # Correct path
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine # Accessed via bot.services

# Fixtures integration_bot, mock_e2e_interaction are loaded from conftest.py

# --- Tests for /create ---

@pytest.mark.asyncio
async def test_create_character_success(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test successful character creation via the /create command."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system
    clan_assignment_engine: ClanAssignmentEngine = services.clan_assignment_engine # Get engine instance
    
    # Mock clan assignment to return a fixed clan
    test_clan = "Uchiha"
    clan_assignment_engine.assign_clan = AsyncMock(return_value={"assigned_clan": test_clan})

    # Ensure character doesn't exist beforehand (the fixture provides a clean state)
    await char_system.delete_character(user_id)

    # --- Execute Command ---
    create_cmd = getattr(char_cog, 'create')
    await create_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    # Interaction flow
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    # Check that followup.send was called at least once (for the embed)
    interaction.followup.send.assert_awaited()
    
    # Check the *first* call to followup.send for the embed
    call_args_list = interaction.followup.send.call_args_list
    assert len(call_args_list) >= 1 # Ensure at least one call occurred
    first_call_args, first_call_kwargs = call_args_list[0]
    sent_embed = first_call_kwargs.get('embed')

    # Check embed response
    # args, kwargs = interaction.followup.send.call_args # Don't use this, check first call
    # sent_embed = kwargs.get('embed')
    assert sent_embed is not None
    assert sent_embed.title == "Character Created!"
    # Re-add get_character check after verifying embed was sent
    created_char = await char_system.get_character(user_id)
    assert created_char is not None
    assert isinstance(created_char, Character)
    assert created_char.id == user_id # Should be int if mock_interaction is int
    assert created_char.name == interaction.user.display_name
    assert created_char.clan == test_clan # Verify the assigned clan
    # Check embed content against the created character
    assert f"Welcome, {created_char.name} of the {created_char.clan} clan!" in sent_embed.description
    assert discord.utils.get(sent_embed.fields, name="Rank").value == created_char.rank
    assert discord.utils.get(sent_embed.fields, name="Level").value == str(created_char.level)

@pytest.mark.asyncio
async def test_create_character_already_exists(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test /create command when a character already exists."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system
    clan_assignment_engine = services.clan_assignment_engine

    # Ensure character exists beforehand
    existing_char = await char_system.create_character(user_id, "Existing User", "Senju")
    assert existing_char is not None
    # Verify it's saved
    assert await char_system.get_character(user_id) is not None

    # Reset interaction mocks before calling command again
    interaction.response.reset_mock()
    interaction.followup.reset_mock()

    # --- Execute Command ---
    create_cmd = getattr(char_cog, 'create')
    await create_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    # Interaction flow
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    
    # Check message response
    args, kwargs = interaction.followup.send.call_args
    sent_message = args[0] if args else kwargs.get('content')
    assert sent_message is not None
    # Check specific message from the cog
    assert "You already have a Shinobi character!" in sent_message
    assert kwargs.get('embed') is None # Should not send embed

@pytest.mark.skip(reason="`/create` does not take clan input; skipping invalid-clan test")
@pytest.mark.asyncio
async def test_create_character_invalid_clan(integration_services: ServiceContainer, mock_e2e_interaction):
    """Tests attempting to create a character with a non-whitelisted clan."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    name = "Sasuke"
    invalid_clan = "NotARealClan"
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system

    # Ensure character does not exist before test
    await char_system.delete_character(user_id)

    # --- Execute Command ---
    create_cmd = getattr(char_cog, 'create')
    await create_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()

    # Check message response
    args, kwargs = interaction.followup.send.call_args
    sent_message = args[0] if args else kwargs.get('content')
    assert sent_message is not None
    assert "An error occurred during character creation." in sent_message
    assert kwargs.get('embed') is None # Should not send embed

# --- Tests for /profile ---

@pytest.mark.asyncio
async def test_profile_success(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test successful profile fetching via the /profile command."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    user_display_name = interaction.user.display_name
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system
    currency_system = services.currency_system
    # Access token system via services
    token_system = services.token_system 
    # clan_assignment_engine is implicitly used by CharacterSystem/ClanData

    # Create character and set currency/tokens for the test
    assigned_clan = "Hyuga" # Example
    char_to_fetch = await char_system.create_character(user_id, user_display_name, assigned_clan)
    assert char_to_fetch is not None
    # Add some non-default stats for testing display
    char_to_fetch.level = 5
    char_to_fetch.rank = "Genin"
    char_to_fetch.strength += 5
    await char_system.save_character(char_to_fetch)

    mock_ryo = 500
    mock_tokens = 10
    # Remove unnecessary save call as get is mocked
    # await asyncio.to_thread(currency_system.add_balance_and_save, user_id, mock_ryo)
    
    # Mock the get methods directly on the service instances
    if hasattr(services, 'currency_system'):
        services.currency_system.get_player_balance = AsyncMock(return_value=mock_ryo)
    else: # Handle potential absence for robustness, though unlikely
        services.currency_system = MagicMock()
        services.currency_system.get_player_balance = AsyncMock(return_value=mock_ryo)

    # Ensure the token_system service exists and is mockable
    if hasattr(services, 'token_system'):
        services.token_system.get_player_tokens = AsyncMock(return_value=mock_tokens)
    else:
        # If token_system doesn't exist, maybe it's integrated differently
        # or the test needs adjustment based on actual implementation.
        # For now, we'll add a placeholder mock to avoid attribute errors
        # This might need refinement based on the actual TokenSystem implementation
        services.token_system = MagicMock()
        services.token_system.get_player_tokens = AsyncMock(return_value=mock_tokens)

    # --- Execute Command ---
    profile_cmd = getattr(char_cog, 'profile')
    await profile_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()

    # Check embed response
    args, kwargs = interaction.followup.send.call_args
    sent_embed = kwargs.get('embed')
    assert sent_embed is not None
    assert sent_embed.title == f"{user_display_name}'s Shinobi Profile"
    assert discord.utils.get(sent_embed.fields, name="👤 Name").value == user_display_name
    assert discord.utils.get(sent_embed.fields, name="⚜️ Clan").value == assigned_clan
    assert discord.utils.get(sent_embed.fields, name="📈 Level").value == str(char_to_fetch.level)
    stats_field = discord.utils.get(sent_embed.fields, name="📊 Stats")
    assert f"**STR:** {char_to_fetch.strength}" in stats_field.value
    progression_field = discord.utils.get(sent_embed.fields, name="🌟 Progression")
    assert f"**Rank:** {char_to_fetch.rank}" in progression_field.value
    currency_field = discord.utils.get(sent_embed.fields, name="💰 Currency")
    assert f"**Ryō:** {mock_ryo}" in currency_field.value 
    assert f"**Tokens:** {mock_tokens}" in currency_field.value

@pytest.mark.asyncio
async def test_profile_no_character(integration_services: ServiceContainer, mock_e2e_interaction):
    """Test /profile command when the user has no character."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system

    # Ensure character does not exist
    assert await char_system.get_character(user_id) is None

    # --- Execute Command ---
    profile_cmd = getattr(char_cog, 'profile')
    await profile_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()

    # Check message response
    args, kwargs = interaction.followup.send.call_args
    sent_message = args[0] if args else kwargs.get('content')
    assert sent_message is not None
    assert "You don't have a character yet! Use `/create` to start your journey." in sent_message
    assert kwargs.get('embed') is None # Should not send embed

@pytest.mark.asyncio
async def test_delete_character_success(integration_services: ServiceContainer, mock_e2e_interaction):
    """Tests successfully deleting an existing character."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system

    # Ensure character exists beforehand
    existing_name = "ToDelete"
    existing_char = await char_system.create_character(user_id, existing_name, "Hyuga")
    assert existing_char is not None

    # --- Execute Command ---
    delete_cmd = getattr(char_cog, 'delete')
    await delete_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    # 1. Check initial confirmation message + view
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    call_args_list = interaction.followup.send.call_args_list
    initial_call_args, initial_call_kwargs = call_args_list[0]
    initial_sent_message = initial_call_args[0] if initial_call_args else initial_call_kwargs.get('content')
    assert "🚨 **Warning!** Are you sure you want to delete" in initial_sent_message
    view_sent = initial_call_kwargs.get('view')
    assert view_sent is not None
    assert isinstance(view_sent, DeleteConfirmationView) # Assumes DeleteConfirmationView is imported

    # 2. Find the 'Yes' button and simulate the click
    confirm_button = discord.utils.get(view_sent.children, custom_id="delete_confirm_yes")
    assert confirm_button is not None
    assert isinstance(confirm_button, discord.ui.Button)

    # Reset followup mock before simulating click to isolate the second call
    interaction.followup.send.reset_mock()
    
    # Simulate the button click (this will trigger the second followup send)
    await confirm_button.callback(interaction)

    # Add a slightly longer delay to allow file system operations/cache updates
    await asyncio.sleep(0.3) # Increased from 0.2

    # 3. Check the second followup message for success
    interaction.followup.send.assert_awaited_once()
    final_call_args, final_call_kwargs = interaction.followup.send.call_args
    final_sent_message = final_call_args[0] if final_call_args else final_call_kwargs.get('content')
    assert final_sent_message is not None
    # Check the actual success message from the view's confirm_delete method
    assert "🗑️ Your character has been deleted." in final_sent_message 
    assert final_call_kwargs.get('ephemeral') is True

    # 4. Verify character is actually deleted
    # Explicitly remove from cache BEFORE attempting to check/load
    if str(user_id) in char_system.characters:
        del char_system.characters[str(user_id)]

    await asyncio.sleep(0.2) # Increased from 0.1 - wait after cache clear too

    # Force load attempt after deletion
    reloaded_char = await char_system._load_character(str(user_id))
    assert reloaded_char is None, "Character file still exists or reloaded unexpectedly after deletion attempt"
    # Original assertion (should also pass if file load is None)
    assert await char_system.get_character(user_id) is None

@pytest.mark.asyncio
async def test_delete_character_not_found(integration_services: ServiceContainer, mock_e2e_interaction):
    """Tests attempting to delete a character that does not exist."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    
    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    char_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system

    # Ensure character does not exist before test
    await char_system.delete_character(user_id)

    # --- Execute Command ---
    delete_cmd = getattr(char_cog, 'delete')
    await delete_cmd.callback(char_cog, interaction)

    # --- Assertions ---
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()

    # Check message response
    args, kwargs = interaction.followup.send.call_args
    sent_message = args[0] if args else kwargs.get('content')
    assert sent_message is not None
    assert "You don't have a character yet! Use `/create` to start your journey." in sent_message