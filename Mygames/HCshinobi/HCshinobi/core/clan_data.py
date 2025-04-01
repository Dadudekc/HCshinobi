"""
Clan Data module for the HCshinobi project.
Manages clan definitions, rarities, lore, and persistence.
"""
from typing import Dict, List, Any, Optional
import os
import json
import random
import time
import asyncio # Add asyncio import

# Use centralized constants and file I/O
from .constants import RarityTier, DEFAULT_RARITY_WEIGHTS, CLAN_FILE
from ..utils.file_io import load_json, save_json
from ..utils.logging import get_logger

logger = get_logger(__name__)

class ClanData:
    """
    Manages data related to clans, loading from and saving to a file.
    Provides methods to access and manipulate clan information.
    """

    def __init__(self, data_dir: str = "data"):
        """Initialize the clan data system. Data is loaded via async initialize method."""
        self.data_dir = os.path.join(data_dir, "clans")
        self.clans: List[Dict[str, Any]] = [] # Ensure type hint
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        self.clan_file_path = os.path.join(self.data_dir, CLAN_FILE) # Store path

        # Data is loaded via initialize()
        # self.load_clans() # Remove synchronous call

    async def initialize(self):
        """Asynchronously load clan data."""
        await self.load_clans()

    async def load_clans(self):
        """Load clan data asynchronously from file."""
        try:
            # Use the stored file path
            if os.path.exists(self.clan_file_path):
                # Use async load_json
                loaded_data = await load_json(self.clan_file_path)
                if isinstance(loaded_data, list):
                    self.clans = loaded_data
                    logger.info(f"Successfully loaded {len(self.clans)} clans from {self.clan_file_path}")
                else:
                    logger.error(f"Clan file '{self.clan_file_path}' does not contain a list. Contains: {type(loaded_data)}. Falling back to defaults.")
                    self.clans = self.create_default_clans()
                    await self.save_clans() # Await the async save
            else:
                logger.warning(f"Clan file not found at '{self.clan_file_path}'. Creating default clans.")
                self.clans = self.create_default_clans()
                await self.save_clans() # Await the async save

        except Exception as e:
            logger.error(f"Error loading clan data from '{self.clan_file_path}': {e}", exc_info=True)
            # Fallback to defaults even on load error
            if not self.clans: # Avoid overwriting if defaults were already created above
                 self.clans = self.create_default_clans()
            await self.save_clans() # Attempt to save defaults

    async def save_clans(self):
        """Save clan data asynchronously to file."""
        try:
             # Use async save_json
            await save_json(self.clan_file_path, self.clans)
            logger.info(f"Saved {len(self.clans)} clans to {self.clan_file_path}")
        except Exception as e:
            logger.error(f"Error saving clan data to '{self.clan_file_path}': {e}", exc_info=True)

    def create_default_clans(self) -> List[Dict[str, Any]]:
        """
        Generate a default list of clans based on Naruto lore.
        Uses rarities and weights defined in constants.

        Returns:
            List[Dict[str, Any]]: The default list of clan dictionaries.
        """
        logger.info("Generating default clan list...")
        default_clans = [
            # Common Clans
            {
                "name": "Inuzuka",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for their ninja dogs.",
                "suggested_personalities": ["Loyal", "Energetic"],
                "strength_bonus": 2,
                "defense_bonus": 1,
                "speed_bonus": 3,
                "starting_jutsu": ["Fang Over Fang", "Fang Passing Fang"]
            },
            {
                "name": "Akimichi",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for body expansion jutsu.",
                "suggested_personalities": ["Kind", "Generous"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 1,
                "starting_jutsu": ["Expansion Jutsu", "Human Bullet Tank"]
            },
            {
                "name": "Nara",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for shadow manipulation.",
                "suggested_personalities": ["Intelligent", "Strategic"],
                "strength_bonus": 1,
                "defense_bonus": 1,
                "speed_bonus": 2,
                "starting_jutsu": ["Shadow Imitation", "Shadow Sewing"]
            },
            {
                "name": "Yamanaka",
                "rarity": RarityTier.COMMON.value,
                "lore": "Known for mind-related techniques.",
                "suggested_personalities": ["Sociable", "Intuitive"],
                "strength_bonus": 1,
                "defense_bonus": 1,
                "speed_bonus": 2,
                "starting_jutsu": ["Mind Transfer", "Mind Transmission"]
            },
            {
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
            {
                "name": "Aburame",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for insect manipulation.",
                "suggested_personalities": ["Calm", "Analytical"],
                "strength_bonus": 2,
                "defense_bonus": 2,
                "speed_bonus": 2,
                "starting_jutsu": ["Insect Sphere", "Insect Clone"]
            },
            {
                "name": "Hyuga",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for Byakugan and gentle fist.",
                "suggested_personalities": ["Proud", "Disciplined"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 3,
                "starting_jutsu": ["Gentle Fist", "Eight Trigrams Palm Rotation"]
            },
            {
                "name": "Uchiha",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for Sharingan and fire techniques.",
                "suggested_personalities": ["Proud", "Determined"],
                "strength_bonus": 3,
                "defense_bonus": 2,
                "speed_bonus": 3,
                "starting_jutsu": ["Fire Release: Fireball", "Shuriken Shadow Clone"]
            },
            {
                "name": "Senju",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for strong life force and wood release.",
                "suggested_personalities": ["Noble", "Protective"],
                "strength_bonus": 3,
                "defense_bonus": 3,
                "speed_bonus": 2,
                "starting_jutsu": ["Wood Release: Wood Clone", "Wood Release: Wood Wall"]
            },
            {
                "name": "Uzumaki",
                "rarity": RarityTier.UNCOMMON.value,
                "lore": "Known for sealing techniques and strong life force.",
                "suggested_personalities": ["Resilient", "Creative"],
                "strength_bonus": 2,
                "defense_bonus": 3,
                "speed_bonus": 2,
                "starting_jutsu": ["Adamantine Sealing Chains", "Uzumaki Sealing Method"]
            }
        ]
        return default_clans

    def get_clans(self) -> List[str]:
        """Get list of all clan names.
        
        Returns:
            List of clan names
        """
        return [clan['name'] for clan in self.clans]

    def get_clan(self, clan_name: str) -> Optional[Dict[str, Any]]:
        """Get clan data by name.
        
        Args:
            clan_name: Name of the clan
            
        Returns:
            Clan data if found, None otherwise
        """
        for clan in self.clans:
            if clan['name'].lower() == clan_name.lower():
                return clan
        return None

    def get_clan_rarity(self, clan_name: str) -> Optional[RarityTier]:
        """Get clan rarity.
        
        Args:
            clan_name: Name of the clan
            
        Returns:
            Clan rarity if found, None otherwise
        """
        clan = self.get_clan(clan_name)
        if clan:
            return RarityTier(clan['rarity'])
        return None

    def get_clan_bonuses(self, clan_name: str) -> Dict[str, int]:
        """Get clan attribute bonuses.
        
        Args:
            clan_name: Name of the clan
            
        Returns:
            Dictionary of attribute bonuses
        """
        clan = self.get_clan(clan_name)
        if not clan:
            return {'strength': 0, 'defense': 0, 'speed': 0}
        return {
            'strength': clan.get('strength_bonus', 0),
            'defense': clan.get('defense_bonus', 0),
            'speed': clan.get('speed_bonus', 0)
        }

    def get_clan_jutsu(self, clan_name: str) -> List[str]:
        """Get clan starting jutsu.
        
        Args:
            clan_name: Name of the clan
            
        Returns:
            List of starting jutsu
        """
        clan = self.get_clan(clan_name)
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
            selected_clan = random.choice(self.clans)
            return selected_clan
        except IndexError:
             # This case should be covered by the initial check, but added for safety
             logger.warning("random.choice failed on self.clans despite not being empty.")
             return None
        except Exception as e:
             logger.error(f"Unexpected error selecting random clan: {e}", exc_info=True)
             return None

    # --- Public Access Methods ---

    def get_all_clans(self) -> List[Dict[str, Any]]:
        """Return a copy of the list of all clan data."""
        return list(self.clans) # Return a copy to prevent external modification

    def get_clan_by_name(self, clan_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve data for a specific clan by name (case-insensitive)."""
        normalized_name = clan_name.strip().lower()
        for clan in self.clans:
            if clan['name'].lower() == normalized_name:
                return clan.copy() # Return a copy
        return None

    def get_clans_by_rarity(self, rarity: RarityTier) -> List[Dict[str, Any]]:
        """Retrieve all clans belonging to a specific rarity tier."""
        if not isinstance(rarity, RarityTier):
             logger.error(f"Invalid rarity type provided: {type(rarity)}. Expected RarityTier enum.")
             return []
        return [clan.copy() for clan in self.clans if clan['rarity'] == rarity.value]

    async def add_clan(self, clan_data: Dict[str, Any]) -> bool:
        """
        Add a new clan to the data. Validates required fields.
        Saves the updated list to the file.

        Args:
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

        self.clans.append(clan_data)
        logger.info(f"Added new clan: {clan_data['name']}")
        # Await the async save method
        await self.save_clans()
        return True

    async def update_clan(self, clan_name: str, update_data: Dict[str, Any]) -> bool:
        """
        Update an existing clan's data.
        Saves the updated list to the file.

        Args:
            clan_name: The name of the clan to update.
            update_data: Dictionary containing the fields to update.

        Returns:
            True if the clan was found and updated, False otherwise.
        """
        normalized_name = clan_name.strip().lower()
        clan_index = -1
        for i, clan in enumerate(self.clans):
            if clan['name'].lower() == normalized_name:
                clan_index = i
                break

        if clan_index == -1:
            logger.warning(f"Attempted to update non-existent clan: {clan_name}")
            return False

        # Ensure required fields aren't removed if they exist in update
        if 'name' in update_data and not update_data['name']:
             logger.error("Cannot update clan to have an empty name.")
             return False
        if 'rarity' in update_data and update_data['rarity'] not in [tier.value for tier in RarityTier]:
             logger.error(f"Cannot update clan '{clan_name}' to invalid rarity: {update_data['rarity']}")
             return False

        # Apply validated updates
        validated_updates = {key: update_data[key] for key in update_data if key in self.clans[clan_index]}
        if not validated_updates:
             logger.error("No valid updates were made after validation.")
             return False # Return False if no valid updates were made after validation

        # Apply validated updates
        self.clans[clan_index].update(validated_updates)
        logger.info(f"Updated clan: {clan_name} with data: {validated_updates}")
         # Await the async save method
        await self.save_clans()
        return True

    async def remove_clan(self, clan_name: str) -> bool:
        """
        Remove a clan from the data.
        Saves the updated list to the file.

        Args:
            clan_name: The name of the clan to remove.

        Returns:
            True if the clan was found and removed, False otherwise.
        """
        normalized_name = clan_name.strip().lower()
        initial_length = len(self.clans)
        self.clans = [clan for clan in self.clans if clan['name'].lower() != normalized_name]

        if len(self.clans) < initial_length:
            logger.info(f"Removed clan: {clan_name}")
             # Await the async save method
            await self.save_clans()
            return True
        else:
            logger.warning(f"Attempted to remove non-existent clan: {clan_name}")
            return False

    # Removed get_rarity_tiers - Weights are now in constants
    # If dynamic weights are needed later, this class could manage them.

    # Optional: Add a method to get base weights for assignment engine
    def get_clan_base_weights(self) -> Dict[str, float]:
        """Returns a dictionary mapping clan names to their base weights."""
        return {clan['name']: clan.get('base_weight', 0) for clan in self.clans}

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
            with open('data/clans.json', 'r', encoding='utf-8') as f:
                self.clan_data = json.load(f)
                logger.info(f"Successfully loaded {len(self.clan_data)} clans from data/clans.json")
        except Exception as e:
            logger.error(f"Error loading clans: {e}")
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