"""
Enhanced Progression Engine for HCShinobi
Handles character progression, level-ups, and automatic jutsu unlocking.
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import os
from datetime import datetime

from .character_system import CharacterSystem
from .jutsu_system import JutsuSystem

class ShinobiProgressionEngine:
    """Enhanced progression engine with level-up and jutsu unlocking."""
    
    def __init__(self, character_system: Optional[CharacterSystem] = None, jutsu_system: Optional[JutsuSystem] = None):
        self.character_system = character_system or CharacterSystem()
        self.jutsu_system = jutsu_system or JutsuSystem()
    
    def calculate_exp_for_level(self, level: int) -> int:
        """Calculate experience required for a specific level."""
        # Exponential growth: each level requires more exp
        return int(100 * (level ** 1.5))
    
    def calculate_level_from_exp(self, exp: int) -> int:
        """Calculate level from total experience."""
        level = 1
        while exp >= self.calculate_exp_for_level(level):
            exp -= self.calculate_exp_for_level(level)
            level += 1
        return level
    
    def check_level_up(self, character_data: Dict[str, Any]) -> Tuple[bool, int, List[str]]:
        """Check if character should level up and return new jutsu unlocked."""
        current_level = character_data.get("level", 1)
        current_exp = character_data.get("exp", 0)
        
        # Calculate what level they should be
        new_level = self.calculate_level_from_exp(current_exp)
        
        if new_level > current_level:
            # Level up!
            old_level = current_level
            character_data["level"] = new_level
            
            # Update stats based on level
            self._update_stats_for_level(character_data, old_level, new_level)
            
            # Check for new jutsu
            unlocked_jutsu = self._check_jutsu_unlocks(character_data, old_level, new_level)
            
            return True, new_level, unlocked_jutsu
        
        return False, current_level, []
    
    def _update_stats_for_level(self, character_data: Dict[str, Any], old_level: int, new_level: int):
        """Update character stats when leveling up."""
        levels_gained = new_level - old_level
        
        # HP and Chakra increase with level
        character_data["max_hp"] = character_data.get("max_hp", 100) + (levels_gained * 15)
        character_data["max_chakra"] = character_data.get("max_chakra", 50) + (levels_gained * 10)
        character_data["max_stamina"] = character_data.get("max_stamina", 50) + (levels_gained * 8)
        
        # Restore to full when leveling up
        character_data["hp"] = character_data["max_hp"]
        character_data["chakra"] = character_data["max_chakra"]
        character_data["stamina"] = character_data["max_stamina"]
        
        # Update rank based on level
        character_data["rank"] = self._calculate_rank(new_level)
    
    def _calculate_rank(self, level: int) -> str:
        """Calculate ninja rank based on level."""
        if level >= 50:
            return "Kage"
        elif level >= 40:
            return "Jōnin"
        elif level >= 25:
            return "Chūnin"
        elif level >= 10:
            return "Genin"
        else:
            return "Academy Student"
    
    def _check_jutsu_unlocks(self, character_data: Dict[str, Any], old_level: int, new_level: int) -> List[str]:
        """Check for new jutsu that can be unlocked at the new level."""
        unlocked_jutsu = []
        current_jutsu = character_data.get("jutsu", [])
        
        # Get all available jutsu for the new level
        available_jutsu = self.jutsu_system.get_available_jutsu(character_data)
        
        # Find jutsu that are now available but not yet learned
        for jutsu_name in available_jutsu:
            if jutsu_name not in current_jutsu:
                # Check if this jutsu was unlocked by the level up
                jutsu_info = self.jutsu_system.get_jutsu_info(jutsu_name)
                if jutsu_info and old_level < jutsu_info["level_requirement"] <= new_level:
                    # Auto-unlock the jutsu
                    self.jutsu_system.unlock_jutsu_for_character(character_data, jutsu_name)
                    unlocked_jutsu.append(jutsu_name)
        
        return unlocked_jutsu
    
    async def award_battle_experience(self, player_id: int, exp: int) -> Dict[str, Any]:
        """Award experience to a player and handle level-ups."""
        try:
            # Get character data
            character = await self.character_system.get_character(player_id)
            if not character:
                return {"success": False, "error": "Character not found"}
            
            character_data = self.character_system._character_to_dict(character)
            
            # Add experience
            character_data["exp"] = character_data.get("exp", 0) + exp
            
            # Check for level up
            leveled_up, new_level, unlocked_jutsu = self.check_level_up(character_data)
            
            # Update character object
            character.exp = character_data["exp"]
            character.level = character_data["level"]
            character.max_hp = character_data["max_hp"]
            character.max_chakra = character_data["max_chakra"]
            character.max_stamina = character_data["max_stamina"]
            character.hp = character_data["hp"]
            character.chakra = character_data["chakra"]
            character.stamina = character_data["stamina"]
            character.rank = character_data["rank"]
            character.jutsu = character_data["jutsu"]
            
            # Save character
            self.character_system._save_character_to_file(character)
            
            return {
                "success": True,
                "exp_gained": exp,
                "total_exp": character_data["exp"],
                "leveled_up": leveled_up,
                "new_level": new_level,
                "unlocked_jutsu": unlocked_jutsu
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def award_mission_experience(self, player_id: str, exp: int) -> Dict[str, Any]:
        """Award experience from mission completion."""
        return await self.award_battle_experience(int(player_id), exp)
    
    def get_progression_info(self, character_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed progression information for a character."""
        current_level = character_data.get("level", 1)
        current_exp = character_data.get("exp", 0)
        
        # Calculate progress to next level
        exp_for_current_level = sum(self.calculate_exp_for_level(i) for i in range(1, current_level))
        exp_for_next_level = self.calculate_exp_for_level(current_level)
        exp_progress = current_exp - exp_for_current_level
        exp_needed = exp_for_next_level
        
        # Get available jutsu
        available_jutsu = self.jutsu_system.get_available_jutsu(character_data)
        learned_jutsu = character_data.get("jutsu", [])
        unlockable_jutsu = [jutsu for jutsu in available_jutsu if jutsu not in learned_jutsu]
        
        return {
            "current_level": current_level,
            "current_exp": current_exp,
            "exp_progress": exp_progress,
            "exp_needed": exp_needed,
            "progress_percentage": (exp_progress / exp_needed * 100) if exp_needed > 0 else 100,
            "rank": character_data.get("rank", "Academy Student"),
            "jutsu_learned": len(learned_jutsu),
            "jutsu_available": len(available_jutsu),
            "jutsu_unlockable": len(unlockable_jutsu),
            "next_level_exp": exp_for_current_level + exp_for_next_level
        }
    
    def get_level_rewards(self, level: int) -> Dict[str, Any]:
        """Get rewards and unlocks for reaching a specific level."""
        rewards = {
            "hp_bonus": level * 15,
            "chakra_bonus": level * 10,
            "stamina_bonus": level * 8,
            "rank": self._calculate_rank(level)
        }
        
        # Add jutsu that unlock at this level
        level_jutsu = []
        for jutsu_id, jutsu in self.jutsu_system.jutsu_database.items():
            if jutsu.level_requirement == level:
                level_jutsu.append({
                    "name": jutsu.name,
                    "element": jutsu.element,
                    "damage": jutsu.damage,
                    "rarity": jutsu.rarity
                })
        
        rewards["unlockable_jutsu"] = level_jutsu
        
        return rewards
