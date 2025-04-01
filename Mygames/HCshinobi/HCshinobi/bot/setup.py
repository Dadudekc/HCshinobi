"""
Setup module for HCShinobi bot.
Handles cog loading and command syncing.
"""

import os
import discord
from discord.ext import commands
from typing import List, Optional
from .config import BotConfig
import logging

logger = logging.getLogger(__name__)

class BotSetup:
    """Handles bot setup and initialization."""

    def __init__(self, bot, config):
        """Initialize bot setup."""
        self.bot = bot
        self.config = config
        self.initialized = False

    async def setup(self) -> None:
        """Run bot setup."""
        logger.info("Running bot setup...")
        
        try:
            # Load extensions first
            logger.info("Loading extensions...")
            await self._load_extensions()
            
            # Initialize services
            logger.info("Initializing services...")
            await self.bot.services.initialize()
            
            # Set initialized flag
            self.bot.initialized = True
            
            # Sync commands
            logger.info("Syncing commands...")
            await self._sync_commands()
            
            self.initialized = True
            logger.info("Bot setup completed successfully")
            
        except Exception as e:
            logger.error(f"Error during bot setup: {e}")
            self.initialized = False
            raise
    
    async def _load_extensions(self) -> None:
        """Load all cogs from the cogs directory."""
        print("Loading cogs...")
        
        # Define the path to the cogs directory
        cogs_path = "HCshinobi.bot.cogs"
        print(f"Attempting to load extensions from: {cogs_path}")
        
        # Try to find python files in the cogs directory
        try:
            cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
            potential_cogs = [f[:-3] for f in os.listdir(cogs_dir) 
                            if f.endswith('.py') and not f.startswith('__')]
            print(f"Found cog files in directory: {potential_cogs}")
        except FileNotFoundError:
            print(f"Cogs directory not found at {cogs_dir}. Cannot load cogs.")
            potential_cogs = []
        
        if not potential_cogs:
            print("No potential cog files found. Skipping loading.")
            return
        
        print(f"Found potential cogs: {potential_cogs}")
        loaded_cogs = []
        failed_cogs = []
        
        for cog_name in potential_cogs:
            module_path = f"{cogs_path}.{cog_name}"
            try:
                await self.bot.load_extension(module_path)
                print(f"Successfully loaded cog: {cog_name}")
                loaded_cogs.append(cog_name)
            except commands.ExtensionNotFound:
                print(f"Cog module not found at {module_path}. Check file name/path.")
                failed_cogs.append(cog_name)
            except commands.ExtensionAlreadyLoaded:
                print(f"Cog {cog_name} already loaded.")
            except commands.NoEntryPointError:
                print(f"Cog {module_path} has no 'setup(bot)' function.")
                failed_cogs.append(cog_name)
            except commands.ExtensionFailed as e:
                print(f"Failed loading cog {module_path}: {e.original}")
                failed_cogs.append(cog_name)
            except Exception as e:
                print(f"Unexpected error loading cog {module_path}: {e}")
                failed_cogs.append(cog_name)
        
        if failed_cogs:
            print(f"Failed to load cogs: {', '.join(failed_cogs)}")
        if loaded_cogs:
            print(f"Successfully loaded cogs: {', '.join(loaded_cogs)}")
    
    async def _sync_commands(self) -> None:
        """Sync slash commands to either a target guild or globally."""
        try:
            print("Starting command sync process...")
            existing_commands = [cmd.name for cmd in self.bot.tree.get_commands()]
            print(f"Current command tree: {existing_commands}")
            
            # We won't clear existing commands as it's preventing registration
            # Instead, we'll sync the commands that were added during initialization
            
            if self.config.guild_id:
                print(f"Syncing commands to guild {self.config.guild_id}...")
                guild = discord.Object(id=self.config.guild_id)
                # First, copy global commands to guild
                self.bot.tree.copy_global_to(guild=guild)
                # Then sync
                await self.bot.tree.sync(guild=guild)
                print(f"Commands synced to guild {self.config.guild_id}.")
            else:
                print("Syncing commands globally (may take time)...")
                await self.bot.tree.sync()
                print("Successfully synced commands globally.")
            
            # Log final command tree after sync
            commands = self.bot.tree.get_commands()
            command_names = [cmd.name for cmd in commands]
            print(f"Final command tree after sync: {command_names}")
            print(f"Total commands registered: {len(commands)}")
            
        except discord.DiscordException as e:
            print(f"Command sync error: {e}")
            logger.error(f"Discord error during command sync: {e}")
        except Exception as e:
            print(f"Error in command sync: {e}")
            logger.error(f"Unexpected error during command sync: {e}", exc_info=True) 