import pytest
import discord
from discord.ext import commands
from discord import app_commands
from unittest.mock import AsyncMock, MagicMock, patch
from HCshinobi.bot.cogs.help import HelpCommands

@pytest.fixture
def mock_interaction():
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.user = MagicMock(spec=discord.Member)
    interaction.user.id = 123456789
    interaction.user.name = "TestUser"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 987654321
    interaction.guild.name = "Test Guild"
    return interaction

@pytest.fixture
def mock_bot():
    bot = MagicMock(spec=commands.Bot)
    bot.commands = []
    bot.cogs = {}
    bot.tree = MagicMock()
    return bot

@pytest.mark.asyncio
async def test_help_command(mock_interaction, mock_bot):
    """Test the basic help command functionality."""
    # Setup mock bot with some commands
    async def test_callback(interaction: discord.Interaction):
        pass
    test_cmd = app_commands.Command(
        name="test",
        description="This is a test command",
        callback=test_callback
    )
    mock_bot.tree.get_commands = lambda: [test_cmd]
    
    # Create help cog with support URL
    help_cog = HelpCommands(mock_bot)
    help_cog.support_url = "https://discord.gg/test"
    help_command = help_cog.help

    # Mock the interaction response methods
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    # Call the help command
    await help_command.callback(help_cog, mock_interaction)

    # Verify the interaction was deferred and a response was sent
    mock_interaction.response.defer.assert_awaited_once_with(ephemeral=True)
    mock_interaction.followup.send.assert_awaited_once()

@pytest.mark.asyncio
async def test_help_command_with_specific_command(mock_interaction, mock_bot):
    """Test help command with a specific command argument."""
    async def test_callback(interaction: discord.Interaction):
        pass
    test_cmd = app_commands.Command(
        name="test",
        description="This is a test command",
        callback=test_callback
    )
    mock_bot.tree.get_command = lambda name: test_cmd if name == "test" else None
    help_cog = HelpCommands(mock_bot)
    help_command = help_cog.help

    with patch.object(mock_interaction.response, "send_message", new_callable=AsyncMock) as send_message, \
         patch.object(mock_interaction, "edit_original_response", new_callable=AsyncMock) as edit_original, \
         patch.object(mock_interaction.followup, "send", new_callable=AsyncMock) as followup_send:
        await help_command.callback(help_cog, mock_interaction, command_or_category="test")
        assert send_message.called or edit_original.called or followup_send.called

@pytest.mark.asyncio
async def test_help_command_with_category(mock_interaction, mock_bot):
    """Test help command with a specific category."""
    class TestCog(commands.Cog):
        @property
        def qualified_name(self):
            return "Test Category"
    test_cog = TestCog()
    async def test_callback(interaction: discord.Interaction):
        pass
    test_cmd = app_commands.Command(
        name="test",
        description="Test command",
        callback=test_callback
    )
    mock_bot.tree.get_commands = lambda: [test_cmd]
    mock_bot.cogs = {"Test Category": test_cog}
    help_cog = HelpCommands(mock_bot)
    help_command = help_cog.help

    with patch.object(mock_interaction.response, "send_message", new_callable=AsyncMock) as send_message, \
         patch.object(mock_interaction, "edit_original_response", new_callable=AsyncMock) as edit_original, \
         patch.object(mock_interaction.followup, "send", new_callable=AsyncMock) as followup_send:
        await help_command.callback(help_cog, mock_interaction, command_or_category="Test Category")
        assert send_message.called or edit_original.called or followup_send.called

@pytest.mark.asyncio
async def test_help_command_error_handling(mock_interaction, mock_bot):
    """Test help command error handling."""
    help_cog = HelpCommands(mock_bot)
    help_command = help_cog.help

    with patch.object(mock_interaction.response, "send_message", new_callable=AsyncMock) as send_message, \
         patch.object(mock_interaction, "edit_original_response", new_callable=AsyncMock) as edit_original, \
         patch.object(mock_interaction.followup, "send", new_callable=AsyncMock) as followup_send:
        await help_command.callback(help_cog, mock_interaction, command_or_category="nonexistent")
        assert send_message.called or edit_original.called or followup_send.called 