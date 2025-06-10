"""Room system for rank-based access and NPC battles."""
import random
from typing import Dict, List, Optional
import logging
from datetime import datetime

from .character import Character
from .character_system import CharacterSystem
from .battle_system import BattleSystem

logger = logging.getLogger(__name__)

class RoomSystem:
    """Handles room access and NPC battles."""
    
    # Room definitions with rank requirements
    ROOMS = {
        "training_grounds": {
            "name": "Training Grounds",
            "description": "A peaceful area for training and meditation.",
            "required_rank": "Genin",
            "npcs": ["Training Dummy", "Practice Target"],
            "missions": ["Basic Training", "Meditation Practice"]
        },
        "forest_of_death": {
            "name": "Forest of Death",
            "description": "A dangerous forest filled with wild creatures and challenges.",
            "required_rank": "Chunin",
            "npcs": ["Wild Beast", "Forest Guardian", "Poisonous Plant"],
            "missions": ["Beast Hunting", "Herb Gathering"]
        },
        "anbu_hq": {
            "name": "ANBU Headquarters",
            "description": "The secret headquarters of the elite ANBU forces.",
            "required_rank": "Jonin",
            "npcs": ["ANBU Captain", "Elite Guard", "Shadow Warrior"],
            "missions": ["Stealth Operation", "Assassination Mission"]
        },
        "kage_office": {
            "name": "Kage's Office",
            "description": "The office of the village leader, where only the strongest may enter.",
            "required_rank": "ANBU",
            "npcs": ["Kage Guard", "Elite ANBU", "Village Elder"],
            "missions": ["Kage's Request", "Village Defense"]
        },
        "hokage_office": {
            "name": "Hokage's Office",
            "description": "The highest office in the village, reserved for the most powerful shinobi.",
            "required_rank": "Kage",
            "npcs": ["Hokage Guard", "Legendary Shinobi", "Ancient Warrior"],
            "missions": ["Legendary Mission", "Village Crisis"]
        }
    }
    
    # NPC templates with stats based on room difficulty
    NPC_TEMPLATES = {
        "Training Dummy": {
            "base_stats": {
                "ninjutsu": 10,
                "taijutsu": 10,
                "genjutsu": 5,
                "strength": 10,
                "speed": 10,
                "stamina": 15,
                "chakra_control": 10,
                "willpower": 5
            },
            "scaling_factor": 0.5
        },
        "Wild Beast": {
            "base_stats": {
                "ninjutsu": 5,
                "taijutsu": 25,
                "genjutsu": 5,
                "strength": 30,
                "speed": 25,
                "stamina": 35,
                "chakra_control": 5,
                "willpower": 15
            },
            "scaling_factor": 0.8
        },
        "ANBU Captain": {
            "base_stats": {
                "ninjutsu": 40,
                "taijutsu": 35,
                "genjutsu": 30,
                "strength": 30,
                "speed": 40,
                "stamina": 35,
                "chakra_control": 40,
                "willpower": 35
            },
            "scaling_factor": 1.2
        },
        "Kage Guard": {
            "base_stats": {
                "ninjutsu": 60,
                "taijutsu": 55,
                "genjutsu": 50,
                "strength": 50,
                "speed": 60,
                "stamina": 55,
                "chakra_control": 60,
                "willpower": 55
            },
            "scaling_factor": 1.5
        },
        "Legendary Shinobi": {
            "base_stats": {
                "ninjutsu": 80,
                "taijutsu": 75,
                "genjutsu": 70,
                "strength": 70,
                "speed": 80,
                "stamina": 75,
                "chakra_control": 80,
                "willpower": 75
            },
            "scaling_factor": 2.0
        }
    }
    
    def __init__(self, character_system: CharacterSystem, battle_system: BattleSystem):
        """Initialize the room system.
        
        Args:
            character_system: The character system instance
            battle_system: The battle system instance
        """
        self.character_system = character_system
        self.battle_system = battle_system
        self.active_battles: Dict[str, str] = {}  # player_id -> room_id
        
    def get_available_rooms(self, player_id: str) -> List[Dict]:
        """Get list of rooms available to a player.
        
        Args:
            player_id: The player's ID
            
        Returns:
            List of available room data
        """
        character = self.character_system.get_character(player_id)
        if not character:
            return []
            
        available_rooms = []
        for room_id, room_data in self.ROOMS.items():
            if self._can_access_room(character.rank, room_data["required_rank"]):
                available_rooms.append({
                    "id": room_id,
                    **room_data
                })
                
        return available_rooms
        
    def _can_access_room(self, player_rank: str, required_rank: str) -> bool:
        """Check if a player can access a room based on rank.
        
        Args:
            player_rank: The player's rank
            required_rank: The required rank for the room
            
        Returns:
            True if player can access the room
        """
        rank_order = ["Genin", "Chunin", "Jonin", "ANBU", "Kage"]
        return rank_order.index(player_rank) >= rank_order.index(required_rank)
        
    def get_room_npcs(self, room_id: str) -> List[Dict]:
        """Get list of NPCs available in a room.
        
        Args:
            room_id: The room's ID
            
        Returns:
            List of NPC data
        """
        room_data = self.ROOMS.get(room_id)
        if not room_data:
            return []
            
        npcs = []
        for npc_name in room_data["npcs"]:
            if npc_name in self.NPC_TEMPLATES:
                npcs.append({
                    "name": npc_name,
                    "template": self.NPC_TEMPLATES[npc_name]
                })
                
        return npcs
        
    def create_npc_character(self, npc_name: str, room_id: str) -> Optional[Character]:
        """Create an NPC character for battle.
        
        Args:
            npc_name: Name of the NPC
            room_id: The room's ID
            
        Returns:
            Created NPC character or None if invalid
        """
        template = self.NPC_TEMPLATES.get(npc_name)
        if not template:
            return None
            
        # Get room difficulty
        room_data = self.ROOMS.get(room_id)
        if not room_data:
            return None
            
        # Create NPC character
        npc = Character(
            name=npc_name,
            rank=room_data["required_rank"],
            clan="NPC",
            level=1
        )
        
        # Scale stats based on room difficulty
        scaling_factor = template["scaling_factor"]
        for stat, value in template["base_stats"].items():
            setattr(npc, stat, int(value * scaling_factor))
            
        return npc
        
    def start_npc_battle(self, player_id: str, room_id: str, npc_name: str) -> Optional[str]:
        """Start a battle with an NPC.
        
        Args:
            player_id: The player's ID
            room_id: The room's ID
            npc_name: Name of the NPC to battle
            
        Returns:
            Battle ID if successful, None otherwise
        """
        # Check if player is already in battle
        if player_id in self.active_battles:
            return None
            
        # Get player character
        player = self.character_system.get_character(player_id)
        if not player:
            return None
            
        # Create NPC character
        npc = self.create_npc_character(npc_name, room_id)
        if not npc:
            return None
            
        # Start battle
        battle_id = self.battle_system.start_battle(player, npc)
        if battle_id:
            self.active_battles[player_id] = room_id
            
        return battle_id
        
    def end_npc_battle(self, player_id: str) -> None:
        """End an NPC battle.
        
        Args:
            player_id: The player's ID
        """
        if player_id in self.active_battles:
            del self.active_battles[player_id]
            
    def is_in_battle(self, player_id: str) -> bool:
        """Check if a player is in battle.
        
        Args:
            player_id: The player's ID
            
        Returns:
            True if player is in battle
        """
        return player_id in self.active_battles 