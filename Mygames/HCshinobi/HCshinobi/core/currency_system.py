"""Currency system for managing in-game currency."""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Union, Any

logger = logging.getLogger(__name__)

class CurrencySystem:
    """Manages in-game currency for players."""
    
    def __init__(self, data_file: str = "data/currency.json"):
        """Initialize the currency system.
        
        Args:
            data_file: Path to currency data file
        """
        self.data_file = data_file
        self.currency_data: Dict[str, int] = {}
        self.load_currency_data()
    
    def load_currency_data(self) -> None:
        """Load currency data from file."""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.currency_data = json.load(f)
                logger.info(f"Loaded currency data from {self.data_file}")
            else:
                logger.info(f"No currency data file found at {self.data_file}, creating new")
                self.save_currency_data()
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading currency data: {e}")
            self.currency_data = {}
    
    def save_currency_data(self) -> None:
        """Save currency data to file."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, 'w') as f:
                json.dump(self.currency_data, f, indent=4)
            logger.info(f"Saved currency data to {self.data_file}")
        except IOError as e:
            logger.error(f"Error saving currency data: {e}")
    
    def get_player_balance(self, player_id: str) -> int:
        """Get a player's current balance.
        
        Args:
            player_id: Player's unique identifier
            
        Returns:
            Current balance
        """
        return self.currency_data.get(player_id, 0)
    
    def set_player_balance(self, player_id: str, amount: int) -> None:
        """Set a player's balance to a specific amount.
        
        Args:
            player_id: Player's unique identifier
            amount: New balance amount
        """
        self.currency_data[player_id] = max(0, amount)
        self.save_currency_data()
    
    def add_to_balance(self, player_id: str, amount: int) -> int:
        """Add currency to a player's balance.
        
        Args:
            player_id: Player's unique identifier
            amount: Amount to add
            
        Returns:
            New balance
        """
        current = self.get_player_balance(player_id)
        new_balance = current + amount
        self.set_player_balance(player_id, new_balance)
        return new_balance
    
    def deduct_from_balance(self, player_id: str, amount: int) -> bool:
        """Deduct currency from a player's balance.
        
        Args:
            player_id: Player's unique identifier
            amount: Amount to deduct
            
        Returns:
            True if deduction successful, False if insufficient funds
        """
        current = self.get_player_balance(player_id)
        if current >= amount:
            self.set_player_balance(player_id, current - amount)
            return True
        self.set_player_balance(player_id, 0)  # Set to 0 if insufficient funds
        return False
    
    def has_sufficient_funds(self, player_id: str, amount: int) -> bool:
        """Check if a player has sufficient funds.
        
        Args:
            player_id: Player's unique identifier
            amount: Amount to check
            
        Returns:
            True if player has sufficient funds
        """
        return self.get_player_balance(player_id) >= amount
    
    def transfer_funds(self, from_player: str, to_player: str, amount: int) -> bool:
        """Transfer currency between players.
        
        Args:
            from_player: Source player's ID
            to_player: Target player's ID
            amount: Amount to transfer
            
        Returns:
            True if transfer successful
        """
        if self.deduct_from_balance(from_player, amount):
            self.add_to_balance(to_player, amount)
            return True
        return False 