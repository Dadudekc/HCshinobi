"""
Character System for loading, saving, and managing Character objects.
"""
import os
import json
import logging
import asyncio  # Import asyncio
from typing import Dict, Optional, List, Any, Tuple, Set, TYPE_CHECKING
import aiofiles # Import aiofiles
from dataclasses import asdict, is_dataclass
from datetime import datetime  # Add this missing import
from .character import Character
import aiofiles.os # Add this import if not already present near other aiofiles imports
# Import constants for subdir
from .constants import CHARACTERS_SUBDIR
from ..utils.file_io import load_json, save_json

# Import or define constants
# from .constants import MAX_JUTSU_LEVEL, MAX_JUTSU_GAUGE

# Add forward reference typing if needed
if TYPE_CHECKING:
    from .progression_engine import ShinobiProgressionEngine

logger = logging.getLogger(__name__)

class CharacterSystem:
    """Manages character data loading, saving, and retrieval."""

    def __init__(self, data_dir: str, progression_engine: Optional['ShinobiProgressionEngine'] = None):
        """
        Initializes the CharacterSystem.

        Args:
            data_dir: The *base* data directory for the bot.
            progression_engine: The ShinobiProgressionEngine instance (can be injected later).
        """
        # Construct the specific path for character data
        self.character_data_dir = os.path.join(data_dir, CHARACTERS_SUBDIR)
        # Ensure the directory exists (sync check okay at init)
        os.makedirs(self.character_data_dir, exist_ok=True)
        
        self.characters: Dict[str, Character] = {}
        self.progression_engine = progression_engine
        logger.info(f"CharacterSystem initialized. Character data directory: {self.character_data_dir}")
        # Note: Loading is now an async operation, called separately if needed on startup

    async def _load_character(self, user_id: str) -> Optional[Character]:
        """Asynchronously loads a single character file if it exists."""
        # Use the specific character data dir
        filepath = os.path.join(self.character_data_dir, f"{user_id}.json")
        logger.debug(f"Attempting to load character from: {filepath}")
        
        # Use async check
        if not await aiofiles.os.path.exists(filepath):
            logger.debug(f"Character file not found: {filepath}")
            return None

        try:
            logger.debug(f"Opening character file: {filepath}")
            async with aiofiles.open(filepath, mode='r', encoding='utf-8') as f:
                content = await f.read()
                logger.debug(f"Read content from {filepath}")
                data = json.loads(content) # Use json.loads for async string content
                logger.debug(f"Parsed JSON data for {user_id}")
                
                # Set character ID explicitly from user_id
                data['id'] = user_id
                
                # Create character using the safe from_dict method
                character = Character.from_dict(data)
                
                # We already ensured ID matches user_id by setting it above
                # No need for the check: if character.id != user_id:
                
                return character
                
        except Exception as e:
            logger.error(f"Error loading character from {filepath}: {e}", exc_info=True)
            return None

    async def load_characters(self) -> List[Character]:
        """Asynchronously loads all character JSON files from the data directory."""
        logger.info("Starting character loading process...")
        self.characters.clear()

        # Use the specific character data dir
        if not os.path.isdir(self.character_data_dir):
            logger.warning(f"Character directory not found: {self.character_data_dir}. Creating it.")
            try:
                os.makedirs(self.character_data_dir, exist_ok=True)
            except OSError as e:
                 logger.error(f"Failed to create character directory {self.character_data_dir}: {e}")
                 return [] 
            return [] 

        logger.info(f"Loading characters from: {self.character_data_dir}")
        tasks = []
        try:
            filenames = os.listdir(self.character_data_dir)
            logger.debug(f"Found {len(filenames)} files in character directory")
        except OSError as e:
            logger.error(f"Failed to list directory {self.character_data_dir}: {e}")
            return []

        for filename in filenames:
            if filename.lower().endswith('.json'):
                user_id = os.path.splitext(filename)[0]
                logger.debug(f"Creating load task for character: {user_id}")
                # Schedule the loading of each character file concurrently
                tasks.append(asyncio.create_task(self._load_character(user_id)))

        loaded_characters = []
        if tasks:
            logger.debug(f"Waiting for {len(tasks)} character load tasks to complete")
            results = await asyncio.gather(*tasks)
            logger.debug(f"All character load tasks completed")
            for character in results:
                if character:
                    # Add successfully loaded characters to the in-memory dictionary
                    self.characters[character.id] = character
                    loaded_characters.append(character)
                    logger.debug(f"Added character {character.id} to loaded characters")

        logger.info(f"Character loading complete. Loaded: {len(loaded_characters)} characters into memory.")
        return loaded_characters

    async def save_character(self, character: Character) -> bool:
        """Saves a character object to its JSON file asynchronously."""
        user_id = character.id
        filepath = os.path.join(self.character_data_dir, f"{user_id}.json")
        
        data_to_save = {}
        try:
            # Use asdict for serialization if Character is a dataclass
            if is_dataclass(character):
                data_to_save = asdict(character)
            else:
                # Fallback might be needed if not a dataclass
                logger.error(f"Character object (ID: {user_id}) is not a dataclass. Attempting basic __dict__ save.")
                data_to_save = character.__dict__.copy() 

            # Ensure complex types are JSON serializable
            data_to_save = self._serialize_character_data(data_to_save)

        except Exception as e:
            logger.error(f"Error preparing character data for saving (ID: {user_id}): {e}", exc_info=True)
            return False

        # Use save_json utility (assuming it handles async file I/O and atomicity)
        try:
            # Use use_async=True parameter if available, otherwise use it synchronously
            try:
                success = save_json(filepath, data_to_save, use_async=True)
            except TypeError:
                # If use_async parameter isn't supported, use it synchronously
                success = save_json(filepath, data_to_save)
                
            if success:
                # Update cache AFTER successful save
                self.characters[user_id] = character
                logger.debug(f"Character {user_id} saved successfully to {filepath} and cache updated.")
            else:
                # save_json itself should log errors
                logger.error(f"save_json utility reported failure saving character {user_id}.")
            return success
        except Exception as e:
            logger.error(f"Exception during save_character file operation for {user_id}: {e}", exc_info=True)
            return False

    def _serialize_character_data(self, data: Dict) -> Dict:
        """Helper to ensure character dictionary data is JSON serializable."""
        for key, value in data.items():
            if isinstance(value, set):
                data[key] = list(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            # Add other type conversions if needed (e.g., custom objects)
        return data
        
    async def get_character(self, user_id: str) -> Optional[Character]:
        """Get a character by user ID."""
        # First check if character is already loaded
        if user_id in self.characters:
            return self.characters[user_id]
            
        # If not loaded, try to load it
        character = await self._load_character(user_id)
        if character:
            self.characters[user_id] = character
        return character

    # Note: get_character_by_name remains synchronous, iterates over in-memory dict
    def get_character_by_name(self, name: str) -> Optional[Character]:
        """Retrieves a loaded character by name (case-insensitive)."""
        for character in self.characters.values():
            if character.name.lower() == name.lower():
                return character
        return None

    # Note: get_all_characters remains synchronous, returns list from memory
    def get_all_characters(self) -> List[Character]:
        """Returns a list of all loaded character objects."""
        return list(self.characters.values())

    async def create_character(
        self, user_id: str, name: str, clan: str, **kwargs: Any
    ) -> Optional[Character]:
        """
        Creates a new character, saves it, and adds it to the system.
        Returns None if a character with this user_id already exists.

        Args:
            user_id: The unique ID for the user.
            name: The name of the character.
            clan: The clan of the character.
            **kwargs: Additional attributes to initialize the character with.
                      Defaults will be used for attributes not provided.

        Returns:
            The created Character object, or None if creation failed (e.g., already exists).
        """
        # Check both memory and file system for existing character
        if await self.character_exists(user_id):
            logger.warning(f"Attempted to create character, but user_id '{user_id}' already exists.")
            return None

        try:
            # Create the character object
            character = Character(
                id=user_id,
                name=name,
                clan=clan,
                **kwargs
            )

            # Save to file system first
            if not await self.save_character(character):
                logger.error(f"Failed to save character {user_id} to file system")
                return None

            # Update memory cache
            self.characters[user_id] = character
            logger.info(f"Successfully created and saved character: {user_id}")
            return character

        except Exception as e:
            logger.error(f"Error creating character {user_id}: {e}", exc_info=True)
            return None

    async def add_jutsu(self, character_id: str, jutsu_name: str) -> Tuple[bool, List[str]]:
        """Adds a jutsu to a character's known list and initializes mastery.
        
        Returns:
            Tuple[bool, List[str]]: (Success status, List of progression messages)
        """
        character = await self.get_character(character_id)
        if not character:
            logger.warning(f"Attempted to add jutsu to non-existent character: {character_id}")
            return False, [] # Return empty list on failure
        
        progression_messages = [] # Initialize list for messages
        jutsu_added = False
        if jutsu_name not in character.jutsu:
            character.jutsu.append(jutsu_name)
            jutsu_added = True
            # Initialize mastery when jutsu is learned
            if jutsu_name not in character.jutsu_mastery:
                 character.jutsu_mastery[jutsu_name] = {"level": 1, "gauge": 0}
            
            # --- Check for Progression (Ensure engine is available) --- # 
            if self.progression_engine:
                # Call title check (returns messages)
                new_title_messages = await self.progression_engine.check_and_assign_titles(character)
                progression_messages.extend(new_title_messages)
                
                # Call achievement check (adds messages to list)
                await self.progression_engine.check_all_achievements(character, progression_messages)
                
                # Log combined messages if any
                if progression_messages:
                    logger.info(f"Progression updates for {character.id} after learning {jutsu_name}: {progression_messages}")
            else:
                logger.warning(f"ProgressionEngine not available in CharacterSystem when adding jutsu {jutsu_name} for {character.id}. Skipping progression checks.")
            # --- End Progression Check --- #

            await self.save_character(character)
            logger.info(f"Added jutsu '{jutsu_name}' to character {character_id}")
            return True, progression_messages # Return True and messages
        else:
            logger.info(f"Character {character_id} already knows jutsu '{jutsu_name}'")
            # Ensure mastery exists even if jutsu was known before mastery system
            mastery_added = False
            if jutsu_name not in character.jutsu_mastery:
                 character.jutsu_mastery[jutsu_name] = {"level": 1, "gauge": 0}
                 mastery_added = True
            if mastery_added:
                 await self.save_character(character) # Save only if mastery was added
            return False, [] # Return False and empty list (no new jutsu)

    async def increase_jutsu_mastery(self, character_id: str, jutsu_name: str, gain_amount: int) -> Optional[Tuple[int, int, bool]]:
        """
        Increases the mastery gauge for a specific jutsu and handles level ups.

        Args:
            character_id: The ID of the character.
            jutsu_name: The name of the jutsu being used.
            gain_amount: The amount of mastery gauge points to add.

        Returns:
            A tuple (new_level, new_gauge, leveled_up) if successful, None otherwise.
        """
        character = await self.get_character(character_id)
        if not character:
            logger.error(f"Character not found for mastery increase: {character_id}")
            return None
        
        if jutsu_name not in character.jutsu:
             logger.warning(f"Attempted to increase mastery for unlearned jutsu '{jutsu_name}' for character {character_id}")
             return None

        # Ensure mastery entry exists (should be handled by add_jutsu but double-check)
        if jutsu_name not in character.jutsu_mastery:
            character.jutsu_mastery[jutsu_name] = {"level": 1, "gauge": 0}
        
        mastery_data = character.jutsu_mastery[jutsu_name]
        current_level = mastery_data['level']
        current_gauge = mastery_data['gauge']
        leveled_up = False

        # If already max level, do nothing further
        if current_level >= MAX_JUTSU_LEVEL:
            mastery_data['gauge'] = MAX_JUTSU_GAUGE # Ensure gauge stays maxed
            # Save potentially updated gauge if it wasn't maxed before
            await self.save_character(character)
            return current_level, MAX_JUTSU_GAUGE, False

        # Increase gauge
        current_gauge += gain_amount

        # Handle level up
        while current_gauge >= MAX_JUTSU_GAUGE and current_level < MAX_JUTSU_LEVEL:
            current_level += 1
            current_gauge -= MAX_JUTSU_GAUGE
            leveled_up = True
            logger.info(f"Jutsu '{jutsu_name}' leveled up to {current_level} for character {character_id}")

        # If max level reached, cap the gauge
        if current_level >= MAX_JUTSU_LEVEL:
            current_level = MAX_JUTSU_LEVEL
            current_gauge = MAX_JUTSU_GAUGE

        # Update mastery data
        mastery_data['level'] = current_level
        mastery_data['gauge'] = current_gauge
        character.jutsu_mastery[jutsu_name] = mastery_data

        # Save character
        await self.save_character(character)

        return current_level, current_gauge, leveled_up

    async def migrate_jutsu_data(self, master_jutsu_names: Set[str]) -> int:
        """
        Iterates through all loaded characters and removes jutsu/mastery entries
        that are not present in the provided master list of valid names.
        This should be run ONCE after defining the new master jutsu list.

        Args:
            master_jutsu_names: A set of valid Jutsu names from the new master list.

        Returns:
            The number of characters modified.
        """
        logger.warning("--- Starting Jutsu Data Migration --- ")
        modified_character_count = 0
        total_jutsu_removed = 0
        characters_to_process = list(self.characters.values()) # Process loaded characters

        if not characters_to_process:
             logger.warning("No characters loaded in memory to migrate.")
             return 0
             
        if not master_jutsu_names:
            logger.error("Master Jutsu Name list is empty! Aborting migration to prevent data loss.")
            return 0

        logger.info(f"Migrating Jutsu data for {len(characters_to_process)} characters against {len(master_jutsu_names)} master jutsu names...")

        for character in characters_to_process:
            modified = False
            jutsu_to_remove = []
            mastery_to_remove = []

            # Check known Jutsu
            for known_jutsu in character.jutsu:
                if known_jutsu not in master_jutsu_names:
                    jutsu_to_remove.append(known_jutsu)
                    if known_jutsu in character.jutsu_mastery:
                        mastery_to_remove.append(known_jutsu)
                    modified = True
                    total_jutsu_removed += 1
                    logger.debug(f"Marked invalid jutsu '{known_jutsu}' for removal from character {character.id}")

            # Also check mastery dict for entries whose jutsu might have been removed previously
            for mastered_jutsu in list(character.jutsu_mastery.keys()): # Iterate over keys copy
                 if mastered_jutsu not in master_jutsu_names and mastered_jutsu not in mastery_to_remove:
                      mastery_to_remove.append(mastered_jutsu)
                      modified = True
                      logger.debug(f"Marked orphaned mastery entry '{mastered_jutsu}' for removal from character {character.id}")

            if modified:
                modified_character_count += 1
                logger.info(f"Character {character.id} ('{character.name}') requires migration. Removing {len(jutsu_to_remove)} jutsu entries and {len(mastery_to_remove)} mastery entries.")
                
                # Perform removal
                for j_name in jutsu_to_remove:
                    if j_name in character.jutsu:
                        character.jutsu.remove(j_name)
                for m_name in mastery_to_remove:
                    if m_name in character.jutsu_mastery:
                         del character.jutsu_mastery[m_name]
                
                # Save the modified character
                await self.save_character(character)
            else:
                 logger.debug(f"Character {character.id} ('{character.name}') requires no jutsu migration.")

        logger.warning(f"--- Jutsu Data Migration Complete --- Modified {modified_character_count} characters. Total invalid entries removed: {total_jutsu_removed}.")
        return modified_character_count

    async def update_character_stat(self, user_id: str, stat: str, amount: float) -> bool:
        """
        Update a specific stat for a character by the given amount.
        
        Args:
            user_id: The ID of the character to update
            stat: The name of the stat to update (e.g., 'strength', 'intelligence')
            amount: The amount to increase the stat by
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        logger.debug(f"Updating stat {stat} for character {user_id} by {amount}")
        
        character = await self.get_character(user_id)
        if not character:
            logger.warning(f"Cannot update stat: Character {user_id} not found")
            return False
            
        # Make sure the attribute exists on the character
        valid_attributes = [
            "ninjutsu", "taijutsu", "genjutsu", "intelligence", 
            "strength", "speed", "stamina", "chakra_control", 
            "perception", "willpower"
        ]
        
        if stat.lower() not in valid_attributes:
            logger.warning(f"Invalid attribute '{stat}' for character {user_id}")
            return False
            
        # Update the stat - make sure we're using the correct case from the dataclass
        for attr_name in valid_attributes:
            if stat.lower() == attr_name:
                current_value = getattr(character, attr_name, 0)
                new_value = current_value + amount
                setattr(character, attr_name, new_value)
                
                # Save the updated character
                save_success = await self.save_character(character)
                if save_success:
                    logger.info(f"Updated {attr_name} for {user_id} from {current_value} to {new_value}")
                    return True
                else:
                    logger.error(f"Failed to save character {user_id} after updating {attr_name}")
                    return False
                    
        # Should not reach here if implementation is correct
        return False

    async def shutdown(self):
        """Perform any cleanup needed for the CharacterSystem."""
        logger.info("CharacterSystem shutting down...")
        # Potentially save all modified characters if there's a risk of data loss
        # For now, saving happens on modification, so shutdown is simple
        pass

    async def delete_character(self, user_id: str) -> bool:
        """Delete a character from the system using user_id."""
        character_removed_from_cache = False
        try:
            # Remove from memory first
            if user_id in self.characters:
                del self.characters[user_id]
                character_removed_from_cache = True
                logger.debug(f"Removed character {user_id} from memory cache.")
            else:
                logger.debug(f"Character {user_id} not found in memory cache during deletion attempt.")
            
            # Construct the filepath using the specific dir and user_id
            filepath = os.path.join(self.character_data_dir, f"{user_id}.json")
            logger.debug(f"Attempting to delete character file: {filepath}")

            # Check if file exists asynchronously
            file_exists = await aiofiles.os.path.exists(filepath)
            
            if file_exists:
                # Remove file asynchronously
                await aiofiles.os.remove(filepath)
                logger.info(f"Successfully deleted character file for user {user_id} at {filepath}")
                # File existed and was removed - success
                return True
            else:
                logger.warning(f"Character file not found for deletion: {filepath}")
                # If removed from cache OR file never existed, consider it success
                return character_removed_from_cache 
                
        except Exception as e:
            logger.error(f"Error deleting character for user {user_id}: {e}", exc_info=True)
            return False 