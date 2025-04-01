"""
Core Bot logic for HCShinobi Discord Bot.
Handles bot initialization and dependency injection.
"""

import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from typing import Optional
from pathlib import Path
import logging
from discord import app_commands

# --- Core Service Imports ---
try:
    from ..core.clan_data import ClanData
    from ..core.token_system import TokenSystem, TokenError
    from ..core.personality_modifiers import PersonalityModifiers
    from ..core.npc_manager import NPCManager
    from ..core.clan_assignment_engine import ClanAssignmentEngine
    from ..core.character_manager import CharacterManager
    from ..core.battle_manager import BattleManager, BattleManagerError
    from ..core.engine import Engine as GameEngine
    from ..core.character_system import CharacterSystem
    from ..core.battle_system import BattleSystem
except ImportError as e:
    print(f"FATAL: Error importing core services: {e}. Check structure and dependencies.")
    exit(f"Core service import failed: {e}")

# --- Utility Imports ---
try:
    from ..utils.logging import get_logger, log_error
    from ..utils.ollama_client import OllamaClient, OllamaError
    from ..utils.openai_client import OpenAIClient
    from ..utils.discord_ui import get_rarity_color
except ImportError:
    print("Warning: Could not import HCshinobi logger, using basic logging.")
    get_logger = logging.getLogger
    def log_error(event, msg, data=None):
        logging.error(f"{event}: {msg} {data if data else ''}")
    # If imports fail, define as None
    OpenAIClient = None

# --- Extensions Import --- (REMOVED - Cogs loaded dynamically in setup_hook) ---
# try:
#     from . import extensions
# except ImportError:
#     print("Error: Could not import extensions package. Ensure __init__.py exists.")
#     extensions = None

logger = get_logger("discord_bot")

from .config import BotConfig, load_config
from .services import ServiceContainer
from .events import BotEvents
from .setup import BotSetup
from ..commands.character_commands import CharacterCommands
from ..commands.battle_commands import BattleCommands

class HCBot(commands.Bot):
    """Main bot class."""
    
    def __init__(self, config: BotConfig):
        """Initialize the bot."""
        super().__init__(
            command_prefix=config.command_prefix,
            intents=discord.Intents.all()
        )
        
        self.config = config
        self.guild_id = config.guild_id
        self.battle_channel_id = config.battle_channel_id
        self.online_channel_id = config.online_channel_id
        self.services: Optional[ServiceContainer] = None
        
        # Set up logging
        logging.basicConfig(
            level=config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def setup(self):
        """Set up the bot."""
        await self.setup_services()
        await self.setup_commands()
        await self.setup_events()
        logger.info("Bot setup complete")
    
    async def setup_services(self):
        """Set up bot services."""
        self.services = ServiceContainer(self.config)
        await self.services.initialize()
        logger.info("Services initialized")
    
    async def setup_commands(self):
        """Set up bot commands."""
        # Load command extensions
        extensions = [
            'HCshinobi.extensions.character_commands',
            'HCshinobi.extensions.battle_commands',
            'HCshinobi.extensions.clan_commands',
            'HCshinobi.extensions.announcement_commands',
            'HCshinobi.extensions.ai_commands'
        ]
        
        for extension in extensions:
            try:
                await self.load_extension(extension)
                logger.info(f"Loaded extension: {extension}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension}: {e}")
    
    async def setup_events(self):
        """Set up bot events."""
        # Define event handlers
        async def on_ready():
            """Called when the bot is ready."""
            logger.info(f"Logged in as {self.user.name} ({self.user.id})")
            # Safely get guild name
            guild = self.get_guild(self.guild_id)
            guild_name = guild.name if guild else f"ID: {self.guild_id}"
            logger.info(f"Connected to guild: {guild_name}")
        
        async def on_command_error(ctx: commands.Context, error: Exception):
            """Handle command errors."""
            if isinstance(error, commands.CommandNotFound):
                await ctx.send("Command not found.")
            elif isinstance(error, commands.MissingPermissions):
                await ctx.send("You don't have permission to use this command.")
            else:
                logger.error(f"Command error occurred: {error}")
                await ctx.send("An error occurred while processing the command.")

        # Add event handlers to the extra_events dictionary
        self.extra_events['on_ready'] = on_ready
        self.extra_events['on_command_error'] = on_command_error

        # Apply the registered events (discord.py handles this internally when using @self.event)
        # We manually add them here for testing purposes and clarity
        # The bot will still use its internal event dispatching
    
    async def run(self):
        """Run the bot."""
        await self.setup()
        await self.start(self.config.token)

async def run_bot():
    """
    Main entry point to configure environment, init core services, and start the HCShinobiBot.
    Includes manual sign-in to OpenAI using undetected-chromedriver if configured.
    """
    logger.info("===== Initializing HCShinobi Bot =====")
    
    # Load configuration first
    config = load_config()
    
    # Create and run bot
    bot = HCBot(config)
    
    try:
        logger.info("Starting bot login...")
        await bot.run()
    except discord.LoginFailure:
        log_error("login_error", "Invalid Discord token.")
        logger.critical("Login failed: invalid token.")
    except discord.PrivilegedIntentsRequired:
        log_error("startup_error", "Privileged intents not enabled in Developer Portal.")
        logger.critical("Bot lacks required privileged intents.")
    except Exception as e:
        log_error("runtime_error", "Unexpected error during bot runtime", {"error": str(e)})
        logger.critical(f"Bot runtime error: {e}", exc_info=True)
    finally:
        # Shut down services
        await bot.services.shutdown()
        
        # Close the bot if still running
        if not bot.is_closed():
            logger.info("Closing bot connection...")
            await bot.close()
        logger.info("===== HCShinobi Bot has shut down. =====")
