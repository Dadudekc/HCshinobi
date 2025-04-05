"""Main entry point for the HCshinobi bot."""
import asyncio
import argparse
from HCshinobi.bot.bot import HCBot
from HCshinobi.bot.config import load_config

async def main(silent_start: bool = False):
    """Run the bot."""
    config = load_config()
    bot = HCBot(config, silent_start=silent_start)
    await bot.run()

if __name__ == "__main__":
    # --- Argument Parsing --- #
    parser = argparse.ArgumentParser(description="Run the HCShinobi Discord bot.")
    parser.add_argument(
        "--silent", 
        action="store_true", 
        help="Start the bot without sending startup announcements (e.g., online status, initial shop post)."
    )
    args = parser.parse_args()
    # --- End Argument Parsing --- #

    asyncio.run(main(silent_start=args.silent)) 