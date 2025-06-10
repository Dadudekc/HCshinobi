"""Test configuration and fixtures."""
import os
import json
import pytest
import tempfile
from pathlib import Path
import shutil
from unittest.mock import MagicMock, AsyncMock, patch
import pytest_asyncio
from HCshinobi.core.token_system import TokenSystem, TOKEN_FILE, TOKEN_LOG_FILE
import discord
import aiohttp
from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.personality_modifiers import PersonalityModifiers
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.clan_system import ClanSystem
from HCshinobi.core.battle_system import BattleSystem
from HCshinobi.bot.core.notifications.notification_dispatcher import NotificationDispatcher
from HCshinobi.bot.config import BotConfig, load_config # Import real config loading
from discord.ext import commands

@pytest.fixture
def setup_test_environment(tmp_path):
    """Set up test environment with required directories."""
    test_data_dir = tmp_path / "test_data"
    
    # Create test directories
    directories = [
        "characters",
        "clans",
        "currency",
        "tokens",
        "modifiers",
        "logs",
        "config",
        "battles"
    ]
    
    # Clean up any existing test directories
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir)
    
    # Create fresh directories
    for directory in directories:
        (test_data_dir / directory).mkdir(parents=True, exist_ok=True)
        
    # Create empty config file
    config_file = test_data_dir / "config" / "config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text("{}")
    
    yield test_data_dir
    
    # Cleanup after tests
    try:
        if test_data_dir.exists():
            shutil.rmtree(test_data_dir)
    except (PermissionError, OSError):
        pass  # Ignore cleanup errors

@pytest.fixture
def mock_config(setup_test_environment):
    """Create mock bot configuration."""
    config = MagicMock()
    config.token = "test_token"
    config.application_id = 123456789
    config.command_prefix = "!"
    config.guild_id = 987654321
    config.battle_channel_id = 111222333
    config.online_channel_id = 444555666
    config.announcement_channel_id = 777888999
    config.data_dir = str(setup_test_environment)
    config.config_dir = str(setup_test_environment / "config")
    config.logs_dir = str(setup_test_environment / "logs")
    config.webhook_url = "https://discord.com/api/webhooks/test"
    config.ollama_base_url = "http://localhost:11434"
    config.ollama_model = "test_model"
    config.openai_api_key = "test_key"
    config.openai_target_gpt_url = "http://localhost:3000"
    config.openai_headless = True
    
    # Add helper methods
    config._load_env_value = lambda key, default=None: default
    config._convert_to_int = lambda value: int(value) if value else None
    config.to_dict = lambda: {
        'token': config.token,
        'application_id': config.application_id,
        'command_prefix': config.command_prefix,
        'guild_id': config.guild_id,
        'battle_channel_id': config.battle_channel_id,
        'online_channel_id': config.online_channel_id,
        'announcement_channel_id': config.announcement_channel_id,
        'data_dir': config.data_dir,
        'config_dir': config.config_dir,
        'logs_dir': config.logs_dir,
        'webhook_url': config.webhook_url,
        'ollama_base_url': config.ollama_base_url,
        'ollama_model': config.ollama_model,
        'openai_api_key': config.openai_api_key,
        'openai_target_gpt_url': config.openai_target_gpt_url,
        'openai_headless': config.openai_headless
    }
    
    return config

@pytest.fixture
def mock_bot(mock_config):
    """Create mock bot instance."""
    bot = AsyncMock()
    bot.config = mock_config
    bot.command_prefix = mock_config.command_prefix
    bot.application_id = mock_config.application_id
    bot.get_channel = AsyncMock()
    bot.get_guild = AsyncMock()
    bot.wait_until_ready = AsyncMock()
    bot.services = MagicMock()
    bot.services.character_system = MagicMock()
    bot.services.clan_system = MagicMock()
    bot.services.currency_system = MagicMock()
    bot.services.battle_system = MagicMock()
    bot.services.token_system = MagicMock()
    
    # Mock logger
    bot.logger = MagicMock()
    bot.logger.info = MagicMock()
    bot.logger.error = MagicMock()
    bot.logger.warning = MagicMock()
    bot.logger.debug = MagicMock()
    
    # Mock methods
    bot.add_cog = AsyncMock()
    bot.remove_cog = AsyncMock()
    bot.get_cog = MagicMock()
    bot.dispatch = MagicMock()
    bot.is_closed = MagicMock(return_value=False)
    bot.is_ready = MagicMock(return_value=True)
    
    return bot

@pytest.fixture
def mock_author():
    """Creates a mock author (discord.Member)."""
    author = MagicMock(spec=discord.Member)
    author.id = 12345
    author.mention = "<@12345>"
    author.name = "TestUser"
    return author

@pytest.fixture
def mock_recipient():
    """Creates a mock recipient (discord.Member)."""
    recipient = MagicMock(spec=discord.Member)
    recipient.id = 67890
    recipient.mention = "<@67890>"
    recipient.name = "RecipientUser"
    return recipient

@pytest.fixture
def mock_ctx(mock_author):
    """Creates a mock command context."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.author = mock_author
    ctx.send = AsyncMock()
    return ctx

@pytest.fixture
def mock_currency_system(mock_bot):
    """Returns the mocked CurrencySystem from the mock_bot."""
    return mock_bot.services.currency_system

@pytest.fixture
def mock_clan_system(mock_bot):
    """Returns the mocked ClanSystem from the mock_bot."""
    return mock_bot.services.clan_system

@pytest_asyncio.fixture
async def mock_services(mock_config, temp_data_dir):
    services = MagicMock(spec=ServiceContainer)
    services.config = mock_config

    # Mock core data managers
    services.clan_data = AsyncMock(spec=ClanData)
    services.personality_modifiers = AsyncMock(spec=PersonalityModifiers)
    services.token_system = AsyncMock(spec=TokenSystem)

    # Mock core systems
    services.character_system = AsyncMock(spec=CharacterSystem)
    # Add mocks for methods used in tests if not covered by spec
    services.character_system.get_character = AsyncMock()
    services.character_system.create_character = AsyncMock()
    services.character_system.update_character = AsyncMock()
    services.character_system.get_all_characters = MagicMock(return_value=[])

    services.clan_system = AsyncMock(spec=ClanSystem)
    services.clan_system.get_clan = AsyncMock()
    services.clan_system.create_clan = AsyncMock()
    services.clan_system.get_all_clans = MagicMock(return_value=[])

    services.battle_system = AsyncMock(spec=BattleSystem)

    # Mock AI clients (optional, can return None or mock instances)
    services.ollama_client = None
    services.openai_client = None

    # Mock notification dispatcher
    services.notification_dispatcher = AsyncMock(spec=NotificationDispatcher)
    services.notification_dispatcher.webhook = AsyncMock(spec=discord.Webhook)

    services.session = AsyncMock(spec=aiohttp.ClientSession)

    return services

@pytest.fixture(autouse=True)
def mock_config_file(tmp_path):
    """Create a mock config file for testing."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    
    config_data = {
        "discord_bot_token": "test_token",
        "discord_guild_id": "123456789",
        "discord_battle_channel_id": "987654321",
        "discord_online_channel_id": "123789456",
        "data_dir": str(tmp_path / "data"),
        "ollama_base_url": "http://localhost:11434",
        "ollama_model": "test_model",
        "openai_api_key": "test_key",
        "openai_target_url": "http://localhost:8080",
        "openai_headless": True,
        "command_prefix": "!",
        "webhook_url": "http://test.webhook",
        "log_level": "DEBUG"
    }
    
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps(config_data))
    
    # Set environment variable to point to mock config
    os.environ["CONFIG_DIR"] = str(config_dir)
    
    return config_file

@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir 

@pytest.fixture
def mock_token_data():
    # Simplified mock data
    return {"tokens": {"user1": 100, "user2": 50}, "unlocks": {"user1": ["clan_creation"]}}

@pytest_asyncio.fixture
async def token_system(tmp_path, mock_token_data):
    """Fixture to provide an initialized TokenSystem instance with mocked file I/O."""
    token_file = tmp_path / "tokens.json"
    log_file = tmp_path / "token_log.json"
    token_file.parent.mkdir(exist_ok=True)
    log_file.parent.mkdir(exist_ok=True)

    # Mock file I/O functions specifically for this fixture's instance
    mock_load = AsyncMock()
    mock_save = AsyncMock()

    # Configure mock_load to return specific data based on file path
    def load_side_effect(path):
        normalized_path = Path(path).resolve()
        if normalized_path == token_file.resolve():
            return mock_token_data
        elif normalized_path == log_file.resolve():
            return [] # Return empty log initially
        return None # Default
    mock_load.side_effect = load_side_effect

    # Patch load_json and save_json within the core module
    with patch('HCshinobi.core.token_system.load_json', mock_load), \
         patch('HCshinobi.core.token_system.save_json', mock_save):

        instance = TokenSystem(token_file=str(token_file), log_file=str(log_file))
        await instance.initialize() # Await the new async initializer
        yield instance # Yield the initialized instance 

@pytest_asyncio.fixture
async def real_services(mock_config_file): # Use the fixture that sets up the mock config file
    """Provides a real, initialized ServiceContainer instance and handles shutdown."""
    # Load config using the mocked file path from mock_config_file fixture
    # Assuming load_config() can work with the structure provided by mock_config_file
    config = load_config() # This might need adjustment based on load_config implementation

    services = ServiceContainer(config)
    try:
        await services.initialize()
        yield services # Provide the initialized services to the test
    finally:
        # Ensure shutdown is called even if initialization or test fails
        if services._initialized: # Check if it was successfully initialized
            await services.shutdown() 