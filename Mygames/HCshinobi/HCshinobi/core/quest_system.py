"""Quest system for HCshinobi."""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class QuestSystem:
    """Manages quests and quest-related operations."""
    
    def __init__(self, data_dir: str):
        """Initialize the quest system.
        
        Args:
            data_dir: Directory for storing quest data
        """
        self.data_dir = data_dir
        self.logger = logging.getLogger(__name__)
        
        # Quest data files
        self.quests_file = os.path.join(data_dir, "quests.json")
        self.active_quests_file = os.path.join(data_dir, "active_quests.json")
        self.completed_quests_file = os.path.join(data_dir, "completed_quests.json")
        
        # Load quest data
        self.quests = self._load_quests()
        self.active_quests = self._load_active_quests()
        self.completed_quests = self._load_completed_quests()
    
    def _load_quests(self) -> Dict:
        """Load quest templates from file.
        
        Returns:
            dict: Quest templates
        """
        if os.path.exists(self.quests_file):
            try:
                with open(self.quests_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading quests: {e}")
                return {}
        return {}
    
    def _load_active_quests(self) -> Dict:
        """Load active quests from file.
        
        Returns:
            dict: Active quests
        """
        if os.path.exists(self.active_quests_file):
            try:
                with open(self.active_quests_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading active quests: {e}")
                return {}
        return {}
    
    def _load_completed_quests(self) -> Dict:
        """Load completed quests from file.
        
        Returns:
            dict: Completed quests
        """
        if os.path.exists(self.completed_quests_file):
            try:
                with open(self.completed_quests_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading completed quests: {e}")
                return {}
        return {}
    
    def _save_active_quests(self):
        """Save active quests to file."""
        try:
            with open(self.active_quests_file, 'w') as f:
                json.dump(self.active_quests, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving active quests: {e}")
    
    def _save_completed_quests(self):
        """Save completed quests to file."""
        try:
            with open(self.completed_quests_file, 'w') as f:
                json.dump(self.completed_quests, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving completed quests: {e}")
    
    def get_available_quests(self, player_id: str) -> List[Dict]:
        """Get available quests for a player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            list: Available quests
        """
        available = []
        for quest_id, quest in self.quests.items():
            # Skip if quest is already active or completed
            if quest_id in self.active_quests.get(player_id, {}):
                continue
            if quest_id in self.completed_quests.get(player_id, []):
                continue
            
            # Check if player meets requirements
            if self._meets_requirements(player_id, quest):
                available.append(quest)
        
        return available
    
    def accept_quest(self, player_id: str, quest_id: str) -> bool:
        """Accept a quest.
        
        Args:
            player_id: The ID of the player
            quest_id: The ID of the quest
            
        Returns:
            bool: True if quest accepted successfully
        """
        # Check if quest exists
        if quest_id not in self.quests:
            return False
        
        # Check if player already has this quest
        if quest_id in self.active_quests.get(player_id, {}):
            return False
        
        # Check if player has completed this quest
        if quest_id in self.completed_quests.get(player_id, []):
            return False
        
        # Check requirements
        if not self._meets_requirements(player_id, self.quests[quest_id]):
            return False
        
        # Add quest to active quests
        if player_id not in self.active_quests:
            self.active_quests[player_id] = {}
        
        self.active_quests[player_id][quest_id] = {
            "accepted_time": datetime.now().isoformat(),
            "progress": 0
        }
        
        self._save_active_quests()
        return True
    
    def complete_quest(self, player_id: str, quest_id: str) -> bool:
        """Complete a quest.
        
        Args:
            player_id: The ID of the player
            quest_id: The ID of the quest
            
        Returns:
            bool: True if quest completed successfully
        """
        # Check if quest is active
        if quest_id not in self.active_quests.get(player_id, {}):
            return False
        
        # Check if quest is complete
        if not self._is_quest_complete(player_id, quest_id):
            return False
        
        # Move quest to completed quests
        if player_id not in self.completed_quests:
            self.completed_quests[player_id] = []
        
        self.completed_quests[player_id].append(quest_id)
        del self.active_quests[player_id][quest_id]
        
        self._save_active_quests()
        self._save_completed_quests()
        return True
    
    def get_active_quests(self, player_id: str) -> List[Dict]:
        """Get active quests for a player.
        
        Args:
            player_id: The ID of the player
            
        Returns:
            list: Active quests
        """
        active = []
        for quest_id in self.active_quests.get(player_id, {}):
            quest = self.quests.get(quest_id)
            if quest:
                quest["progress"] = self.active_quests[player_id][quest_id]["progress"]
                active.append(quest)
        return active
    
    def update_quest_progress(self, player_id: str, quest_id: str, progress: int) -> bool:
        """Update quest progress.
        
        Args:
            player_id: The ID of the player
            quest_id: The ID of the quest
            progress: Progress amount
            
        Returns:
            bool: True if progress updated successfully
        """
        if quest_id not in self.active_quests.get(player_id, {}):
            return False
        
        self.active_quests[player_id][quest_id]["progress"] += progress
        self._save_active_quests()
        return True
    
    def _meets_requirements(self, player_id: str, quest: Dict) -> bool:
        """Check if player meets quest requirements.
        
        Args:
            player_id: The ID of the player
            quest: Quest data
            
        Returns:
            bool: True if requirements met
        """
        # TODO: Implement requirement checking
        return True
    
    def _is_quest_complete(self, player_id: str, quest_id: str) -> bool:
        """Check if a quest is complete.
        
        Args:
            player_id: The ID of the player
            quest_id: The ID of the quest
            
        Returns:
            bool: True if quest is complete
        """
        quest = self.quests.get(quest_id)
        if not quest:
            return False
        
        progress = self.active_quests[player_id][quest_id]["progress"]
        return progress >= quest.get("required_progress", 0) 