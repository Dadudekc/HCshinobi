import pytest # Ensure pytest is imported
import asyncio # Add missing import
from unittest.mock import AsyncMock, MagicMock
# from HCshinobi.core.service_container import ServiceContainer # Incorrect path
from HCshinobi.bot.services import ServiceContainer # Correct path for ServiceContainer

# from HCshinobi.cogs.profile_command import ProfileCommand # Incorrect path
from HCshinobi.bot.cogs.character_commands import CharacterCommands # Correct class/cog
from HCshinobi.core.character import Character
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
import discord

# --- Tests for /profile ---
@pytest.mark.asyncio
async def test_profile_success(integration_services: ServiceContainer, mock_e2e_interaction): # Use ServiceContainer type hint
    """Test successful profile fetching via the /profile command."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id
    user_display_name = interaction.user.display_name

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    profile_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system
    currency_system: CurrencySystem = services.currency_system
    # Removed token_system access here as it's mocked later

    # Ensure character exists beforehand
    char_name = "TestProfileChar"
    # Create a dummy character first - use await directly with specific clan
    character = await char_system.create_character(user_id, char_name, "Hyuga") # Use Hyuga clan
    assert character is not None # Verify creation succeeded
    # Explicitly update cache to bypass potential file I/O delays in test
    char_system.characters[str(user_id)] = character 
    # Force save before command execution
    await char_system.save_character(character)
    # Assert character exists after saving
    assert await char_system.get_character(user_id) is not None, "Character not found immediately after create/save"

    # Add a small delay to mitigate potential race conditions
    await asyncio.sleep(0.5) # Increased delay significantly

    # Mock the get_player_balance and get_player_tokens methods
    mock_ryo = 500
    mock_tokens = 10

    if hasattr(services, 'currency_system'):
        services.currency_system.get_player_balance = AsyncMock(return_value=mock_ryo)
    else:
        services.currency_system = MagicMock()
        services.currency_system.get_player_balance = AsyncMock(return_value=mock_ryo)

    # Mock the get_player_tokens method directly on the service instance
    # mock_tokens = 10 # Define mock_tokens before using it
    # Ensure the token_system service exists and is mockable
    if hasattr(services, 'token_system'):
        services.token_system.get_player_tokens = AsyncMock(return_value=mock_tokens)
    else:
        # If token_system doesn't exist, handle appropriately (e.g., mock it)
        services.token_system = MagicMock()
        services.token_system.get_player_tokens = AsyncMock(return_value=mock_tokens)

    # --- Execute Command ---
    profile_cmd = getattr(profile_cog, 'profile')
    await profile_cmd.callback(profile_cog, interaction) # Call the command callback

    # --- Assertions ---
    # Assert defer() and followup.send() were called, not send_message()
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once()
    
    # Check the arguments of followup.send()
    args, kwargs = interaction.followup.send.call_args
    sent_embed = kwargs.get('embed')
    assert sent_embed is not None
    # Further assertions can be made on the embed content
    assert sent_embed.title == f"{user_display_name}\'s Shinobi Profile"
    # Add more specific embed checks if necessary
    assert discord.utils.get(sent_embed.fields, name="👤 Name").value == char_name # Check name matches created char
    assert discord.utils.get(sent_embed.fields, name="⚜️ Clan").value == "Hyuga" # Expect Hyuga clan
    assert discord.utils.get(sent_embed.fields, name="💰 Currency") # Check currency field exists


@pytest.mark.asyncio
async def test_profile_no_character(integration_services: ServiceContainer, mock_e2e_interaction): # Use ServiceContainer type hint
    """Test /profile command when the user has no character."""
    services = integration_services
    interaction = mock_e2e_interaction
    user_id = interaction.user.id

    # Create minimal mock bot needed for Cog init
    mock_bot = MagicMock()
    mock_bot.services = services

    # Instantiate the Cog directly
    profile_cog = CharacterCommands(mock_bot)
    char_system: CharacterSystem = services.character_system

    # Ensure character does not exist
    await char_system.delete_character(user_id) # Correct method call

    # --- Execute Command ---
    profile_cmd = getattr(profile_cog, 'profile')
    await profile_cmd.callback(profile_cog, interaction) # Call the command callback

    # --- Assertions ---
    # Assert defer() and followup.send() were called
    interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    interaction.followup.send.assert_awaited_once_with(
        "You don't have a character yet! Use `/create` to start your journey.",
        ephemeral=True
    )
    # interaction.response.send_message.assert_called_once_with(
    #     "You need to create a character first! Use `/create_character`.",
    #     ephemeral=True
    # ) # Incorrect assertion 