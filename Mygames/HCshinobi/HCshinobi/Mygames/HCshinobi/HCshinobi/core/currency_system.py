"""Currency system for managing in-game currency."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union, Any
from discord.ext import tasks, commands
import asyncio

# --- NEW: Import constants if needed, or define filename --- #
# from .constants import CURRENCY_SUBDIR, CURRENCY_FILE # Assuming these exist
# If not defined in constants.py, define locally:
CURRENCY_FILENAME = "currency.json"
# --- END NEW --- #

logger = logging.getLogger(__name__)

# --- Data Logic Class ---
class CurrencySystem:
    """Manages in-game currency data storage and manipulation."""

    def __init__(self, data_dir: str):
        """Initialize the currency system.
        
        Args:
            data_dir: Base data directory path.
        """
        self.data_dir = data_dir
        # Assuming currency file resides directly in data_dir for now
        # If it should be in CURRENCY_SUBDIR, adjust path construction
        self.data_file = os.path.join(self.data_dir, CURRENCY_FILENAME)
        self.currency_data: Dict[str, int] = {}
        logger.info(f"CurrencySystem initialized. Data file path: {self.data_file}")
        # Load data immediately on init (sync for now)
        self.load_currency_data()

    def load_currency_data(self) -> None:
        """Load currency data from file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.currency_data = json.load(f)
                logger.info(f"Loaded currency data from {self.data_file}")
            else:
                logger.info(f"No currency data file found at {self.data_file}, creating new")
                self.currency_data = {}
                self.save_currency_data() # Save initial empty state
        except (json.JSONDecodeError, IOError, TypeError) as e:
            logger.error(f"Error loading currency data from {self.data_file}: {e}")
            self.currency_data = {}

    def save_currency_data(self) -> None:
        """Save currency data to file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            # Save atomically using a temporary file
            temp_filepath = f"{self.data_file}.tmp"
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.currency_data, f, indent=4, ensure_ascii=False)
            os.replace(temp_filepath, self.data_file)
            logger.debug(f"Saved currency data to {self.data_file}")
        except IOError as e:
            logger.error(f"Error saving currency data to {self.data_file}: {e}")

    def get_player_balance(self, player_id: str) -> int:
        """Get a player's current balance.
        
        Args:
            player_id: Player's unique identifier
            
        Returns:
            Current balance
        """
        return self.currency_data.get(str(player_id), 0)

    def set_player_balance(self, player_id: str, amount: int) -> None:
        """Set a player's balance to a specific amount (in memory only)."""
        self.currency_data[str(player_id)] = max(0, amount)
        # NO SAVE HERE

    def add_to_balance(self, player_id: str, amount: int) -> int:
        """Add currency to a player's balance (in memory only). Returns new balance."""
        player_id_str = str(player_id)
        current = self.get_player_balance(player_id_str)
        new_balance = max(0, current + amount)
        self.currency_data[player_id_str] = new_balance
        # NO SAVE HERE
        return new_balance

    def add_balance_and_save(self, player_id: str, amount: int) -> int:
        """Add currency to a player's balance and save immediately.
        
        Use this method for critical operations like purchases and sales
        where persistence is important.
        
        Args:
            player_id: Player's unique identifier
            amount: Amount to add (use negative for deductions)
            
        Returns:
            New balance after the operation
        """
        new_balance = self.add_to_balance(player_id, amount)
        self.save_currency_data()  # Save immediately
        return new_balance

    def deduct_from_balance(self, player_id: str, amount: int) -> bool:
        """Deduct currency from a player's balance (in memory only). Returns success."""
        player_id_str = str(player_id)
        if amount < 0: # Prevent adding money via deduction
             return False
        current = self.get_player_balance(player_id_str)
        if current >= amount:
            self.currency_data[player_id_str] = current - amount
            # NO SAVE HERE
            return True
        return False # Insufficient funds

    def has_sufficient_funds(self, player_id: str, amount: int) -> bool:
        """Check if a player has sufficient funds.
        
        Args:
            player_id: Player's unique identifier
            amount: Amount to check
            
        Returns:
            True if player has sufficient funds
        """
        return self.get_player_balance(str(player_id)) >= amount

    def transfer_funds(self, from_player: str, to_player: str, amount: int) -> bool:
        """Transfer currency between players (in memory only)."""
        if amount <=0:
            return False
        from_player_str = str(from_player)
        to_player_str = str(to_player)

        if self.has_sufficient_funds(from_player_str, amount):
            # Perform deductions and additions directly on the dict
            self.currency_data[from_player_str] = self.get_player_balance(from_player_str) - amount
            self.currency_data[to_player_str] = self.get_player_balance(to_player_str) + amount
            # NO SAVE HERE
            return True
        return False

# --- Cog for Managing the System and Tasks ---
class CurrencyCog(commands.Cog, name="Currency"): # Added Cog name
    """Cog to manage the CurrencySystem and its save loop."""

    def __init__(self, bot):
        self.bot = bot
        # Assuming data_dir is accessible via bot or config
        # Example: get from bot instance attribute or default to 'data'
        data_dir = getattr(bot, 'data_dir', 'data')
        # Instantiate the actual system
        self.currency_system = CurrencySystem(data_dir)
        # Start the save loop associated with this Cog instance
        self.save_loop.start()

    def cog_unload(self):
        """Called when the Cog is unloaded. Cancels the task and saves one last time."""
        self.save_loop.cancel()
        logger.info("Currency save loop cancelled. Performing final save...")
        # Perform final save
        self.currency_system.save_currency_data()

    @tasks.loop(minutes=5.0) # Save every 5 minutes
    async def save_loop(self):
        """Periodically saves the currency data."""
        logger.debug("Periodic currency save triggered.")
        try:
            # Run the synchronous save method in an executor to avoid blocking
            await asyncio.to_thread(self.currency_system.save_currency_data)
        except Exception as e:
            logger.error(f"Error during periodic currency save: {e}", exc_info=True)

    @save_loop.before_loop
    async def before_save_loop(self):
        """Wait until the bot is ready before starting the loop."""
        await self.bot.wait_until_ready()
        logger.info("Currency save loop starting.")

    # --- Add Accessor Method ---
    # This allows other Cogs to easily get the system instance
    def get_system(self) -> CurrencySystem:
        return self.currency_system

async def setup(bot):
    """Setup function to add the CurrencyCog to the bot."""
    await bot.add_cog(CurrencyCog(bot))
    logger.info("CurrencyCog added.")

# Example of how another Cog would access the system:
# currency_cog = bot.get_cog('Currency')
# if currency_cog:
#     currency_system = currency_cog.get_system()
#     balance = currency_system.get_player_balance(user_id)

# --- NEW: Async Ready Hook --- #
async def ready_hook(self):
    """Loads currency data asynchronously (though file I/O is sync)."""
    logger.info("CurrencySystem ready hook: Loading currency data...")
    self.load_currency_data() # Call the synchronous load method
    logger.info("CurrencySystem ready hook completed.")
# --- END NEW --- # 