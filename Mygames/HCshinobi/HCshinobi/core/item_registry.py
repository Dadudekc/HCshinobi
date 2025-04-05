import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any
from ..core.constants import DATA_DIR, SHOPS_SUBDIR, SHOP_ITEMS_FILE # Import constants

# Use constants to build the path
# Note: This directory/file might not exist yet based on logs
ITEM_DATA_PATH = Path(DATA_DIR) / SHOPS_SUBDIR / SHOP_ITEMS_FILE

logger = logging.getLogger(__name__)

class ItemRegistry:
    """Manages the registry of all available items in the game."""

    def __init__(self):
        """Initializes the ItemRegistry, loading item data."""
        self.items: Dict[str, Dict[str, Any]] = self._load_items()
        logger.info(f"Loaded {len(self.items)} items into the registry.")

    def _load_items(self) -> Dict[str, Dict[str, Any]]:
        """Loads item data from a JSON file."""
        try:
            # Ensure the directory exists if needed
            # ITEM_DATA_PATH.parent.mkdir(parents=True, exist_ok=True) 
            if not ITEM_DATA_PATH.exists():
                 logger.warning(f"Item data file not found at {ITEM_DATA_PATH}. No items loaded.")
                 # Create an empty file? Or handle this case differently?
                 # with open(ITEM_DATA_PATH, 'w', encoding='utf-8') as f:
                 #     json.dump({}, f)
                 return {}
                 
            with open(ITEM_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Assuming the JSON structure is a dictionary where keys are item IDs
                if isinstance(data, dict):
                    # Convert keys to lowercase for consistent lookup?
                    return {k.lower(): v for k, v in data.items()} 
                else:
                    logger.error(f"Invalid format in {ITEM_DATA_PATH}. Expected a dictionary.")
                    return {}
        except json.JSONDecodeError:
            logger.exception(f"Error decoding JSON from {ITEM_DATA_PATH}.")
            return {}
        except Exception:
            logger.exception(f"Failed to load item data from {ITEM_DATA_PATH}.")
            return {}

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves item details by its ID (case-insensitive)."""
        return self.items.get(item_id.lower())

    def get_all_items(self) -> Dict[str, Dict[str, Any]]:
        """Returns all loaded items."""
        return self.items

# Example usage (optional, for testing)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     registry = ItemRegistry()
#     print("Loaded items:", registry.get_all_items())
#     test_item = registry.get_item("basic_kunai") # Replace with an actual item ID if known
#     if test_item:
#         print("\nFound test item:", test_item)
#     else:
#         print("\nTest item not found.") 