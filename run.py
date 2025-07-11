"""
HCShinobi – Discord bot bootstrap.
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

# --------------------------------------------------------------------------- #
# ASCII Art Banner
# --------------------------------------------------------------------------- #

def print_ascii_banner():
    """Print the classic HCShinobi ASCII art banner"""
    banner = """
    ██╗  ██╗ ██████╗███████╗██╗  ██╗██╗███╗   ██╗ ██████╗ ██████╗ ██╗
    ██║  ██║██╔════╝██╔════╝██║  ██║██║████╗  ██║██╔═══██╗██╔══██╗██║
    ███████║██║     ███████╗███████║██║██╔██╗ ██║██║   ██║██████╔╝██║
    ██╔══██║██║     ╚════██║██╔══██║██║██║╚██╗██║██║   ██║██╔══██╗██║
    ██║  ██║╚██████╗███████║██║  ██║██║██║ ╚████║╚██████╔╝██████╔╝██║
    ╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚═╝
                                                                      
    🎌 SHINOBI CHRONICLES - DISCORD BOT 🎌
    ════════════════════════════════════════════════════════════════════
    
    🎮 Complete Command Suite Loading:
    • Character & Clan Systems
    • Battle & Training Systems  
    • Mission & Quest Systems
    • Economy & Token Systems
    • Boss Battle Systems
    • ShinobiOS Battle Missions
    
    ════════════════════════════════════════════════════════════════════
    """
    print(banner)

# --------------------------------------------------------------------------- #
# Initialisation helpers
# --------------------------------------------------------------------------- #

COGS: Final[Sequence[str]] = (
    "HCshinobi.bot.cogs.character_commands.CharacterCommands",
    "HCshinobi.bot.cogs.currency.CurrencyCommands",
    "HCshinobi.bot.cogs.battle_system.BattleSystemCommands",
    "HCshinobi.bot.cogs.missions.MissionCommands",
    "HCshinobi.bot.cogs.clan_mission_commands.ClanMissionCommands",
    "HCshinobi.bot.cogs.shop_commands.ShopCommands",
    "HCshinobi.bot.cogs.training_commands.TrainingCommands",
    "HCshinobi.bot.cogs.token_commands.TokenCommands",
)


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("discord").setLevel(logging.WARNING)


def load_env() -> None:
    """Load .env if present."""
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        logging.warning(".env file not found – relying on system environment.")


def require_env() -> BotConfig:
    """Check for and return all required environment variables."""
    missing = []
    required = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_APPLICATION_ID",
        "DISCORD_GUILD_ID",
        "DISCORD_BATTLE_CHANNEL_ID",
        "DISCORD_ONLINE_CHANNEL_ID",
    ]
    for var in required:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    # --- Token Validation Logic (optional) ---
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    app_id = os.getenv("DISCORD_APPLICATION_ID", "").strip()
    print("--> [DEBUG] Loaded token prefix:", token.split('.')[0])
    print("--> [DEBUG] Expected App ID:", app_id)

    parts = token.split('.')
    if len(parts) != 3:
        raise RuntimeError(
            "--> [CRITICAL ERROR] The provided DISCORD_BOT_TOKEN is not in three-part format."
        )
    try:
        # URL-safe Base64 decode with correct padding
        p0 = parts[0]
        pad = '=' * (-len(p0) % 4)
        decoded_id = base64.urlsafe_b64decode(p0 + pad).decode('utf-8')
        if decoded_id != app_id:
            raise RuntimeError(
                f"--> [CRITICAL ERROR] Token does not match Application ID. "
                f"Token ID '{decoded_id}' vs App ID '{app_id}'."
            )
    except Exception as e:
        # If you prefer to skip this check, comment it out
        raise RuntimeError(f"--> [CRITICAL ERROR] Could not decode token. Error: {e}")

    print("--> [SUCCESS] Token format appears valid and matches the Application ID.")
    return BotConfig(
        command_prefix="!",
        application_id=int(app_id),
        guild_id=int(os.getenv("DISCORD_GUILD_ID")),
        battle_channel_id=int(os.getenv("DISCORD_BATTLE_CHANNEL_ID")),
        online_channel_id=int(os.getenv("DISCORD_ONLINE_CHANNEL_ID")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


async def build_bot(config: BotConfig) -> "HCBot":
    """Instantiate bot with intents and load cogs dynamically."""
    from HCshinobi.bot.bot import HCBot  # local import avoids circular issues

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    logging.info("Creating HCBot instance...")
    bot = HCBot(config=config)
    logging.info("HCBot instance created successfully")

    logging.info(f"Loading {len(COGS)} cogs...")
    for i, cog_path in enumerate(COGS):
        logging.info(f"Loading cog {i+1}/{len(COGS)}: {cog_path}")
        try:
            # Assumes cog_path is like "folder.module.ClassName"
            # We need to import "folder.module" and then get "ClassName"
            module_path, class_name = cog_path.rsplit(".", 1)
            logging.debug(f"Importing module: {module_path}")
            module = import_module(module_path)
            logging.debug(f"Getting class: {class_name}")
            cog_class = getattr(module, class_name)
            logging.debug(f"Instantiating cog: {class_name}")
            cog_instance = cog_class(bot)
            logging.debug(f"Adding cog to bot: {class_name}")
            await bot.add_cog(cog_instance)
            logging.info(f"Successfully loaded cog: {class_name}")
        except Exception as e:
            logging.error(f"Failed to load cog {cog_path}: {e}")
            raise

    logging.info("All cogs loaded successfully")
    return bot


async def run_bot() -> None:
    setup_logging()
    load_env()
    cfg = require_env()

    logging.info("Building bot instance...")

    bot = await build_bot(cfg)
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()

    try:
        logging.info("Connecting to Discord…")
        logging.info("Starting bot.start() call...")
        await bot.start(token)
        logging.info("Bot.start() completed successfully")
    except discord.errors.LoginFailure as e:
        logging.error(f"Login failed: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error during connection: {e}")
        raise
    except KeyboardInterrupt:
        logging.info("Shutdown requested by user.")
    finally:
        logging.info("Closing bot connection...")
        await bot.close()
        logging.info("Bot closed gracefully.")


# --------------------------------------------------------------------------- #
# Script entry-point
# --------------------------------------------------------------------------- #

def main() -> None:
    """Main entry point with classic ASCII art banner."""
    # Display the classic ASCII banner first
    print_ascii_banner()
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 Bot shutdown requested by user.")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
