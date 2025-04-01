"""
Manages character data loaded from JSON files.
"""
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CharacterManager:
    """Handles loading and accessing character data from JSON files."""

    def __init__(self, data_dir: str):
        """
        Initializes the CharacterManager.

        Args:
            data_dir: The root directory where application data is stored.
                      Expected to contain a 'characters' subdirectory.
        """
        self.character_dir = os.path.join(data_dir, 'characters')
        self.characters: Dict[str, Dict[str, Any]] = {}
        self._load_characters()

    def _load_characters(self):
        """Loads all character JSON files from the character directory."""
        if not os.path.isdir(self.character_dir):
            logger.warning(f"Character directory not found: {self.character_dir}. No characters loaded.")
            return

        logger.info(f"Loading characters from: {self.character_dir}")
        loaded_count = 0
        skipped_count = 0
        for filename in os.listdir(self.character_dir):
            if filename.lower().endswith('.json') and filename.lower() != 'template.json':
                file_path = os.path.join(self.character_dir, filename)
                character_name = os.path.splitext(filename)[0] # Use filename without extension as key
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Basic validation (optional but recommended)
                        if isinstance(data, dict): # Check if it's a dictionary
                            self.characters[character_name] = data
                            loaded_count += 1
                            logger.debug(f"Loaded character '{character_name}' from {filename}")
                        else:
                            logger.warning(f"Skipping non-dictionary JSON file: {filename}")
                            skipped_count += 1
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from file: {filename}")
                    skipped_count += 1
                except Exception as e:
                    logger.error(f"Error loading character file {filename}: {e}")
                    skipped_count += 1
            elif filename.lower() == 'template.json':
                 logger.debug(f"Skipping template file: {filename}")
                 skipped_count +=1

        logger.info(f"Character loading complete. Loaded: {loaded_count}, Skipped/Errors: {skipped_count}")

    def get_character(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves data for a specific character by name (filename without extension).

        Args:
            name: The name of the character (case-sensitive, matches filename).

        Returns:
            A dictionary containing the character's data, or None if not found.
        """
        return self.characters.get(name)

    def get_all_characters(self) -> Dict[str, Dict[str, Any]]:
        """Returns a dictionary of all loaded characters."""
        return self.characters

    def save_character(self, name: str, data: Dict[str, Any]) -> None:
        """
        Saves character data to a JSON file.

        Args:
            name: The name of the character (will be used as filename).
            data: The character data to save.

        Raises:
            Exception: If there's an error saving the file.
        """
        # Ensure the character directory exists
        os.makedirs(self.character_dir, exist_ok=True)
        
        # Create filename (lowercase, spaces replaced with underscores)
        filename = f"{name.lower().replace(' ', '_')}.json"
        filepath = os.path.join(self.character_dir, filename)
        
        try:
            # Save to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            # Update in-memory cache
            self.characters[name] = data
            
            logger.info(f"Successfully saved character '{name}' to {filepath}")
        except Exception as e:
            logger.error(f"Error saving character '{name}': {e}")
            raise

    def reload_characters(self):
        """Clears existing character data and reloads from files."""
        logger.info("Reloading character data...")
        self.characters.clear()
        self._load_characters()

# Example usage (if run directly, for testing)
if __name__ == '__main__':
    # Configure basic logging for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Assume 'data' directory exists in the same directory as this script for testing
    test_data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data') # Points to project root/data
    print(f"Attempting to load from: {test_data_dir}")

    # Create dummy data dir and files if they don't exist
    dummy_char_dir = os.path.join(test_data_dir, 'characters')
    if not os.path.exists(dummy_char_dir):
        os.makedirs(dummy_char_dir)
        print(f"Created dummy directory: {dummy_char_dir}")
        # Create dummy files
        with open(os.path.join(dummy_char_dir, 'TestChar1.json'), 'w') as f:
            json.dump({"name": "Test One", "level": 5}, f)
        with open(os.path.join(dummy_char_dir, 'TestChar2.json'), 'w') as f:
            json.dump({"name": "Test Two", "class": "Warrior"}, f)
        with open(os.path.join(dummy_char_dir, 'template.json'), 'w') as f:
            json.dump({"template": True}, f)
        with open(os.path.join(dummy_char_dir, 'invalid.txt'), 'w') as f:
            f.write("not json")
        print("Created dummy character files for testing.")


    manager = CharacterManager(data_dir=test_data_dir)
    print("\nLoaded characters:")
    all_chars = manager.get_all_characters()
    if all_chars:
        for name, data in all_chars.items():
            print(f"  {name}: {data}")
    else:
        print("  No characters loaded.")

    print("\nGetting TestChar1:")
    char1 = manager.get_character('TestChar1')
    print(f"  {char1}")

    print("\nGetting NonExistentChar:")
    char_none = manager.get_character('NonExistentChar')
    print(f"  {char_none}")

    print("\nReloading characters...")
    manager.reload_characters()
    print("Reload complete.")
    print(f"  Characters after reload: {len(manager.get_all_characters())}") 