"""
Debug entry point for the HCShinobi Discord bot.
Handles environment setup and bot initialization with enhanced logging.
"""

import os
import sys
import asyncio
import traceback
from dotenv import load_dotenv
import discord
import logging
from typing import Optional
from pathlib import Path

# Load environment variables from .env file
load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# Import the bot components
logger = logging.getLogger(__name__)
logger.info("Starting HCShinobi bot in debug mode")

try:
    logger.info("Importing bot modules...")
    from HCshinobi.bot.bot import HCBot
    from HCshinobi.bot.config import load_config, BotConfig
    from HCshinobi.bot.services import ServiceContainer
    logger.info("Successfully imported bot modules")
except ImportError as e:
    logger.critical(f"Failed to import required modules: {e}")
    traceback.print_exc()
    sys.exit(1)

async def initialize_services(config: BotConfig) -> Optional[ServiceContainer]:
    """Initialize bot services with detailed error handling."""
    try:
        logger.info("Initializing service container...")
        services = ServiceContainer(config)
        
        logger.info("Starting service initialization...")
        await services.initialize()
        
        logger.info("Services initialized successfully")
        return services
    except Exception as e:
        logger.critical(f"Failed to initialize services: {e}")
        traceback.print_exc()
        return None

async def run_bot(config: BotConfig, services: ServiceContainer) -> None:
    """Run the Discord bot with enhanced error handling and debugging."""
    bot = None
    try:
        # Log configuration details (excluding sensitive info)
        logger.info(f"Command prefix: {config.command_prefix}")
        logger.info(f"Application ID: {config.application_id}")
        logger.info(f"Data directory: {config.data_dir}")
        
        # Create bot instance
        logger.info("Creating bot instance...")
        bot = HCBot(config)
        
        # Set up the bot (this will initialize services)
        logger.info("Setting up bot...")
        await bot.setup()
        
        # Start the bot
        logger.info("Starting bot login...")
        await bot.start(config.token)
        
        # Keep the bot running
        logger.info("Waiting for bot to be ready...")
        await bot.wait_until_ready()
        logger.info(f"Bot is ready! Logged in as {bot.user.name} (ID: {bot.user.id})")
        
    except discord.LoginFailure as e:
        logger.critical(f"Failed to log in: {e}")
        traceback.print_exc()
        raise
    except discord.PrivilegedIntentsRequired as e:
        logger.critical(f"Missing privileged intents: {e}")
        traceback.print_exc()
        raise
    except discord.HTTPException as e:
        logger.critical(f"Discord HTTP error: {e}")
        traceback.print_exc()
        raise
    except Exception as e:
        logger.critical(f"Unexpected error during bot runtime: {e}")
        traceback.print_exc()
        raise
    finally:
        # Clean up resources
        if bot and not bot.is_closed():
            logger.info("Closing bot connection...")
            await bot.close()

def main():
    """Main entry point for the bot with improved error handling and debugging."""
    logger.info("Starting main function")
    
    # Check for maintenance mode flag
    maintenance_mode = "--maintenance" in sys.argv or "-m" in sys.argv
    if maintenance_mode:
        os.environ["MAINTENANCE_MODE"] = "true"
        logger.info("Maintenance mode enabled")
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config()
        logger.info("Configuration loaded successfully")
        
        # Run the bot
        logger.info("Running bot...")
        asyncio.run(run_bot(config, None))  # Pass None for services since bot will create its own
        
    except KeyboardInterrupt:
        logger.info("Bot shutting down due to keyboard interrupt...")
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Critical error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Script started")
    main()
    logger.info("Script ended") 