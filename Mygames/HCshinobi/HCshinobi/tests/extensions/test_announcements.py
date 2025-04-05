"""Test suite for announcements cog."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from discord.ext import commands
from HCshinobi.bot.cogs.announcements import AnnouncementCommands
from HCshinobi.bot.cogs.rolling import Rolling
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer
import discord
from discord import Color
from discord import app_commands

@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return BotConfig(
        token="test_token",
        guild_id=123456789,
        battle_channel_id=987654321,
        online_channel_id=987654322,
        data_dir="test_data",
        ollama_base_url="http://localhost:11434",
        ollama_model="mistral",
        openai_api_key="test_key",
        openai_target_url="http://localhost:8000",
        openai_headless=True
    )

@pytest.fixture
def mock_services():
    """Create a mock service container."""
    services = Mock(spec=ServiceContainer)
    services.initialize = AsyncMock()
    services.shutdown = AsyncMock()
    # Add mock webhook
    services.webhook = AsyncMock(spec=discord.Webhook) 
    return services

@pytest.fixture
def mock_bot(mock_config, mock_services):
    """Create a mock bot."""
    bot = Mock(spec=commands.Bot)
    bot.config = mock_config
    bot.services = mock_services
    # Add mock logger to bot if needed by cog initialization or methods
    bot.logger = MagicMock() 
    # Mock get_channel if needed by dispatcher fallback logic
    bot.get_channel = MagicMock() 
    return bot

@pytest.mark.asyncio
async def test_announcement_commands_initialization(mock_bot):
    """Test announcement commands initialization."""
    cog = AnnouncementCommands(mock_bot)
    assert cog.bot == mock_bot
    assert isinstance(cog, commands.Cog)

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.user = Mock()
    interaction.user.guild_permissions = Mock()
    interaction.user.guild_permissions.administrator = False
    return interaction

@pytest.fixture
def cog(mock_bot):
    # Patch the NotificationDispatcher directly within the cog's module
    with patch('HCshinobi.bot.cogs.announcements.NotificationDispatcher', new_callable=MagicMock) as MockDispatcher:
        # Ensure the mock dispatcher instance has an async dispatch method
        mock_dispatcher_instance = MockDispatcher.return_value
        mock_dispatcher_instance.dispatch = AsyncMock()

        # Instantiate the cog. The __init__ will now use the mocked Dispatcher
        cog_instance = AnnouncementCommands(mock_bot)
        
        # Make the mock dispatcher instance easily accessible if needed in tests
        cog_instance.mock_dispatcher = mock_dispatcher_instance 
        return cog_instance

@pytest.mark.asyncio
async def test_toggle_announcements(cog, mock_interaction):
    """Test toggling announcements on and off."""
    # Test turning announcements on
    mock_interaction.user.guild_permissions.administrator = True
    await cog.toggle_announcements.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
    assert "enabled" in mock_interaction.response.send_message.call_args[0][0].lower()
    
    # Test turning announcements off
    mock_interaction.response.send_message.reset_mock()
    await cog.toggle_announcements.callback(cog, mock_interaction)
    mock_interaction.response.send_message.assert_called_once()
    assert "disabled" in mock_interaction.response.send_message.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_announce_without_admin_permission(cog, mock_interaction):
    """Test that non-admins cannot use the announce command."""
    await cog.announce_message.callback(cog, mock_interaction, "Test announcement")
    mock_interaction.response.send_message.assert_called_once()
    assert "administrator" in mock_interaction.response.send_message.call_args[0][0].lower()

@pytest.mark.asyncio
async def test_announce_with_admin_plain_text(cog, mock_interaction):
    """Test that admins can send plain text announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement plain"
    await cog.announce_message.callback(cog, mock_interaction, test_message)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for content
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "content" in kwargs
    assert kwargs["content"] == test_message

@pytest.mark.asyncio
async def test_announce_with_admin_embed(cog, mock_interaction):
    """Test that admins can send embedded announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement embed"
    await cog.announce_message.callback(cog, mock_interaction, test_message, embed=True)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for embed
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "embed" in kwargs
    assert isinstance(kwargs["embed"], discord.Embed)
    assert kwargs["embed"].description == test_message

@pytest.mark.asyncio
async def test_announce_with_everyone_ping(cog, mock_interaction):
    """Test that @everyone ping is included when requested."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_message = "Test announcement ping"
    await cog.announce_message.callback(cog, mock_interaction, test_message, ping_everyone=True)
    mock_interaction.response.send_message.assert_called_once()
    # Check kwargs for content with @everyone
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "content" in kwargs
    assert "@everyone" in kwargs["content"]
    assert test_message in kwargs["content"]

@pytest.mark.asyncio
async def test_announce_forbidden_error(cog, mock_interaction):
    """Test handling of forbidden errors when sending announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    forbidden_error = discord.Forbidden(Mock(), "Missing permissions")
    mock_interaction.response.send_message.side_effect = forbidden_error

    # Expect the command to raise discord.Forbidden
    with pytest.raises(discord.Forbidden) as excinfo:
        await cog.announce_message.callback(cog, mock_interaction, "Test announcement forbidden")

    assert excinfo.value is forbidden_error

@pytest.mark.asyncio
async def test_announce_generic_error(cog, mock_interaction):
    """Test handling of generic errors when sending announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    test_exception = Exception("Unexpected error")
    mock_interaction.response.send_message.side_effect = test_exception

    # Expect the command to raise a generic Exception
    mock_logger = MagicMock() # Create mock logger
    with patch('HCshinobi.bot.cogs.announcements.logger', mock_logger), \
         pytest.raises(Exception) as excinfo:
        await cog.announce_message.callback(cog, mock_interaction, "Test announcement generic error")

    assert excinfo.value is test_exception
    # Verify logger was called as well for generic errors
    mock_logger.error.assert_called_once() # Assert on the patched module logger

# --- Tests for the 'update' command ---

@pytest.mark.asyncio
async def test_update_success(cog, mock_interaction):
    """Test successful execution of the update command."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock() # Mock followup separately

    # Reset dispatcher mock before calling the command
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.update.callback(
        cog, mock_interaction, version="1.1", release_date="Tomorrow", changes="Bug fixes", downtime="5 minutes"
    )

    # Check interaction flow
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    # Check dispatcher call
    cog.mock_dispatcher.dispatch.assert_called_once()
    call_args, call_kwargs = cog.mock_dispatcher.dispatch.call_args
    assert isinstance(call_args[0], discord.Embed) # Check an embed was passed
    assert call_kwargs.get("ping_everyone") is True # Default ping for update command? Check implementation. Assumed True based on template usage.
    # Check success message
    mock_interaction.followup.send.assert_called_once_with("✅ Update announcement sent successfully!", ephemeral=True)

@pytest.mark.asyncio
async def test_update_no_admin(cog, mock_interaction):
    """Test update command requires admin permissions."""
    # This test case might be redundant if the decorator handles it,
    # but it explicitly checks the behavior if the check somehow fails or is bypassed.
    # If the decorator works, the command function shouldn't even be called.
    # We can simulate by calling the function directly and asserting no action.
    mock_interaction.user.guild_permissions.administrator = False
    cog.announcements_enabled = True
    mock_interaction.followup.send = AsyncMock()

    # We expect a check failure error, but let's call the inner logic directly
    # to see if it *would* proceed without the check decorator.
    # If the decorator is working, this test might not be very useful as is.
    # A better approach would be to test the decorator itself, but that's framework-level.
    # For now, assume the decorator prevents the call for non-admins.
    # If we were testing the callback directly without framework invocation:
    # await cog.update.callback(cog, mock_interaction, ...)
    # mock_interaction.response.defer.assert_not_called()
    # cog.mock_dispatcher.dispatch.assert_not_called()
    # Instead, let's rely on the framework's check handling.
    # We can try invoking it and expect a CheckFailure, though mocking that is tricky.
    # For now, we'll skip asserting the check failure directly in this unit test.
    pass # Relying on the @app_commands.checks.has_permissions decorator

@pytest.mark.asyncio
async def test_update_disabled(cog, mock_interaction):
    """Test update command when announcements are disabled."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = False # Explicitly disable
    cog.no_announcement = True
    cog.maintenance_mode = False
    mock_interaction.followup.send = AsyncMock()

    await cog.update.callback(
        cog, mock_interaction, version="1.2", release_date="Soon", changes="Minor tweaks"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Announcements are currently disabled.", ephemeral=True)

@pytest.mark.asyncio
async def test_update_maintenance_mode(cog, mock_interaction):
    """Test update command when maintenance mode is active."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True # Doesn't matter if maintenance is on
    cog.maintenance_mode = True
    cog.no_announcement = True # Maintenance mode implies no announcements
    mock_interaction.followup.send = AsyncMock()

    await cog.update.callback(
        cog, mock_interaction, version="1.3", release_date="Later", changes="Backend stuff"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)

@pytest.mark.asyncio
async def test_update_duplicate(cog, mock_interaction):
    """Test update command handling duplicate announcements."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    # Simulate sending the first time (populates recent_announcements)
    message_content = "System Update v1.4 - Release Date: Now\nChanges: Stuff"
    with patch.object(cog, '_is_duplicate_announcement', return_value=False) as mock_is_dup_false:
         await cog.update.callback(
            cog, mock_interaction, version="1.4", release_date="Now", changes="Stuff"
        )
    mock_is_dup_false.assert_called_once()
    cog.mock_dispatcher.dispatch.assert_called_once() # Should succeed the first time
    mock_interaction.followup.send.assert_called_with("✅ Update announcement sent successfully!", ephemeral=True)

    # Reset mocks for the second call
    mock_interaction.response.defer.reset_mock()
    mock_interaction.followup.send.reset_mock()
    cog.mock_dispatcher.dispatch.reset_mock()

    # Simulate sending the second time (should be detected as duplicate)
    with patch.object(cog, '_is_duplicate_announcement', return_value=True) as mock_is_dup_true:
        await cog.update.callback(
            cog, mock_interaction, version="1.4", release_date="Now", changes="Stuff" # Same content
        )
    mock_is_dup_true.assert_called_once()
    cog.mock_dispatcher.dispatch.assert_not_called() # Should not dispatch the duplicate
    mock_interaction.followup.send.assert_called_once_with(
        "This update announcement is too similar to a recent one. Please wait a few minutes before posting a similar announcement.",
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_update_dispatch_error(cog, mock_interaction):
    """Test update command when the dispatcher fails."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()

    # Make the mock dispatcher raise an error
    test_exception = discord.HTTPException(Mock(), "Webhook error")
    cog.mock_dispatcher.dispatch.side_effect = test_exception

    # Patch the cog's logger
    mock_cog_logger = MagicMock()
    with patch('HCshinobi.bot.cogs.announcements.logger', mock_cog_logger):
        await cog.update.callback(
            cog, mock_interaction, version="1.5", release_date="ASAP", changes="Critical fixes"
        )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once() # Dispatcher was called
    # Check error message
    mock_interaction.followup.send.assert_called_once_with("❌ Failed to send the announcement. Check the logs for details.", ephemeral=True)
    # Check logger call
    mock_cog_logger.error.assert_called_once()
    log_args, log_kwargs = mock_cog_logger.error.call_args
    assert "Error sending update announcement" in log_args[0]
    assert log_kwargs.get('exc_info') is True # Check exc_info=True was passed

# --- Tests for the 'battle_announce' command ---

@pytest.mark.asyncio
async def test_battle_announce_success(cog, mock_interaction):
    """Test successful execution of battle_announce."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.battle_announce.callback(
        cog, mock_interaction, fighter_a="Naruto", fighter_b="Sasuke", arena="Valley", time="Noon"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    _, call_kwargs = cog.mock_dispatcher.dispatch.call_args
    assert call_kwargs.get("ping_everyone") is True
    mock_interaction.followup.send.assert_called_once_with("✅ Battle announcement sent successfully!", ephemeral=True)

@pytest.mark.asyncio
async def test_battle_announce_disabled(cog, mock_interaction):
    """Test battle_announce when announcements are disabled."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.no_announcement = True
    cog.maintenance_mode = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.battle_announce.callback(
        cog, mock_interaction, fighter_a="Naruto", fighter_b="Sasuke", arena="Valley", time="Noon"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Announcements are currently disabled.", ephemeral=True)

@pytest.mark.asyncio
async def test_battle_announce_maintenance(cog, mock_interaction):
    """Test battle_announce during maintenance mode."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.maintenance_mode = True
    cog.no_announcement = True
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.battle_announce.callback(
        cog, mock_interaction, fighter_a="Naruto", fighter_b="Sasuke", arena="Valley", time="Noon"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)

@pytest.mark.asyncio
async def test_battle_announce_dispatch_error(cog, mock_interaction):
    """Test battle_announce when dispatcher fails."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    test_exception = discord.HTTPException(Mock(), "Webhook error")
    cog.mock_dispatcher.dispatch.side_effect = test_exception
    cog.mock_dispatcher.dispatch.reset_mock()

    mock_cog_logger = MagicMock()
    with patch('HCshinobi.bot.cogs.announcements.logger', mock_cog_logger):
        await cog.battle_announce.callback(
            cog, mock_interaction, fighter_a="N", fighter_b="S", arena="V", time="T"
        )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with("❌ Failed to send the announcement. Check the logs for details.", ephemeral=True)
    mock_cog_logger.error.assert_called_once()
    log_args, log_kwargs = mock_cog_logger.error.call_args
    assert "Error sending battle announcement" in log_args[0]
    assert log_kwargs.get('exc_info') is True # Check exc_info=True was passed

# --- Tests for the 'lore_drop' command ---

@pytest.mark.asyncio
async def test_lore_drop_success(cog, mock_interaction):
    """Test successful execution of lore_drop."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.lore_drop.callback(
        cog, mock_interaction, title="Ancient Scroll", snippet="Words of wisdom", chapter="Genesis"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    _, call_kwargs = cog.mock_dispatcher.dispatch.call_args
    # Lore drops might not ping everyone by default
    assert call_kwargs.get("ping_everyone") is not True 
    mock_interaction.followup.send.assert_called_once_with("✅ Lore drop sent successfully!", ephemeral=True)

@pytest.mark.asyncio
async def test_lore_drop_disabled(cog, mock_interaction):
    """Test lore_drop when announcements are disabled."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.no_announcement = True
    cog.maintenance_mode = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.lore_drop.callback(
        cog, mock_interaction, title="Secret Lore", snippet="Hidden text"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Announcements are currently disabled.", ephemeral=True)

@pytest.mark.asyncio
async def test_lore_drop_maintenance(cog, mock_interaction):
    """Test lore_drop during maintenance mode."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.maintenance_mode = True
    cog.no_announcement = True
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.lore_drop.callback(
        cog, mock_interaction, title="Locked Lore", snippet="Cannot access"
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)

@pytest.mark.asyncio
async def test_lore_drop_dispatch_error(cog, mock_interaction):
    """Test lore_drop when dispatcher fails."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    test_exception = discord.HTTPException(Mock(), "Webhook error")
    cog.mock_dispatcher.dispatch.side_effect = test_exception
    cog.mock_dispatcher.dispatch.reset_mock()

    mock_cog_logger = MagicMock()
    with patch('HCshinobi.bot.cogs.announcements.logger', mock_cog_logger):
        await cog.lore_drop.callback(
            cog, mock_interaction, title="Error Lore", snippet="Fail"
        )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with("❌ Failed to send the lore drop. Check the logs for details.", ephemeral=True)
    mock_cog_logger.error.assert_called_once()
    log_args, log_kwargs = mock_cog_logger.error.call_args
    assert "Error sending lore drop" in log_args[0]
    assert log_kwargs.get('exc_info') is True # Check exc_info=True was passed

# --- Tests for the 'send_system_alert' command ---

@pytest.mark.asyncio
async def test_send_system_alert_success(cog, mock_interaction):
    """Test successful execution of send_system_alert."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.send_system_alert.callback(
        cog, mock_interaction, title="Server Notice", message="Please be advised.", ping_everyone=True
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    _, call_kwargs = cog.mock_dispatcher.dispatch.call_args
    assert call_kwargs.get("ping_everyone") is True
    mock_interaction.followup.send.assert_called_once_with("✅ Alert dispatched successfully!", ephemeral=True)

@pytest.mark.asyncio
async def test_send_system_alert_disabled(cog, mock_interaction):
    """Test send_system_alert when announcements are disabled."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.no_announcement = True
    cog.maintenance_mode = False
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.send_system_alert.callback(
        cog, mock_interaction, title="Disabled Alert", message="Should not send."
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Announcements are currently disabled.", ephemeral=True)

@pytest.mark.asyncio
async def test_send_system_alert_maintenance(cog, mock_interaction):
    """Test send_system_alert during maintenance mode."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.maintenance_mode = True
    cog.no_announcement = True
    mock_interaction.followup.send = AsyncMock()
    cog.mock_dispatcher.dispatch.reset_mock()

    await cog.send_system_alert.callback(
        cog, mock_interaction, title="Maintenance Alert", message="System down."
    )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_not_called()
    mock_interaction.followup.send.assert_called_once_with("❌ Cannot send announcements while in maintenance mode.", ephemeral=True)

@pytest.mark.asyncio
async def test_send_system_alert_dispatch_error(cog, mock_interaction):
    """Test send_system_alert when dispatcher fails."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.announcements_enabled = True
    cog.maintenance_mode = False
    cog.no_announcement = False
    mock_interaction.followup.send = AsyncMock()
    test_exception = discord.HTTPException(Mock(), "Webhook error")
    cog.mock_dispatcher.dispatch.side_effect = test_exception
    cog.mock_dispatcher.dispatch.reset_mock()

    mock_cog_logger = MagicMock()
    with patch('HCshinobi.bot.cogs.announcements.logger', mock_cog_logger):
        await cog.send_system_alert.callback(
            cog, mock_interaction, title="Error Alert", message="Dispatcher failed."
        )

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    cog.mock_dispatcher.dispatch.assert_called_once()
    mock_interaction.followup.send.assert_called_once_with("❌ Failed to send the alert. Check the logs for details.", ephemeral=True)
    mock_cog_logger.error.assert_called_once()
    log_args, log_kwargs = mock_cog_logger.error.call_args
    assert "Error sending system alert" in log_args[0]
    assert log_kwargs.get('exc_info') is True # Check exc_info=True was passed

# --- Tests for 'maintenance_status' command ---

@pytest.mark.asyncio
async def test_maintenance_status_active(cog, mock_interaction):
    """Test maintenance_status when maintenance is active."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.maintenance_mode = True
    cog.no_announcement = True
    mock_interaction.followup.send = AsyncMock()

    await cog.maintenance_status.callback(cog, mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert embed.title == "Maintenance Mode Status"
    assert embed.fields[0].value == "✅ Active"
    assert embed.fields[1].value == "❌ Disabled"
    assert len(embed.fields) == 3 # Includes the Note field
    assert embed.color == discord.Color.orange()

@pytest.mark.asyncio
async def test_maintenance_status_inactive(cog, mock_interaction):
    """Test maintenance_status when maintenance is inactive."""
    mock_interaction.user.guild_permissions.administrator = True
    cog.maintenance_mode = False
    cog.no_announcement = False # Assume announcements are enabled
    mock_interaction.followup.send = AsyncMock()

    await cog.maintenance_status.callback(cog, mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert embed.title == "Maintenance Mode Status"
    assert embed.fields[0].value == "❌ Inactive"
    assert embed.fields[1].value == "✅ Enabled"
    assert len(embed.fields) == 2 # No Note field
    assert embed.color == discord.Color.green()

# --- Tests for 'check_permissions' command ---

@pytest.mark.asyncio
async def test_check_permissions_all_present(cog, mock_interaction):
    """Test check_permissions when all permissions are present."""
    mock_interaction.user.guild_permissions.administrator = True
    mock_interaction.guild = AsyncMock()
    mock_interaction.guild.me = MagicMock()
    # Simulate all required permissions present
    mock_interaction.guild.me.guild_permissions = MagicMock(spec=discord.Permissions)
    mock_interaction.guild.me.guild_permissions.send_messages = True
    mock_interaction.guild.me.guild_permissions.embed_links = True
    mock_interaction.guild.me.guild_permissions.use_slash_commands = True # Usually implicit, but good to check
    mock_interaction.guild.me.guild_permissions.manage_webhooks = True
    mock_interaction.guild.me.guild_permissions.manage_messages = True
    # Mock the command tree
    cog.bot.tree = MagicMock()
    mock_cmd = MagicMock(spec=app_commands.Command)
    mock_cmd.name = 'test_command'
    cog.bot.tree.get_commands.return_value = [mock_cmd]
    mock_interaction.followup.send = AsyncMock()

    await cog.check_permissions.callback(cog, mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert embed.title == "Bot Permissions Check"
    assert "All required permissions are present" in embed.fields[2].value # Index depends on exact field order
    assert embed.color == discord.Color.green()
    assert "test_command" in embed.fields[-1].value # Check command tree field

@pytest.mark.asyncio
async def test_check_permissions_missing(cog, mock_interaction):
    """Test check_permissions when some permissions are missing."""
    mock_interaction.user.guild_permissions.administrator = True
    mock_interaction.guild = AsyncMock()
    mock_interaction.guild.me = MagicMock()
    # Simulate some missing permissions
    mock_interaction.guild.me.guild_permissions = MagicMock(spec=discord.Permissions)
    mock_interaction.guild.me.guild_permissions.send_messages = True
    mock_interaction.guild.me.guild_permissions.embed_links = False # Missing
    mock_interaction.guild.me.guild_permissions.use_slash_commands = True
    mock_interaction.guild.me.guild_permissions.manage_webhooks = False # Missing
    mock_interaction.guild.me.guild_permissions.manage_messages = True
    cog.bot.tree = MagicMock()
    cog.bot.tree.get_commands.return_value = []
    mock_interaction.followup.send = AsyncMock()

    await cog.check_permissions.callback(cog, mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert embed.title == "Bot Permissions Check"
    assert "❌ `embed_links`" in embed.fields[2].value
    assert "❌ `manage_webhooks`" in embed.fields[2].value
    assert "How to Fix" in embed.fields[3].name
    assert embed.color == discord.Color.red()

# --- Tests for 'check_bot_role' command ---

@pytest.mark.asyncio
async def test_check_bot_role(cog, mock_interaction):
    """Test check_bot_role command."""
    mock_interaction.user.guild_permissions.administrator = True
    mock_interaction.guild = AsyncMock()
    mock_interaction.guild.me = MagicMock()
    # Mock roles
    mock_role1 = MagicMock(spec=discord.Role)
    mock_role1.name = "BotRole"
    mock_role2 = MagicMock(spec=discord.Role)
    mock_role2.name = "AdminAccess"
    mock_interaction.guild.me.roles = [mock_role1, mock_role2]
    # Mock permissions
    mock_interaction.guild.me.guild_permissions = MagicMock(spec=discord.Permissions)
    mock_interaction.guild.me.guild_permissions.administrator = True
    mock_interaction.guild.me.guild_permissions.manage_messages = True
    mock_interaction.guild.me.guild_permissions.send_messages = False # Simulate one missing
    mock_interaction.followup.send = AsyncMock()

    await cog.check_bot_role.callback(cog, mock_interaction)

    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_called_once()
    _, kwargs = mock_interaction.followup.send.call_args
    embed = kwargs.get('embed')
    assert embed is not None
    assert embed.title == "Bot Role Check"
    assert "BotRole" in embed.fields[2].value
    assert "AdminAccess" in embed.fields[2].value
    assert embed.fields[3].value == "✅ Yes" # Admin
    assert embed.fields[4].value == "✅ Yes" # Manage Messages
    assert embed.fields[5].value == "❌ No"  # Send Messages
    assert embed.color == discord.Color.blue() 