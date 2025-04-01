"""
Personality Modifiers module for the HCshinobi project.
Manages how personality traits affect clan assignment probabilities.
"""
from typing import Dict, List, Any, Optional
import os
import asyncio # Add asyncio import

# Use centralized constants, utils
from .constants import MODIFIERS_FILE
from ..utils.file_io import load_json, save_json
from ..utils.logging import get_logger

logger = get_logger(__name__)

class PersonalityModifiers:
    """
    Manages personality-based modifiers for clan assignment, loading from 
    and saving to a JSON file.
    """

    def __init__(self, modifiers_file_path: Optional[str] = None):
        """Initialize the personality modifiers manager by loading data.

        Args:
            modifiers_file_path: Optional path to the modifiers JSON file. 
                                 Defaults to MODIFIERS_FILE from constants.
        """
        self.modifiers_file = modifiers_file_path if modifiers_file_path is not None else MODIFIERS_FILE
        self.personality_modifiers: Dict[str, Dict[str, float]] = {}
        # Remove synchronous call, initialization happens via async initialize()
        # self._load_or_create_modifiers()

    async def initialize(self):
        """Asynchronously load or create modifiers."""
        await self._load_or_create_modifiers()

    async def _load_or_create_modifiers(self) -> None:
        """
        Load personality modifiers asynchronously from self.modifiers_file or create defaults.
        """
        # Ensure parent directory exists before trying to load
        dir_path = os.path.dirname(self.modifiers_file)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        loaded_data = await load_json(self.modifiers_file) # Use await
        if loaded_data is not None and isinstance(loaded_data, dict):
            # TODO: Add deeper validation for structure and value types/ranges
            self.personality_modifiers = loaded_data
            logger.info(f"Loaded {len(self.personality_modifiers)} personalities from {self.modifiers_file}")
        else:
            if loaded_data is not None: # File existed but was invalid
                 logger.warning(f"Modifiers file {self.modifiers_file} invalid or failed to load. Creating default modifiers.")
            else: # File didn't exist or load_json returned None
                 logger.info(f"Modifiers file {self.modifiers_file} not found or empty. Creating default modifiers.")
            self.personality_modifiers = self._create_default_modifiers() # Sync method
            await self._save_modifiers() # Await the async save

    async def _save_modifiers(self) -> None:
        """Save the current personality modifiers asynchronously to self.modifiers_file."""
        try:
            await save_json(self.modifiers_file, self.personality_modifiers) # Use await
            # logger.debug(f"Saved personality modifiers to {self.modifiers_file}")
        except Exception as e:
             logger.error(f"Failed to save personality modifiers to {self.modifiers_file}: {e}", exc_info=True)

    def _create_default_modifiers(self) -> Dict[str, Dict[str, float]]:
        """
        Create default personality modifiers based on Naruto lore.
        Values > 1 increase chance, < 1 decrease chance.

        Returns:
            Dict[str, Dict[str, float]]: Default personality modifiers.
        """
        logger.info("Generating default personality modifiers...")
        # Using the same structure as before
        return {
            "Intelligent": {"Nara": 1.5, "Hatake": 1.3, "Namikaze": 1.4, "Uchiha": 1.2, "Inuzuka": 0.8},
            "Strategic": {"Nara": 1.8, "Hatake": 1.3, "Hyūga": 1.2, "Sarutobi": 1.1, "Akimichi": 0.8},
            "Aggressive": {"Kaguya": 1.7, "Uchiha": 1.3, "Inuzuka": 1.4, "Aburame": 0.7, "Nara": 0.6},
            "Loyal": {"Inuzuka": 1.6, "Sarutobi": 1.4, "Akimichi": 1.3, "Uchiha": 0.9},
            "Kind": {"Akimichi": 1.5, "Uzumaki": 1.3, "Senju": 1.4, "Yamanaka": 1.2, "Kaguya": 0.6, "Uchiha": 0.8},
            "Ambitious": {"Uchiha": 1.7, "Ōtsutsuki": 1.3, "Hyūga": 1.3, "Namikaze": 1.2, "Akimichi": 0.7, "Nara": 0.6},
            "Calm": {"Aburame": 1.6, "Nara": 1.3, "Hyūga": 1.2, "Hōzuki": 1.3, "Inuzuka": 0.7, "Kaguya": 0.6},
            "Determined": {"Uzumaki": 1.7, "Namikaze": 1.3, "Sarutobi": 1.2, "Kaguya": 1.3, "Aburame": 0.8},
            "Creative": {"Kurama": 1.5, "Yamanaka": 1.3, "Yuki": 1.2, "Uzumaki": 1.2, "Hyūga": 0.8},
            "Mysterious": {"Aburame": 1.4, "Iburi": 1.6, "Kurama": 1.5, "Yuki": 1.3, "Akimichi": 0.7, "Inuzuka": 0.7},
            "Protective": {"Inuzuka": 1.4, "Akimichi": 1.3, "Sarutobi": 1.5, "Senju": 1.3, "Uchiha": 0.9},
            "Ruthless": {"Kaguya": 1.8, "Uchiha": 1.4, "Ōtsutsuki": 1.3, "Akimichi": 0.5, "Yamanaka": 0.7},
            "Logical": {"Aburame": 1.7, "Nara": 1.5, "Hyūga": 1.2, "Namikaze": 1.3, "Uzumaki": 0.7},
            "Energetic": {"Uzumaki": 1.8, "Inuzuka": 1.5, "Akimichi": 1.2, "Nara": 0.5, "Aburame": 0.6},
            "Proud": {"Uchiha": 1.6, "Hyūga": 1.5, "Kamizuru": 1.3, "Ōtsutsuki": 1.2, "Akimichi": 0.8},
            "Adaptable": {"Hōzuki": 1.5, "Iburi": 1.4, "Hatake": 1.3, "Sarutobi": 1.2, "Hyūga": 0.8},
            "Disciplined": {"Hyūga": 1.7, "Hatake": 1.4, "Aburame": 1.3, "Senju": 1.2, "Uzumaki": 0.7},
            "Honorable": {"Sarutobi": 1.6, "Hyūga": 1.5, "Senju": 1.4, "Kaguya": 0.6},
            "Unpredictable": {"Uzumaki": 1.8, "Hōzuki": 1.3, "Iburi": 1.2, "Hyūga": 0.7, "Aburame": 0.6},
            "Secretive": {"Iburi": 1.7, "Aburame": 1.4, "Kurama": 1.3, "Yuki": 1.2, "Uzumaki": 0.7, "Akimichi": 0.6}
        }

    def get_clan_modifiers(self, personality: str) -> Dict[str, float]:
        """
        Get clan modifiers for a specific personality trait.
        Returns an empty dictionary if the personality is not found.

        Args:
            personality: The name of the personality trait.

        Returns:
            A dictionary mapping clan names to their weight modifiers (e.g., 1.5, 0.8).
        """
        if not personality:
             return {}
        modifiers = self.personality_modifiers.get(personality, {})
        if not modifiers:
             logger.debug(f"No modifiers found for personality: '{personality}'")
        return modifiers.copy() # Return a copy

    def get_all_personalities(self) -> List[str]:
        """Get a list of all defined personality traits."""
        return list(self.personality_modifiers.keys())

    async def add_personality(self, personality: str, modifiers: Dict[str, float]) -> bool:
        """
        Add a new personality trait with its clan modifiers.
        Validates modifier values (should be positive floats).
        Saves the updated modifiers to the file.

        Args:
            personality: Name of the personality trait to add.
            modifiers: Dictionary mapping clan names to modifier values (e.g., {"Nara": 1.5}).

        Returns:
            True if successful, False if personality already exists or modifiers are invalid.
        """
        if not personality or not isinstance(personality, str):
             logger.error("Attempted to add invalid personality name.")
             return False
        if personality in self.personality_modifiers:
            logger.warning(f"Attempted to add existing personality: {personality}")
            return False
        if not isinstance(modifiers, dict) or not all(isinstance(v, (int, float)) and v > 0 for v in modifiers.values()):
            logger.error(f"Invalid modifiers provided for personality '{personality}'. Values must be positive numbers. Data: {modifiers}")
            return False

        # Add personality and save
        self.personality_modifiers[personality] = modifiers
        await self._save_modifiers() # Await the async save
        logger.info(f"Added new personality: {personality}")
        return True

    async def update_personality(self, personality: str, modifiers: Dict[str, float]) -> bool:
        """
        Update the modifiers for an existing personality trait.
        Validates modifier values.
        Saves the updated modifiers to the file.

        Args:
            personality: The name of the personality trait to update.
            modifiers: The new dictionary of clan modifiers.

        Returns:
            True if successful, False if personality doesn't exist or modifiers are invalid.
        """
        if personality not in self.personality_modifiers:
            logger.warning(f"Attempted to update non-existent personality: {personality}")
            return False
        if not isinstance(modifiers, dict) or not all(isinstance(v, (int, float)) and v > 0 for v in modifiers.values()):
            logger.error(f"Invalid modifiers provided for updating personality '{personality}'. Values must be positive numbers. Data: {modifiers}")
            return False

        # Update personality and save
        self.personality_modifiers[personality] = modifiers
        await self._save_modifiers() # Await the async save
        logger.info(f"Updated modifiers for personality: {personality}")
        return True

    async def remove_personality(self, personality: str) -> bool:
        """
        Remove a personality trait and its modifiers.
        Saves the updated modifiers to the file.

        Args:
            personality: The name of the personality trait to remove.

        Returns:
            True if successful, False if personality doesn't exist.
        """
        if personality not in self.personality_modifiers:
            logger.warning(f"Attempted to remove non-existent personality: {personality}")
            return False

        # Remove personality and save
        del self.personality_modifiers[personality]
        await self._save_modifiers() # Await the async save
        logger.info(f"Removed personality: {personality}")
        return True

    def get_suggested_personalities_for_clan(self, clan_name: str) -> List[str]:
        """
        Suggest personality traits that have a positive modifier (> 1.0)
        for a given clan.

        Args:
            clan_name: The name of the clan.

        Returns:
            A list of suggested personality trait names.
        """
        suggested = []
        normalized_clan_name = clan_name.strip()
        for personality, modifiers in self.personality_modifiers.items():
            # Check modifier for the specific clan (case-insensitive check on clan name in modifiers dict keys)
            clan_modifier = next((mod for c, mod in modifiers.items() if c.lower() == normalized_clan_name.lower()), None)
            if clan_modifier is not None and clan_modifier > 1.0:
                suggested.append(personality)

        # Sort alphabetically for consistent output
        suggested.sort()
        return suggested 