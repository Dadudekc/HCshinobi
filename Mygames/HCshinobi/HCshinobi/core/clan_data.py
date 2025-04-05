"""
Clan Data module for the HCshinobi project.
Manages clan definitions, rarities, lore, and persistence.
"""
from typing import Dict, List, Any, Optional, Tuple
import os
import json
import random
import time
import asyncio # Add asyncio import
import logging

# Use centralized constants and file I/O
from .constants import (
    RarityTier, DEFAULT_RARITY_WEIGHTS, CLANS_SUBDIR, CLANS_FILE, 
    CLAN_POPULATION_FILE, ASSIGNMENT_HISTORY_FILE, 
    CLAN_FORMAT_TRANSITION_VERSION, CLAN_FORMAT_TRANSITION_MESSAGE
)
from ..utils.file_io import load_json, save_json, async_save_json
from ..utils.logging import get_logger
from HCshinobi.utils.config import DEFAULT_CLANS_PATH # Added import

logger = logging.getLogger(__name__)

class ClanData:
    """
    Manages data related to clans, loading from and saving to a file.
    Provides methods to access and manipulate clan information.
    """

    def __init__(self, data_dir: str):
        self.base_data_dir = data_dir
        # Construct specific path for clan files
        self.clans_data_dir = os.path.join(data_dir, CLANS_SUBDIR)
        os.makedirs(self.clans_data_dir, exist_ok=True)
        
        # Construct full file path for the main clans data file
        self.clans_file_path = os.path.join(self.clans_data_dir, CLANS_FILE)
        
        self.clans: Dict[str, Dict[str, Any]] = {} # Key: clan_id, Value: clan details dict
        self.using_legacy_format = False
        logger.info(f"ClanData initialized. Data dir: {self.clans_data_dir}")
        # Loading is handled by an explicit async call

    async def load_clan_data(self):
        """Loads clan data from village-specific clan files with legacy fallback to clans.json."""
        self.clans = {}  # Reset clan data before loading
        self.using_legacy_format = False  # Reset legacy format flag
        legacy_clans_loaded = False
        
        try:
            # First, load all village-specific clan files, which are the new preferred format
            village_files_count = 0
            for filename in os.listdir(self.clans_data_dir):
                if filename != CLANS_FILE and filename.endswith('.json'):
                    file_path = os.path.join(self.clans_data_dir, filename)
                    try:
                        village_data = load_json(file_path)
                        
                        # Handle clan_tiers.json specifically
                        if filename == "clan_tiers.json":
                            logger.info(f"Loading clan tiers from {filename}")
                            # Clan tiers has a different structure with tiers as keys
                            for tier_name, tier_info in village_data.items():
                                if isinstance(tier_info, dict) and 'clans' in tier_info:
                                    # Process clan information in this tier
                                    for clan_name, clan_desc in tier_info['clans'].items():
                                        # Create or update clan entry
                                        if clan_name not in self.clans:
                                            self.clans[clan_name] = {
                                                'name': clan_name,
                                                'rarity': tier_name,
                                                'lore': clan_desc,
                                                'tier': tier_name,
                                                'description': clan_desc,
                                                'source_file': filename  # Track source file
                                            }
                                        else:
                                            # Only update if not from a more specific file
                                            if 'source_file' not in self.clans[clan_name] or self.clans[clan_name]['source_file'] == CLANS_FILE:
                                                self.clans[clan_name].update({
                                                    'tier': tier_name,
                                                    'description': clan_desc,
                                                    'source_file': filename
                                                })
                            village_files_count += 1
                        
                        # Handle village clan files (e.g., Konohagakure_clans.json)
                        elif isinstance(village_data, dict) and any(village_key.endswith("Clans") for village_key in village_data.keys()):
                            # Village-specific clan file with structure {"VillageName Clans": [...]}
                            for village_key, clan_list in village_data.items():
                                if isinstance(clan_list, list):
                                    village_name = village_key.replace(" Clans", "")
                                    logger.info(f"Loading {len(clan_list)} clans from {village_name}")
                                    
                                    for clan_data in clan_list:
                                        if isinstance(clan_data, dict) and 'name' in clan_data:
                                            clan_name = clan_data['name']
                                            
                                            # Convert abilities to starting_jutsu if not present
                                            if 'abilities' in clan_data and 'starting_jutsu' not in clan_data:
                                                clan_data['starting_jutsu'] = clan_data['abilities'][:2] if len(clan_data['abilities']) > 1 else clan_data['abilities']
                                            
                                            # Add default values for required fields
                                            if 'rarity' not in clan_data:
                                                clan_data['rarity'] = 'Standard'
                                                
                                            # Add bonuses if not present
                                            if 'strength_bonus' not in clan_data:
                                                clan_data['strength_bonus'] = 2
                                            if 'defense_bonus' not in clan_data:
                                                clan_data['defense_bonus'] = 2
                                            if 'speed_bonus' not in clan_data:
                                                clan_data['speed_bonus'] = 2
                                            
                                            # Add village information
                                            clan_data['village'] = village_name
                                            clan_data['source_file'] = filename
                                                
                                            # Add or update clan in our dictionary
                                            if clan_name not in self.clans:
                                                self.clans[clan_name] = clan_data
                                            else:
                                                # Only overwrite if the existing entry wasn't from a village file
                                                if 'source_file' not in self.clans[clan_name] or self.clans[clan_name]['source_file'] == CLANS_FILE:
                                                    self.clans[clan_name].update(clan_data)
                                        else:
                                            logger.warning(f"Skipping invalid clan object in {filename} (missing 'name')")
                            village_files_count += 1
                        else:
                            logger.warning(f"Unknown format in {filename}, skipping")
                    except Exception as e:
                        logger.error(f"Error loading clan from {filename}: {e}", exc_info=True)
            
            # If we loaded village files, notify user about transition status
            if village_files_count > 0:
                logger.info(f"Loaded {len(self.clans)} clans from {village_files_count} village-specific files")
            
            # DEPRECATED: Fallback to legacy clans.json only if no village files found
            if len(self.clans) == 0:
                logger.warning(f"No clan data found in village-specific files. Falling back to legacy {CLANS_FILE} (DEPRECATED)")
                loaded_data = load_json(self.clans_file_path)
                if loaded_data is None:
                    logger.warning(f"Legacy clan file not found: {self.clans_file_path}. Using default clans.")
                    self.clans = self.create_default_clans()
                    # Save these default clans to new format files
                    self._migrate_clans_to_new_format()
                elif isinstance(loaded_data, list):
                    processed_count = 0
                    for clan_obj in loaded_data:
                        if isinstance(clan_obj, dict) and 'name' in clan_obj:
                            clan_name = clan_obj['name']
                            clan_obj['source_file'] = CLANS_FILE  # Mark as legacy source
                            self.clans[clan_name] = clan_obj
                            processed_count += 1
                        else:
                            logger.warning(f"Skipping invalid clan object in {self.clans_file_path}: {clan_obj}")
                    logger.info(f"DEPRECATED: Processed {processed_count} clans from legacy list format in {self.clans_file_path}")
                    # Suggest migration to new format
                    logger.warning("Legacy clan format detected. Consider migrating to the new village-specific format.")
                    self.using_legacy_format = True  # Mark that we're using legacy format
                elif isinstance(loaded_data, dict):
                    self.clans = loaded_data
                    # Mark all as from legacy source
                    for clan_name in self.clans:
                        self.clans[clan_name]['source_file'] = CLANS_FILE
                    logger.info(f"DEPRECATED: Loaded {len(self.clans)} clans (dict format) from legacy {self.clans_file_path}")
                    # Suggest migration to new format
                    logger.warning("Legacy clan format detected. Consider migrating to the new village-specific format.")
                    self.using_legacy_format = True  # Mark that we're using legacy format
                legacy_clans_loaded = True
            # If we have village clans but clans.json also exists, load it for compatibility but don't overwrite
            elif os.path.exists(self.clans_file_path):
                loaded_data = load_json(self.clans_file_path)
                if loaded_data:
                    logger.warning(f"DEPRECATED: Legacy {CLANS_FILE} exists alongside new format files. Consider removing it.")
                    # We could do a merge here if needed, but prioritizing village files
                  
            logger.info(f"Total clans loaded after processing all files: {len(self.clans)}")
            
        except Exception as e:
            logger.error(f"Error loading clan data: {e}", exc_info=True)
            # Fallback to default clans if there was an error
            if not self.clans:
                self.clans = self.create_default_clans()
                logger.info(f"Loaded {len(self.clans)} default clans due to error")
    
    def _migrate_clans_to_new_format(self):
        """
        Migrates clans from the legacy format to the new village-specific format.
        This is called when only default clans are available.
        """
        try:
            # Create a structure for Konohagakure clans (default village)
            konoha_clans = {"Konohagakure Clans": []}
            
            # Move each clan to the appropriate structure
            for clan_name, clan_data in self.clans.items():
                # Create a new format clan entry
                new_clan = {
                    "name": clan_name,
                    "village": "Konohagakure",  # Default village
                    "kekkei_genkai": "",
                    "abilities": clan_data.get("starting_jutsu", []),
                    "traits": [],
                    "role": clan_data.get("lore", "")
                }
                konoha_clans["Konohagakure Clans"].append(new_clan)
            
            # Save to the new format file
            konoha_file_path = os.path.join(self.clans_data_dir, "Konohagakure_clans.json")
            save_json(konoha_file_path, konoha_clans)
            logger.info(f"Migrated {len(self.clans)} default clans to new format: {konoha_file_path}")
            
            # Create a simple clan tiers structure
            tiers = {
                "Standard Tier (~79%)": {
                    "description": "Common clans that form the foundation of shinobi society.",
                    "clans": {}
                },
                "Rare Tier (~15%)": {
                    "description": "Uncommon clans with special abilities.",
                    "clans": {}
                },
                "Epic Tier (~5%)": {
                    "description": "Rare clans with powerful bloodlines.",
                    "clans": {}
                },
                "Legendary Tier (~1%)": {
                    "description": "Extremely rare clans with legendary abilities.",
                    "clans": {}
                }
            }
            
            # Assign clans to tiers based on their rarity
            for clan_name, clan_data in self.clans.items():
                rarity = clan_data.get("rarity", "Standard")
                
                if rarity == RarityTier.COMMON.value:
                    tier = "Standard Tier (~79%)"
                elif rarity == RarityTier.UNCOMMON.value:
                    tier = "Rare Tier (~15%)"
                elif rarity == RarityTier.RARE.value:
                    tier = "Epic Tier (~5%)"
                else:
                    tier = "Legendary Tier (~1%)"
                    
                tiers[tier]["clans"][clan_name] = clan_data.get("lore", "No information available.")
            
            # Save tiers file
            tiers_file_path = os.path.join(self.clans_data_dir, "clan_tiers.json")
            save_json(tiers_file_path, tiers)
            logger.info(f"Created clan tiers file: {tiers_file_path}")
            
        except Exception as e:
            logger.error(f"Error migrating clans to new format: {e}", exc_info=True)

    async def _save_clan_data(self):
        """Saves the current clan data asynchronously."""
        try:
            # Use async_save_json for async operation
            success = await async_save_json(self.clans_file_path, self.clans)
            if success:
                logger.info("Clan data saved successfully.")
            else:
                logger.error("Failed to save clan data.")
        except Exception as e:
            logger.error(f"Failed to save clan data to {self.clans_file_path}: {e}", exc_info=True)
            
    def save_clan_data(self):
        """Saves the current clan data synchronously."""
        try:
            # Use save_json for sync operation
            success = save_json(self.clans_file_path, self.clans)
            if success:
                logger.info("Clan data saved successfully.")
            else:
                logger.error("Failed to save clan data.")
        except Exception as e:
            logger.error(f"Failed to save clan data to {self.clans_file_path}: {e}", exc_info=True)

    def create_default_clans(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate a default list of clans based on Naruto lore.
        Uses rarities and weights defined in constants.

        Returns:
            Dict[str, Dict[str, Any]]: The default list of clan dictionaries.
        """
        logger.info("Generating default clan list...")
        default_clans = {
            # Common Clans
            "Inuzuka": {
                "name": "Inuzuka",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for their ninja dogs.",
                "suggested_personalities": ["Loyal", "Energetic"],
                "strength_bonus": 2,
                "defense_bonus": 1,
                "speed_bonus": 3,
                "starting_jutsu": ["Fang Over Fang", "Fang Passing Fang"]
            },
            "Akimichi": {
                "name": "Akimichi",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for body expansion jutsu.",
                "suggested_personalities": ["Kind", "Generous"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 1,
                "starting_jutsu": ["Expansion Jutsu", "Human Bullet Tank"]
            },
            "Nara": {
                "name": "Nara",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for shadow manipulation.",
                "suggested_personalities": ["Intelligent", "Strategic"],
                "strength_bonus": 1,
                "defense_bonus": 1,
                "speed_bonus": 2,
                "starting_jutsu": ["Shadow Imitation", "Shadow Sewing"]
            },
            "Yamanaka": {
                "name": "Yamanaka",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for mind-related techniques.",
                "suggested_personalities": ["Sociable", "Intuitive"],
                "strength_bonus": 1,
                "defense_bonus": 1,
                "speed_bonus": 2,
                "starting_jutsu": ["Mind Transfer", "Mind Transmission"]
            },
            "Sarutobi": {
                "name": "Sarutobi",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for strong chakra and fire affinity.",
                "suggested_personalities": ["Wise", "Honorable"],
                "strength_bonus": 2,
                "defense_bonus": 2,
                "speed_bonus": 1,
                "starting_jutsu": ["Enma Staff", "Fire Release: Fireball"]
            },

            # Uncommon Clans
            "Aburame": {
                "name": "Aburame",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for insect manipulation.",
                "suggested_personalities": ["Calm", "Analytical"],
                "strength_bonus": 2,
                "defense_bonus": 2,
                "speed_bonus": 2,
                "starting_jutsu": ["Insect Sphere", "Insect Clone"]
            },
            "Hyuga": {
                "name": "Hyuga",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for Byakugan and gentle fist.",
                "suggested_personalities": ["Proud", "Disciplined"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 3,
                "starting_jutsu": ["Gentle Fist", "Eight Trigrams Palm Rotation"]
            },
            "Uchiha": {
                "name": "Uchiha",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for Sharingan and fire techniques.",
                "suggested_personalities": ["Proud", "Determined"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 3,
                "starting_jutsu": ["Fire Release: Fireball", "Shuriken Shadow Clone"]
            },
            "Senju": {
                "name": "Senju",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for strong life force and wood release.",
                "suggested_personalities": ["Noble", "Protective"],
                "strength_bonus": 3,
                "defense_bonus": 3,
                "speed_bonus": 2,
                "starting_jutsu": ["Wood Release: Wood Clone", "Wood Release: Wood Wall"]
            },
            "Uzumaki": {
                "name": "Uzumaki",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for sealing techniques and strong life force.",
                "suggested_personalities": ["Resilient", "Creative"],
                "strength_bonus": 2,
                "defense_bonus": 3,
                "speed_bonus": 2,
                "starting_jutsu": ["Adamantine Sealing Chains", "Uzumaki Sealing Method"]
            }
        }
        return default_clans

    def get_clans(self) -> List[str]:
        """Get list of all clan names.
        
        Returns:
            List of clan names
        """
        return list(self.clans.keys())

    def get_clan(self, clan_id: str) -> Optional[Dict[str, Any]]:
        """Get clan data by name.
        
        Args:
            clan_id: The ID of the clan
            
        Returns:
            Clan data if found, None otherwise
        """
        return self.clans.get(clan_id)

    def get_clan_rarity(self, clan_id: str) -> Optional[RarityTier]:
        """Get clan rarity.
        
        Args:
            clan_id: The ID of the clan
            
        Returns:
            Clan rarity if found, None otherwise
        """
        clan = self.get_clan(clan_id)
        if clan:
            return RarityTier(clan['rarity'])
        return None

    def get_clan_bonuses(self, clan_id: str) -> Dict[str, int]:
        """Get clan attribute bonuses.
        
        Args:
            clan_id: The ID of the clan
            
        Returns:
            Dictionary of attribute bonuses
        """
        clan = self.get_clan(clan_id)
        if not clan:
            return {'strength': 0, 'defense': 0, 'speed': 0}
        return {
            'strength': clan.get('strength_bonus', 0),
            'defense': clan.get('defense_bonus', 0),
            'speed': clan.get('speed_bonus', 0)
        }

    def get_clan_jutsu(self, clan_id: str) -> List[str]:
        """Get clan starting jutsu.
        
        Args:
            clan_id: The ID of the clan
            
        Returns:
            List of starting jutsu
        """
        clan = self.get_clan(clan_id)
        if not clan:
            return []
        return clan.get('starting_jutsu', [])

    def get_random_clan(self) -> Optional[Dict[str, Any]]:
        """Select and return a random clan from the loaded data.

        Returns:
            A dictionary containing the data of a randomly selected clan,
            or None if no clans are loaded.
        """
        if not self.clans:
            logger.warning("Attempted to get a random clan, but no clans are loaded.")
            return None
        
        try:
            selected_clan = random.choice(list(self.clans.values()))
            return selected_clan
        except IndexError:
             # This case should be covered by the initial check, but added for safety
             logger.warning("random.choice failed on self.clans despite not being empty.")
             return None
        except Exception as e:
             logger.error(f"Unexpected error selecting random clan: {e}", exc_info=True)
             return None

    # --- Public Access Methods ---

    def get_all_clans(self) -> Dict[str, Dict[str, Any]]:
        """Return a copy of the list of all clan data."""
        return self.clans.copy()

    def get_clan_by_name(self, clan_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for a specific clan by name (case-insensitive)."""
        normalized_name = clan_name.strip().lower()
        for clan_id, clan in self.clans.items():
            if clan['name'].lower() == normalized_name:
                return clan.copy() # Return a copy
        return None

    def get_clans_by_rarity(self, rarity: RarityTier) -> List[Dict[str, Any]]:
        """Retrieve all clans belonging to a specific rarity tier."""
        if not isinstance(rarity, RarityTier):
             logger.error(f"Invalid rarity type provided: {type(rarity)}. Expected RarityTier enum.")
             return []
        return [clan.copy() for clan in self.clans.values() if clan['rarity'] == rarity.value]

    def add_clan(self, clan_id: str, clan_data: Dict[str, Any]) -> bool:
        """
        Add a new clan to the data. Validates required fields.
        Saves the updated list to the file.

        Args:
            clan_id: The ID of the new clan
            clan_data: Dictionary containing the new clan's information.
                       Required keys: 'name', 'rarity', 'lore', 'base_weight'.

        Returns:
            True if the clan was added successfully, False otherwise.
        """
        required_keys = {'name', 'rarity', 'lore', 'base_weight'}
        if not required_keys.issubset(clan_data.keys()):
            logger.error(f"Attempted to add clan with missing keys. Data: {clan_data}")
            return False

        # Check if rarity is valid
        if clan_data['rarity'] not in [tier.value for tier in RarityTier]:
             logger.error(f"Attempted to add clan '{clan_data['name']}' with invalid rarity: {clan_data['rarity']}")
             return False

        # Check for duplicates
        if self.get_clan_by_name(clan_data['name']):
            logger.warning(f"Attempted to add duplicate clan: {clan_data['name']}")
            return False # Or update existing?

        self.clans[clan_id] = clan_data
        logger.info(f"Added new clan: {clan_data['name']}")
        # Await the async save method
        self.save_clan_data()
        return True

    def update_clan(self, clan_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing clan's data.
        Saves the updated list to the file.

        Args:
            clan_id: The ID of the clan to update.
            update_data: Dictionary containing the fields to update.

        Returns:
            True if the clan was found and updated, False otherwise.
        """
        if clan_id not in self.clans:
            logger.warning(f"Attempted to update non-existent clan: {clan_id}")
            return False

        # Ensure required fields aren't removed if they exist in update
        if 'name' in update_data and not update_data['name']:
             logger.error("Cannot update clan to have an empty name.")
             return False
        if 'rarity' in update_data and update_data['rarity'] not in [tier.value for tier in RarityTier]:
             logger.error(f"Cannot update clan '{clan_id}' to invalid rarity: {update_data['rarity']}")
             return False

        # Apply validated updates
        validated_updates = {key: update_data[key] for key in update_data if key in self.clans[clan_id]}
        if not validated_updates:
             logger.error("No valid updates were made after validation.")
             return False # Return False if no valid updates were made after validation

        # Apply validated updates
        self.clans[clan_id].update(validated_updates)
        logger.info(f"Updated clan: {clan_id} with data: {validated_updates}")
         # Await the async save method
        self.save_clan_data()
        return True

    def remove_clan(self, clan_id: str) -> bool:
        """
        Remove a clan from the data.
        Saves the updated list to the file.

        Args:
            clan_id: The ID of the clan to remove.

        Returns:
            True if the clan was found and removed, False otherwise.
        """
        if clan_id not in self.clans:
            logger.warning(f"Attempted to remove non-existent clan: {clan_id}")
            return False

        removed_clan = self.clans.pop(clan_id)
        logger.info(f"Removed clan: {removed_clan['name']}")
         # Await the async save method
        self.save_clan_data()
        return True

    # Removed get_rarity_tiers - Weights are now in constants
    # If dynamic weights are needed later, this class could manage them.

    # Optional: Add a method to get base weights for assignment engine
    def get_clan_base_weights(self) -> Dict[str, float]:
        """Returns a dictionary mapping clan names to their base weights."""
        return {clan['name']: clan.get('base_weight', 0) for clan in self.clans.values()}

    # Ready hook (if needed, e.g., for background tasks related to clans)
    async def ready_hook(self):
        await self.load_clan_data()
        logger.info(f"ClanData ready. Loaded data for {len(self.clans)} clans.")
        
        # Display transition message if using legacy format
        if self.using_legacy_format:
            logger.warning(f"CLAN SYSTEM TRANSITION v{CLAN_FORMAT_TRANSITION_VERSION}: {CLAN_FORMAT_TRANSITION_MESSAGE}")

    def migrate_to_new_format(self):
        """
        Migrates all clan data from the legacy format to the new village-specific format.
        This can be called explicitly by admin commands to convert the data.
        """
        if not self.using_legacy_format or len(self.clans) == 0:
            logger.warning("No legacy clan data to migrate or already using new format.")
            return False
            
        try:
            # Call the migration helper
            self._migrate_clans_to_new_format()
            
            # Optionally, move the old file to a backup
            if os.path.exists(self.clans_file_path):
                backup_path = f"{self.clans_file_path}.bak"
                import shutil
                shutil.copy2(self.clans_file_path, backup_path)
                logger.info(f"Created backup of legacy clan data at {backup_path}")
                
                # Create an empty new file as a placeholder
                with open(self.clans_file_path, 'w') as f:
                    f.write('{"migrated": true, "version": "' + CLAN_FORMAT_TRANSITION_VERSION + '"}')
                logger.info(f"Replaced {CLANS_FILE} with placeholder")
                
            return True
        except Exception as e:
            logger.error(f"Failed to migrate clan data: {e}", exc_info=True)
            return False

class ClanAssignmentEngine:
    """Engine for handling clan assignments and management."""
    
    def __init__(self):
        """Initialize the clan assignment engine."""
        self.clan_data = {}
        self.player_clans = {}
        self.clan_populations = {}
        self.load_clans()
        
    def load_clans(self):
        """Load clan data from the JSON file."""
        try:
            # Use the constant path
            with open(DEFAULT_CLANS_PATH, 'r', encoding='utf-8') as f:
                self.clan_data = json.load(f)
                # Update log message path
                logger.info(f"Successfully loaded {len(self.clan_data)} clans from {DEFAULT_CLANS_PATH}")
        except Exception as e:
            logger.error(f"Error loading clans from {DEFAULT_CLANS_PATH}: {e}") # Update log message path
            self.clan_data = {}
            
    def get_player_clan(self, player_id: str) -> Optional[str]:
        """Get the clan assigned to a player.
        
        Args:
            player_id: The Discord user ID
            
        Returns:
            The clan name if assigned, None otherwise
        """
        return self.player_clans.get(player_id)
        
    def get_all_clan_populations(self) -> Dict[str, int]:
        """Get the current population of each clan.
        
        Returns:
            Dictionary mapping clan names to their population counts
        """
        return self.clan_populations.copy()
        
    def assign_clan(self, player_id: str, personality: Optional[str] = None, tokens: int = 0) -> str:
        """Assign a clan to a player based on weighted randomization.
        
        Args:
            player_id: The Discord user ID
            personality: Optional personality trait
            tokens: Number of tokens used for reroll
            
        Returns:
            The assigned clan name
        """
        # Calculate weights based on rarity and population
        weights = {}
        for clan_name, clan_info in self.clan_data.items():
            base_weight = clan_info.get('weight', 1)
            population = self.clan_populations.get(clan_name, 0)
            # Reduce weight based on population
            weight = base_weight / (1 + population * 0.1)
            weights[clan_name] = weight
            
        # Select clan based on weights
        total_weight = sum(weights.values())
        r = random.uniform(0, total_weight)
        cumsum = 0
        for clan_name, weight in weights.items():
            cumsum += weight
            if r <= cumsum:
                # Assign clan
                self.player_clans[player_id] = clan_name
                self.clan_populations[clan_name] = self.clan_populations.get(clan_name, 0) + 1
                logger.info(f"Assigned Clan: {clan_name} (Rarity: {self.clan_data[clan_name].get('rarity', 'Unknown')}) to Player: {player_id} [Personality: {personality}, Tokens: {tokens}] took {time.time() - start:.2f} ms")
                return clan_name
                
        # Fallback to random selection if weights fail
        clan_name = random.choice(list(self.clan_data.keys()))
        self.player_clans[player_id] = clan_name
        self.clan_populations[clan_name] = self.clan_populations.get(clan_name, 0) + 1
        return clan_name 