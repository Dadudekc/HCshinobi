"""
Main entry point for the HCShinobi Discord bot.
"""
import os
import asyncio
import logging
from typing import TYPE_CHECKING
from dotenv import load_dotenv
from discord.ext import commands
from HCshinobi.bot.config import BotConfig

if TYPE_CHECKING:
    from HCshinobi.bot.bot import HCBot

# Load environment variables
load_dotenv()

def get_discord_token():
    """Get the Discord token from environment variables."""
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set")
    return token

async def main():
    """Main entry point for the bot."""
    # Create bot instance
    config = BotConfig(
        command_prefix="!",
        application_id=int(os.getenv("DISCORD_APPLICATION_ID", "0")),
        guild_id=int(os.getenv("DISCORD_GUILD_ID", "0")),
        battle_channel_id=int(os.getenv("DISCORD_BATTLE_CHANNEL_ID", "0")),
        online_channel_id=int(os.getenv("DISCORD_ONLINE_CHANNEL_ID", "0")),
        log_level="INFO"
    )
    
    # Import HCBot here to avoid circular imports
    from HCshinobi.bot.bot import HCBot
    bot = HCBot(config=config)
    
    # Load cogs after bot is instantiated
    from HCshinobi.bot.cogs.character_commands import CharacterCommands
    from HCshinobi.bot.cogs.currency import CurrencyCommands
    from HCshinobi.bot.cogs.battle_system import BattleCommands
    from HCshinobi.bot.cogs.missions import MissionCommands
    from HCshinobi.bot.cogs.clan_commands import ClanMissionCommands
    
    # Add cogs to bot
    await bot.add_cog(CharacterCommands(bot))
    await bot.add_cog(CurrencyCommands(bot))
    await bot.add_cog(BattleCommands(bot))
    await bot.add_cog(MissionCommands(bot))
    await bot.add_cog(ClanMissionCommands(bot))
    
    # Start the bot
    try:
        await bot.start(get_discord_token())
    except Exception as e:
        logging.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        logging.error(f"Bot failed with error: {e}", exc_info=True)
        sys.exit(1)