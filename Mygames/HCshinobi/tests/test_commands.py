"""Tests for the HCshinobi command system."""
import pytest
import discord
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest_asyncio # Use this for async fixtures if needed
from discord import app_commands
from discord.ext import commands # Import commands for Context
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.announcements import AnnouncementCommands
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.character import Character
import dataclasses
from HCshinobi.bot.bot import register_commands_command

@pytest_asyncio.fixture # Use async fixture decorator if needed later
async def mock_ctx():
    """Create a mock discord.ext.commands.Context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.author = Mock(spec=discord.Member) # Use Member for guild context
    ctx.author.id = 123456789
    ctx.author.roles = [] # Define roles for the author/member
    ctx.guild = Mock(spec=discord.Guild)
    ctx.guild.id = 987654321
    ctx.guild.roles = [] # Define roles as an iterable
    ctx.channel = Mock(spec=discord.TextChannel)
    ctx.send = AsyncMock()
    ctx.bot = AsyncMock(spec=commands.Bot) # Add bot reference if needed
    # Mock interaction attribute if commands try to access it (though unlikely for prefix commands)
    # ctx.interaction = AsyncMock(spec=discord.Interaction) 
    # ctx.interaction.response = AsyncMock()
    # ctx.interaction.followup = AsyncMock()
    return ctx

@pytest.fixture
def mock_client():
    """Create a mock Discord client."""
    client = Mock(spec=discord.Client)
    client.announcement_channel_id = 987654321
    return client

@pytest.fixture
def character_system():
    """Create a mock character system instance."""
    cs = Mock(spec=CharacterSystem)
    cs.get_character = AsyncMock() # Make async
    cs.create_character = AsyncMock() # Add create mock
    cs.update_character = AsyncMock()
    return cs

@pytest.fixture
def clan_assignment_engine():
    """Create a mock clan assignment engine instance."""
    cae = Mock(spec=ClanAssignmentEngine)
    mock_clan_info_uchiha = {'name': 'Uchiha', 'rarity': 'Legendary'}
    mock_clan_info_hyuga = {'name': 'Hyuga', 'rarity': 'Rare'}
    # Mock assign_clan to return a dict
    cae.assign_clan = AsyncMock(return_value={'assigned_clan': 'Uchiha', 'clan_rarity': 'Legendary'})
    # Mock get_player_clan as SYNC mock
    cae.get_player_clan = MagicMock(return_value=None) # Default to no clan
    # Mock get_clan if needed (though assignment engine might not expose this directly)
    # cae.get_clan = AsyncMock(side_effect=lambda name: mock_clan_info_hyuga if name == 'Hyuga' else mock_clan_info_uchiha if name == 'Uchiha' else None)
    # cae.get_all_clans = AsyncMock(return_value={'Uchiha': mock_clan_info_uchiha, 'Hyuga': mock_clan_info_hyuga})
    return cae

@pytest.fixture
def mock_bot_with_services(character_system, clan_assignment_engine):
    """Creates a mock bot instance and attaches mocked services."""
    mock_bot = MagicMock(spec=commands.Bot)
    mock_bot.services = MagicMock()
    mock_bot.services.character_system = character_system
    mock_bot.services.clan_assignment_engine = clan_assignment_engine
    mock_bot.services.currency_system = AsyncMock() # Add currency mock here
    mock_bot.services.token_system = AsyncMock()    # Add token mock here
    mock_bot.services.ollama_client = AsyncMock() # Mock Ollama as well
    # Mock the command tree if needed
    mock_tree = Mock(spec=app_commands.CommandTree)
    mock_tree.get_commands = Mock(return_value=[])
    mock_bot.tree = mock_tree
    return mock_bot

@pytest.fixture
def character_commands(mock_bot_with_services):
    """Create a character commands instance using the mock bot with services."""
    cog = CharacterCommands(bot=mock_bot_with_services)
    return cog

@pytest.fixture
def mock_bot():
    """Provides a mock Bot object with necessary configurations."""
    bot = AsyncMock() # Reverted: Use AsyncMock
    bot.tree = Mock(spec=app_commands.CommandTree)
    bot.tree.get_commands = Mock(return_value=[])
    bot.announcement_channel_id = 123456789 # Example ID

    # Configure get_channel and the channel/message mocks it returns
    mock_channel = AsyncMock()
    mock_message_channel = AsyncMock() # Message returned by channel.send
    mock_message_channel.edit = AsyncMock() # Edit on channel message
    mock_channel.send = AsyncMock(return_value=mock_message_channel) # channel.send is async
    bot.get_channel = Mock(return_value=mock_channel) # get_channel is sync

    return bot

@pytest.fixture
def mock_interaction():
    """Provides a mock Interaction object for app commands."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member) # Use Member for guild context
    interaction.user.id = "123456789" # Use string ID consistent with system
    interaction.user.display_name = "Test User"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 987654321
    interaction.channel = MagicMock(spec=discord.TextChannel)
    interaction.client = MagicMock(spec=commands.Bot) # Reference to the bot

    # Mock response/followup
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()

    return interaction

@pytest.fixture
def announcement_commands(mock_bot):
    """Fixture for AnnouncementCommands, using mock_bot."""
    return AnnouncementCommands(bot=mock_bot)

@pytest.mark.asyncio
async def test_create_character_success(character_commands, mock_interaction, character_system, clan_assignment_engine):
    """Test successful character creation via /create."""
    user_id = mock_interaction.user.id
    user_name = mock_interaction.user.display_name

    # Mock system calls
    character_system.get_character.return_value = None # No existing character
    # clan_assignment_engine.get_player_clan.return_value = None # No existing clan assignment <- REMOVED
    # Mock character creation returning a valid Character object
    mock_created_char = Character(id=user_id, name=user_name) # Add other fields as needed
    character_system.create_character.return_value = mock_created_char
    # Mock clan assignment returning a success dict
    clan_assignment_engine.assign_clan.return_value = {
        'assigned_clan': 'Uchiha',
        'clan_rarity': 'Legendary'
    }
    # Mock ollama response if needed
    character_commands.ollama_client.generate_response = AsyncMock(return_value="Ollama glimpse text.")

    # Call the command callback
    await character_commands.create.callback(character_commands, mock_interaction)

    # Assertions
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    character_system.get_character.assert_awaited_once_with(user_id)
    # Use assert_called_once_with for the synchronous get_player_clan
    # clan_assignment_engine.get_player_clan.assert_called_once_with(user_id) <- REMOVED
    character_system.create_character.assert_awaited_once_with(user_id=user_id, name=user_name, clan='Uchiha')
    clan_assignment_engine.assign_clan.assert_awaited_once_with(player_id=user_id, player_name=user_name)
    # Check ollama was called if client exists (REMOVED - Not called in this flow)
    # if character_commands.ollama_client:
    #     character_commands.ollama_client.generate_response.assert_awaited_once()
    # Check the followup message embed
    mock_interaction.followup.send.assert_awaited_once()
    _, kwargs = mock_interaction.followup.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert embed.title == "Character Created!"
    # assert "Uchiha" in embed.fields[0].value # Check specific field if structure is stable
    # If ollama text was part of the embed, remove that check too:
    # if character_commands.ollama_client:
    #     assert "Ollama glimpse text." in embed.fields[1].value 

@pytest.mark.asyncio
async def test_create_character_already_exists(character_commands, mock_interaction, character_system):
    """Test /create when character already exists."""
    user_id = mock_interaction.user.id

    # Mock system to return an existing character
    existing_char = Character(id=user_id, name="Existing User")
    character_system.get_character.return_value = existing_char

    # Call the command callback
    await character_commands.create.callback(character_commands, mock_interaction)

    # Assertions
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    character_system.get_character.assert_awaited_once_with(user_id)
    # Ensure other creation steps weren't called
    character_system.create_character.assert_not_awaited()
    # Check the followup message
    mock_interaction.followup.send.assert_awaited_once_with(
        "You already have a Shinobi character! Use `/profile`.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_profile_command_success(character_commands, mock_interaction, mock_bot_with_services):
    """Test successful profile view via /profile."""
    user_id = mock_interaction.user.id

    # Use the services attached to the bot passed to the cog
    character_system = mock_bot_with_services.services.character_system
    clan_assignment_engine = mock_bot_with_services.services.clan_assignment_engine
    currency_system = mock_bot_with_services.services.currency_system
    token_system = mock_bot_with_services.services.token_system

    # Mock system calls
    mock_char_data = {
        'id': user_id,
        'name': 'Test User',
        'clan': 'Hyuga', # Explicitly set clan here
        'level': 5,
        'hp': 90, 'max_hp': 100,
        'chakra': 45, 'max_chakra': 50,
        'stamina': 80, 'max_stamina': 85,
        'strength': 12,
        'speed': 11, # Assuming speed replaced agility or is relevant
        'defense': 10, # Added defense for completeness
        'willpower': 9, # Added willpower
        'chakra_control': 8, # Added chakra_control
        'intelligence': 13,
        'xp': 150,
        'rank': 'Chunin'
        # Add other *valid* stats as needed by the profile command
    }
    valid_fields = {f.name for f in dataclasses.fields(Character)}
    filtered_char_data = {k: v for k, v in mock_char_data.items() if k in valid_fields}
    character_system.get_character.return_value = Character(**filtered_char_data)
    # clan_assignment_engine.get_player_clan.return_value = "Hyuga" # This is no longer needed
    # Configure return values for currency/token mocks (target correct methods)
    currency_system.get_player_balance.return_value = 1000
    token_system.get_player_tokens.return_value = 50

    # Call the command callback
    await character_commands.profile.callback(character_commands, mock_interaction)

    # Assertions
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    character_system.get_character.assert_awaited_once_with(user_id)
    # Check currency/token systems were called AND awaited (target correct methods)
    currency_system.get_player_balance.assert_awaited_once_with(user_id)
    token_system.get_player_tokens.assert_awaited_once_with(user_id)
    # Check the followup message embed
    mock_interaction.followup.send.assert_awaited_once()
    _, kwargs = mock_interaction.followup.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert embed.title == "Test User's Shinobi Profile"
    assert any(field.name == "⚜️ Clan" and field.value == "Hyuga" for field in embed.fields)
    # Check the exact format of the currency field value
    expected_currency_value = f"**Ryō:** {1000}\n**Tokens:** {50}"
    assert any(field.name == "💰 Currency" and field.value == expected_currency_value for field in embed.fields)

@pytest.mark.asyncio
async def test_profile_no_character(character_commands, mock_interaction, mock_bot_with_services):
    """Test /profile when the user has no character."""
    user_id = mock_interaction.user.id
    character_system = mock_bot_with_services.services.character_system

    # Mock system to return None
    character_system.get_character.return_value = None

    # Call the command callback
    await character_commands.profile.callback(character_commands, mock_interaction)

    # Assertions
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
    character_system.get_character.assert_awaited_once_with(user_id)
    # Check the followup message - should be ephemeral
    mock_interaction.followup.send.assert_awaited_once_with(
        "You don't have a character yet! Use `/create` to start your journey.",
        ephemeral=True # Ensure this keyword arg is present
    )

# Remove obsolete countdown test
# @pytest.mark.asyncio
# async def test_countdown_command(announcement_commands, mock_bot):
#     """Test the countdown command by calling the underlying method directly."""
#
#     # --- Create mocks manually within the test ---
#     interaction = AsyncMock()
#     interaction.user = MagicMock() # Use MagicMock for simple attributes
#     interaction.user.id = 12345
#     # interaction.guild = MagicMock() # Not needed directly by countdown method
#     # interaction.channel_id = 98765 # Not needed directly by countdown method
#
#     # Mock response and its methods
#     interaction.response = AsyncMock()
#     interaction.response.defer = AsyncMock()
#
#     # Mock followup and its methods
#     interaction.followup = AsyncMock()
#     interaction.followup.send = AsyncMock()
#
#     # --- Store captured description ---
#     captured_initial_description = None
#
#     # --- Create the mock message instance OUTSIDE the side effect ---
#     mock_sent_message = AsyncMock()
#     mock_sent_message.edit = AsyncMock()
#
#     # --- Side effect function to capture embed state and return CONSISTENT mock message ---
#     async def send_side_effect(*args, **kwargs):
#         nonlocal captured_initial_description
#         if 'embed' in kwargs:
#             captured_initial_description = kwargs['embed'].description
#         # Return the SAME pre-configured mock message instance
#         return mock_sent_message
#
#     # Configure bot mocks (get_channel, channel.send, message.edit)
#     mock_channel = AsyncMock()
#     # Apply the side effect to capture the description
#     mock_channel.send = AsyncMock(side_effect=send_side_effect)
#
#     # Ensure the mock_bot fixture's get_channel returns our mock channel
#     mock_bot.get_channel.return_value = mock_channel
#     # Set the announcement channel ID used by the command
#     mock_bot.announcement_channel_id = 98765
#     # --- End Mock Setup ---
#
#     # Patch sleep manually if needed, or rely on timing if acceptable for this test.
#     with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep: # Patch sleep manually
#
#         # Call the underlying implementation method directly
#         await announcement_commands.countdown(interaction, minutes=1, reason="Test maintenance")
#
#         # Assertions
#         interaction.response.defer.assert_awaited_once_with(ephemeral=True)
#
#         # Check the send call arguments
#         mock_channel = mock_bot.get_channel.return_value
#         mock_channel.send.assert_awaited_once()
#         # Use assert_awaited_once_with for more precise argument checking if needed,
#         # but checking the captured args is often clearer for complex objects like embeds.
#         # We no longer need to get args from call_args, use the captured description
#         # _call_args, call_kwargs = mock_channel.send.call_args 
#         # assert 'embed' in call_kwargs
#         # sent_embed = call_kwargs['embed']
#         # initial_description = sent_embed.description # No longer needed
#         
#         # Assertions on the captured description
#         assert captured_initial_description is not None
#         # assert sent_embed.title == "⚠️ System Maintenance Countdown" # Title check remains valid if needed on call_args
#         # Check the actual initial description content
#         assert f"**Reason:** Test maintenance" in captured_initial_description
#         assert "Time Remaining:** 1 minutes" in captured_initial_description # More specific check
#
#         # The loop runs (sleep is patched), editing the message
#         mock_sleep.assert_awaited_once_with(60) 
#
#         # Check the edit call arguments (should be called twice for minutes=1: once in loop, once after)
#         # Assert edit on the specific mock_sent_message instance created earlier
#         # mock_sent_message.edit.assert_awaited_once() # Incorrect: Edit is called twice for minutes=1
#         assert mock_sent_message.edit.await_count == 2
#         # We can check the args of the *last* call if needed
#         _call_args_edit, call_kwargs_edit = mock_sent_message.edit.call_args 
#         assert 'embed' in call_kwargs_edit
#         edited_embed = call_kwargs_edit['embed'] 
#         # Assert the state of the embed *as it was passed to the final edit*
#         final_description = edited_embed.description
#         # Check the final description content
#         assert "System is now going down for maintenance!" in final_description
#         assert "Time Remaining:** 0 minutes" in final_description # More specific check
#
#         interaction.followup.send.assert_awaited_once_with("✅ Countdown completed!", ephemeral=True) 

@pytest.mark.asyncio
async def test_commands_command():
    """Test that the 'commands' command lists all available commands."""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    list_commands = register_commands_command(bot)
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    # Add some dummy commands for test
    @bot.command(name="inventory")
    async def inventory(ctx): pass
    @bot.command(name="jutsu")
    async def jutsu(ctx): pass
    await list_commands(ctx)
    ctx.send.assert_called_once()
    message = ctx.send.call_args[0][0]
    assert "Available commands:" in message
    assert "!inventory" in message
    assert "!jutsu" in message
    assert "!commands" in message

@pytest.mark.asyncio
async def test_all_commands_listed():
    """Test that the 'commands' command lists all registered commands."""
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    list_commands = register_commands_command(bot)
    ctx = AsyncMock(spec=commands.Context)
    ctx.send = AsyncMock()
    # Register a set of known commands
    @bot.command(name="inventory")
    async def inventory(ctx): pass
    @bot.command(name="jutsu")
    async def jutsu(ctx): pass
    @bot.command(name="status")
    async def status(ctx): pass
    @bot.command(name="missions")
    async def missions(ctx): pass
    @bot.command(name="team")
    async def team(ctx): pass
    @bot.command(name="clan")
    async def clan(ctx): pass
    @bot.command(name="shop")
    async def shop(ctx): pass
    @bot.command(name="balance")
    async def balance(ctx): pass
    @bot.command(name="train")
    async def train(ctx): pass
    await list_commands(ctx)
    ctx.send.assert_called_once()
    message = ctx.send.call_args[0][0]
    assert "Available commands:" in message
    assert "!inventory" in message
    assert "!jutsu" in message
    assert "!status" in message
    assert "!missions" in message
    assert "!team" in message
    assert "!clan" in message
    assert "!shop" in message
    assert "!balance" in message
    assert "!train" in message
    assert "!commands" in message 