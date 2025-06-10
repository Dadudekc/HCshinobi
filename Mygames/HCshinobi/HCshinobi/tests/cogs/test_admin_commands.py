import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord import app_commands

# Import the actual cog
from HCshinobi.bot.cogs.admin_commands import AdminCommands 

# Import necessary systems (adjust paths as needed)
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.core.clan_system import ClanSystem
# from HCshinobi.core.lore_system import LoreSystem # Assume this path # Commented out

# --- Fixtures ---

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Bot instance."""
    bot = MagicMock()
    bot.get_channel = MagicMock() # For announcements
    # Mock guilds for broadcast
    guild = MagicMock(spec=discord.Guild)
    guild.id = 12345 # Example guild ID
    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.name = 'general'
    mock_channel.permissions_for.return_value = discord.Permissions(send_messages=True)
    mock_channel.send = AsyncMock()
    guild.text_channels = [mock_channel]
    
    # Mock bot member for permission checks
    mock_bot_member = MagicMock(spec=discord.Member)
    mock_role = MagicMock(spec=discord.Role)
    mock_role.name = "BotRole"
    mock_role.permissions = discord.Permissions(read_messages=True, send_messages=True)
    mock_bot_member.roles = [guild.default_role, mock_role]
    mock_bot_member.guild_permissions = mock_role.permissions 
    guild.me = mock_bot_member
    bot.guilds = [guild]
    
    return bot

# Mock systems needed by admin commands
@pytest.fixture
def mock_currency_system():
    mock = AsyncMock(spec=CurrencySystem)
    mock.add_balance_and_save = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_battle_system():
    mock = AsyncMock(spec=BattleSystem)
    mock.admin_clear_battle = AsyncMock(return_value=True)
    return mock

@pytest.fixture
def mock_clan_system():
    mock = AsyncMock(spec=ClanSystem)
    mock.get_clan_info = AsyncMock()
    return mock

# Comment out mock_lore_system fixture
# @pytest.fixture
# def mock_lore_system():
#     mock = AsyncMock(spec=LoreSystem)
#     mock.get_lore_entry = AsyncMock()
#     return mock

# Mock interaction with admin permissions
@pytest.fixture
def mock_admin_interaction(mock_bot): # Pass mock_bot to access guild
    """Fixture for a mocked discord.Interaction with admin permissions."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member) # Use Member for permissions
    interaction.user.id = 111 # Admin user ID
    interaction.user.mention = "<@111>"
    interaction.user.display_name = "AdminUser"
    interaction.user.guild_permissions = discord.Permissions(administrator=True)
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.guild = mock_bot.guilds[0] # Assign guild from bot
    interaction.channel = mock_bot.guilds[0].text_channels[0] # Assign channel
    interaction.command = MagicMock(spec=app_commands.Command)
    interaction.command.checks = [] # Assume checks pass unless overridden
    # Add is_done mock for error handler check
    interaction.response.is_done = MagicMock(return_value=False)
    return interaction

@pytest.fixture
def mock_target_user():
    """Fixture for a mocked target discord.User."""
    user = MagicMock(spec=discord.User)
    user.id = 999
    user.mention = "<@999>"
    user.display_name = "TargetUser"
    return user

# Remove lore_system from admin_cog fixture parameters and instantiation
@pytest.fixture
def admin_cog(mock_bot, mock_currency_system, mock_battle_system, mock_clan_system):
    """Fixture for the AdminCommands cog instance."""
    # Use the actual cog class, remove lore_system
    cog = AdminCommands(bot=mock_bot, currency_system=mock_currency_system, 
                        battle_system=mock_battle_system, clan_system=mock_clan_system)
    return cog

# --- /add_tokens Tests --- 

@pytest.mark.asyncio
async def test_add_tokens_success(admin_cog, mock_admin_interaction, mock_target_user, mock_currency_system):
    """Test /add_tokens successfully adds tokens to a user."""
    amount = 1000
    target_user_id = str(mock_target_user.id)
    
    # Call actual command callback
    await admin_cog.add_tokens.callback(admin_cog, mock_admin_interaction, user=mock_target_user, amount=amount)

    mock_currency_system.add_balance_and_save.assert_awaited_once_with(target_user_id, amount)
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert f"Successfully added {amount:,} tokens" in args[0]
    assert mock_target_user.mention in args[0]
    assert kwargs.get('ephemeral') is True

@pytest.mark.asyncio
async def test_add_tokens_failure(admin_cog, mock_admin_interaction, mock_target_user, mock_currency_system):
    """Test /add_tokens when adding tokens fails."""
    amount = 500
    target_user_id = str(mock_target_user.id)
    mock_currency_system.add_balance_and_save.return_value = False # Simulate failure
    
    # Call actual command callback
    await admin_cog.add_tokens.callback(admin_cog, mock_admin_interaction, user=mock_target_user, amount=amount)

    mock_currency_system.add_balance_and_save.assert_awaited_once_with(target_user_id, amount)
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert "Failed to add tokens" in args[0]
    assert kwargs.get('ephemeral') is True

# --- /admin_clear_battle Tests ---

@pytest.mark.asyncio
async def test_admin_clear_battle_success(admin_cog, mock_admin_interaction, mock_target_user, mock_battle_system):
    """Test /admin_clear_battle successfully clears a user's battle."""
    target_user_id = str(mock_target_user.id)
    mock_battle_system.admin_clear_battle.return_value = True # Simulate success
    
    # Call actual command callback
    await admin_cog.admin_clear_battle.callback(admin_cog, mock_admin_interaction, user=mock_target_user)

    mock_battle_system.admin_clear_battle.assert_awaited_once_with(target_user_id)
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert f"Successfully cleared active battle for {mock_target_user.mention}" in args[0]
    assert kwargs.get('ephemeral') is True

@pytest.mark.asyncio
async def test_admin_clear_battle_failure(admin_cog, mock_admin_interaction, mock_target_user, mock_battle_system):
    """Test /admin_clear_battle when clearing fails."""
    target_user_id = str(mock_target_user.id)
    mock_battle_system.admin_clear_battle.return_value = False # Simulate failure
    
    # Call actual command callback
    await admin_cog.admin_clear_battle.callback(admin_cog, mock_admin_interaction, user=mock_target_user)

    mock_battle_system.admin_clear_battle.assert_awaited_once_with(target_user_id)
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert "Failed to clear battle" in args[0]
    assert kwargs.get('ephemeral') is True

# --- /alert_clan Tests ---

@pytest.mark.asyncio
async def test_alert_clan_success(admin_cog, mock_admin_interaction, mock_clan_system, mock_bot):
    """Test /alert_clan successfully sends an alert."""
    clan_name = "TargetClan"
    message = "Important meeting tonight!"
    member_ids = ['101', '102', '103']
    clan_info_data = {'name': clan_name, 'members': member_ids, 'description': 'Desc'}
    
    mock_clan_system.get_clan_info.return_value = clan_info_data
    
    # Mock fetch_user and send
    mock_user_101 = MagicMock(spec=discord.User); mock_user_101.bot = False; mock_user_101.send = AsyncMock()
    mock_user_102 = MagicMock(spec=discord.User); mock_user_102.bot = False; mock_user_102.send = AsyncMock()
    mock_user_103 = MagicMock(spec=discord.User); mock_user_103.bot = False; mock_user_103.send = AsyncMock()
    async def fetch_user_side_effect(uid):
        if uid == 101: return mock_user_101
        if uid == 102: return mock_user_102
        if uid == 103: return mock_user_103
        return None
    mock_bot.fetch_user = AsyncMock(side_effect=fetch_user_side_effect)

    # Call actual command callback
    await admin_cog.alert_clan.callback(admin_cog, mock_admin_interaction, clan_name=clan_name, message=message)

    mock_clan_system.get_clan_info.assert_awaited_once_with(clan_name)
    # Assert DMs were sent
    assert mock_bot.fetch_user.await_count == len(member_ids)
    mock_user_101.send.assert_awaited_once()
    mock_user_102.send.assert_awaited_once()
    mock_user_103.send.assert_awaited_once()
        
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert f"Alert sent to {len(member_ids)} members" in args[0]
    assert kwargs.get('ephemeral') is True

@pytest.mark.asyncio
async def test_alert_clan_not_found(admin_cog, mock_admin_interaction, mock_clan_system, mock_bot):
    """Test /alert_clan when the clan is not found."""
    clan_name = "GhostClan"
    message = "Boo!"
    mock_clan_system.get_clan_info.return_value = None # Clan not found

    # Call actual command callback
    await admin_cog.alert_clan.callback(admin_cog, mock_admin_interaction, clan_name=clan_name, message=message)

    mock_clan_system.get_clan_info.assert_awaited_once_with(clan_name)
    mock_bot.fetch_user.assert_not_called() # Ensure DMs weren't attempted
    mock_admin_interaction.response.send_message.assert_awaited_once_with(
        f"❌ Clan '{clan_name}' not found.", ephemeral=True
    )

# Comment out /broadcast_lore tests
# --- /broadcast_lore Tests ---
# 
# @pytest.mark.asyncio
# async def test_broadcast_lore_success(admin_cog, mock_admin_interaction, mock_lore_system, mock_bot):
#     """Test /broadcast_lore successfully broadcasts a lore entry."""
#     lore_id = "village_history"
#     lore_entry_data = {'title': 'Village History', 'content': 'Long ago...', 'image_url': None}
#     mock_lore_system.get_lore_entry.return_value = lore_entry_data
#     
#     # Find the mock channel to assert against
#     mock_channel = mock_bot.guilds[0].text_channels[0]
#     
#     # Call actual command callback
#     await admin_cog.broadcast_lore.callback(admin_cog, mock_admin_interaction, lore_id=lore_id)
# 
#     mock_lore_system.get_lore_entry.assert_awaited_once_with(lore_id)
#     # Check if message was sent to the channel (assuming it sends to first channel found)
#     mock_channel.send.assert_awaited_once()
#     args, kwargs = mock_channel.send.call_args
#     assert 'embed' in kwargs
#     embed = kwargs['embed']
#     assert lore_entry_data['title'] in embed.title
#     assert lore_entry_data['content'] in embed.description
#     
#     mock_admin_interaction.response.send_message.assert_awaited_once_with(f"✅ Lore entry '{lore_id}' broadcasted to 1 guild(s).", ephemeral=True)
# 
# @pytest.mark.asyncio
# async def test_broadcast_lore_not_found(admin_cog, mock_admin_interaction, mock_lore_system):
#     """Test /broadcast_lore when the lore entry is not found."""
#     lore_id = "missing_lore"
#     mock_lore_system.get_lore_entry.return_value = None # Lore not found
# 
#     # Call actual command callback
#     await admin_cog.broadcast_lore.callback(admin_cog, mock_admin_interaction, lore_id=lore_id)
# 
#     mock_lore_system.get_lore_entry.assert_awaited_once_with(lore_id)
#     mock_admin_interaction.response.send_message.assert_awaited_once_with(f"❌ Lore entry '{lore_id}' not found.", ephemeral=True)

# --- /check_bot_role Tests ---

@pytest.mark.asyncio
async def test_check_bot_role_success(admin_cog, mock_admin_interaction):
    """Test /check_bot_role successfully displays bot roles and permissions."""
    # Guild and bot member are mocked in mock_admin_interaction fixture
    mock_role_name = "BotRole" # From fixture

    # Call actual command callback
    await admin_cog.check_bot_role.callback(admin_cog, mock_admin_interaction)

    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert "Bot Roles and Permissions" in embed.title
    assert "Roles" in embed.fields[0].name
    assert mock_role_name in embed.fields[0].value
    assert "Guild Permissions" in embed.fields[1].name
    assert "Send Messages" in embed.fields[1].value
    assert "Read Messages" in embed.fields[1].value
    assert kwargs.get('ephemeral') is True

# --- /check_permissions Tests ---

@pytest.mark.asyncio
async def test_check_permissions_success(admin_cog, mock_admin_interaction):
    """Test /check_permissions successfully displays bot permissions in the current channel."""
    # Guild, channel, bot member are mocked in mock_admin_interaction fixture
    mock_channel = mock_admin_interaction.channel
    mock_bot_member = mock_admin_interaction.guild.me
    
    # Set specific permissions for the bot in this channel
    channel_permissions = discord.Permissions(read_messages=True, send_messages=True, embed_links=True)
    mock_channel.permissions_for.return_value = channel_permissions

    # Call actual command callback
    await admin_cog.check_permissions.callback(admin_cog, mock_admin_interaction)

    # Verify it checked permissions for the bot in the specific channel
    mock_channel.permissions_for.assert_called_once_with(mock_bot_member)
    
    mock_admin_interaction.response.send_message.assert_awaited_once()
    args, kwargs = mock_admin_interaction.response.send_message.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert f"Bot Permissions in #{mock_channel.name}" in embed.title
    assert "Send Messages: Yes" in embed.description # Example permission checks
    assert "Embed Links: Yes" in embed.description
    assert "Manage Messages: No" in embed.description # Example of a missing permission
    assert kwargs.get('ephemeral') is True

# --- Admin Permission Failure Test ---

@pytest.fixture
def mock_non_admin_interaction(mock_bot): # Pass mock_bot to access guild
    """Fixture for a mocked discord.Interaction WITHOUT admin permissions."""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.Member) # Use Member for permissions
    interaction.user.id = 222 # Non-Admin user ID
    interaction.user.mention = "<@222>"
    interaction.user.display_name = "RegularUser"
    # Set non-admin permissions
    interaction.user.guild_permissions = discord.Permissions.none() 
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.guild = mock_bot.guilds[0] # Assign guild
    interaction.channel = mock_bot.guilds[0].text_channels[0] # Assign channel
    interaction.command = MagicMock(spec=app_commands.Command)
    # Add is_done mock
    interaction.response.is_done = MagicMock(return_value=False)
    
    # Simulate the check failing by attaching the CheckFailure error
    # The cog's error handler should catch this
    interaction.command.checks = [app_commands.checks.has_permissions(administrator=True)] # Add the check
    
    return interaction

@pytest.mark.asyncio
async def test_admin_command_permission_failure(admin_cog, mock_non_admin_interaction, mock_target_user):
    """Test that the cog's error handler catches MissingPermissions."""
    # We use add_tokens as an example admin command
    amount = 100

    # The check decorator should raise MissingPermissions before the command runs.
    # We test if the cog_app_command_error handler sends the correct message.
    
    # Simulate the error being passed to the error handler
    error = app_commands.MissingPermissions(['administrator'])
    await admin_cog.cog_app_command_error(mock_non_admin_interaction, error)

    # Assert the expected permission error message was sent by the error handler
    mock_non_admin_interaction.response.send_message.assert_awaited_once_with(
        "❌ You do not have permission to use this command.", 
        ephemeral=True
    )
    # Ensure the actual command logic (adding balance) was not called
    admin_cog.currency_system.add_balance_and_save.assert_not_called()

# TODO: Add tests for permission failures 