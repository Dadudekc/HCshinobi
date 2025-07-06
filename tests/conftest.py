import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock
import discord
import json
from typing import Dict, Any, AsyncGenerator
import asyncio
from discord.ext import commands

# Ensure project root is on the import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.character_system import CharacterSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.token_system import TokenSystem
from HCshinobi.core.training_system import TrainingSystem
from HCshinobi.core.clan_data import ClanData
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.constants import CHARACTERS_SUBDIR, CURRENCY_FILE, TOKEN_FILE, TRAINING_SESSIONS_FILE, TRAINING_COOLDOWNS_FILE, CLANS_SUBDIR
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.training import TrainingCommands

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "temp_test_data")
TEST_CHARS_DIR = os.path.join(TEST_DATA_DIR, CHARACTERS_SUBDIR)
TEST_CURRENCY_FILE = os.path.join(TEST_DATA_DIR, CURRENCY_FILE)
TEST_TOKENS_FILE = os.path.join(TEST_DATA_DIR, TOKEN_FILE)
TEST_TRAINING_SESSIONS_FILE = os.path.join(TEST_DATA_DIR, TRAINING_SESSIONS_FILE)
TEST_TRAINING_COOLDOWNS_FILE = os.path.join(TEST_DATA_DIR, TRAINING_COOLDOWNS_FILE)
TEST_CLANS_DIR = os.path.join(TEST_DATA_DIR, CLANS_SUBDIR)

@pytest.fixture(scope="function", autouse=True)
def setup_test_data_dir():
    """Ensure the test data directory exists and is clean before each test."""
    # Create directories if they don't exist
    os.makedirs(TEST_CHARS_DIR, exist_ok=True)
    os.makedirs(TEST_CLANS_DIR, exist_ok=True) 
    # Ensure main test data dir exists
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    
    # Example: Create dummy clan data file if needed for tests
    dummy_clan_file = os.path.join(TEST_CLANS_DIR, "leaf_clans.json")
    if not os.path.exists(dummy_clan_file):
        with open(dummy_clan_file, 'w') as f:
            json.dump({"Leaf Village": [{"name": "Uchiha", "specialty": "Sharingan"}, {"name": "Hyuga", "specialty": "Byakugan"}]}, f)
            
    # Create dummy clan tiers file
    dummy_tiers_file = os.path.join(TEST_CLANS_DIR, "clan_tiers.json")
    if not os.path.exists(dummy_tiers_file):
         with open(dummy_tiers_file, 'w') as f:
             json.dump({"S": ["Uchiha", "Senju"], "A": ["Hyuga"], "B": []}, f)

    yield # Test runs here

    # Teardown: Clean up files created during the test
    # Be careful here not to delete essential structure if reused
    # Example: Remove character files, reset currency/token/training files
    for filename in os.listdir(TEST_CHARS_DIR):
        if filename.endswith('.json'):
            os.remove(os.path.join(TEST_CHARS_DIR, filename))
    if os.path.exists(TEST_CURRENCY_FILE):
        os.remove(TEST_CURRENCY_FILE)
    if os.path.exists(TEST_TOKENS_FILE):
        os.remove(TEST_TOKENS_FILE)
    if os.path.exists(TEST_TRAINING_SESSIONS_FILE):
        os.remove(TEST_TRAINING_SESSIONS_FILE)
    if os.path.exists(TEST_TRAINING_COOLDOWNS_FILE):
        os.remove(TEST_TRAINING_COOLDOWNS_FILE)
    # Optionally remove dummy clan files if strictly per-test
    # if os.path.exists(dummy_clan_file):
    #     os.remove(dummy_clan_file)
    # if os.path.exists(dummy_tiers_file):
    #      os.remove(dummy_tiers_file)

@pytest.fixture(scope="function")
async def integration_services(setup_test_data_dir) -> AsyncGenerator[ServiceContainer, None]:
    """Provides an isolated ServiceContainer initialized with test data paths."""
    # Ensure the fixture dependency runs first
    _ = setup_test_data_dir 
    
    # Initialize services pointing to the temporary test directory
    services = ServiceContainer(data_dir=TEST_DATA_DIR)
    
    try:
        # Run ready hooks if they exist and are relevant for tests
        await services.run_ready_hooks()
        yield services
    finally:
        # Cleanup any async resources
        if hasattr(services, 'cleanup'):
            await services.cleanup()
        
        # Close any aiohttp sessions
        for attr_name in dir(services):
            attr = getattr(services, attr_name)
            if hasattr(attr, 'close') and callable(attr.close):
                await attr.close()

# Mock interaction fixture for E2E tests (can be reused)
@pytest.fixture(scope="function")
def mock_e2e_interaction() -> AsyncMock:
    """Provides a reusable mock discord.Interaction for E2E tests."""
    mock_user = MagicMock(spec=discord.Member)
    mock_user.id = 1234567890  # Example user ID
    mock_user.name = "TestUser"
    mock_user.display_name = "TestUser Display"
    # Add avatar mock if needed by tests
    mock_user.display_avatar = MagicMock(spec=discord.Asset)
    mock_user.display_avatar.url = "http://example.com/avatar.png"

    mock_guild = MagicMock(spec=discord.Guild)
    mock_guild.id = 9876543210  # Example guild ID

    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.user = mock_user
    mock_interaction.guild = mock_guild
    mock_interaction.response = AsyncMock(spec=discord.InteractionResponse)
    mock_interaction.followup = AsyncMock(spec=discord.Webhook)
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    # Add edit_original_response mock if needed
    mock_interaction.edit_original_response = AsyncMock()
    
    # Helper to simulate getting the view from the send/followup call
    def get_sent_view(**kwargs):
        return kwargs.get('view')
    mock_interaction.followup.send.side_effect = get_sent_view
    
    return mock_interaction

@pytest.fixture
async def integration_bot(integration_services: ServiceContainer):
    """Creates a minimal mock bot with services attached."""
    mock_bot = MagicMock()
    mock_bot.services = integration_services
    # Simulate get_cog behavior if needed by tests calling it
    def get_cog_mock(name):
        if name == "CharacterCommands":
            # Need to ensure CharacterCommands is imported
            return CharacterCommands(mock_bot) 
        elif name == "TrainingCommands":
            # Need to ensure TrainingCommands is imported
            return TrainingCommands(mock_bot) 
        # Add other cogs as needed for tests
        return None
    mock_bot.get_cog = get_cog_mock
    # Add other essential bot attributes/methods if tests rely on them
    # mock_bot.user = MagicMock(id=BOT_ID)
    # mock_bot.loop = asyncio.get_running_loop()
    return mock_bot 

@pytest.fixture
def mock_bot():
    """Create a mock bot with required services."""
    bot = MagicMock()
    bot.services = MagicMock(spec=ServiceContainer)
    return bot 

@pytest.fixture
def mock_ctx():
    """Create a mock context for testing commands."""
    ctx = AsyncMock()
    ctx.user = AsyncMock()
    ctx.user.id = 1234567890
    ctx.user.display_name = "Test User"
    
    # Set up response and followup
    ctx.response = AsyncMock()
    ctx.followup = AsyncMock()
    
    # Set up interaction
    ctx.interaction = AsyncMock()
    ctx.interaction.user = ctx.user
    ctx.interaction.response = ctx.response
    ctx.interaction.followup = ctx.followup
    
    # Set up defer method
    ctx.interaction.response.defer = AsyncMock(return_value=None)
    
    # Set up send methods
    ctx.interaction.response.send_message = AsyncMock(return_value=None)
    ctx.interaction.followup.send = AsyncMock(return_value=None)
    
    # Set up guild and permissions
    ctx.guild = AsyncMock()
    ctx.guild_permissions = AsyncMock()
    ctx.guild_permissions.administrator = True
    
    return ctx 

@pytest.fixture(scope="function", autouse=True)
async def cleanup_resources():
    """Cleanup fixture that runs after each test."""
    yield
    
    # Get the current event loop
    loop = asyncio.get_event_loop()
    
    # Cancel all pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    # Close any remaining aiohttp sessions
    for task in asyncio.all_tasks(loop):
        if hasattr(task, 'client_session') and task.client_session:
            await task.client_session.close() 