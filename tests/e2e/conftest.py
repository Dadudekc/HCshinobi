# tests/e2e/conftest.py
import pytest
import asyncio
import discord
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import os
import shutil
import json
from contextlib import asynccontextmanager # Import asynccontextmanager
import logging # Added

# Assume necessary imports from the project
# from HCshinobi.bot.bot import HCBot # Unused
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.services import ServiceContainer
from HCshinobi.core.character_system import CharacterSystem
# from HCshinobi.core.training_system import TrainingSystem, TrainingIntensity # TrainingIntensity unused here
from HCshinobi.core.training_system import TrainingSystem # Import only TrainingSystem
from HCshinobi.core.currency_system import CurrencySystem
from HCshinobi.core.token_system import TokenSystem
from HCshinobi.core.clan_assignment_engine import ClanAssignmentEngine
from HCshinobi.core.progression_engine import ShinobiProgressionEngine
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.training_commands import TrainingCommands
from HCshinobi.core.clan_data import ClanData
# from HCshinobi.core.personality_modifiers import PersonalityModifiers  # Module doesn't exist
from HCshinobi.core.constants import DATA_DIR as DEFAULT_PROJECT_DATA_DIR

logger = logging.getLogger(__name__) # Added

# --- Shared Fixtures for E2E Tests ---

@pytest.fixture(scope="session") # Use session scope if config is constant for all tests
def test_config():
    # Simplified config for testing
    print("\nCreating Test Config...")
    return BotConfig(
        token="test_token",
        battle_channel_id=11111,
        online_channel_id=22222,
        database_url="sqlite:///./temp_e2e_data/test_db.sqlite", # Needs unique name per test or cleanup
        guild_id=12345,
        application_id=67890,
        log_level="DEBUG",
        command_prefix="!",
        data_dir="./temp_e2e_data", # Placeholder, overridden by temp_data_dir
        equipment_shop_channel_id=33333 # Add potentially missing required args
        # Add other required args if any
    )

@pytest.fixture(scope="function") # Use function scope for clean data dir per test
def temp_data_dir(tmp_path, test_config): # Depends on test_config for DB path potentially
    # Determine the project's base data directory more reliably
    project_root = Path(__file__).parent.parent.parent
    base_data_dir = project_root / DEFAULT_PROJECT_DATA_DIR
    if not base_data_dir.is_dir():
        base_data_dir = project_root / "data"
    print(f"Using project data source: {base_data_dir}")

    e2e_data_dir = tmp_path / f"e2e_data_{os.urandom(4).hex()}" # Unique dir per test
    print(f"\nCreating E2E data directory: {e2e_data_dir}")
    if e2e_data_dir.exists():
        shutil.rmtree(e2e_data_dir)
    e2e_data_dir.mkdir()

    # Update config to use this temp dir BEFORE service init
    test_config.data_dir = str(e2e_data_dir)
    # Update DB URL to be unique per test run
    test_config.database_url = f"sqlite:///{e2e_data_dir}/test_db.sqlite"

    required_structure = {
        "characters": [],
        "clans": ["clans.json"],
        "jutsu": ["master_jutsu_list.json"],
        "progression": ["ranks.json", "achievements.json", "titles.json", "level_curve.json"],
        "shops": ["jutsu_shop_state.json", "equipment_shop.json", "equipment_shop_state.json", "general_items.json"],
        "missions": ["mission_definitions.json", "active_missions.json", "completed_missions.json"],
        "currency": ["currency.json"],
        "tokens": ["tokens.json", "assignment_history.json"],
        "battles": ["active_battles.json", "battle_history.json"],
        ".": ["modifiers.json", "npcs.json"]
    }

    temp_clan_data_instance = ClanData(data_dir=str(tmp_path / "__clandata_temp"))
    default_clans_dict = temp_clan_data_instance.create_default_clans()

    for subdir, files in required_structure.items():
        subdir_path = e2e_data_dir / subdir
        if subdir != ".":
            subdir_path.mkdir(exist_ok=True)
        
        for filename in files:
            source_file = base_data_dir / subdir / filename
            target_file = subdir_path / filename
            try:
                if source_file.exists() and source_file.is_file():
                    shutil.copy(source_file, target_file)
                    # print(f"  Copied {source_file} to {target_file}")
                else:
                    default_content = {}
                    if filename == "clans.json" and subdir == "clans":
                        default_clans_list = list(default_clans_dict.values())
                        default_content = default_clans_list
                    elif "list" in filename or "history" in filename or "definitions" in filename or "items" in filename:
                        default_content = []
                    with open(target_file, 'w') as f:
                        json.dump(default_content, f, indent=2)
                    # print(f"  Created default {target_file}")
            except Exception as e:
                print(f"  ERROR setting up {target_file}: {e}")
                with open(target_file, 'w') as f: json.dump({}, f)

    yield str(e2e_data_dir)

    # Teardown (optional, tmp_path handles it, but good for DB potentially)
    print(f"Cleaning up {e2e_data_dir}")
    # shutil.rmtree(e2e_data_dir, ignore_errors=True)

# The core integration fixture using the REAL services and cogs
@pytest.fixture(scope="function") # Function scope to get fresh services each time
# async def integration_bot(temp_data_dir, test_config):
async def integration_services(temp_data_dir, test_config):
    logger.warning(f"\n>>> [Fixture] integration_services setup starting... Temp dir: {temp_data_dir}") # Added Log
    # temp_data_dir fixture already updated test_config.data_dir
    # print(f"\nSetting up Integration Bot in {temp_data_dir}...")
    print(f"\nSetting up Integration Services in {temp_data_dir}...")
    # bot = None # Define bot in outer scope
    services = None # Define services in outer scope
    try:
        services = ServiceContainer(test_config)
        
        # Mock the bot object THAT WILL BE PASSED to initialize
        # Services only need logger, loop, user.id, and services ref during init
        bot_mock_for_init = MagicMock() 
        bot_mock_for_init.user = MagicMock(spec=discord.ClientUser)
        bot_mock_for_init.user.id = 99999
        bot_mock_for_init.logger = MagicMock()
        bot_mock_for_init.loop = asyncio.get_running_loop()
        bot_mock_for_init.services = services 

        await services.initialize(bot=bot_mock_for_init) 

        # Remove bot mocking and cog setup from fixture
        # # Now create the final mock bot to yield, assigning the REAL services
        # bot = MagicMock(spec=HCBot)
        # bot.services = services # Assign the initialized container
        # bot.user = bot_mock_for_init.user # Reuse user mock
        # bot.logger = bot_mock_for_init.logger # Reuse logger mock
        # bot.loop = bot_mock_for_init.loop
        # bot._cogs = {}

        # # Configure get_cog to lookup in the internal dict
        # bot.get_cog = MagicMock(side_effect=lambda name: bot._cogs.get(name))

        # # Instantiate REAL Cogs, passing the mock bot that has REAL services
        # char_cog = CharacterCommands(bot) 
        # training_cog = TrainingCommands(bot)
        # # Add other cogs as needed for wider testing

        # # Add Cogs directly to the internal dict
        # bot._cogs[CharacterCommands.__name__] = char_cog
        # bot._cogs[TrainingCommands.__name__] = training_cog

        logger.warning(f">>> [Fixture] integration_services setup complete. Services instance ID: {id(services)}") # Added Log
        yield services # Yield the initialized services container

        # Code after yield runs as teardown
        logger.warning(f"\n>>> [Fixture] integration_services teardown starting... Services instance ID: {id(services)}") # Added Log
        if services and hasattr(services, '_initialized') and services._initialized:
            await services.shutdown()
        logger.warning(f">>> [Fixture] integration_services teardown complete.") # Added Log

    except Exception as e:
        # pytest.fail(f"Error during integration_bot fixture setup: {e}", pytrace=True)
        pytest.fail(f"Error during integration_services fixture setup: {e}", pytrace=True)
    finally:
        # Ensure services are shut down even if yield fails (covered by context manager)
        # No need for explicit shutdown here if handled after yield
        pass 

@pytest.fixture(scope="function")
async def mock_e2e_interaction(): # Change to async def
    # Keep this function scope to get fresh mocks per test
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.user = MagicMock(spec=discord.User)
    # Assign unique IDs dynamically? For now, keep static but maybe problematic
    interaction.user.id = 1234567890 # Use integer for user ID
    interaction.user.name = "E2ETester"
    interaction.user.display_name = "E2E Tester"
    interaction.guild = MagicMock(spec=discord.Guild)
    interaction.guild.id = 12345 # Matches config
    interaction.response = AsyncMock(spec=discord.InteractionResponse)
    interaction.followup = AsyncMock(spec=discord.Webhook)
    interaction.original_response = AsyncMock(return_value=AsyncMock(spec=discord.InteractionMessage))
    logger.warning(f"\n>>> [Fixture] Mock Interaction created for user {interaction.user.id}") # Added Log
    return interaction 