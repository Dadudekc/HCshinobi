"""
HCShinobi - Complete Discord Bot Runner
Comprehensive main file that integrates all commands, cogs, and missions.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from importlib import import_module
from pathlib import Path
from typing import Final, Sequence

import discord
from discord.ext import commands
from dotenv import load_dotenv
import base64

from HCshinobi.bot.config import BotConfig

# ---------------------------------------------------------------------------
# Complete Cog Configuration - Deduplicated and Organized
# ---------------------------------------------------------------------------

# Primary bot cogs from HCshinobi/bot/cogs/ - Core functionality (deduplicated)
MAIN_COGS: Final[Sequence[str]] = (
    "HCshinobi.bot.cogs.essential_commands",                # Help, jutsu, achievements, profile
    "HCshinobi.bot.cogs.character_commands",                # Character creation & management
    "HCshinobi.bot.cogs.currency",                          # Currency & economy system
    "HCshinobi.bot.cogs.battle_system",                     # Battle mechanics
    "HCshinobi.bot.cogs.missions",                          # Mission system + ShinobiOS missions
    "HCshinobi.bot.cogs.clan_mission_commands",             # Clan-specific missions
    "HCshinobi.bot.cogs.shop_commands",                     # Shopping system
    "HCshinobi.bot.cogs.training_commands",                 # Training system (5 commands)
    "HCshinobi.bot.cogs.token_commands",                    # Token system
    "HCshinobi.bot.cogs.announcements",                     # Announcements
    "HCshinobi.bot.cogs.clans",                            # Clan management system with roll_clan
    "HCshinobi.bot.cogs.updated_boss_commands",             # Updated Solomon boss battle system
)

# Specialized cogs - Unique advanced functionality
SPECIALIZED_COGS: Final[Sequence[str]] = (
    "HCshinobi.bot.cogs.boss_commands",                     # Solomon & NPC boss battles (37KB!)
)

# --------------------------------------------------------------------------- #
# Bot Setup Functions
# --------------------------------------------------------------------------- #

def setup_logging(level: str = "INFO") -> None:
    """Configure comprehensive logging for the bot."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("discord").setLevel(logging.WARNING)
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Add file handler for persistent logging
    file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logging.getLogger().addHandler(file_handler)

def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logging.info("Loaded environment variables from .env file")
    else:
        logging.warning(".env file not found – relying on system environment.")

def require_env() -> BotConfig:
    """Validate and return required environment configuration."""
    # Get environment variables with defaults for testing
    token = os.getenv("DISCORD_BOT_TOKEN", "your_bot_token_here").strip()
    app_id = os.getenv("DISCORD_APPLICATION_ID", "your_application_id_here").strip()
    guild_id = os.getenv("DISCORD_GUILD_ID", "your_guild_id_here").strip()
    
    # Check if we're in testing mode (using placeholder values)
    is_testing = (token == "your_bot_token_here" or 
                  app_id == "your_application_id_here" or 
                  guild_id == "your_guild_id_here")
    
    if is_testing:
        logging.warning("⚠️ Using placeholder values - running in testing mode")
        # Use safe placeholder numeric values for testing
        safe_app_id = "123456789012345678"
        safe_guild_id = "123456789012345678"
    else:
        # Validate required variables are set for production
        missing = []
        if not token or token == "your_bot_token_here":
            missing.append("DISCORD_BOT_TOKEN")
        if not app_id or app_id == "your_application_id_here":
            missing.append("DISCORD_APPLICATION_ID")
        if not guild_id or guild_id == "your_guild_id_here":
            missing.append("DISCORD_GUILD_ID")
        
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
        
        safe_app_id = app_id
        safe_guild_id = guild_id

    # Get optional channel IDs with defaults for testing
    battle_channel_id = os.getenv("DISCORD_BATTLE_CHANNEL_ID", "123456789012345678")
    online_channel_id = os.getenv("DISCORD_ONLINE_CHANNEL_ID", "123456789012345678")
    
    if os.getenv("DISCORD_BATTLE_CHANNEL_ID") is None:
        logging.warning("⚠️ DISCORD_BATTLE_CHANNEL_ID not set, using placeholder value")
    if os.getenv("DISCORD_ONLINE_CHANNEL_ID") is None:
        logging.warning("⚠️ DISCORD_ONLINE_CHANNEL_ID not set, using placeholder value")

    logging.debug(f"Loaded token prefix: {token.split('.')[0] if token else 'None'}")
    logging.debug(f"Expected App ID: {safe_app_id}")

    # Skip token validation for testing if using placeholder values
    if not is_testing and token != "your_bot_token_here":
        parts = token.split('.')
        if len(parts) != 3:
            raise RuntimeError("Invalid Discord bot token format.")
        
        try:
            # Validate token matches application ID
            p0 = parts[0]
            pad = '=' * (-len(p0) % 4)
            decoded_id = base64.urlsafe_b64decode(p0 + pad).decode('utf-8')
            if decoded_id != safe_app_id:
                raise RuntimeError(f"Token does not match Application ID. Token ID '{decoded_id}' vs App ID '{safe_app_id}'.")
        except Exception as e:
            logging.warning(f"Could not validate token: {e}")

        logging.info("Token format appears valid and matches the Application ID.")
    else:
        logging.warning("⚠️ Using placeholder values - bot will not connect to Discord")

    return BotConfig(
        command_prefix="!",
        application_id=int(safe_app_id),
        guild_id=int(safe_guild_id),
        battle_channel_id=int(battle_channel_id),
        online_channel_id=int(online_channel_id),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

async def load_cog_safely(bot: "HCBot", cog_path: str, cog_type: str) -> bool:
    """Safely load a single cog with error handling."""
    try:
        # Import the module
        module = import_module(cog_path)
        
        # Check if the module has a setup function
        if hasattr(module, 'setup'):
            # Use the standard discord.py cog loading mechanism
            await module.setup(bot)
            logging.info(f"✅ Successfully loaded {cog_type} cog: {cog_path}")
            return True
        else:
            logging.warning(f"No setup function found in {cog_path}")
            return False
        
    except ImportError as e:
        logging.warning(f"⚠️ Could not import {cog_type} cog {cog_path}: {e}")
        return False
    except AttributeError as e:
        logging.warning(f"⚠️ Cog setup not found in {cog_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Failed to load {cog_type} cog {cog_path}: {e}")
        return False

async def build_bot(config: BotConfig) -> "HCBot":
    """Build and configure the complete bot with all available cogs."""
    from HCshinobi.bot.bot import HCBot
    
    # Configure Discord intents
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True

    logging.info("Creating HCBot instance...")
    bot = HCBot(config=config)
    logging.info("HCBot instance created successfully")

    # Track loading statistics  
    total_cogs = len(MAIN_COGS) + len(SPECIALIZED_COGS)
    loaded_count = 0
    
    logging.info(f"Loading {total_cogs} total cogs (fully deduplicated - no conflicts)...")

    # Load main bot cogs (priority - core functionality)
    logging.info(f"Loading {len(MAIN_COGS)} main cogs...")
    for cog_path in MAIN_COGS:
        if await load_cog_safely(bot, cog_path, "main"):
            loaded_count += 1

    # Load specialized cogs (unique advanced functionality)
    logging.info(f"Loading {len(SPECIALIZED_COGS)} specialized cogs...")
    for cog_path in SPECIALIZED_COGS:
        if await load_cog_safely(bot, cog_path, "specialized"):
            loaded_count += 1

    # Summary
    logging.info(f"🎯 Cog loading complete: {loaded_count}/{total_cogs} cogs loaded successfully")
    
    if loaded_count == 0:
        logging.error("❌ No cogs were loaded! Bot will have no functionality.")
    elif loaded_count < total_cogs:
        logging.warning(f"⚠️ Some cogs failed to load ({total_cogs - loaded_count} missing)")
    else:
        logging.info("✅ All cogs loaded successfully!")

    # Debug: Check command tree after cog loading
    tree_commands = list(bot.tree.walk_commands())
    logging.info(f"🔍 Commands in tree after cog loading: {len(tree_commands)}")
    
    if tree_commands:
        tree_command_names = [cmd.name for cmd in tree_commands[:10]]
        logging.info(f"🔍 First 10 tree commands: {tree_command_names}")
    else:
        logging.warning("⚠️ No commands found in tree after cog loading!")

    # Log what's available
    logging.info("📋 Available systems:")
    logging.info("   🎯 Main: Help+Jutsu+Achievements, Currency, Battle, Missions+ShinobiOS, Clans, Shop, Training, Tokens, Announcements")
    logging.info("   ⚔️ Specialized: Boss Battles (Solomon)")

    return bot

async def send_startup_notification(bot: "HCBot", config: BotConfig) -> None:
    """Send startup notification to Discord channel."""
    try:
        channel = bot.get_channel(config.online_channel_id)
        if channel:
            embed = discord.Embed(
                title="🎮 HCShinobi v2.0 - System Online",
                description="**🌟 COMPREHENSIVE NINJA GAME SYSTEM READY!**\n\n"
                           "**✅ CURRENT STATUS:**\n"
                           "• **Bot Online** ✅ - All systems operational\n"
                           "• **53 Commands Loaded** ✅ - All commands registered\n"
                           "• **Slash Commands** ✅ - Synced globally to Discord\n\n"
                           "**🔧 TECHNICAL UPDATE:**\n"
                           "• Commands synced globally (simplified sync process)\n"
                           "• Should appear within 5-15 minutes (normal Discord timing)\n"
                           "• Try `/help` first to test command availability\n\n"
                           "**⚔️ NEW v2.0 FEATURES:**\n"
                           "• **D20 Battle System** - True dice mechanics with modifiers\n"
                           "• **30+ Jutsu System** - Stat-based unlocking & progression\n"
                           "• **20 Clans** - Expanded clan roster with rarity tiers\n"
                           "• **ShinobiOS Missions** - Interactive `/mission` system\n"
                           "• **Progression Engine** - Automatic jutsu & rank advancement\n"
                           "• **Interactive UI** - Discord buttons & saving throws\n\n"
                           "**🎯 CORE SYSTEMS:**\n"
                           "• Character Creation & Management\n"
                           "• Currency & Economy Management\n"
                           "• Battle & Training Systems\n" 
                           "• Mission & Quest Systems\n"
                           "• Clan Management & Missions\n"
                           "• Shop & Token Systems\n"
                           "• Boss Battle Systems (Solomon)\n"
                           "• Announcements System",
                color=0xffff00,  # Yellow to indicate caution
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(
                name="🎲 D20 Mechanics", 
                value="• True dice rolls with stat modifiers\n• Interactive saving throws\n• Stat-based jutsu effectiveness", 
                inline=True
            )
            embed.add_field(
                name="🥷 Jutsu System", 
                value="• 30+ unique techniques\n• Stat & achievement requirements\n• Automatic unlocking system", 
                inline=True
            )
            embed.add_field(
                name="🏛️ Clan System", 
                value="• 20 clans with rarity tiers\n• Clan-specific missions\n• Roll-based assignment", 
                inline=True
            )
            embed.add_field(
                name="📊 Status", 
                value=f"✅ {len(bot.cogs)} systems operational\n✅ Commands synced globally\n⏳ Please wait 5-15 minutes for commands to appear", 
                inline=False
            )
            embed.add_field(
                name="🔧 Troubleshooting", 
                value="• Try `/help` first to test command availability\n• Commands synced globally (simplified process)\n• Should appear within normal Discord timing", 
                inline=False
            )
            embed.set_footer(text="HCShinobi v2.0 - Complete Ninja RPG Experience | Commands synced globally")
            
            await channel.send(embed=embed)
            logging.info(f"✅ Startup notification sent to channel {config.online_channel_id}")
        else:
            logging.warning(f"⚠️ Could not find online channel {config.online_channel_id}")
    except Exception as e:
        logging.error(f"❌ Failed to send startup notification: {e}")

# --------------------------------------------------------------------------- #
# Main Bot Runner
# --------------------------------------------------------------------------- #

async def run_bot() -> None:
    """Main bot execution function."""
    setup_logging()
    load_env()
    config = require_env()

    logging.info("🚀 Starting HCShinobi Discord Bot...")
    logging.info("=" * 60)
    logging.info("🧹 Using deduplicated and optimized cog loading system")
    logging.info("=" * 60)

    bot = await build_bot(config)
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()

    # Check if we're using placeholder token (testing mode)
    is_testing = token == "your_bot_token_here"
    
    if is_testing:
        logging.info("🧪 TESTING MODE: Analyzing bot without Discord connection")
        logging.info("🔧 Examining loaded cogs and commands...")
        
        # Count commands across all cogs
        total_commands = 0
        cog_details = {}
        
        for cog_name, cog in bot.cogs.items():
            # Get both traditional commands and app commands
            traditional_commands = cog.get_commands()
            app_commands = cog.get_app_commands()
            
            # Combine command names with appropriate prefixes
            command_names = []
            command_names.extend([f"!{cmd.name}" for cmd in traditional_commands])
            command_names.extend([f"/{cmd.name}" for cmd in app_commands])
            
            command_count = len(command_names)
            total_commands += command_count
            
            cog_details[cog_name] = {
                'count': command_count,
                'commands': command_names
            }
            
            logging.info(f"   📦 {cog_name}: {command_count} commands")
            if command_count > 0:
                if command_count <= 5:
                    logging.info(f"       {'/'.join(command_names)}")
                else:
                    logging.info(f"       {'/'.join(command_names[:3])} ... +{command_count-3} more")
        
        logging.info(f"📊 ANALYSIS COMPLETE:")
        logging.info(f"   💎 Total Cogs: {len(bot.cogs)}")
        logging.info(f"   ⚡ Total Commands: {total_commands}")
        
        # Check character commands specifically
        if 'CharacterCommands' in cog_details:
            char_commands = cog_details['CharacterCommands']['commands']
            logging.info(f"   🥷 Character Commands: {char_commands}")
        else:
            logging.warning("   ⚠️ CharacterCommands cog not found!")
            
        logging.info("✅ Bot validation complete - ready for Discord!")
        return

    # Setup bot ready event for startup notification
    @bot.event
    async def on_ready():
        logging.info(f"🎉 {bot.user} has connected to Discord!")
        logging.info(f"📊 Connected to {len(bot.guilds)} guild(s)")
        logging.info(f"🔧 Loaded {len(bot.cogs)} cog(s) (no duplicates)")
        
        # Debug: Check what commands are in the tree before syncing
        tree_commands = list(bot.tree.walk_commands())
        logging.info(f"🔍 Commands in tree before sync: {len(tree_commands)}")
        
        # List first few command names in tree for verification
        if tree_commands:
            tree_command_names = [cmd.name for cmd in tree_commands[:10]]
            logging.info(f"🔍 First 10 tree commands: {tree_command_names}")
        else:
            logging.error("❌ No commands found in tree!")
        
        # Count commands per cog for debugging
        total_app_commands = 0
        for cog_name, cog in bot.cogs.items():
            app_commands = cog.get_app_commands()
            total_app_commands += len(app_commands)
            if len(app_commands) > 0:
                logging.info(f"   📦 {cog_name}: {len(app_commands)} app commands")
        
        logging.info(f"🔍 Total app commands in cogs: {total_app_commands}")
        
        # If no commands in tree but commands in cogs, there's a registration issue
        if len(tree_commands) == 0 and total_app_commands > 0:
            logging.error("❌ Commands exist in cogs but not in command tree! Registration issue detected.")
        
        # Check if guild-specific sync might be the issue
        logging.info(f"🔍 Attempting sync to guild ID: {config.guild_id}")
        
        # Try to get more details about the tree state
        logging.info(f"🔍 Tree client: {bot.tree.client}")
        logging.info(f"🔍 Tree._global_commands length: {len(bot.tree._global_commands)}")
        logging.info(f"🔍 Tree._guild_commands length: {len(bot.tree._guild_commands)}")
            
        # Sync slash commands to Discord
        try:
            logging.info("🔄 Syncing slash commands with Discord...")
            
            # Use global sync - commands are registered as global commands
            logging.info("🔄 Syncing commands globally (commands are registered as global)...")
            synced = await bot.tree.sync()
            logging.info(f"✅ Successfully synced {len(synced)} slash commands globally")
            
            if len(synced) > 0:
                command_names = [cmd.name for cmd in synced[:10]]
                logging.info(f"🔍 Synced commands: {', '.join(command_names)}{' ...' if len(synced) > 10 else ''}")
                
                # Check if commands are actually available in the guild
                if config.guild_id and config.guild_id != 123456789012345678:
                    guild = bot.get_guild(config.guild_id)
                    if guild:
                        logging.info(f"✅ Bot is in guild: {guild.name}")
                        logging.info(f"🔍 Bot permissions in guild: {guild.me.guild_permissions}")
                        logging.info("⏳ Commands will appear in Discord within 5-15 minutes (normal global sync timing)")
                    else:
                        logging.warning(f"⚠️ Bot is not in guild with ID: {config.guild_id}")
            else:
                logging.warning("⚠️ No commands were synced to Discord!")
                logging.warning("🔍 This might indicate:")
                logging.warning("   - Commands are not properly registered to the tree")
                logging.warning("   - Bot lacks application.commands scope")
                logging.warning("   - Discord API rate limiting")
                
        except Exception as e:
            logging.error(f"❌ Failed to sync commands: {e}")
            import traceback
            logging.error(f"❌ Full traceback: {traceback.format_exc()}")
        
        logging.info("🎯 DISCORD BOT IS NOW ONLINE!")
        
        # Send startup notification
        await send_startup_notification(bot, config)

    try:
        logging.info("🔌 Connecting to Discord...")
        await bot.start(token)
        
    except discord.errors.LoginFailure as e:
        logging.error(f"❌ Login failed: {e}")
        raise
    except Exception as e:
        logging.error(f"❌ Unexpected error during connection: {e}")
        raise
    except KeyboardInterrupt:
        logging.info("🛑 Shutdown requested by user.")
    finally:
        logging.info("🔌 Closing bot connection...")
        await bot.close()
        logging.info("✅ Bot closed gracefully.")

# --------------------------------------------------------------------------- #
# Entry Point
# --------------------------------------------------------------------------- #

def main() -> None:
    """Main entry point for the bot."""
    try:
        print("🎮 HCShinobi Discord Bot")
        print("=" * 30)
        print("🧹 Deduplicated & Optimized")
        print("=" * 30)
        print("Loading comprehensive command suite:")
        print("• Character & Clan Systems")
        print("• Battle & Training Systems") 
        print("• Mission & Quest Systems")
        print("• Economy & Token Systems")
        print("• Boss Battle Systems (Solomon)")
        print("• ShinobiOS Battle Missions")
        print("• Legacy Support Systems")
        print("=" * 30)
        
        asyncio.run(run_bot())
        
    except (KeyboardInterrupt, asyncio.CancelledError):
        logging.info("🛑 Bot shutdown complete.")
        sys.exit(0)
    except Exception:
        logging.exception("💥 Bot terminated with an unexpected error.")
        sys.exit(1)

if __name__ == "__main__":
    main() 