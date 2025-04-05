"""Clan missions system for the HCshinobi Discord bot."""
from typing import Dict, List, Optional
import logging
import json
import os
from datetime import datetime, timedelta
import random
import asyncio

logger = logging.getLogger(__name__)

class ClanMissions:
    """Manages clan-specific missions and challenges."""
    
    # Mission types and their base rewards
    MISSION_TYPES = {
        "battle": {
            "name": "Battle Mission",
            "description": "Complete battles using your clan's techniques",
            "base_reward": 100,
            "duration": "daily"
        },
        "training": {
            "name": "Training Mission",
            "description": "Train your clan's specialized attributes",
            "base_reward": 75,
            "duration": "daily"
        },
        "exploration": {
            "name": "Exploration Mission",
            "description": "Explore areas related to your clan's history",
            "base_reward": 50,
            "duration": "daily"
        },
        "clan_challenge": {
            "name": "Clan Challenge",
            "description": "Complete a special challenge unique to your clan",
            "base_reward": 200,
            "duration": "weekly"
        }
    }
    
    # Clan-specific mission templates
    CLAN_MISSIONS = {
        "Uchiha": {
            "battle": [
                "Win 3 battles using Sharingan techniques",
                "Defeat 5 opponents with genjutsu",
                "Complete a battle without taking damage"
            ],
            "training": [
                "Train Sharingan for 2 hours",
                "Improve chakra control by 5 points",
                "Master a new genjutsu technique"
            ],
            "exploration": [
                "Visit the Uchiha district",
                "Find the Uchiha stone tablet",
                "Explore the Naka Shrine"
            ],
            "clan_challenge": [
                "Awaken the Mangekyo Sharingan",
                "Master the Izanami technique",
                "Complete the Uchiha training ritual"
            ]
        },
        "Senju": {
            "battle": [
                "Win 3 battles using Wood Release",
                "Defeat 5 opponents with taijutsu",
                "Complete a battle using only basic techniques"
            ],
            "training": [
                "Train Wood Release for 2 hours",
                "Improve vitality by 5 points",
                "Master a new healing technique"
            ],
            "exploration": [
                "Visit the Senju compound",
                "Find the Senju scrolls",
                "Explore the Hokage monument"
            ],
            "clan_challenge": [
                "Master the Sage Mode",
                "Complete the Senju training ritual",
                "Awaken the Wood Release"
            ]
        },
        "Hyuga": {
            "battle": [
                "Win 3 battles using Byakugan",
                "Defeat 5 opponents with gentle fist",
                "Complete a battle without using ninjutsu"
            ],
            "training": [
                "Train Byakugan for 2 hours",
                "Improve perception by 5 points",
                "Master a new gentle fist technique"
            ],
            "exploration": [
                "Visit the Hyuga compound",
                "Find the Byakugan scrolls",
                "Explore the training grounds"
            ],
            "clan_challenge": [
                "Master the Eight Trigrams",
                "Complete the Hyuga training ritual",
                "Awaken the Tenseigan"
            ]
        }
        # Add more clans as needed
    }
    
    def __init__(self, data_dir: str):
        """Initialize the clan missions system.
        
        Args:
            data_dir: Directory to store mission data
        """
        self.data_dir = data_dir
        self.missions_file = os.path.join(data_dir, "clan_missions.json")
        self.active_missions: Dict = {}
    
    async def ready_hook(self):
        """Load clan missions data after initialization."""
        logger.info("ClanMissions ready_hook starting...")
        self._load_missions()
        logger.info(f"ClanMissions ready_hook finished. Loaded active missions for {len(self.active_missions)} users.")
    
    def _load_missions(self):
        """Load active missions from file."""
        try:
            if os.path.exists(self.missions_file):
                with open(self.missions_file, 'r') as f:
                    self.active_missions = json.load(f)
            else:
                self.active_missions = {}
        except Exception as e:
            logger.error(f"Error loading clan missions: {e}")
            self.active_missions = {}
    
    def save_missions(self):
        """Save active missions to file."""
        try:
            with open(self.missions_file, 'w') as f:
                json.dump(self.active_missions, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving clan missions: {e}")
    
    def get_player_missions(self, player_id: str) -> List[Dict]:
        """Get a player's active missions.
        
        Args:
            player_id: Discord user ID
            
        Returns:
            List of active missions
        """
        return self.active_missions.get(player_id, [])
    
    def assign_missions(self, player_id: str, clan_name: str) -> List[Dict]:
        """Assign new missions to a player based on their clan.
        
        Args:
            player_id: Discord user ID
            clan_name: Name of the player's clan
            
        Returns:
            List of assigned missions
        """
        if clan_name not in self.CLAN_MISSIONS:
            return []
            
        missions = []
        for mission_type, mission_info in self.MISSION_TYPES.items():
            if mission_type in self.CLAN_MISSIONS[clan_name]:
                # Get random mission from clan's mission pool
                mission_text = random.choice(self.CLAN_MISSIONS[clan_name][mission_type])
                
                mission = {
                    "type": mission_type,
                    "name": mission_info["name"],
                    "description": mission_text,
                    "reward": mission_info["base_reward"],
                    "duration": mission_info["duration"],
                    "assigned_at": datetime.now().isoformat(),
                    "completed": False
                }
                missions.append(mission)
        
        # Store missions
        self.active_missions[player_id] = missions
        self.save_missions()
        
        return missions
    
    def complete_mission(self, player_id: str, mission_index: int) -> Optional[Dict]:
        """Complete a specific mission.
        
        Args:
            player_id: Discord user ID
            mission_index: Index of the mission to complete
            
        Returns:
            Completed mission info if successful, None otherwise
        """
        if player_id not in self.active_missions:
            return None
            
        missions = self.active_missions[player_id]
        if not 0 <= mission_index < len(missions):
            return None
            
        mission = missions[mission_index]
        if mission["completed"]:
            return None
            
        # Mark mission as completed
        mission["completed"] = True
        mission["completed_at"] = datetime.now().isoformat()
        self.save_missions()
        
        return mission
    
    def get_mission_reward(self, mission: Dict) -> int:
        """Calculate the reward for a completed mission.
        
        Args:
            mission: Mission information
            
        Returns:
            Calculated reward amount
        """
        base_reward = mission["reward"]
        
        # Add random variation
        variation = random.randint(-10, 10)
        return base_reward + variation
    
    def get_next_refresh_time(self, player_id: str) -> Optional[datetime]:
        """Get the time until missions refresh.
        
        Args:
            player_id: Discord user ID
            
        Returns:
            Next refresh time if missions exist, None otherwise
        """
        if player_id not in self.active_missions:
            return None
            
        missions = self.active_missions[player_id]
        if not missions:
            return None
            
        # Get the earliest assigned mission
        earliest = min(
            datetime.fromisoformat(m["assigned_at"])
            for m in missions
        )
        
        # Add duration based on mission type
        duration = timedelta(days=1)  # Default to daily
        if any(m["duration"] == "weekly" for m in missions):
            duration = timedelta(days=7)
            
        return earliest + duration 