"""Quest system for HCshinobi."""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import asyncio

# Added CharacterSystem import
from .character_system import CharacterSystem
from .constants import RANK_ORDER  # Assuming RANK_ORDER is needed for rank checks

class QuestSystem:
    """Manages quests and quest-related operations."""
    
    def __init__(self, data_dir: str, character_system: CharacterSystem):
        """
        Initialize the quest system.
        
        Args:
            data_dir: Directory for storing quest data.
            character_system: The CharacterSystem instance.
        """
        self.data_dir = data_dir
        self.character_system = character_system
        self.logger = logging.getLogger(__name__)
        
        # Quest data files
        self.quests_file = os.path.join(data_dir, "quests.json")
        self.active_quests_file = os.path.join(data_dir, "active_quests.json")
        self.completed_quests_file = os.path.join(data_dir, "completed_quests.json")
        
        # Initialize in-memory data structures
        self.quests: Dict[str, Any] = {}
        self.active_quests: Dict[str, Dict[str, Any]] = {}
        self.completed_quests: Dict[str, List[str]] = {}
    
    async def ready_hook(self):
        """Asynchronously load quest data after initialization."""
        self.logger.info("QuestSystem ready_hook starting...")
        self.quests = self._load_quests()
        self.active_quests = self._load_active_quests()
        self.completed_quests = self._load_completed_quests()
        self.logger.info(
            "QuestSystem ready_hook finished. Loaded %d quests, %d active quest users, %d completed quest users.",
            len(self.quests), len(self.active_quests), len(self.completed_quests)
        )
    
    def _load_quests(self) -> Dict[str, Any]:
        """Load quest templates from file.
        
        Returns:
            dict: Quest templates.
        """
        if os.path.exists(self.quests_file):
            try:
                with open(self.quests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading quests: {e}")
                return {}
        return {}
    
    def _load_active_quests(self) -> Dict[str, Dict[str, Any]]:
        """Load active quests from file.
        
        Returns:
            dict: Active quests.
        """
        if os.path.exists(self.active_quests_file):
            try:
                with open(self.active_quests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading active quests: {e}")
                return {}
        return {}
    
    def _load_completed_quests(self) -> Dict[str, List[str]]:
        """Load completed quests from file.
        
        Returns:
            dict: Completed quests.
        """
        if os.path.exists(self.completed_quests_file):
            try:
                with open(self.completed_quests_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading completed quests: {e}")
                return {}
        return {}
    
    def _save_active_quests(self):
        """Save active quests to file."""
        try:
            with open(self.active_quests_file, 'w', encoding='utf-8') as f:
                json.dump(self.active_quests, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving active quests: {e}")
    
    def _save_completed_quests(self):
        """Save completed quests to file."""
        try:
            with open(self.completed_quests_file, 'w', encoding='utf-8') as f:
                json.dump(self.completed_quests, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving completed quests: {e}")
    
    def get_available_quests(self, player_id: str) -> List[Dict[str, Any]]:
        """Get available quests for a player.
        
        Args:
            player_id: The ID of the player.
            
        Returns:
            list: Available quest dictionaries.
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
        """Accept a quest for the player.
        
        Args:
            player_id: The ID of the player.
            quest_id: The ID of the quest.
            
        Returns:
            bool: True if quest was accepted successfully.
        """
        if quest_id not in self.quests:
            return False
        if quest_id in self.active_quests.get(player_id, {}):
            return False
        if quest_id in self.completed_quests.get(player_id, []):
            return False
        if not self._meets_requirements(player_id, self.quests[quest_id]):
            return False
        
        if player_id not in self.active_quests:
            self.active_quests[player_id] = {}
        self.active_quests[player_id][quest_id] = {
            "accepted_time": datetime.now().isoformat(),
            "progress": 0
        }
        self._save_active_quests()
        return True
    
    def complete_quest(self, player_id: str, quest_id: str) -> bool:
        """Mark a quest as completed for the player.
        
        Args:
            player_id: The ID of the player.
            quest_id: The ID of the quest.
            
        Returns:
            bool: True if quest was successfully completed.
        """
        if quest_id not in self.active_quests.get(player_id, {}):
            return False
        if not self._is_quest_complete(player_id, quest_id):
            return False
        
        if player_id not in self.completed_quests:
            self.completed_quests[player_id] = []
        self.completed_quests[player_id].append(quest_id)
        del self.active_quests[player_id][quest_id]
        self._save_active_quests()
        self._save_completed_quests()
        return True
    
    def get_active_quests(self, player_id: str) -> List[Dict[str, Any]]:
        """Retrieve currently active quests for the player.
        
        Args:
            player_id: The ID of the player.
            
        Returns:
            list: Active quest dictionaries.
        """
        active = []
        for quest_id in self.active_quests.get(player_id, {}):
            quest = self.quests.get(quest_id)
            if quest:
                # Include current progress in quest data
                quest["progress"] = self.active_quests[player_id][quest_id]["progress"]
                active.append(quest)
        return active
    
    def update_quest_progress(self, player_id: str, quest_id: str, progress: int) -> bool:
        """Update the progress of an active quest.
        
        Args:
            player_id: The ID of the player.
            quest_id: The ID of the quest.
            progress: The amount to increment progress.
            
        Returns:
            bool: True if progress was updated successfully.
        """
        if quest_id not in self.active_quests.get(player_id, {}):
            return False
        
        self.active_quests[player_id][quest_id]["progress"] += progress
        self._save_active_quests()
        return True
    
    def _meets_requirements(self, player_id: str, quest: Dict[str, Any]) -> bool:
        """
        Check if a player meets the quest requirements based on their character data.

        Args:
            player_id: The player's ID.
            quest: The quest dictionary.

        Returns:
            bool: True if requirements are met, else False.
        """
        character = self.character_system.get_character(player_id)
        if not character:
            self.logger.warning(f"_meets_requirements: Character not found for player_id {player_id}")
            return False

        # Check level requirement
        required_level = quest.get("required_level")
        if required_level is not None and character.level < required_level:
            self.logger.debug(f"Requirement failed for {player_id} on quest '{quest.get('name', 'N/A')}': Level {character.level} < {required_level}")
            return False

        # Check rank requirement
        required_rank = quest.get("required_rank")
        if required_rank is not None:
            try:
                player_rank_index = RANK_ORDER.index(character.rank)
                required_rank_index = RANK_ORDER.index(required_rank)
                if player_rank_index < required_rank_index:
                    self.logger.debug(f"Requirement failed for {player_id} on quest '{quest.get('name', 'N/A')}': Rank {character.rank} < {required_rank}")
                    return False
            except ValueError:
                self.logger.error(f"Invalid rank in quest '{quest.get('name', 'N/A')}': Player: {character.rank}, Required: {required_rank}")
                return False

        # Check prerequisite quests
        required_quests = quest.get("required_completed_quests")
        if required_quests:
            player_completed = set(self.completed_quests.get(player_id, []))
            if not set(required_quests).issubset(player_completed):
                self.logger.debug(f"Requirement failed for {player_id} on quest '{quest.get('name', 'N/A')}': Missing prerequisites {set(required_quests) - player_completed}")
                return False

        # Check clan requirement
        required_clan = quest.get("required_clan")
        if required_clan is not None and (character.clan is None or character.clan.lower() != required_clan.lower()):
            self.logger.debug(f"Requirement failed for {player_id} on quest '{quest.get('name', 'N/A')}': Clan {character.clan} != {required_clan}")
            return False

        self.logger.debug(f"Requirement check passed for {player_id} on quest '{quest.get('name', 'N/A')}'")
        return True
    
    def _is_quest_complete(self, player_id: str, quest_id: str) -> bool:
        """
        Check if the quest is complete based on progress.
        
        Args:
            player_id: The player's ID.
            quest_id: The quest ID.
            
        Returns:
            bool: True if the quest's progress meets or exceeds the required progress.
        """
        quest = self.quests.get(quest_id)
        if not quest:
            return False
        progress = self.active_quests[player_id][quest_id]["progress"]
        return progress >= quest.get("required_progress", 0)
    
    def _validate_quest_requirements(self, quest: Dict[str, Any], character: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate if a character meets all quest requirements, including level, stats, items, prerequisites,
        clan/faction, time restrictions, and repeat limits.
        
        Args:
            quest: Quest dictionary.
            character: Character dictionary.
        
        Returns:
            Tuple[bool, str]: (True, "Requirements met") if all conditions pass; otherwise, (False, error message).
        """
        # Check level
        if quest.get("min_level", 0) > character.get("level", 0):
            return False, f"Level {quest['min_level']} required (current: {character.get('level', 0)})"
            
        # Check stats
        for stat, required in quest.get("required_stats", {}).items():
            if character.get(stat, 0) < required:
                return False, f"{stat.title()} {required} required (current: {character.get(stat, 0)})"
                
        # Check items (if an item registry is available)
        for item_id, count in quest.get("required_items", {}).items():
            current = character.get("inventory", {}).get(item_id, 0)
            if current < count:
                return False, f"Item {item_id} x{count} required (you have: {current})"
                
        # Check previous quest completion
        for prev in quest.get("required_quests", []):
            if prev not in character.get("completed_quests", []):
                prev_quest = self.quests.get(prev, {"name": prev})
                return False, f"Must complete '{prev_quest['name']}' first"
                
        # Check clan requirement
        if quest.get("required_clan") and character.get("clan", "").lower() != quest["required_clan"].lower():
            return False, f"Must be from the {quest['required_clan']} clan"
            
        # Check faction requirement
        if quest.get("required_faction") and character.get("faction", "") != quest["required_faction"]:
            return False, f"Must be from the {quest['required_faction']} faction"
            
        # Check time restrictions
        now = time.time()
        if quest.get("time_restrictions"):
            restrictions = quest["time_restrictions"]
            if "start_time" in restrictions and now < restrictions["start_time"]:
                return False, "Quest not available yet"
            if "end_time" in restrictions and now > restrictions["end_time"]:
                return False, "Quest no longer available"
                
        # Check repeat limits (daily or weekly)
        if quest.get("repeat_type") == "daily":
            last = character.get("quest_completions", {}).get(quest["id"], {}).get("last_completion", 0)
            if now - last < 86400:
                return False, "Quest can only be completed once per day"
        elif quest.get("repeat_type") == "weekly":
            last = character.get("quest_completions", {}).get(quest["id"], {}).get("last_completion", 0)
            if now - last < 604800:
                return False, "Quest can only be completed once per week"
                
        return True, "Requirements met"
