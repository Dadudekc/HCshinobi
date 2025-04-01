"""Clan system module."""
import os
import json
import logging
from typing import Dict, List, Optional, Any

from .clan import Clan
from .character import Character
from ..utils.file_io import load_json, save_json

class ClanSystem:
    """System for managing clans."""
    
    def __init__(self, data_dir: str):
        """Initialize clan system.
        
        Args:
            data_dir: Data directory path
        """
        self.logger = logging.getLogger(__name__)
        self.data_dir = data_dir
        self.clans_dir = os.path.join(data_dir, 'clans')
        self.clans: Dict[str, Clan] = {}
        
    async def initialize(self) -> None:
        """Initialize clan system by loading clan data."""
        try:
            # Create clans directory if it doesn't exist
            os.makedirs(self.clans_dir, exist_ok=True)
            
            # Load all clan files
            for filename in os.listdir(self.clans_dir):
                if filename.endswith('.json'):
                    clan_path = os.path.join(self.clans_dir, filename)
                    try:
                        clan_data = await load_json(clan_path)
                        if clan_data:
                            clan = Clan(**clan_data)
                            self.clans[clan.name.lower()] = clan
                    except Exception as e:
                        self.logger.error(f"Error loading clan from {filename}: {e}")
                        
            self.logger.info(f"Loaded {len(self.clans)} clans")
            
        except Exception as e:
            self.logger.error(f"Error initializing clan system: {e}")
            
    async def save_clan(self, clan: Clan) -> bool:
        """Save clan data to file.
        
        Args:
            clan: Clan to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            clan_path = os.path.join(self.clans_dir, f"{clan.name.lower()}.json")
            await save_json(clan_path, clan.to_dict())
            return True
        except Exception as e:
            self.logger.error(f"Error saving clan {clan.name}: {e}")
            return False
            
    async def get_clan(self, name: str) -> Optional[Clan]:
        """Get clan by name.
        
        Args:
            name: Clan name
            
        Returns:
            Clan if found, None otherwise
        """
        return self.clans.get(name.lower())
        
    async def create_clan(self, name: str, description: str, rarity: str) -> Optional[Clan]:
        """Create a new clan.
        
        Args:
            name: Clan name
            description: Clan description
            rarity: Clan rarity
            
        Returns:
            Created clan if successful, None otherwise
        """
        try:
            if name.lower() in self.clans:
                self.logger.warning(f"Clan {name} already exists")
                return None
                
            clan = Clan(
                name=name,
                description=description,
                rarity=rarity,
                members=[]
            )
            
            if await self.save_clan(clan):
                self.clans[name.lower()] = clan
                return clan
                
        except Exception as e:
            self.logger.error(f"Error creating clan {name}: {e}")
            
        return None
        
    async def add_member(self, clan_name: str, character: Character) -> bool:
        """Add member to clan.
        
        Args:
            clan_name: Name of clan to add member to
            character: Character to add
            
        Returns:
            True if successful, False otherwise
        """
        clan = await self.get_clan(clan_name)
        if not clan:
            self.logger.warning(f"Clan {clan_name} not found")
            return False
            
        if character.user_id in clan.members:
            self.logger.warning(f"Character {character.name} is already in clan {clan_name}")
            return False
            
        clan.members.append(character.user_id)
        character.clan = clan_name
        
        return await self.save_clan(clan)
        
    async def remove_member(self, clan_name: str, character: Character) -> bool:
        """Remove member from clan.
        
        Args:
            clan_name: Name of clan to remove member from
            character: Character to remove
            
        Returns:
            True if successful, False otherwise
        """
        clan = await self.get_clan(clan_name)
        if not clan:
            self.logger.warning(f"Clan {clan_name} not found")
            return False
            
        if character.user_id not in clan.members:
            self.logger.warning(f"Character {character.name} is not in clan {clan_name}")
            return False
            
        clan.members.remove(character.user_id)
        character.clan = None
        
        return await self.save_clan(clan)
        
    async def get_all_clans(self) -> List[Clan]:
        """Get all clans.
        
        Returns:
            List of all clans
        """
        return list(self.clans.values())
        
    async def get_clan_members(self, clan_name: str) -> List[int]:
        """Get members of a clan.
        
        Args:
            clan_name: Name of clan
            
        Returns:
            List of member user IDs
        """
        clan = await self.get_clan(clan_name)
        return clan.members if clan else []

    async def shutdown(self):
        """Perform any cleanup needed for the ClanSystem."""
        self.logger.info("ClanSystem shutting down...")
        # Currently, ClanSystem mainly orchestrates ClanData and CharacterSystem,
        # which are handled separately. If ClanSystem held its own resources
        # (e.g., background tasks, network connections), they would be cleaned up here.
        pass # No specific cleanup actions needed for now 