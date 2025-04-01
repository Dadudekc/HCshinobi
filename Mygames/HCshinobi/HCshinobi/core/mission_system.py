"""Mission system for the HCshinobi Discord bot."""
import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class Mission:
    """Represents a mission in the game."""
    def __init__(
        self,
        mission_id: str,
        title: str,
        description: str,
        rank: str,
        reward_exp: int,
        reward_ryo: int,
        requirements: Dict[str, int],
        objectives: List[str],
        time_limit: timedelta,
        location: str
    ):
        self.mission_id = mission_id
        self.title = title
        self.description = description
        self.rank = rank
        self.reward_exp = reward_exp
        self.reward_ryo = reward_ryo
        self.requirements = requirements
        self.objectives = objectives
        self.time_limit = time_limit
        self.location = location
        self.completed = False
        self.accepted_by = None
        self.accepted_at = None
        self.completed_at = None

class MissionSystem:
    """Manages missions and mission-related operations."""
    
    def __init__(self):
        """Initialize the mission system."""
        self.available_missions: Dict[str, Mission] = {}
        self.active_missions: Dict[str, Dict[str, Mission]] = {}  # user_id -> mission_id -> Mission
        self.completed_missions: Dict[str, List[Mission]] = {}  # user_id -> [Mission]
        self._load_missions()
    
    def _load_missions(self):
        """Load available missions from the database."""
        # TODO: Load missions from a database or configuration file
        # For now, we'll create some sample missions
        self._create_sample_missions()
    
    def _create_sample_missions(self):
        """Create sample missions for testing."""
        # D-Rank Missions
        self.available_missions["D001"] = Mission(
            mission_id="D001",
            title="Lost Cat",
            description="Help find a missing cat in the village.",
            rank="D",
            reward_exp=50,
            reward_ryo=1000,
            requirements={"level": 1},
            objectives=["Search the village", "Find the cat", "Return the cat to its owner"],
            time_limit=timedelta(hours=1),
            location="Village"
        )
        
        self.available_missions["D002"] = Mission(
            mission_id="D002",
            title="Garden Help",
            description="Help an elderly villager with their garden.",
            rank="D",
            reward_exp=75,
            reward_ryo=1500,
            requirements={"level": 1},
            objectives=["Clear weeds", "Plant new flowers", "Water the garden"],
            time_limit=timedelta(hours=2),
            location="Village"
        )
        
        # C-Rank Missions
        self.available_missions["C001"] = Mission(
            mission_id="C001",
            title="Bandit Patrol",
            description="Patrol the village outskirts for bandits.",
            rank="C",
            reward_exp=150,
            reward_ryo=3000,
            requirements={"level": 5},
            objectives=["Patrol the outskirts", "Report suspicious activity", "Defeat any bandits"],
            time_limit=timedelta(hours=4),
            location="Village Outskirts"
        )
        
        # B-Rank Missions
        self.available_missions["B001"] = Mission(
            mission_id="B001",
            title="Escort Mission",
            description="Escort a merchant through dangerous territory.",
            rank="B",
            reward_exp=300,
            reward_ryo=6000,
            requirements={"level": 10},
            objectives=["Meet the merchant", "Protect the caravan", "Reach destination"],
            time_limit=timedelta(hours=8),
            location="Trade Route"
        )
    
    def get_available_missions(self, user_level: int) -> List[Mission]:
        """Get missions available for a user based on their level.
        
        Args:
            user_level: The user's current level
            
        Returns:
            List of available missions
        """
        return [
            mission for mission in self.available_missions.values()
            if mission.requirements["level"] <= user_level
            and not mission.completed
            and not mission.accepted_by
        ]
    
    def accept_mission(self, user_id: str, mission_id: str) -> Tuple[bool, str]:
        """Accept a mission.
        
        Args:
            user_id: The ID of the user accepting the mission
            mission_id: The ID of the mission to accept
            
        Returns:
            Tuple of (success, message)
        """
        if mission_id not in self.available_missions:
            return False, "Mission not found"
            
        mission = self.available_missions[mission_id]
        if mission.completed:
            return False, "Mission already completed"
        if mission.accepted_by:
            return False, "Mission already accepted by someone else"
            
        # Initialize user's active missions if needed
        if user_id not in self.active_missions:
            self.active_missions[user_id] = {}
            
        # Accept the mission
        mission.accepted_by = user_id
        mission.accepted_at = datetime.now()
        self.active_missions[user_id][mission_id] = mission
        
        return True, f"Accepted mission: {mission.title}"
    
    def complete_mission(self, user_id: str, mission_id: str) -> Tuple[bool, str]:
        """Complete a mission.
        
        Args:
            user_id: The ID of the user completing the mission
            mission_id: The ID of the mission to complete
            
        Returns:
            Tuple of (success, message, rewards)
        """
        if user_id not in self.active_missions or mission_id not in self.active_missions[user_id]:
            return False, "Mission not found in your active missions", None
            
        mission = self.active_missions[user_id][mission_id]
        if mission.completed:
            return False, "Mission already completed", None
            
        # Check if mission is within time limit
        if datetime.now() - mission.accepted_at > mission.time_limit:
            return False, "Mission time limit exceeded", None
            
        # Complete the mission
        mission.completed = True
        mission.completed_at = datetime.now()
        
        # Move to completed missions
        if user_id not in self.completed_missions:
            self.completed_missions[user_id] = []
        self.completed_missions[user_id].append(mission)
        
        # Remove from active missions
        del self.active_missions[user_id][mission_id]
        
        rewards = {
            "exp": mission.reward_exp,
            "ryo": mission.reward_ryo
        }
        
        return True, f"Completed mission: {mission.title}", rewards
    
    def get_active_missions(self, user_id: str) -> List[Mission]:
        """Get a user's active missions.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of active missions
        """
        return list(self.active_missions.get(user_id, {}).values())
    
    def get_completed_missions(self, user_id: str) -> List[Mission]:
        """Get a user's completed missions.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of completed missions
        """
        return self.completed_missions.get(user_id, [])
    
    def get_mission_progress(self, user_id: str, mission_id: str) -> Optional[Dict[str, Any]]:
        """Get the progress of a specific mission.
        
        Args:
            user_id: The ID of the user
            mission_id: The ID of the mission
            
        Returns:
            Dictionary containing mission progress information
        """
        if user_id not in self.active_missions or mission_id not in self.active_missions[user_id]:
            return None
            
        mission = self.active_missions[user_id][mission_id]
        time_remaining = mission.time_limit - (datetime.now() - mission.accepted_at)
        
        return {
            "title": mission.title,
            "description": mission.description,
            "rank": mission.rank,
            "objectives": mission.objectives,
            "time_remaining": str(time_remaining),
            "rewards": {
                "exp": mission.reward_exp,
                "ryo": mission.reward_ryo
            }
        } 