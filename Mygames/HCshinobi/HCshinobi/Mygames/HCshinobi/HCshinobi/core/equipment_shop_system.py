"""
System for managing the Ninja Equipment Shop.
"""
import logging
import json
import os
from typing import Dict, Optional, List, Any, Tuple
from pathlib import Path

from .character_system import CharacterSystem
from .currency_system import CurrencySystem
from .character import Character
from ..utils.file_io import load_json, save_json

# Import constants
from .constants import (
    DATA_DIR, 
    SHOPS_SUBDIR, 
    EQUIPMENT_SHOP_FILE, 
    EQUIPMENT_SHOP_STATE_FILE,
    DEFAULT_SELL_MODIFIER
)

logger = logging.getLogger(__name__)
# DEFAULT_EQUIPMENT_FILE = "ninja_equipment_shop.json" # Now in constants
# DEFAULT_STATE_FILE = "equipment_shop_state.json" # Now in constants

# Use constants for paths
EQUIPMENT_DATA_PATH = Path(DATA_DIR) / SHOPS_SUBDIR / EQUIPMENT_SHOP_FILE
EQUIPMENT_STATE_PATH = Path(DATA_DIR) / SHOPS_SUBDIR / EQUIPMENT_SHOP_STATE_FILE

class EquipmentShopSystem:
    """Manages loading, displaying, buying, and selling of equipment."""

    def __init__(self, data_dir: str, character_system: CharacterSystem, currency_system: CurrencySystem, equipment_shop_channel_id: Optional[int] = None):
        # Store base data dir
        self.base_data_dir = data_dir
        # Construct specific path for shop files
        self.shop_data_dir = os.path.join(data_dir, SHOPS_SUBDIR)
        os.makedirs(self.shop_data_dir, exist_ok=True)
        
        self.character_system = character_system
        self.currency_system = currency_system
        self.equipment_data: Dict[str, Dict] = {}
        
        # Use specific dir and constants for file paths
        self.equipment_file_path = os.path.join(self.shop_data_dir, EQUIPMENT_SHOP_FILE)
        self.state_file_path = os.path.join(self.shop_data_dir, EQUIPMENT_SHOP_STATE_FILE)
        
        # State attributes
        self.equipment_shop_channel_id: Optional[int] = equipment_shop_channel_id
        self.equipment_shop_message_id: Optional[int] = None
        
        # Defer loading to ready_hook
        # self._load_equipment_data()
        # self._load_shop_state()
        logger.info("EquipmentShopSystem initialized. Loading deferred.")

    async def _load_equipment_data(self):
        """Loads equipment data from the JSON file asynchronously."""
        try:
            # Corrected: Call load_json synchronously
            loaded_data = load_json(self.equipment_file_path)
            if loaded_data is None:
                logger.warning(f"Equipment shop file not found or invalid: {self.equipment_file_path}. Using empty data.")
                self.equipment_data = {}
                # Optionally create empty file if needed
                # save_json(self.equipment_file_path, {}) # Assuming sync save_json
            elif not isinstance(loaded_data, dict):
                logger.warning(f"Invalid equipment data format in {self.equipment_file_path}, expected dict. Resetting.")
                self.equipment_data = {}
            else:
                 self.equipment_data = loaded_data
            logger.info(f"Loaded {len(self.equipment_data)} equipment items from {self.equipment_file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.equipment_file_path}: {e}. Using empty data.")
            self.equipment_data = {}
        except Exception as e:
            logger.exception(f"An unexpected error occurred loading {self.equipment_file_path}: {e}")
            self.equipment_data = {}

    async def _load_shop_state(self):
        """Loads the shop state (message ID) asynchronously."""
        try:
            # Corrected: Call load_json synchronously
            state_data = load_json(self.state_file_path)
            if state_data is None:
                logger.info(f"Equipment shop state file not found or invalid: {self.state_file_path}. Will create on save.")
                state_data = {}
            elif not isinstance(state_data, dict):
                logger.warning(f"Invalid shop state format in {self.state_file_path}, expected dict. Resetting.")
                state_data = {}

            self.equipment_shop_message_id = state_data.get('equipment_shop_message_id')
            # Ensure channel ID from init takes precedence unless missing
            self.equipment_shop_channel_id = self.equipment_shop_channel_id or state_data.get('equipment_shop_channel_id')
            logger.info(f"Loaded equipment shop state: Channel={self.equipment_shop_channel_id}, Message={self.equipment_shop_message_id}")
        except FileNotFoundError:
            logger.info(f"Equipment shop state file not found: {self.state_file_path}. Will create on save.")
        except Exception as e:
            logger.error(f"Error loading equipment shop state from {self.state_file_path}: {e}")

    async def _save_shop_state(self):
        """Saves the current shop state (message ID)."""
        state_data = {"equipment_shop_message_id": self.equipment_shop_message_id}
        try:
            # Use save_json
            success = save_json(self.state_file_path, state_data)
            if success:
                logger.info(f"Equipment shop state saved successfully to {self.state_file_path}")
            else:
                logger.error(f"Failed to save equipment shop state to {self.state_file_path}")
        except Exception as e:
            logger.error(f"Error saving shop state to {self.state_file_path}: {e}", exc_info=True)
            
    async def set_shop_message_id(self, message_id: Optional[int]):
        """Updates the message ID and saves the state asynchronously."""
        if self.equipment_shop_message_id != message_id:
             self.equipment_shop_message_id = message_id
             await self._save_shop_state() # Await async save

    def get_shop_inventory(self) -> Dict[str, Dict]:
        """Returns the currently loaded equipment data for display."""
        # Maybe add filtering/sorting later
        return self.equipment_data

    async def ready_hook(self):
        """Hook called when bot is ready. Loads equipment and state data."""
        await self._load_equipment_data()
        await self._load_shop_state()
        logger.info("EquipmentShopSystem ready. Data loaded.")

    async def buy_equipment(self, character_id: str, item_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Handles the logic for a character buying a piece of equipment."""
        character = await self.character_system.get_character(character_id)
        if not character:
            return False, "Character not found.", None

        item_id_lower = item_id.lower()
        item_data = self.equipment_data.get(item_id_lower)

        if not item_data:
            return False, f"Equipment with ID '{item_id}' not found in the shop.", None

        item_name = item_data.get('name', item_id_lower)
        cost = item_data.get('price')

        if not isinstance(cost, int) or cost <= 0:
            logger.error(f"Invalid price defined for equipment {item_id_lower}: {cost}")
            return False, f"'{item_name}' cannot be purchased due to an invalid price.", None

        # Check affordability
        if not self.currency_system.has_sufficient_funds(character_id, cost):
            balance = self.currency_system.get_player_balance(character_id)
            return False, f"Insufficient Ryō. Cost: {cost:,}, Your Balance: {balance:,}.", None

        # Add item to inventory (ensure inventory exists)
        if not hasattr(character, 'inventory') or character.inventory is None:
            character.inventory = []
            
        # Maybe check for duplicates if equipment isn't stackable?
        character.inventory.append(item_id_lower) # Add item ID

        # Deduct cost - Try add_balance_and_save first, then fall back to add_balance
        deducted = False
        if hasattr(self.currency_system, 'add_balance_and_save'):
            # Use the new atomic method that saves immediately
            deducted = self.currency_system.add_balance_and_save(character_id, -cost)
        else:
            # Fall back to old method + manual save if needed
            try:
                # Old style may be synchronous or asynchronous
                potential_coroutine = self.currency_system.add_balance(character_id, -cost)
                if hasattr(potential_coroutine, '__await__'): 
                    deducted = await potential_coroutine
                else:
                    deducted = potential_coroutine
                
                # Manually save after old-style add_balance
                if hasattr(self.currency_system, 'save_currency_data'):
                    if hasattr(self.currency_system.save_currency_data, '__await__'):
                        await self.currency_system.save_currency_data()
                    else:
                        self.currency_system.save_currency_data()
            except AttributeError as e:
                logger.error(f"Currency system missing required methods: {e}")
                deducted = False

        if not deducted:
             # This suggests an issue with add_balance or concurrent modification, rollback inventory
             try: character.inventory.remove(item_id_lower) 
             except ValueError: pass 
             logger.error(f"Failed to deduct currency for {item_id_lower} purchase by {character_id}.")
             return False, "Transaction failed: Could not deduct currency.", None

        # Save character
        saved = await self.character_system.save_character(character)
        if not saved:
            # Rollback currency and inventory
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(character_id, cost)
            else:
                try:
                    # Try old method
                    potential_coroutine = self.currency_system.add_balance(character_id, cost)
                    if hasattr(potential_coroutine, '__await__'):
                        await potential_coroutine
                    else:
                        potential_coroutine
                    # Save after rollback
                    if hasattr(self.currency_system, 'save_currency_data'):
                        if hasattr(self.currency_system.save_currency_data, '__await__'):
                            await self.currency_system.save_currency_data()
                        else:
                            self.currency_system.save_currency_data()
                except:
                    logger.error("Failed to rollback currency during failed character save.")
            
            try: character.inventory.remove(item_id_lower)
            except ValueError: pass
            logger.error(f"Failed to save character {character_id} after buying {item_id_lower}.")
            return False, "Transaction failed: Could not save character data after purchase.", None

        logger.info(f"Character {character_id} purchased equipment '{item_name}' ({item_id_lower}) for {cost} Ryō.")
        return True, f"Successfully purchased **{item_name}** for {cost:,} Ryō!", item_data

    async def sell_equipment(self, character_id: str, item_id: str) -> Tuple[bool, str]:
        """Handles the logic for a character selling a piece of equipment."""
        character = await self.character_system.get_character(character_id)
        if not character:
            return False, "Character not found."

        item_id_lower = item_id.lower()
        
        # Ensure inventory exists and remove item
        if not hasattr(character, 'inventory') or character.inventory is None or item_id_lower not in character.inventory:
             return False, f"Item with ID '{item_id_lower}' not found in your inventory."
        
        try:
            character.inventory.remove(item_id_lower)
        except ValueError: 
             # Should be caught by the check above, but handle defensively
             return False, f"Failed to remove item '{item_id_lower}' from inventory."

        # Get item data to determine sell price
        item_data = self.equipment_data.get(item_id_lower)
        if not item_data or not isinstance(item_data.get('price'), int) or item_data['price'] <= 0:
            # Item was in inventory but has no valid shop data? 
            # Give minimal value or prevent sale?
            # For now, give 0 Ryo and log warning.
            sell_price = 0 
            item_name = item_id_lower
            logger.warning(f"Character {character_id} sold item '{item_id_lower}' which has invalid/missing shop data. Awarding 0 Ryō.")
        else:
            item_name = item_data.get('name', item_id_lower)
            sell_price = int(item_data['price'] * DEFAULT_SELL_MODIFIER)

        # Add currency - Try add_balance_and_save first, then fall back to add_balance
        added = False
        if hasattr(self.currency_system, 'add_balance_and_save'):
            # Use the new atomic method that saves immediately
            added = self.currency_system.add_balance_and_save(character_id, sell_price)
        else:
            # Fall back to old method + manual save if needed
            try:
                # Old style may be synchronous or asynchronous
                potential_coroutine = self.currency_system.add_balance(character_id, sell_price)
                if hasattr(potential_coroutine, '__await__'):
                    added = await potential_coroutine
                else:
                    added = potential_coroutine
                
                # Manually save after old-style add_balance
                if hasattr(self.currency_system, 'save_currency_data'):
                    if hasattr(self.currency_system.save_currency_data, '__await__'):
                        await self.currency_system.save_currency_data()
                    else:
                        self.currency_system.save_currency_data()
            except AttributeError as e:
                logger.error(f"Currency system missing required methods: {e}")
                added = False

        if not added:
             # Rollback inventory removal
             character.inventory.append(item_id_lower)
             logger.error(f"Failed to add currency for {item_id_lower} sale by {character_id}.")
             return False, "Transaction failed: Could not add currency."

        # Save character
        saved = await self.character_system.save_character(character)
        if not saved:
            # Rollback currency and inventory
            if hasattr(self.currency_system, 'add_balance_and_save'):
                self.currency_system.add_balance_and_save(character_id, -sell_price)
            else:
                try:
                    # Try old method
                    potential_coroutine = self.currency_system.add_balance(character_id, -sell_price)
                    if hasattr(potential_coroutine, '__await__'):
                        await potential_coroutine
                    else:
                        potential_coroutine
                    # Save after rollback
                    if hasattr(self.currency_system, 'save_currency_data'):
                        if hasattr(self.currency_system.save_currency_data, '__await__'):
                            await self.currency_system.save_currency_data()
                        else:
                            self.currency_system.save_currency_data()
                except:
                    logger.error("Failed to rollback currency during failed character save.")
            
            character.inventory.append(item_id_lower)
            logger.error(f"Failed to save character {character_id} after selling {item_id_lower}.")
            return False, "Transaction failed: Could not save character data after sale."

        logger.info(f"Character {character_id} sold equipment '{item_name}' ({item_id_lower}) for {sell_price} Ryō.")
        return True, f"Successfully sold **{item_name}** for {sell_price:,} Ryō!" 