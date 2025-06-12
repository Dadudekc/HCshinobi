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
from datetime import datetime, timezone  # Add this missing import
from .character import Character
import aiofiles.os # Add this import if not already present near other aiofiles imports
# Import constants for subdir
from .constants import CHARACTERS_SUBDIR, CLANS_SUBDIR
from ..utils.file_io import load_json, save_json, async_save_json
from HCshinobi.core.clan_data import ClanData # Import ClanData

# Import or define constants
# from .constants import MAX_JUTSU_LEVEL, MAX_JUTSU_GAUGE

# Add forward reference typing if needed
if TYPE_CHECKING:
    from .progression_engine import ShinobiProgressionEngine

logger = logging.getLogger(__name__)

class CharacterSystem:
    """Manages character data loading, saving, and retrieval."""

    def __init__(self, 
                 data_dir: str, 
                 clan_data_service: ClanData, # Add ClanData service dependency
                 progression_engine: Optional['ShinobiProgressionEngine'] = None):
        """
        Initializes the CharacterSystem.

        Args:
            data_dir: The *base* data directory for the bot.
            clan_data_service: The initialized ClanData service instance.
            progression_engine: The ShinobiProgressionEngine instance (can be injected later).
        """
        # Construct the specific path for character data
        self.character_data_dir = os.path.join(data_dir, CHARACTERS_SUBDIR)
        # Ensure the directory exists (sync check okay at init)
        os.makedirs(self.character_data_dir, exist_ok=True)
        # self.clans_data_dir = os.path.join(data_dir, CLANS_SUBDIR) # No longer needed here
        
        self.characters: Dict[str, Character] = {}
        self.progression_engine = progression_engine
        # Store the injected ClanData service instance
        self.clan_data_service = clan_data_service 
        # self.clan_data: Dict[str, Dict[str, Any]] = self._load_clan_data() # Remove direct loading
        
        logger.info(f"CharacterSystem initialized. Character data directory: {self.character_data_dir}")
        # logger.info(f"Loaded {len(self.clan_data)} clans from {self.clans_data_dir}.") # Remove this log
        # Note: Loading is now an async operation, called separately if needed on startup
        logger.warning(f">>> [Service Init] CharacterSystem initialized. Instance ID: {id(self)}") # Added Log

    async def ready_hook(self):
        """Called after bot setup is complete. Can load initial data."""
        # Load existing characters? Optional, depends on desired behavior.
        # Example: await self.load_all_characters() 
        logger.info("CharacterSystem ready_hook complete.")
        # We rely on the injected clan_data_service already being loaded

    def _load_clan_data(self) -> Dict[str, Dict[str, Any]]:
        """Loads clan data from JSON files in the clans subdirectory."""
        all_clans = {}
        logger.info(f"Loading clan data from: {self.clans_data_dir}")
        if not os.path.isdir(self.clans_data_dir):
            logger.error(f"Clans directory not found: {self.clans_data_dir}")
            return {}

        try:
            for filename in os.listdir(self.clans_data_dir):
                # Skip non-JSON files or specific files like clan_tiers
                if not filename.lower().endswith('.json') or filename.lower() == 'clan_tiers.json':
                    continue
                
                filepath = os.path.join(self.clans_data_dir, filename)
                try:
                    # Use the synchronous load_json utility here as it's part of initialization
                    data = load_json(filepath)
                    # The structure seems to be {"Village Clans": [list of clans]}
                    # We need to extract the list based on the key
                    clans_list = None
                    if isinstance(data, dict) and len(data) == 1:
                        clans_list = list(data.values())[0]
                        
                    if isinstance(clans_list, list):
                        for clan_info in clans_list:
                            if isinstance(clan_info, dict) and 'name' in clan_info:
                                clan_name = clan_info['name']
                                if clan_name in all_clans:
                                     logger.warning(f"Duplicate clan name found: {clan_name} in {filename}. Overwriting.")
                                all_clans[clan_name] = clan_info
                            else:
                                logger.warning(f"Invalid clan entry structure found in {filename}: {clan_info}")
                    else:
                         logger.warning(f"Unexpected data structure in clan file {filename}. Expected dict with one key mapping to a list.")
                         
                except Exception as e:
                    logger.error(f"Error loading clan data from {filepath}: {e}", exc_info=True)
        except OSError as e:
            logger.error(f"Error listing files in clans directory {self.clans_data_dir}: {e}")

        return all_clans

    async def _load_character(self, user_id: str) -> Optional[Character]:
        logger.warning(f">>> [Service Load] _load_character called for {user_id}. Instance ID: {id(self)}") # Added Log
        """Asynchronously loads a single character file if it exists."""
        # Use the specific character data dir
        filepath = os.path.join(self.character_data_dir, f"{user_id}.json")
        print(f"DEBUG [CharacterSystem._load_character]: Checking path: {filepath}") # DEBUG
        
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
                print(f"DEBUG [CharacterSystem._load_character]: Loaded and parsed data for {user_id}") # DEBUG
                
                # Set character ID explicitly from user_id (convert numeric IDs to int)
                data['id'] = int(user_id) if user_id.isdigit() else user_id
                
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
        logger.warning(f">>> [Service Save] save_character called for {character.id}. Instance ID: {id(self)}") # Added Log
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

        # Save character data synchronously using save_json for compatibility with tests
        try:
            success = save_json(filepath, data_to_save)
            if success:
                self.characters[user_id] = character
                logger.debug(f"Character {user_id} saved successfully to {filepath} and cache updated.")
            else:
                logger.error(f"save_json utility reported failure saving character {user_id}.")
            return success
        except Exception as e:
            logger.error(f"Exception during save_character file operation for {user_id}: {e}", exc_info=True)
            return False

    def _serialize_character_data(self, data: Dict) -> Dict:
        """Helper to ensure character dictionary data is JSON serializable."""
        # Use a copy to avoid modifying the original dict during iteration
        serialized_data = {}
        for key, value in data.items():
            # Skip complex objects like mocks that shouldn't be serialized
            if key == 'progression_engine' and hasattr(value, '_is_mock') and value._is_mock:
                continue
                
            if isinstance(value, set):
                # Sort sets for consistent output, although JSON itself doesn't guarantee order
                serialized_data[key] = sorted(list(value)) 
            elif isinstance(value, datetime):
                serialized_data[key] = value.isoformat()
            elif isinstance(value, dict): # Recursively serialize nested dicts
                 serialized_data[key] = self._serialize_character_data(value)
            # Add other type conversions if needed (e.g., custom objects)
            else:
                # Assume other types are directly serializable
                serialized_data[key] = value
                
        return serialized_data
        
    async def get_character(self, user_id: str) -> Optional[Character]:
        """Get a character by user ID."""
        # Normalize user_id to string
        user_id = str(user_id)
        # First check if character is already loaded
        if user_id in self.characters:
            print(f"DEBUG [CharacterSystem.get_character]: Returning cached character for {user_id}") # DEBUG
            return self.characters[user_id]
            
        # If not loaded, try to load it
        print(f"DEBUG [CharacterSystem.get_character]: Character {user_id} not cached, attempting load.") # DEBUG
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

    async def create_character(self, user_id: str, name: str, clan: Optional[str] = None, **kwargs) -> Optional[Character]:
        """Creates and saves a new character."""
        # Normalize user_id to string
        user_id = str(user_id)
        print(f"DEBUG [CharacterSystem.create_character]: Received args - user_id={user_id!r}, name={name!r}, clan={clan!r}, kwargs={kwargs!r}")

        # Determine id type: convert numeric IDs to int for consistency, leave others as string
        char_id_value = int(user_id) if user_id.isdigit() else user_id
        existing = await self.get_character(user_id)
        if existing:
            logger.warning(f"Attempted to create character, but user_id '{user_id}' already exists.")
            return None # Return None if character already exists

        try:
            final_clan_name = None
            elemental_affinity = None
            clan_bonuses = {}

            if clan:
                clan_details = self.clan_data_service.get_clan_by_name(clan)
                if clan_details:
                    final_clan_name = clan_details.get('name')
                    clan_bonuses = self._get_clan_stat_bonuses(final_clan_name)
                    elemental_affinity = self._determine_affinity(final_clan_name)
                    logger.info(f"Character {name} assigned to clan: {final_clan_name}, Affinity: {elemental_affinity}")
                else:
                    logger.warning(f"Clan '{clan}' specified but not found. Character will be clanless.")
            else:
                logger.info(f"No clan specified for character {name}. Character will be clanless.")

            # Initialize base stats
            base_stats = {
                'strength': 10, 'defense': 10, 'speed': 10,
                'current_health': 50, 'max_health': 50,
                'current_chakra': 20, 'max_chakra': 20,
                'current_stamina': 20, 'max_stamina': 20,
                'chakra_control': 5
            }

            # Apply clan bonuses to base stats
            final_stats = base_stats.copy() # Start with base stats
            for stat, bonus in clan_bonuses.items():
                if stat in final_stats:
                    final_stats[stat] += bonus
                    logger.debug(f"Applied clan bonus to {stat}: +{bonus}")

            # Recalculate dependent stats if bonuses affected them
            # Example: Max health might increase based on strength/stamina bonus
            # Example: Max chakra might increase based on chakra_control bonus
            if 'chakra_control' in clan_bonuses:
                 # Adjust max chakra based on the updated chakra control
                 final_stats['max_chakra'] = max(20, 20 + (final_stats['chakra_control'] - 5) * 2)
                 final_stats['current_chakra'] = final_stats['max_chakra'] # Max out current chakra on creation
            if 'strength' in clan_bonuses or 'defense' in clan_bonuses: # Example dependency
                # Adjust max health based on updated strength/defense
                final_stats['max_health'] = max(50, 50 + (final_stats['strength'] - 10) + (final_stats['defense'] - 10))
                final_stats['current_health'] = final_stats['max_health'] # Max out current health on creation
            # Add similar recalculations for other stats if needed

            # Correct Character instantiation
            new_character = Character(
                id=char_id_value,
                name=name,
                clan=final_clan_name,
                level=1,
                exp=0,
                # --- Map final_stats to Character fields ---
                hp=final_stats.get('current_health', 50), # Use appropriate defaults if needed
                max_hp=final_stats.get('max_health', 50),
                chakra=final_stats.get('current_chakra', 20),
                max_chakra=final_stats.get('max_chakra', 20),
                stamina=final_stats.get('current_stamina', 20),
                max_stamina=final_stats.get('max_stamina', 20),
                strength=final_stats.get('strength', 10),
                speed=final_stats.get('speed', 10),
                defense=final_stats.get('defense', 10),
                chakra_control=final_stats.get('chakra_control', 5),
                # --- Add other necessary fields from final_stats or defaults ---
                willpower=final_stats.get('willpower', 10), # Assuming these are in final_stats or have defaults
                intelligence=final_stats.get('intelligence', 10),
                perception=final_stats.get('perception', 0),
                # Apply clan bonuses to jutsu stats (default base values + bonuses)
                ninjutsu=clan_bonuses.get('ninjutsu', 0),
                taijutsu=clan_bonuses.get('taijutsu', 0) + 10,
                genjutsu=clan_bonuses.get('genjutsu', 0) + 10,
                # --- Set other non-stat fields ---
                rank='Academy Student', # Use correct rank
                elemental_affinity=elemental_affinity,
                inventory={}, # Use dataclass default
                jutsu=[], # Use dataclass default (list)
                equipment={} # Use dataclass default
                # Other fields like achievements, titles, etc., will use dataclass defaults
            )

            # Save the new character
            success = await self.save_character(new_character)
            if success:
                logger.info(f"Successfully created and saved new character: {name} (ID: {user_id})")
                self.characters[user_id] = new_character # Add to cache
                return new_character
            else:
                logger.error(f"Failed to save the newly created character: {name} (ID: {user_id})")
                return None # Return None if saving failed

        except Exception as e:
            logger.error(f"Error during character creation for user_id '{user_id}': {e}", exc_info=True)
            return None

    def _get_clan_stat_bonuses(self, clan_name: Optional[str]) -> Dict[str, int]:
        """Retrieves stat bonuses for a given clan using the ClanData service."""
        if not clan_name:
            return {}
        # Delegate bonus retrieval (handles nested 'stat_bonuses' and legacy keys)
        try:
            return self.clan_data_service.get_clan_bonuses(clan_name)
        except Exception as e:
            logger.error(f"Error retrieving bonuses for clan '{clan_name}': {e}", exc_info=True)
            return {}

    def _determine_affinity(self, clan_name: Optional[str]) -> Optional[str]:
        """Determines elemental affinity based on clan details."""
        if not clan_name:
            return None
        # Use the injected service
        clan_details = self.clan_data_service.get_clan_by_name(clan_name)
        if not clan_details:
            return None
        # Return provided affinity if present
        affinity = clan_details.get('affinity')
        if affinity:
            return affinity
        # Fallback logic (legacy)
        if clan_name == "Uchiha":
            return "Fire"
        elif clan_name == "Senju":
            return "Wood"
        # Default
        return None

    async def add_jutsu(self, character_id: str, jutsu_name: str) -> Tuple[bool, List[str]]:
        """Adds a jutsu to a character's known jutsu if they meet the requirements."""
        character = await self.get_character(character_id)
        if not character:
            return False, [f"Character {character_id} not found."]

        # Access JutsuRegistry through the progression engine
        if not self.progression_engine or not self.progression_engine.jutsu_registry:
            return False, ["Jutsu system not available."]
            
        jutsu = self.progression_engine.jutsu_registry.get_jutsu(jutsu_name)
        if not jutsu:
            return False, [f"Jutsu '{jutsu_name}' not found."]

        # Check if character already knows the jutsu
        if jutsu_name in character.jutsu_mastery:
            return False, [f"Character already knows '{jutsu_name}'."]

        # Check requirements using the registry's method
        can_learn, unmet_reqs = self.progression_engine.jutsu_registry.check_jutsu_requirements(character, jutsu_name)

        if can_learn:
            # Add jutsu with initial mastery level (e.g., 0)
            character.jutsu_mastery[jutsu_name] = {"level": 0, "mastery_points": 0, "unlocked": True} # Add 'unlocked' flag
            await self.save_character(character)
            logger.info(f"Character {character_id} learned jutsu: {jutsu_name}")
            return True, []
        else:
            logger.info(f"Character {character_id} cannot learn {jutsu_name}. Unmet requirements: {unmet_reqs}")
            return False, [f"Cannot learn '{jutsu_name}'. Unmet requirements:"] + unmet_reqs
            
    async def increase_jutsu_mastery(self, character_id: str, jutsu_name: str, gain_amount: int) -> Optional[Tuple[int, int, bool]]:
        """
        Increases the mastery points for a specific jutsu for a character.
        Handles leveling up the jutsu if mastery points reach the threshold.

        Args:
            character_id: The ID of the character.
            jutsu_name: The name of the jutsu.
            gain_amount: The amount of mastery points gained.

        Returns:
            A tuple (new_level, new_mastery_points, leveled_up) if successful, None otherwise.
            - new_level: The jutsu's level after the gain.
            - new_mastery_points: The jutsu's mastery points after the gain.
            - leveled_up: Boolean indicating if the jutsu leveled up.
        """
        character = await self.get_character(character_id)
        if not character:
            logger.error(f"increase_jutsu_mastery: Character {character_id} not found.")
            return None

        if jutsu_name not in character.jutsu_mastery:
            logger.error(f"increase_jutsu_mastery: Character {character_id} does not know jutsu '{jutsu_name}'.")
            return None
            
        if not self.progression_engine or not self.progression_engine.jutsu_registry:
            logger.error("increase_jutsu_mastery: Progression engine or Jutsu registry not available.")
            return None

        jutsu_data = character.jutsu_mastery[jutsu_name]
        current_level = jutsu_data.get("level", 0)
        current_mastery = jutsu_data.get("mastery_points", 0)
        
        jutsu_details = self.progression_engine.jutsu_registry.get_jutsu(jutsu_name)
        if not jutsu_details:
             logger.error(f"increase_jutsu_mastery: Jutsu details for '{jutsu_name}' not found in registry.")
             return None # Should not happen if jutsu is in character mastery

        # Calculate required points for the next level
        # This assumes progression_engine has a way to calculate this
        required_for_next = self.progression_engine.get_mastery_required_for_level(current_level + 1)
        
        # Add gain amount
        new_mastery_points = current_mastery + gain_amount
        new_level = current_level
        leveled_up = False

        # Check for level up - loop in case multiple level ups occur
        while new_mastery_points >= required_for_next:
            new_level += 1
            new_mastery_points -= required_for_next
            leveled_up = True
            logger.info(f"Character {character_id} leveled up jutsu '{jutsu_name}' to level {new_level}.")
            # Get required points for the *next* potential level
            required_for_next = self.progression_engine.get_mastery_required_for_level(new_level + 1)
            # Handle max level if necessary (get_mastery_required_for_level might return infinity or None)
            if required_for_next is None or required_for_next == float('inf'): 
                # Cap mastery points at 0 if max level reached? Or just keep excess?
                # Decide on behavior here. For now, keep excess but log.
                logger.info(f"Jutsu '{jutsu_name}' reached max level {new_level} for character {character_id}.")
                break # Exit loop if max level reached

        # Update character data
        jutsu_data["level"] = new_level
        jutsu_data["mastery_points"] = new_mastery_points
        
        # Save the updated character
        await self.save_character(character)
        
        return new_level, new_mastery_points, leveled_up

    async def migrate_jutsu_data(self, master_jutsu_names: Set[str]) -> int:
        """
        Migrates old jutsu list format to the new dictionary format {jutsu_name: {level: L, mastery_points: P}}.
        It iterates through all loaded characters.

        Args:
            master_jutsu_names: A set of all valid jutsu names from the JutsuRegistry.

        Returns:
            The number of characters migrated.
        """
        migrated_count = 0
        logger.info("Starting jutsu data migration...")

        # Iterate over a copy of character IDs to avoid issues if the dict changes during iteration
        character_ids = list(self.characters.keys()) 

        for char_id in character_ids:
            character = self.characters.get(char_id) # Use .get for safety
            if not character:
                logger.warning(f"Migration: Character {char_id} not found in memory during migration.")
                continue

            needs_migration = False
            new_jutsu_mastery = {}

            # Check if the current jutsu_mastery is a list (old format)
            if isinstance(character.jutsu_mastery, list):
                needs_migration = True
                logger.debug(f"Migrating jutsu data for character {char_id} (old format: list).")
                old_jutsu_list = character.jutsu_mastery
                for jutsu_name in old_jutsu_list:
                    if jutsu_name in master_jutsu_names:
                        # Default new format: level 0, points 0, unlocked True
                        new_jutsu_mastery[jutsu_name] = {"level": 0, "mastery_points": 0, "unlocked": True}
                    else:
                         logger.warning(f"Migration: Character {char_id} had unknown jutsu '{jutsu_name}' which will be skipped.")
            elif isinstance(character.jutsu_mastery, dict):
                 # Check if existing dict entries need the 'unlocked' flag or other standard fields
                 logger.debug(f"Checking jutsu data format for character {char_id} (format: dict).")
                 for jutsu_name, data in character.jutsu_mastery.items():
                     if isinstance(data, dict):
                         # Assume valid structure if it's already a dict, just ensure standard fields exist
                         updated_data = {
                             "level": data.get("level", 0), 
                             "mastery_points": data.get("mastery_points", 0),
                             "unlocked": data.get("unlocked", True) # Default to True if missing
                         }
                         # Check if any change was made by adding default fields
                         if updated_data != data:
                             needs_migration = True
                         # Also prune unknown jutsu found in dict format
                         if jutsu_name not in master_jutsu_names:
                             logger.warning(f"Migration: Character {char_id} had unknown jutsu '{jutsu_name}' in dict format, removing.")
                             needs_migration = True
                         else:
                              new_jutsu_mastery[jutsu_name] = updated_data
                     else:
                         # Handle case where dict value is not a dict (unexpected format)
                         logger.warning(f"Migration: Character {char_id} has invalid data type for jutsu '{jutsu_name}' in dict: {type(data)}. Skipping.")
                         needs_migration = True # Mark for potential save even if skipping jutsu
            else:
                 # Handle completely unexpected format for jutsu_mastery
                 logger.warning(f"Migration: Character {char_id} has unexpected format for jutsu_mastery: {type(character.jutsu_mastery)}. Resetting to empty dict.")
                 needs_migration = True
                 # new_jutsu_mastery is already {}


            if needs_migration:
                logger.info(f"Updating jutsu data structure for character {char_id}.")
                character.jutsu_mastery = new_jutsu_mastery
                # Save the character with the migrated data
                save_success = await self.save_character(character)
                if save_success:
                    migrated_count += 1
                    logger.debug(f"Successfully saved migrated jutsu data for character {char_id}.")
                else:
                    logger.error(f"Failed to save migrated jutsu data for character {char_id}.")

        logger.info(f"Jutsu data migration completed. Migrated {migrated_count} characters.")
        return migrated_count
        
    async def update_character_stat(self, user_id: str, stat: str, amount: float) -> bool:
        """Updates a specific stat for a character and saves the change."""
        character = await self.get_character(user_id)
        if not character:
            logger.error(f"update_character_stat: Character {user_id} not found.")
            return False

        # Validate stat name
        if stat not in character.stats:
             logger.error(f"update_character_stat: Invalid stat name '{stat}' for character {user_id}.")
             return False

        # Apply the change (ensure amount is treated correctly, e.g., float for health/chakra)
        try:
            # Potential type issues if stats dict mixes ints and floats inconsistently
            current_value = character.stats[stat]
            # Convert amount to the type of the current value if possible
            if isinstance(current_value, int) and isinstance(amount, float) and amount.is_integer():
                 amount_typed = int(amount)
            elif isinstance(current_value, float):
                 amount_typed = float(amount)
            else: # Assume types match or direct addition works
                 amount_typed = amount # Use as is

            new_value = current_value + amount_typed
            
            # Add potential clamps or rules here (e.g., health cannot go below 0)
            if stat == 'current_health' and new_value < 0:
                new_value = 0
            elif stat == 'current_health' and new_value > character.stats.get('max_health', new_value): # Check against max health
                new_value = character.stats.get('max_health', new_value) 
            elif stat == 'current_chakra' and new_value < 0:
                new_value = 0
            elif stat == 'current_chakra' and new_value > character.stats.get('max_chakra', new_value): # Check against max chakra
                 new_value = character.stats.get('max_chakra', new_value)

            # Update the stat
            character.stats[stat] = new_value
            logger.debug(f"Updated stat '{stat}' for character {user_id} from {current_value} to {new_value}.")

        except TypeError as e:
             logger.error(f"update_character_stat: Type error updating stat '{stat}' for {user_id}. Current: {current_value}, Amount: {amount}. Error: {e}")
             return False
        except Exception as e:
             logger.error(f"update_character_stat: Unexpected error updating stat '{stat}' for {user_id}: {e}", exc_info=True)
             return False

        # Save the updated character
        success = await self.save_character(character)
        if not success:
            logger.error(f"update_character_stat: Failed to save character {user_id} after updating stat '{stat}'.")
        return success

    async def shutdown(self):
        """Performs any necessary cleanup, like ensuring all characters are saved."""
        logger.info("CharacterSystem shutting down. Saving all modified characters...")
        # Saving all might be redundant if save_character is called on every modification
        # However, it's a safety measure. Consider if performance is critical.
        save_tasks = [self.save_character(char) for char in self.characters.values()]
        results = await asyncio.gather(*save_tasks, return_exceptions=True)
        
        saved_count = sum(1 for res in results if res is True)
        failed_count = len(results) - saved_count
        
        logger.info(f"Shutdown save complete. Saved: {saved_count}, Failed: {failed_count}")
        if failed_count > 0:
            # Log specific failures if possible/needed
             logger.error(f"{failed_count} characters failed to save during shutdown.")

    async def delete_character(self, user_id: str) -> bool:
        logger.warning(f">>> [Service Delete] delete_character called for {user_id}. Instance ID: {id(self)}") # Added Log
        """Deletes a character's data file and removes them from memory."""
        # Normalize user_id to string
        user_id = str(user_id)
        # Remove from memory first
        if user_id in self.characters:
            del self.characters[user_id]
            logger.debug(f"Removed character {user_id} from memory.")
            
        # Delete the file
        filepath = os.path.join(self.character_data_dir, f"{user_id}.json")
        try:
            if await aiofiles.os.path.exists(filepath):
                # Try async remove first
                try:
                    await aiofiles.os.remove(filepath)
                except Exception as aio_err:
                    logger.warning(f"Async remove failed for {filepath}, attempting sync remove: {aio_err}")
                    try:
                        import os as _os
                        _os.remove(filepath)
                    except Exception as sync_err:
                        logger.error(f"Sync remove also failed for {filepath}: {sync_err}", exc_info=True)
                # Delay to ensure file system consistency for E2E tests
                await asyncio.sleep(0.1)
                logger.info(f"Successfully deleted character file: {filepath}")
            else:
                logger.warning(f"Attempted to delete character file, but it did not exist: {filepath}")
            # Return True regardless, as memory removal happened
            return True
        except Exception as e:
            logger.error(f"Error deleting character file {filepath}: {e}", exc_info=True)
            # Attempt sync remove as fallback
            try:
                import os as _os
                if _os.path.exists(filepath):
                    _os.remove(filepath)
                    await asyncio.sleep(0.1)
                    return True
            except Exception as fallback_err:
                logger.error(f"Fallback sync delete failed for {filepath}: {fallback_err}", exc_info=True)
            return False 