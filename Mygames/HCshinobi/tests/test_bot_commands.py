import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from HCshinobi.bot.bot import HCShinobiBot
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer

@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    return BotConfig(
        token="test_token",
        guild_id=123456789,
        command_channel_id=987654321,
        battle_channel_id=987654322,
        online_channel_id=987654323,
        announcement_channel_id=987654324,
        webhook_url="https://test.webhook.url",
        data_dir="test_data",
        ollama_base_url="http://localhost:11434",
        ollama_model="test_model",
        openai_api_key=None,
        openai_target_url=None,
        openai_headless=False,
        command_prefix="!"
    )

@pytest.fixture
def mock_services():
    """Create a mock services container for testing."""
    services = MagicMock(spec=ServiceContainer)
    services.initialize = AsyncMock()
    services.shutdown = AsyncMock()
    return services

@pytest.fixture
def mock_user():
    """Create a mock Discord user."""
    user = MagicMock(spec=discord.User)
    user.name = "Test Bot"
    user.id = 987654321
    user.edit = AsyncMock()
    return user

@pytest.fixture
def mock_channel():
    """Create a mock Discord channel."""
    channel = AsyncMock(spec=discord.TextChannel)
    channel.send = AsyncMock()
    return channel

@pytest.fixture
def mock_guild():
    """Create a mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.name = "Test Guild"
    guild.id = 123456789
    return guild

@pytest.fixture
def mock_bot(mock_config, mock_services, mock_user, mock_channel, mock_guild):
    """Create a mock bot instance for testing."""
    bot = HCShinobiBot(mock_config, mock_services)
    
    # Mock the bot's connection
    bot._connection = MagicMock()
    bot._connection.user = mock_user
    bot._connection._guilds = {mock_guild.id: mock_guild}
    
    # Mock other methods
    bot.process_commands = AsyncMock()
    bot.get_channel = MagicMock(return_value=mock_channel)
    bot.get_guild = MagicMock(return_value=mock_guild)
    return bot

@pytest.fixture
def mock_message(mock_user):
    """Create a mock message for testing."""
    message = AsyncMock(spec=discord.Message)
    message.author = MagicMock(spec=discord.User)
    message.author.id = 123456789
    message.channel = MagicMock(spec=discord.TextChannel)
    message.channel.id = 987654321
    message.content = "!test"
    return message

@pytest.mark.asyncio
async def test_command_channel_check(mock_bot, mock_message):
    """Test that commands are only processed in the command channel."""
    # Test in correct channel
    mock_message.channel.id = mock_bot.config.command_channel_id
    await mock_bot.events.on_message(mock_message)
    mock_bot.process_commands.assert_called_once_with(mock_message)

    # Test in wrong channel
    mock_bot.process_commands.reset_mock()
    mock_message.channel.id = 999999999
    await mock_bot.events.on_message(mock_message)
    mock_bot.process_commands.assert_not_called()

@pytest.mark.asyncio
async def test_bot_ignores_own_messages(mock_bot, mock_message, mock_user):
    """Test that the bot ignores its own messages."""
    mock_message.author = mock_user
    await mock_bot.events.on_message(mock_message)
    mock_bot.process_commands.assert_not_called()

@pytest.mark.asyncio
async def test_command_error_handling(mock_bot):
    """Test command error handling."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.command = MagicMock()
    ctx.command.name = "test_command"
    
    # Test missing permissions error
    error = commands.MissingPermissions(["send_messages"])
    await mock_bot.events.on_command_error(ctx, error)
    ctx.send.assert_called_once_with("You don't have permission to use this command.")

    # Test bot missing permissions error
    ctx.send.reset_mock()
    error = commands.BotMissingPermissions(["send_messages"])
    await mock_bot.events.on_command_error(ctx, error)
    ctx.send.assert_called_once_with("I don't have permission to do that.")

@pytest.mark.asyncio
async def test_bot_initialization(mock_bot):
    """Test bot initialization and ready event."""
    await mock_bot.events.on_ready()
    assert mock_bot.initialized is True
    mock_bot.services.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_online_notification(mock_bot, mock_channel):
    """Test online notification sending."""
    await mock_bot.events.on_ready()
    mock_channel.send.assert_called_once_with("🟢 Shinobi Chronicles is now online!") 