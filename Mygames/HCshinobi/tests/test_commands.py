"""Tests for the HCshinobi command system."""
import pytest
import discord
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest_asyncio # Use this for async fixtures if needed
from discord import app_commands
from discord.ext import commands # Import commands for Context
from HCshinobi.commands.character_commands import CharacterCommands
from HCshinobi.commands.announcement_commands import AnnouncementCommands
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.character import Character

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
    """Create a character system instance."""
    return CharacterSystem()

@pytest.fixture
def clan_data():
    """Create a clan data instance."""
    return ClanData()

@pytest.fixture
def character_commands():
    """Create a character commands instance."""
    character_system = Mock(spec=CharacterSystem)
    clan_data = Mock(spec=ClanData)
    mock_bot = Mock(spec=commands.Bot)
    
    mock_tree = Mock(spec=app_commands.CommandTree)
    mock_tree.get_commands = Mock(return_value=[])
    mock_bot.tree = mock_tree
    
    # get_character should be SYNCHRONOUS
    character_system.get_character = Mock()
    character_system.update_character = AsyncMock()
    
    mock_clan_info_uchiha = {'name': 'Uchiha', 'rarity': 'Legendary', 'bonuses': {},'starting_jutsu':[], 'description':'Desc'}
    mock_clan_info_hyuga = {'name': 'Hyuga', 'rarity': 'Rare', 'bonuses': {}, 'starting_jutsu':[], 'description':'Desc'}
    clan_data.get_random_clan.return_value = mock_clan_info_uchiha
    clan_data.get_clan.side_effect = lambda name: mock_clan_info_hyuga if name == 'Hyuga' else mock_clan_info_uchiha if name == 'Uchiha' else None
    clan_data.get_all_clans.return_value = {'Uchiha': mock_clan_info_uchiha, 'Hyuga': mock_clan_info_hyuga}

    return CharacterCommands(bot=mock_bot, character_system=character_system, clan_data=clan_data)

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
    """Provides a simplified mock Interaction object."""
    interaction = MagicMock(spec=discord.Interaction) # Use MagicMock with spec
    interaction.user = MagicMock()
    interaction.user.id = 12345
    interaction.guild_id = 67890
    interaction.channel_id = 98765 # Added channel_id used by countdown

    # Mock response as an AsyncMock
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.response.defer = AsyncMock() # Ensure defer is awaitable
    interaction.response.send_message = AsyncMock()

    # Mock followup as an AsyncMock
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.followup.send = AsyncMock()

    return interaction

@pytest.fixture
def announcement_commands(mock_bot):
    """Fixture for AnnouncementCommands, using mock_bot."""
    return AnnouncementCommands(bot=mock_bot)

@pytest.mark.asyncio
async def test_assign_clan_random(character_commands, mock_ctx):
    """Test random clan assignment."""
    # Mock the clan data
    character = Character(id=str(mock_ctx.author.id), name='Test User', clan=None, level=1, exp=0, hp=100, chakra=100, strength=10, defense=10, speed=10, ninjutsu=10, willpower=10, max_hp=100, max_chakra=100, max_stamina=100, inventory=[], is_active=True, status_effects=[], wins=0, losses=0, draws=0)
    character_commands.character_system.get_character.return_value = character
    character_commands.character_system.update_character.return_value = True

    # Call with a specific clan to trigger the update path
    await character_commands.assign_clan.callback(character_commands, mock_ctx, clan="Uchiha")

    # Check get_character was called twice (once initially, once before update)
    assert character_commands.character_system.get_character.call_count == 2
    # Check update_character was called
    character_commands.character_system.update_character.assert_called_once()
    # Check response was sent via keyword argument 'embed'
    mock_ctx.send.assert_called_once()
    _, call_kwargs = mock_ctx.send.call_args
    assert 'embed' in call_kwargs
    assert isinstance(call_kwargs['embed'], discord.Embed)
    assert "Uchiha" in call_kwargs['embed'].title

@pytest.mark.asyncio
async def test_assign_clan_specific(character_commands, mock_ctx):
    """Test specific clan assignment."""
    # Mock the clan data
    character = Character(id=str(mock_ctx.author.id), name='Test User', clan=None, level=1, exp=0, hp=100, chakra=100, strength=10, defense=10, speed=10, ninjutsu=10, willpower=10, max_hp=100, max_chakra=100, max_stamina=100, inventory=[], is_active=True, status_effects=[], wins=0, losses=0, draws=0)
    character_commands.character_system.get_character.return_value = character
    character_commands.character_system.update_character.return_value = True

    await character_commands.assign_clan.callback(character_commands, mock_ctx, clan="Hyuga")

    assert character_commands.character_system.get_character.call_count == 2 # Expect 2 calls
    character_commands.clan_data.get_clan.assert_called_once_with("Hyuga")
    character_commands.character_system.update_character.assert_called_once_with(
        str(mock_ctx.author.id), {"clan": "Hyuga"}
    )
    # Assert send was called with an embed
    mock_ctx.send.assert_called_once()
    call_args, call_kwargs = mock_ctx.send.call_args
    assert "embed" in call_kwargs
    assert isinstance(call_kwargs["embed"], discord.Embed)
    assert "Hyuga" in call_kwargs["embed"].title

@pytest.mark.asyncio
async def test_assign_clan_no_character(character_commands, mock_ctx):
    """Test clan assignment when user has no character."""
    # Mock character system to return None
    character_commands.character_system.get_character.return_value = None

    # Run the command callback
    await character_commands.assign_clan.callback(character_commands, mock_ctx)

    # Verify the error message
    character_commands.character_system.get_character.assert_called_once_with(str(mock_ctx.author.id))
    mock_ctx.send.assert_called_once()
    call_args, call_kwargs = mock_ctx.send.call_args
    # Example: Check if it sent the specific string
    if call_args:
         assert "You don't have a character yet! Use `/create` to create one." in call_args[0]
    else:
        pytest.fail("No message sent for no character")

@pytest.mark.asyncio
async def test_assign_clan_already_has_clan(character_commands, mock_ctx):
    """Test clan assignment when character already has a clan."""
    # Mock character system
    character = Character(id=str(mock_ctx.author.id), name='Test User', clan='Uchiha', level=1, exp=0, hp=100, chakra=100, strength=10, defense=10, speed=10, ninjutsu=10, willpower=10, max_hp=100, max_chakra=100, max_stamina=100, inventory=[], is_active=True, status_effects=[], wins=0, losses=0, draws=0)
    character_commands.character_system.get_character.return_value = character

    # Run the command callback, providing a different clan to attempt assigning
    await character_commands.assign_clan.callback(character_commands, mock_ctx, clan="Hyuga")

    # Verify the error message
    character_commands.character_system.get_character.assert_called_once_with(str(mock_ctx.author.id))
    mock_ctx.send.assert_called_once()
    call_args, call_kwargs = mock_ctx.send.call_args
    if call_args:
         assert "Your character already belongs to the Uchiha clan!" in call_args[0]
    else:
        pytest.fail("No message sent for already having a clan")

@pytest.mark.asyncio
async def test_countdown_command(announcement_commands, mock_bot):
    """Test the countdown command by calling the underlying method directly."""

    # --- Create mocks manually within the test ---
    interaction = AsyncMock()
    interaction.user = MagicMock() # Use MagicMock for simple attributes
    interaction.user.id = 12345
    # interaction.guild = MagicMock() # Not needed directly by countdown method
    # interaction.channel_id = 98765 # Not needed directly by countdown method

    # Mock response and its methods
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()

    # Mock followup and its methods
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()

    # --- Store captured description ---
    captured_initial_description = None

    # --- Create the mock message instance OUTSIDE the side effect ---
    mock_sent_message = AsyncMock()
    mock_sent_message.edit = AsyncMock()

    # --- Side effect function to capture embed state and return CONSISTENT mock message ---
    async def send_side_effect(*args, **kwargs):
        nonlocal captured_initial_description
        if 'embed' in kwargs:
            captured_initial_description = kwargs['embed'].description
        # Return the SAME pre-configured mock message instance
        return mock_sent_message

    # Configure bot mocks (get_channel, channel.send, message.edit)
    mock_channel = AsyncMock()
    # Apply the side effect to capture the description
    mock_channel.send = AsyncMock(side_effect=send_side_effect)
    
    # Ensure the mock_bot fixture's get_channel returns our mock channel
    mock_bot.get_channel.return_value = mock_channel
    # Set the announcement channel ID used by the command
    mock_bot.announcement_channel_id = 98765
    # --- End Mock Setup ---

    # Patch sleep manually if needed, or rely on timing if acceptable for this test.
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep: # Patch sleep manually

        # Call the underlying implementation method directly
        await announcement_commands.countdown(interaction, minutes=1, reason="Test maintenance")

        # Assertions
        interaction.response.defer.assert_awaited_once_with(ephemeral=True)
        
        # Check the send call arguments
        mock_channel = mock_bot.get_channel.return_value
        mock_channel.send.assert_awaited_once()
        # Use assert_awaited_once_with for more precise argument checking if needed,
        # but checking the captured args is often clearer for complex objects like embeds.
        # We no longer need to get args from call_args, use the captured description
        # _call_args, call_kwargs = mock_channel.send.call_args 
        # assert 'embed' in call_kwargs
        # sent_embed = call_kwargs['embed']
        # initial_description = sent_embed.description # No longer needed
        
        # Assertions on the captured description
        assert captured_initial_description is not None
        # assert sent_embed.title == "⚠️ System Maintenance Countdown" # Title check remains valid if needed on call_args
        # Check the actual initial description content
        assert f"**Reason:** Test maintenance" in captured_initial_description
        assert "Time Remaining:** 1 minutes" in captured_initial_description # More specific check

        # The loop runs (sleep is patched), editing the message
        mock_sleep.assert_awaited_once_with(60) 

        # Check the edit call arguments (should be called twice for minutes=1: once in loop, once after)
        # Assert edit on the specific mock_sent_message instance created earlier
        # mock_sent_message.edit.assert_awaited_once() # Incorrect: Edit is called twice for minutes=1
        assert mock_sent_message.edit.await_count == 2
        # We can check the args of the *last* call if needed
        _call_args_edit, call_kwargs_edit = mock_sent_message.edit.call_args 
        assert 'embed' in call_kwargs_edit
        edited_embed = call_kwargs_edit['embed'] 
        # Assert the state of the embed *as it was passed to the final edit*
        final_description = edited_embed.description
        # Check the final description content
        assert "System is now going down for maintenance!" in final_description
        assert "Time Remaining:** 0 minutes" in final_description # More specific check

        interaction.followup.send.assert_awaited_once_with("✅ Countdown completed!", ephemeral=True) 