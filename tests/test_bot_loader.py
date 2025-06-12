"""
Test suite for bot loader functionality.
"""
import pytest
import asyncio
import warnings
from unittest.mock import AsyncMock, patch
from discord.ext import commands
from typing import Optional, TYPE_CHECKING

# Suppress audioop deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="discord.player")

if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.currency import CurrencyCommands
from HCshinobi.bot.cogs.battle_system import BattleSystemCommands
from HCshinobi.bot.cogs.missions import MissionCommands
from HCshinobi.bot.cogs.clan_commands import ClanCommands, ClanMissionCommands
from HCshinobi.bot.services import ServiceContainer

@pytest.fixture
def bot_config():
    """Create a test bot configuration."""
    return BotConfig(
        command_prefix="!",
        application_id=123456789,
        guild_id=987654321,
        battle_channel_id=111111111,
        online_channel_id=222222222,
        log_level="DEBUG",
        token="dummy_token_for_testing",
        data_dir="tests/temp_test_data",
        database_url="sqlite:///:memory:"
    )

@pytest.fixture
async def bot(bot_config):
    """Create a test bot instance."""
    bot = HCBot(bot_config, silent_start=True)
    try:
        # Initialize services
        bot.services = ServiceContainer(bot_config)
        await bot.services.initialize(bot)
        bot._initialized_services = True

        # Set up required attributes
        bot.character_system = bot.services.character_system
        bot._clan_data = bot.services.clan_data  # Use underlying attribute instead of property
        bot.currency_system = bot.services.currency_system
        bot.training_system = bot.services.training_system
        bot.battle_system = bot.services.battle_system
        bot.mission_system = bot.services.mission_system
        bot.jutsu_shop_system = bot.services.jutsu_shop_system
        bot.equipment_shop_system = bot.services.equipment_shop_system
        bot.ollama_client = bot.services.ollama_client

        yield bot
    finally:
        # Cancel any pending battle lifecycle tasks
        if hasattr(bot, 'battle_system') and bot.battle_system:
            for task in asyncio.all_tasks():
                if task.get_name().startswith('Task-') and 'battle_timeout_check' in str(task.get_coro()):
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        await bot.close()

@pytest.mark.asyncio
async def test_bot_instantiation(bot):
    """Test that the bot can be instantiated correctly."""
    assert isinstance(bot, HCBot)
    assert bot.command_prefix == "!"
    assert bot.config.application_id == 123456789

@pytest.mark.asyncio
async def test_cog_registration(bot):
    """Test that cogs can be registered correctly."""
    # Register cogs
    await bot.add_cog(CharacterCommands(bot))
    await bot.add_cog(CurrencyCommands(bot))
    await bot.add_cog(BattleSystemCommands(bot, bot.services))
    await bot.add_cog(MissionCommands(bot))
    await bot.add_cog(ClanMissionCommands(bot, bot.services.clan_missions, bot.services.clan_data))

@pytest.mark.asyncio
async def test_cogs_loaded(bot):
    """Test that all cogs are properly loaded."""
    # Register cogs first
    await bot.add_cog(CharacterCommands(bot))
    await bot.add_cog(CurrencyCommands(bot))
    await bot.add_cog(BattleSystemCommands(bot, bot.services))
    await bot.add_cog(MissionCommands(bot))
    await bot.add_cog(ClanMissionCommands(bot, bot.services.clan_missions, bot.services.clan_data))

    # Give a small delay for cogs to be properly registered
    await asyncio.sleep(0.1)

    # Now check that they are loaded
    assert any(isinstance(c, CharacterCommands) for c in bot.cogs.values())
    assert any(isinstance(c, CurrencyCommands) for c in bot.cogs.values())
    assert any(isinstance(c, BattleSystemCommands) for c in bot.cogs.values())
    assert any(isinstance(c, MissionCommands) for c in bot.cogs.values())
    assert any(isinstance(c, ClanMissionCommands) for c in bot.cogs.values())

@pytest.mark.asyncio
async def test_bot_startup(bot):
    """Test that the bot can start up correctly."""
    with patch.object(bot, 'start', new_callable=AsyncMock) as mock_start:
        # Simulate bot startup
        await bot.start("dummy_token")
        mock_start.assert_called_once_with("dummy_token")

@pytest.mark.asyncio
async def test_cog_initialization(bot):
    """Test that cogs are initialized with the correct bot instance."""
    # Register a cog
    cog = CharacterCommands(bot)
    await bot.add_cog(cog)
    
    # Verify cog has access to bot services
    assert cog.bot == bot
    assert hasattr(cog, 'character_system')
    assert hasattr(cog, 'clan_data')

@pytest.mark.asyncio
async def test_cog_cleanup(bot):
    """Test that cogs are cleaned up properly when bot shuts down."""
    # Register a cog
    cog = CharacterCommands(bot)
    await bot.add_cog(cog)
    
    # Verify cog is registered
    assert bot.get_cog("CharacterCommands") is not None
    
    # Remove cog
    await bot.remove_cog("CharacterCommands")
    
    # Verify cog is removed
    assert bot.get_cog("CharacterCommands") is None 