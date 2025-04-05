import logging
import json
from pathlib import Path
from typing import Dict, Optional, Any
from ..core.constants import DATA_DIR, JUTSU_SUBDIR, MASTER_JUTSU_FILE # Import constants

# Use constants to build the path
JUTSU_DATA_PATH = Path(DATA_DIR) / JUTSU_SUBDIR / MASTER_JUTSU_FILE 

logger = logging.getLogger(__name__)

class JutsuSystem:
    """Manages the registry and details of all available jutsu."""

    def __init__(self):
        """Initializes the JutsuSystem, loading jutsu data."""
        self.jutsu: Dict[str, Dict[str, Any]] = self._load_jutsu()
        logger.info(f"Loaded {len(self.jutsu)} jutsu into the system.")

    def _load_jutsu(self) -> Dict[str, Dict[str, Any]]:
        """Loads jutsu data from a JSON file."""
        try:
            # Ensure the directory exists if needed
            # JUTSU_DATA_PATH.parent.mkdir(parents=True, exist_ok=True) 
            if not JUTSU_DATA_PATH.exists():
                 logger.warning(f"Jutsu data file not found at {JUTSU_DATA_PATH}. No jutsu loaded.")
                 # Create an empty file? Or handle this case differently?
                 # with open(JUTSU_DATA_PATH, 'w', encoding='utf-8') as f:
                 #     json.dump({}, f)
                 return {}
                 
            with open(JUTSU_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle dictionary format (keys are jutsu IDs)
                if isinstance(data, dict):
                    # Convert keys to lowercase for consistent lookup
                    return {k.lower(): v for k, v in data.items()} 
                # Handle list format (each item is a jutsu with 'id' field)
                elif isinstance(data, list):
                    jutsu_dict = {}
                    processed_count = 0
                    for jutsu in data:
                        if isinstance(jutsu, dict) and 'id' in jutsu:
                            jutsu_id = jutsu['id'].lower()  # Use the id field as the key
                            jutsu_dict[jutsu_id] = jutsu
                            processed_count += 1
                        else:
                            logger.warning(f"Skipping invalid jutsu object in {JUTSU_DATA_PATH}, missing 'id' field")
                    logger.info(f"Processed {processed_count} jutsu from list format in {JUTSU_DATA_PATH}")
                    return jutsu_dict
                else:
                    logger.error(f"Invalid format in {JUTSU_DATA_PATH}. Expected a dictionary or list of jutsu objects.")
                    return {}
        except json.JSONDecodeError:
            logger.exception(f"Error decoding JSON from {JUTSU_DATA_PATH}.")
            return {}
        except Exception:
            logger.exception(f"Failed to load jutsu data from {JUTSU_DATA_PATH}.")
            return {}

    def get_jutsu(self, jutsu_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves jutsu details by its ID (case-insensitive)."""
        return self.jutsu.get(jutsu_id.lower())

    def get_all_jutsu(self) -> Dict[str, Dict[str, Any]]:
        """Returns all loaded jutsu."""
        return self.jutsu

# Example usage (optional, for testing)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     jutsu_sys = JutsuSystem()
#     print("Loaded jutsu:", jutsu_sys.get_all_jutsu())
#     test_jutsu = jutsu_sys.get_jutsu("fireball_jutsu") # Replace with an actual jutsu ID if known
#     if test_jutsu:
#         print("\nFound test jutsu:", test_jutsu)
#     else:
#         print("\nTest jutsu not found.") 