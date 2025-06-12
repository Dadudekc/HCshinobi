#!/usr/bin/env python
"""
Item Manager for loading and accessing item definitions.
"""

import os
import json
import logging
from typing import Dict, Optional, Any

from .constants import DATA_DIR, SHOPS_SUBDIR, SHOP_ITEMS_FILE, EQUIPMENT_SHOP_FILE
from ..utils.file_io import load_json

logger = logging.getLogger(__name__)

class ItemManager:
    """Loads and provides access to all item definitions."""

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initializes the ItemManager.

        Args:
            data_dir: The base data directory. Defaults to DATA_DIR constant.
        """
        self.base_data_dir = data_dir or DATA_DIR
        self.shops_dir = os.path.join(self.base_data_dir, SHOPS_SUBDIR)
        self.item_definitions: Dict[str, Dict[str, Any]] = {}
        logger.info("ItemManager initialized.")
        # Loading happens in async ready_hook

    async def ready_hook(self):
        """Loads item definition files asynchronously."""
        logger.info("ItemManager ready hook: Loading item definitions...")
        self.item_definitions.clear()
        
        # Define files to load - using constants
        # Note: general_items.json is likely unused/empty, but check anyway
        files_to_load = {
            "general": SHOP_ITEMS_FILE, # general_items.json
            "equipment": EQUIPMENT_SHOP_FILE # equipment_shop.json
        }
        
        loaded_count = 0
        for key, filename in files_to_load.items():
            filepath = os.path.join(self.shops_dir, filename)
            try:
                # Use load_json utility (assuming it handles async loading if needed, 
                # or sync loading is acceptable at startup)
                data = load_json(filepath) # Assuming sync load is okay here
                if isinstance(data, dict):
                    # Merge definitions, potentially overwriting general with equipment if IDs clash
                    self.item_definitions.update(data) 
                    logger.info(f"Loaded {len(data)} items from {filename}.")
                    loaded_count += len(data)
                else:
                    logger.warning(f"Data in {filename} is not a dictionary. Skipping.")
            except FileNotFoundError:
                logger.warning(f"Item definition file not found: {filepath}. Skipping.")
            except Exception as e:
                logger.error(f"Error loading item definitions from {filepath}: {e}", exc_info=True)

        logger.info(f"ItemManager loaded a total of {len(self.item_definitions)} item definitions.")

    def get_item_definition(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the definition for a specific item ID (case-insensitive).

        Args:
            item_id: The unique ID of the item (e.g., 'kunai', 'basic_healing_salve').

        Returns:
            A dictionary containing the item's definition, or None if not found.
        """
        return self.item_definitions.get(item_id.lower())

    def get_all_item_definitions(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns the entire dictionary of loaded item definitions.
        """
        return self.item_definitions 