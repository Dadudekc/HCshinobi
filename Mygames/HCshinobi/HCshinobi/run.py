"""
Main entry point for the HCShinobi Discord bot.
Handles environment setup and bot initialization.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import discord
import logging
from typing import Optional

from HCshinobi.bot.bot import HCShinobiBot
from HCshinobi.bot.config import load_config, BotConfig
from HCshinobi.bot.services import ServiceContainer

logger = logging.getLogger(__name__)

async def initialize_services(config: BotConfig) -> Optional[ServiceContainer]:
    """Initialize bot services with proper error handling."""
    try:
        services = ServiceContainer(config)
        await services.initialize()
        return services
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return None

async def run_bot(config: BotConfig, services: ServiceContainer) -> None:
    """Run the Discord bot with enhanced error handling."""
    bot = None
    try:
        # Create bot instance
        bot = HCShinobiBot(config, services)
        
        # Start the bot
        logger.info("Starting bot login...")
        await bot.start(config.token)
        
        # Keep the bot running
        await bot.wait_until_ready()
        
    except discord.LoginFailure as e:
        logger.error(f"Failed to log in: {e}")
        raise
    except discord.PrivilegedIntentsRequired as e:
        logger.error(f"Missing privileged intents: {e}")
        raise
    except discord.HTTPException as e:
        logger.error(f"Discord HTTP error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during bot runtime: {e}")
        raise
    finally:
        # Clean up resources
        if bot and not bot.is_closed():
            logger.info("Closing bot connection...")
            await bot.close()
        if services:
            logger.info("Shutting down services...")
            await services.shutdown()

def main():
    """Main entry point for the bot with improved error handling."""
    # Check for maintenance mode flag
    maintenance_mode = "--maintenance" in sys.argv or "-m" in sys.argv
    if maintenance_mode:
        os.environ["MAINTENANCE_MODE"] = "true"
        print("Maintenance mode enabled")
    
    try:
        # Load configuration
        config = load_config()
        
        # Initialize services
        services = asyncio.run(initialize_services(config))
        if not services:
            print("Failed to initialize services. Check the logs for details.")
            sys.exit(1)
        
        # Run the bot
        asyncio.run(run_bot(config, services))
        
    except KeyboardInterrupt:
        print("\nBot shutting down...")
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 