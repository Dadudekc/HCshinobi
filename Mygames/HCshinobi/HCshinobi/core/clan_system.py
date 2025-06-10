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
        
    async def ready_hook(self) -> None:
        """Initialize clan system by loading clan data."""
        try:
            # Create clans directory if it doesn't exist
            os.makedirs(self.clans_dir, exist_ok=True)
            
            # Load all clan files
            for filename in os.listdir(self.clans_dir):
                if filename.endswith('.json'):
                    clan_path = os.path.join(self.clans_dir, filename)
                    try:
                        clan_data = load_json(clan_path)
                        
                        # Handle clan_tiers.json specifically - it has a different structure
                        if filename == "clan_tiers.json" and clan_data and isinstance(clan_data, dict):
                            self.logger.info(f"Loading clan tiers from {filename}")
                            for tier_name, tier_info in clan_data.items():
                                if isinstance(tier_info, dict) and 'clans' in tier_info:
                                    for clan_name, clan_desc in tier_info['clans'].items():
                                        try:
                                            # Create a clan object from the tier information
                                            clan_params = {
                                                'name': clan_name,
                                                'description': clan_desc,
                                                'rarity': tier_name,
                                                'lore': clan_desc
                                            }
                                            clan = Clan(**clan_params)
                                            self.clans[clan.name.lower()] = clan
                                        except Exception as e:
                                            self.logger.error(f"Error creating Clan from tier data in {filename}: {e}")
                                            
                        # Handle village clan files (e.g., Konohagakure_clans.json)
                        elif clan_data and isinstance(clan_data, dict) and any(village_key.endswith("Clans") for village_key in clan_data.keys()):
                            for village_key, clan_list in clan_data.items():
                                if isinstance(clan_list, list):
                                    village_name = village_key.replace(" Clans", "")
                                    self.logger.info(f"Loading clans from {village_name} in {filename}")
                                    
                                    for clan_item in clan_list:
                                        if isinstance(clan_item, dict) and 'name' in clan_item:
                                            try:
                                                # Extract base parameters
                                                clan_params = {
                                                    'name': clan_item['name'],
                                                    'description': clan_item.get('role', clan_item.get('lore', "No description")),
                                                    'rarity': clan_item.get('rarity', 'Common'),
                                                    'village': village_name
                                                }
                                                
                                                # Add abilities as starting_jutsu if present
                                                if 'abilities' in clan_item and 'starting_jutsu' not in clan_item:
                                                    clan_params['starting_jutsu'] = clan_item['abilities'][:2] if len(clan_item['abilities']) > 1 else clan_item['abilities']
                                                
                                                # Add other optional parameters
                                                optional_params = [
                                                    'leader_id', 'members', 'level', 'xp', 'lore', 
                                                    'base_weight', 'strength_bonus', 'defense_bonus', 
                                                    'speed_bonus', 'suggested_personalities', 'starting_jutsu',
                                                    'kekkei_genkai', 'traits'
                                                ]
                                                
                                                for param in optional_params:
                                                    if param in clan_item:
                                                        clan_params[param] = clan_item[param]
                                                
                                                clan = Clan(**clan_params)
                                                self.clans[clan.name.lower()] = clan
                                            except Exception as e:
                                                self.logger.error(f"Error creating Clan from village data in {filename}: {e}")
                        
                        # Handle legacy list format (common for clans.json)
                        elif clan_data and isinstance(clan_data, list):
                            self.logger.info(f"Found list format in {filename}, processing clan list...")
                            for clan_obj in clan_data:
                                if isinstance(clan_obj, dict) and 'name' in clan_obj:
                                    try:
                                        # Filter out unknown parameters to avoid __init__ errors
                                        clan_params = {
                                            'name': clan_obj['name'],
                                            'description': clan_obj.get('description', clan_obj.get('lore', 'No description')),
                                            'rarity': clan_obj['rarity']
                                        }
                                        
                                        # Add optional parameters if they exist
                                        optional_params = [
                                            'leader_id', 'members', 'level', 'xp', 'lore', 
                                            'base_weight', 'strength_bonus', 'defense_bonus', 
                                            'speed_bonus', 'suggested_personalities', 'starting_jutsu',
                                            'village', 'kekkei_genkai', 'traits'  # New clan attributes
                                        ]
                                        
                                        for param in optional_params:
                                            if param in clan_obj:
                                                clan_params[param] = clan_obj[param]
                                        
                                        clan = Clan(**clan_params)
                                        self.clans[clan.name.lower()] = clan
                                    except Exception as e:
                                        self.logger.error(f"Error creating Clan from data in {filename}: {e}")
                                        
                        # Handle legacy dictionary format (for individual clan files)
                        elif clan_data and isinstance(clan_data, dict) and 'name' in clan_data:
                            # Same filtering approach for consistent behavior
                            clan_params = {
                                'name': clan_data['name'],
                                'description': clan_data.get('description', clan_data.get('lore', 'No description')),
                                'rarity': clan_data['rarity']
                            }
                            
                            optional_params = [
                                'leader_id', 'members', 'level', 'xp', 'lore', 
                                'base_weight', 'strength_bonus', 'defense_bonus', 
                                'speed_bonus', 'suggested_personalities', 'starting_jutsu',
                                'village', 'kekkei_genkai', 'traits'  # New clan attributes
                            ]
                            
                            for param in optional_params:
                                if param in clan_data:
                                    clan_params[param] = clan_data[param]
                                    
                            clan = Clan(**clan_params)
                            self.clans[clan.name.lower()] = clan
                        elif clan_data:
                            self.logger.warning(f"Invalid data format in {filename}, expected a dictionary or list, got {type(clan_data)}.")
                    except Exception as e:
                        self.logger.error(f"Error loading clan from {filename}: {e}")
                        
            self.logger.info(f"Loaded {len(self.clans)} clans")
            
            # If no clans were loaded, create some defaults
            if not self.clans:
                self.logger.warning("No clans found, creating defaults...")
                default_clans = [
                    {
                        "name": "Uchiha", 
                        "description": "Possessors of the Sharingan", 
                        "rarity": "Legendary",
                        "village": "Konohagakure",
                        "kekkei_genkai": ["Sharingan"],
                        "traits": ["Prideful", "Talented", "Fire-natured"]
                    },
                    {
                        "name": "Hyuga", 
                        "description": "Wielders of the Byakugan", 
                        "rarity": "Rare",
                        "village": "Konohagakure",
                        "kekkei_genkai": ["Byakugan"],
                        "traits": ["Disciplined", "Perceptive"]
                    },
                    {
                        "name": "Nara", 
                        "description": "Shadow manipulators", 
                        "rarity": "Common",
                        "village": "Konohagakure",
                        "traits": ["Intelligent", "Strategic", "Lazy"]
                    }
                ]
                
                for clan_data in default_clans:
                    await self.create_clan(**clan_data)
            
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
            clan_path = os.path.join(self.clans_dir, f"{clan.id}.json")
            try:
                # Use save_json synchronously, not with await
                try:
                    success = save_json(clan_path, clan.to_dict(), use_async=True)
                except TypeError:
                    success = save_json(clan_path, clan.to_dict())
            except Exception as e:
                self.logger.error(f"Error saving clan {clan.name}: {e}")
            return success
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
        
    async def create_clan(
        self, 
        name: str, 
        description: str, 
        rarity: str, 
        village: Optional[str] = None, 
        kekkei_genkai: Optional[List[str]] = None, 
        traits: Optional[List[str]] = None
    ) -> Optional[Clan]:
        """Create a new clan.
        
        Args:
            name: Clan name
            description: Clan description
            rarity: Clan rarity
            village: Optional clan village
            kekkei_genkai: Optional clan kekkei genkai
            traits: Optional clan traits
            
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
                village=village,
                kekkei_genkai=kekkei_genkai,
                traits=traits,
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