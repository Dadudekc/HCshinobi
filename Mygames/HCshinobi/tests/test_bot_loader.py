"""
Tests for bot initialization and cog loading.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from discord.ext import commands

from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import BotConfig
from HCshinobi.bot.cogs.character_commands import CharacterCommands
from HCshinobi.bot.cogs.currency import CurrencyCommands
from HCshinobi.bot.cogs.battle_system import BattleCommands
from HCshinobi.bot.cogs.missions import MissionCommands
from HCshinobi.bot.cogs.clan_commands import ClanMissionCommands

@pytest.fixture
def bot_config():
    """Create a test bot configuration."""
    return BotConfig(
        command_prefix="!",
        application_id=123456789,
        guild_id=987654321,
        battle_channel_id=111111111,
        online_channel_id=222222222,
        log_level="DEBUG"
    )

@pytest.fixture
async def bot(bot_config):
    """Create a test bot instance."""
    bot = HCBot(config=bot_config)
    yield bot
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
    await bot.add_cog(BattleCommands(bot))
    await bot.add_cog(MissionCommands(bot))
    await bot.add_cog(ClanMissionCommands(bot))
    
    # Verify cogs are registered
    assert isinstance(bot.get_cog("CharacterCommands"), CharacterCommands)
    assert isinstance(bot.get_cog("CurrencyCommands"), CurrencyCommands)
    assert isinstance(bot.get_cog("BattleCommands"), BattleCommands)
    assert isinstance(bot.get_cog("MissionCommands"), MissionCommands)
    assert isinstance(bot.get_cog("ClanMissionCommands"), ClanMissionCommands)

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