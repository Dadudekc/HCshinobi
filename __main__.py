"""Main entry point for the HCshinobi bot."""
import sys
import os
# Ensure the package root is in sys.path if running as script
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Setup logging FIRST
import logging
try:
    # Assuming setup_logging is in HCshinobi.utils.logging
    from HCshinobi.utils.logging import setup_logging
    setup_logging() # Call setup immediately
    logging.info("[__main__] Logging setup complete.")
except ImportError as e:
    # Fallback basic config if util cannot be imported
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logging.error(f"[__main__] Failed to import setup_logging: {e}. Using basic config.")
except Exception as e:
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    logging.error(f"[__main__] Error calling setup_logging: {e}. Using basic config.", exc_info=True)

# Now import other modules
logging.info("[__main__] Importing asyncio...")
import asyncio
logging.info("[__main__] Importing argparse...")
import argparse
logging.info("[__main__] Importing HCBot...")
from HCshinobi.bot.bot import HCBot
logging.info("[__main__] Importing load_config...")
from HCshinobi.bot.config import load_config
logging.info("[__main__] Imports complete.")

async def main(silent_start: bool = False):
    logging.info("[main] Starting main async function...")
    config = load_config()
    logging.info("[main] Config loaded.")
    bot = HCBot(config, silent_start=silent_start)
    logging.info("[main] HCBot initialized.")
    # Let HCBot handle the start internally via its run/start methods
    await bot.run() # Reverted to bot.run() which calls bot.start()
    logging.info("[main] bot.run() awaited.")

if __name__ == "__main__":
    logging.info("[__main__] Script execution started.")
    # --- Argument Parsing --- #
    parser = argparse.ArgumentParser(description="Run the HCShinobi Discord bot.")
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Start the bot without sending startup announcements (e.g., online status, initial shop post)."
    )
    args = parser.parse_args()
    logging.info(f"[__main__] Args parsed: silent={args.silent}")
    # --- End Argument Parsing --- #

    try:
        logging.info("[__main__] Running asyncio.run(main)...")
        asyncio.run(main(silent_start=args.silent))
        logging.info("[__main__] asyncio.run(main) completed.")
    except Exception as e:
        logging.critical(f"[__main__] Unhandled exception in main: {e}", exc_info=True)
        # Ensure exit code reflects error
        sys.exit(1)
    finally:
        logging.info("[__main__] Script execution finished.") 