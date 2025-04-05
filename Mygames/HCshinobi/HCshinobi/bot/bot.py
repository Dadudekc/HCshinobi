"""
Core Bot logic for HCShinobi Discord Bot.
Handles bot initialization and dependency injection.
"""

import os
import asyncio
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import Optional, List, Dict
from pathlib import Path
import logging
from discord import app_commands
import json
from HCshinobi.core.constants import DATA_DIR
from ..core.constants import JUTSU_SHOP_CHANNEL_ID
from datetime import datetime
import aiofiles

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
# from .events import BotEvents # Events seem unused, commented out
# from .setup import BotSetup # Setup seems unused, commented out
from ..commands.character_commands import CharacterCommands
from ..commands.battle_commands import BattleCommands
from ..commands.clan_commands import ClanCommands
from ..commands.mission_commands import MissionCommands
from ..commands.currency_commands import CurrencyCommands
from ..commands.training_commands import TrainingCommands
from ..commands.quest_commands import QuestCommands
from ..commands.loot_commands import LootCommands
from ..commands.room_commands import RoomCommands
from ..commands.announcement_commands import AnnouncementCommands
from ..commands.devlog_commands import DevLogCommands
from ..commands.shop_commands import ShopCommands

class HCBot(commands.Bot):
    """Main bot class."""
    
    def __init__(self, config: BotConfig, silent_start: bool = False):
        """Initialize the bot."""
        super().__init__(
            command_prefix=config.command_prefix,
            intents=discord.Intents.all(),
            application_id=config.application_id
        )
        
        self.config = config
        self.guild_id = config.guild_id
        self.battle_channel_id = config.battle_channel_id
        self.online_channel_id = config.online_channel_id
        self.silent_start = silent_start
        
        # Initialize logger FIRST
        self.logger = logging.getLogger(__name__)
        # Configure root logger (consider moving this to main entry point if not done already)
        logging.basicConfig(
            level=config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize other attributes
        self.services: Optional[ServiceContainer] = None
        self._initialized_services = False # Flag to track service init
        self._clan_data = None # This might be needed if ClanData init fails
        self._initial_shop_posted = False # Flag for initial Jutsu shop post
    
    async def setup_hook(self) -> None:
        """Overrides commands.Bot.setup_hook. Called before on_ready."""
        self.logger.info("Running setup_hook...")
        try:
            # 1. Initialize services first (this now loads master list)
            self.services = ServiceContainer(self.config)
            await self.services.initialize()
            self._initialized_services = True # Mark services as initialized
            self.logger.info("Service container initialized successfully.")

            # --- Perform ONE-TIME Jutsu Data Migration --- #
            migration_flag_file = os.path.join(DATA_DIR, ".jutsu_migration_done")
            
            if not os.path.exists(migration_flag_file):
                if self.services.master_jutsu_list: # Check if list loaded in services
                    master_jutsu_names = {jutsu.get('name') for jutsu in self.services.master_jutsu_list if jutsu.get('name')}
                    if master_jutsu_names:
                        modified_count = await self.services.character_system.migrate_jutsu_data(master_jutsu_names)
                        if modified_count >= 0: 
                            try:
                                # Use aiofiles for async flag creation
                                async with aiofiles.open(migration_flag_file, 'w') as f:
                                     await f.write(datetime.utcnow().isoformat())
                                self.logger.info("Created jutsu migration flag file.")
                            except Exception as e:
                                self.logger.error(f"Failed to create jutsu migration flag file: {e}")
                        else:
                             self.logger.error("Jutsu migration failed. Flag file not created.")
                    else:
                         self.logger.error("Could not extract names from master jutsu list. Migration skipped.")
                else:
                     self.logger.error("Master jutsu list is empty or failed to load. Migration skipped.")
            else:
                 self.logger.info("Jutsu migration flag file found. Skipping migration.")
            # --- End Migration Logic --- #
            
            # --- Refresh Jutsu Shop (No Posting Here) --- #
            if self.services.jutsu_shop_system:
                refreshed = await self.services.jutsu_shop_system.refresh_shop_if_needed()
                if refreshed:
                     self.logger.info("Jutsu shop was refreshed during setup_hook.")
                # REMOVED post_shop_inventory call from here
            else:
                 self.logger.error("JutsuShopSystem not initialized. Cannot refresh shop.")
            # --- End Jutsu Shop Refresh Logic --- #

            # 2. Set up core systems references (optional)
            # Access systems via self.services.<system_name> property is preferred
            # Example (if needed, but generally avoid duplicating state):
            # self.character_system = self.services.character_system 
            # self._clan_data = self.services.clan_data
            
            # 3. Register command cogs 
            # Ensure service references are valid before creating cogs
            cogs_to_load = [
                CharacterCommands(self, self.services.character_system, self.services.clan_data, self.services.progression_engine),
                # Corrected initialization: Only pass bot instance
                # CurrencyCommands(self), # REMOVED: Load as extension
                # Corrected initialization: Only pass bot instance
                # ShopCommands(self), # REMOVED: Load as extension
                # BattleCommands(self, self.services.battle_system, self.services.character_system, self.services.battle_manager), # REMOVED: Load as extension
                ClanCommands(self, self.services.clan_system, self.services.character_system),
                MissionCommands(self, self.services.mission_system, self.services.character_system),
                TrainingCommands(self, self.services.training_system, self.services.character_system),
                QuestCommands(self, self.services.quest_system, self.services.character_system),
                LootCommands(self, self.services.loot_system, self.services.character_system, DATA_DIR),
                RoomCommands(self, self.services.room_system, self.services.character_system),
                AnnouncementCommands(self), # Assumes it only needs bot instance
                DevLogCommands(self), # Assumes it only needs bot instance
            ]
            
            # Add diagnostic command (optional)
            # self.tree.add_command(debug_commands) 
            
            loaded_cog_count = 0
            for cog_instance in cogs_to_load:
                try:
                    await self.add_cog(cog_instance)
                    self.logger.info(f"Successfully added cog: {cog_instance.__class__.__name__}")
                    loaded_cog_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to load cog {cog_instance.__class__.__name__}: {e}", exc_info=True)
                    # Continue loading other cogs even if one fails?
            
            self.logger.info(f"Loaded {loaded_cog_count}/{len(cogs_to_load)} cogs directly.") # Updated log message
            
            # --- Load Core System Cogs FIRST --- #
            core_extensions = [
                 "HCshinobi.core.currency_system" # Load Currency Cog first
                 # Add other core system cogs here if they exist (e.g., CharacterSystemCog?)
            ]
            core_load_success = 0
            for extension in core_extensions:
                 try:
                      await self.load_extension(extension)
                      self.logger.info(f"Successfully loaded core extension: {extension}")
                      core_load_success += 1
                 except Exception as e:
                      self.logger.error(f"Failed to load core extension {extension}: {e}", exc_info=True)
                      # Consider stopping if a core cog fails
            self.logger.info(f"Loaded {core_load_success}/{len(core_extensions)} core extensions.")
            # --- End Core Cog Loading ---
            
            # --- Load Command Cogs via load_extension --- # 
            # These can now depend on core cogs loaded above
            extensions_to_load = [
                 "HCshinobi.commands.currency_commands",
                 "HCshinobi.commands.shop_commands",
                 "HCshinobi.commands.battle_commands" 
                 # Add other cogs intended to be loaded via extension here
            ]
            
            extension_load_success = 0
            for extension in extensions_to_load:
                 try:
                      await self.load_extension(extension)
                      self.logger.info(f"Successfully loaded extension: {extension}")
                      extension_load_success += 1
                 except commands.ExtensionNotFound:
                      self.logger.error(f"Extension not found: {extension}")
                 except commands.ExtensionAlreadyLoaded:
                      self.logger.warning(f"Extension already loaded: {extension}")
                      extension_load_success += 1 # Count as success if already loaded
                 except commands.NoEntryPointError:
                      self.logger.error(f"Extension {extension} has no setup function.")
                 except commands.ExtensionFailed as e:
                      self.logger.error(f"Extension {extension} failed to load: {e}", exc_info=True)
                 except Exception as e:
                      self.logger.error(f"Unexpected error loading extension {extension}: {e}", exc_info=True)
            
            self.logger.info(f"Loaded {extension_load_success}/{len(extensions_to_load)} extensions.")
            # --- End Extension Loading --- #

            # 4. Sync application commands 
            if self.guild_id:
                guild_object = discord.Object(id=self.guild_id)
                self.tree.copy_global_to(guild=guild_object)
                synced_commands = await self.tree.sync(guild=guild_object)
                self.logger.info(f"Synced {len(synced_commands)} application commands to guild {self.guild_id}.")
            else:
                # Sync globally if no specific guild ID is set
                synced_commands = await self.tree.sync()
                self.logger.info(f"Synced {len(synced_commands)} application commands globally.")

            # --- ADD Logging before exit --- #
            if self.services and hasattr(self.services, 'jutsu_shop_system'):
                shop_sys_status = type(self.services.jutsu_shop_system) if self.services.jutsu_shop_system else "None"
                self.logger.info(f"setup_hook end: services={type(self.services)}, jutsu_shop_system={shop_sys_status}")
            else:
                 self.logger.warning(f"setup_hook end: services={type(self.services)}, jutsu_shop_system attribute MISSING or services None.")
            # --- End Logging --- #
            
        except Exception as e:
            self.logger.critical(f"CRITICAL ERROR during setup_hook: {e}", exc_info=True)
            # Optionally prevent the bot from fully starting if setup fails critically
            # await self.close() 

    async def on_ready(self):
        """Called when the bot is ready."""
        if not self._initialized_services:
            self.logger.warning("on_ready called but services were not initialized in setup_hook. Bot may not function correctly.")
            # You might want to close the bot here if services are critical
            # await self.close()
            # return 

        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info("------")
        
        # Announce status unless silent start
        if not self.silent_start:
            try:
                self.logger.info("Attempting to announce online status...")
                await self._announce_status("online")
            except Exception as e:
                 self.logger.error(f"Error announcing online status in on_ready: {e}", exc_info=True)
        else:
            self.logger.info("Silent start: Skipping online status announcement.")
             
        # --- ADD Logging before check --- #
        if self.services and hasattr(self.services, 'jutsu_shop_system'):
            shop_sys_status = type(self.services.jutsu_shop_system) if self.services.jutsu_shop_system else "None"
            self.logger.info(f"on_ready start: services={type(self.services)}, jutsu_shop_system={shop_sys_status}")
        else:
             self.logger.warning(f"on_ready start: services={type(self.services)}, jutsu_shop_system attribute MISSING or services None.")
        # --- End Logging --- #
        
        # --- Post Initial Jutsu Shop Inventory --- #
        # Skip if silent start
        if not self.silent_start:
            if not self._initial_shop_posted:
                 self.logger.info("Attempting to post initial Jutsu shop inventory...")
                 if self.services and self.services.jutsu_shop_system:
                     try:
                         # Pass the bot instance AND the channel ID from config
                         await self.services.jutsu_shop_system.post_shop_inventory(
                             bot=self, 
                             channel_id=self.config.jutsu_shop_channel_id # Get ID from config
                         )
                         self._initial_shop_posted = True # Mark as posted only if successful
                     except Exception as e:
                          self.logger.error(f"Error posting initial Jutsu shop inventory: {e}", exc_info=True)
                 else:
                     self.logger.warning("JutsuShopSystem not available, cannot post initial inventory.")
        else:
             self.logger.info("Silent start: Skipping initial Jutsu shop post.")

        # Start background tasks if needed
        # Example: self.check_missions_task.start()

    async def on_disconnect(self):
        """Called when the bot disconnects from Discord."""
        self.logger.warning("Bot disconnected from Discord")
        # self.logger.info("Attempting to announce offline status due to disconnect.") # Removed log
        # await self._announce_status("offline") # Removed offline announcement on temporary disconnect

    async def on_resumed(self):
        """Called when the bot resumes its connection to Discord."""
        self.logger.info("Bot resumed connection to Discord")
        await self._announce_status("online")

    async def _announce_status(self, status: str):
        """Announce bot status changes to the designated channel.
        
        Args:
            status: The status to announce ("online" or "offline")
        """
        self.logger.info(f"_announce_status called with status: {status}")
        try:
            if not self.online_channel_id:
                self.logger.warning("No online channel ID configured, skipping status announcement")
                return

            channel = self.get_channel(self.online_channel_id)
            if not channel:
                self.logger.error(f"Could not find channel with ID {self.online_channel_id}")
                return

            # Check if bot has permission to send messages
            if not channel.permissions_for(channel.guild.me).send_messages:
                self.logger.error(f"Bot lacks permission to send messages in channel {self.online_channel_id}")
                return

            # Check if bot has permission to embed links
            if not channel.permissions_for(channel.guild.me).embed_links:
                self.logger.warning(f"Bot lacks permission to embed links in channel {self.online_channel_id}, sending plain text")
                # Send plain text message instead of embed
                message = "🟢 HCShinobi is now online and ready to serve!" if status == "online" else "🔴 HCShinobi is currently offline"
                await channel.send(message)
                self.logger.info(f"Plain text status announcement sent: {status}")
                return

            # Create status embed
            embed = discord.Embed(
                title="HCShinobi Status Update",
                color=discord.Color.green() if status == "online" else discord.Color.red()
            )
            
            if status == "online":
                # Get system status
                character_count = len(self.services.character_system.characters)
                clan_count = len(self.services.clan_data.get_all_clans())
                command_count = len(self.tree.get_commands())
                
                embed.description = "🟢 HCShinobi is now online and ready to serve!"
                
                # System Status Section
                embed.add_field(
                    name="📊 System Status",
                    value=(
                        "```\n"
                        f"Characters: {character_count}\n"
                        f"Clans: {clan_count}\n"
                        f"Commands: {command_count}\n"
                        "Status: Operational\n"
                        "```"
                    ),
                    inline=False
                )
                
                # Version Info Section
                embed.add_field(
                    name="📝 Version Information",
                    value=(
                        "```\n"
                        f"Version: {self.config.version}\n"
                        f"Build: {getattr(self.config, 'build_number', 'N/A')}\n"
                        f"Environment: {getattr(self.config, 'environment', 'Unknown')}\n"
                        "```"
                    ),
                    inline=False
                )
                
                # Recent Updates Section
                if hasattr(self.config, 'recent_updates') and self.config.recent_updates:
                    embed.add_field(
                        name="🔄 Recent Updates",
                        value=(
                            "```\n"
                            + "\n".join(f"• {update}" for update in self.config.recent_updates)
                            + "\n```"
                        ),
                        inline=False
                    )
                
                # Quick Links Section
                embed.add_field(
                    name="🔗 Quick Links",
                    value=(
                        "```\n"
                        "• /create - Create a new character\n"
                        "• /profile - View your profile\n"
                        "• /help - View all commands\n"
                        "• /devlog - View development updates\n"
                        "```"
                    ),
                    inline=False
                )
                
                # Support Section
                embed.add_field(
                    name="❓ Need Help?",
                    value=(
                        "```\n"
                        "• Use /help for command list\n"
                        "• Check /devlog for updates\n"
                        "• Report bugs in #bug-reports\n"
                        "```"
                    ),
                    inline=False
                )
            else:
                embed.description = "🔴 HCShinobi is currently offline"
                embed.add_field(
                    name="⚠️ Status",
                    value=(
                        "```\n"
                        "Status: Offline\n"
                        "Reason: Connection lost\n"
                        "Action: Attempting to reconnect...\n"
                        "```"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="📅 Last Online",
                    value=(
                        "```\n"
                        f"Time: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                        f"Version: {self.config.version}\n"
                        "```"
                    ),
                    inline=False
                )

            # Add timestamp and footer
            embed.timestamp = discord.utils.utcnow()
            embed.set_footer(
                text=f"HCShinobi v{self.config.version} • {status.title()} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            # Send announcement
            await channel.send(embed=embed)
            self.logger.info(f"Status announcement sent: {status}")
            
        except discord.Forbidden:
            self.logger.error(f"Missing permissions to send status announcement to channel {self.online_channel_id}")
        except discord.HTTPException as e:
            self.logger.error(f"HTTP error sending status announcement: {e}")
        except Exception as e:
            self.logger.error(f"Error sending status announcement: {e}", exc_info=True)

    async def send_announcement(self, title: str, description: str, color: discord.Color, channel_id: Optional[int] = None):
        """Sends a formatted announcement embed to the configured channel."""
        target_channel_id = channel_id or getattr(self.config, 'announcement_channel_id', None)
        if not target_channel_id:
            self.logger.error("Announcement channel ID not configured.")
            return

        try:
            channel = self.get_channel(target_channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                self.logger.error(f"Announcement channel with ID {target_channel_id} not found or is not a text channel.")
                return

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=discord.utils.utcnow()
            )
            # You might want to add a standard footer, e.g.:
            # embed.set_footer(text=f"HCShinobi Bot")

            await channel.send(embed=embed)
            self.logger.info(f"Sent announcement to channel {target_channel_id}: {title}")

        except discord.Forbidden:
            self.logger.error(f"Missing permissions to send announcement to channel {target_channel_id}")
        except discord.HTTPException as e:
            self.logger.error(f"HTTP error sending announcement to {target_channel_id}: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error sending announcement: {e}", exc_info=True)

    async def run(self):
        """Run the bot with proper error handling and connection management."""
        try:
            # REMOVED await self.setup()
            logger.info("Starting bot...")
            await self.start(self.config.token) # start() calls setup_hook internally
            
        except Exception as e:
            logger.critical(f"Fatal error preventing bot startup: {e}", exc_info=True)
        # Removed the wait_until_ready/is_closed loop here as discord.py handles it
        # If you need a long-running task after startup, use @tasks.loop

    async def start(self, token: str, *, reconnect: bool = True):
        """Start the bot with improved error handling and timeouts."""
        try:
            # Start the bot with retry logic
            max_retries = 3
            retry_count = 0
            last_error = None
            
            while retry_count < max_retries:
                try:
                    await super().start(token, reconnect=reconnect)
                    
                    # Set connection timeouts after client is initialized
                    if hasattr(self, 'http') and hasattr(self.http, 'connector'):
                        self.http.connector.set_default_timeout(30)  # 30 second timeout for HTTP requests
                    if hasattr(self, 'ws'):
                        self.ws.max_heartbeat_timeout = 60  # 60 second timeout for heartbeat
                    
                    break
                except discord.ConnectionClosed as e:
                    last_error = e
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"Connection closed, retrying ({retry_count}/{max_retries})...")
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    else:
                        raise
                except Exception as e:
                    logger.error(f"Error starting bot: {e}")
                    raise
            
            if retry_count >= max_retries and last_error:
                raise last_error
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def close(self):
        """Close the bot with proper cleanup."""
        self.logger.info("Closing bot...")
        try:
            # Announce offline status before closing
            if self._initialized_services: # Only announce if services were up
                 self.logger.info("Attempting to announce offline status during graceful shutdown.")
                 await self._announce_status("offline")
            else:
                 self.logger.info("Skipping offline announcement as services were not initialized.")
        except Exception as e:
             self.logger.error(f"Error sending offline status announcement during close: {e}", exc_info=True)
        finally:
            # Ensure services are shut down if they were initialized
            if self._initialized_services and self.services:
                 await self.services.shutdown()
            # Call original close method
            await super().close()
            self.logger.info("Bot closed successfully.")

    @property
    def clan_data(self):
        """Get the clan data service."""
        if not self._clan_data:
            raise RuntimeError("Bot not initialized. Call setup() first.")
        return self._clan_data

async def run_bot():
    """
    Main entry point to configure environment, init core services, and start the HCShinobiBot.
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
        # Ensure services are shut down
        if hasattr(bot, 'services') and bot.services:
            try:
                await bot.services.shutdown()
                logger.info("Services shut down successfully")
            except Exception as e:
                logger.error(f"Error shutting down services: {e}")
        
        # Close the bot if still running
        if not bot.is_closed():
            try:
                logger.info("Closing bot connection...")
                await bot.close()
                logger.info("Bot connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing bot connection: {e}")
        
        logger.info("===== HCShinobi Bot has shut down. =====")
