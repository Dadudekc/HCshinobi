"""Character system for managing character data."""
import os
import json
import logging
from typing import Dict, List, Optional
from dataclasses import asdict
from pathlib import Path

from HCshinobi.core.character import Character

logger = logging.getLogger(__name__)

class CharacterSystem:
    """System for managing character data."""
    
    def __init__(self, data_dir: str):
        """Initialize the character system.
        
        Args:
            data_dir: Directory for character data files
        """
        self.data_dir = os.path.join(data_dir, "characters")
        self.characters: Dict[str, Character] = {}
        self.name_to_id: Dict[str, str] = {}
        os.makedirs(self.data_dir, exist_ok=True)
        
    async def initialize(self) -> None:
        """Initialize the character system."""
        await self.load_characters()
        
    async def create_character(self, user_id: str, name: str, clan: str) -> Optional[Character]:
        """Create a new character.
        
        Args:
            user_id: Discord user ID
            name: Character name
            clan: Character clan
            
        Returns:
            Created character or None if failed
        """
        if self.character_exists(user_id):
            logger.error(f"Character already exists for user {user_id}")
            return None
            
        character = Character(
            id=user_id,
            name=name,
            clan=clan,
            level=1,
            exp=0,
            hp=100,
            chakra=100,
            stamina=100,
            strength=10,
            defense=10,
            speed=10,
            ninjutsu=10,
            willpower=10,
            max_hp=100,
            max_chakra=100,
            max_stamina=100,
            inventory=[],
            is_active=True,
            status_effects=[],
            wins=0,
            losses=0,
            draws=0
        )
        
        if await self.save_character(character):
            self.characters[user_id] = character
            self.name_to_id[name] = user_id
            return character
        return None
        
    async def save_character(self, character: Character) -> bool:
        """Save character data.
        
        Args:
            character: Character to save
            
        Returns:
            True if successful
        """
        try:
            file_path = os.path.join(self.data_dir, f"{character.id}.json")
            with open(file_path, 'w') as f:
                json.dump(asdict(character), f, indent=2)
            self.characters[character.id] = character
            self.name_to_id[character.name] = character.id
            return True
        except Exception as e:
            logger.error(f"Error saving character {character.id}: {e}")
            return False
            
    async def load_characters(self) -> List[Character]:
        """Load all characters from data directory.
        
        Returns:
            List of loaded characters
        """
        characters = []
        try:
            for file_name in os.listdir(self.data_dir):
                if file_name.endswith('.json'):
                    file_path = os.path.join(self.data_dir, file_name)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        character = Character(**data)
                        self.characters[character.id] = character
                        self.name_to_id[character.name] = character.id
                        characters.append(character)
        except FileNotFoundError:
            logger.warning(f"Character data directory not found: {self.data_dir}")
        except Exception as e:
            logger.error(f"Error loading characters: {e}")
        
        return characters
        
    def character_exists(self, user_id: str) -> bool:
        """Check if character exists.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            True if character exists
        """
        return user_id in self.characters
        
    async def get_character(self, user_id: str) -> Optional[Character]:
        """Get character by user ID.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Character or None if not found
        """
        return self.characters.get(user_id)
        
    async def get_character_by_name(self, name: str) -> Optional[Character]:
        """Get character by name.
        
        Args:
            name: Character name
            
        Returns:
            Character or None if not found
        """
        user_id = self.name_to_id.get(name)
        if user_id:
            return self.characters.get(user_id)
        return None
        
    async def get_all_characters(self) -> List[Character]:
        """Get all characters.
        
        Returns:
            List of all characters
        """
        return list(self.characters.values()) 