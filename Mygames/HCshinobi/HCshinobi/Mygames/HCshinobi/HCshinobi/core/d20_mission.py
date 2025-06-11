"""
D20 Mission System - Implements dice-based mechanics for ninja missions

This module provides:
- Dice rolling mechanics for mission challenges
- Skill checks using character attributes
- Combat resolution using d20 mechanics
- Mission objective tracking
"""

import random
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from .character import Character

logger = logging.getLogger(__name__)

class SkillType(Enum):
    """Types of skills used for mission checks."""
    STRENGTH = "strength"
    SPEED = "speed"
    NINJUTSU = "ninjutsu"
    TAIJUTSU = "taijutsu"
    GENJUTSU = "genjutsu"
    INTELLIGENCE = "intelligence"
    PERCEPTION = "perception"
    WILLPOWER = "willpower"
    CHAKRA_CONTROL = "chakra_control"
    DEFENSE = "defense"

class ChallengeType(Enum):
    """Types of challenges in missions."""
    COMBAT = "combat"
    STEALTH = "stealth"
    PUZZLE = "puzzle"
    TRAP = "trap"
    PERSUASION = "persuasion"
    SURVIVAL = "survival"
    INFILTRATION = "infiltration"
    ESCORT = "escort"
    TRACKING = "tracking"
    NEGOTIATION = "negotiation"

class DifficultyLevel(Enum):
    """Difficulty levels for challenges."""
    VERY_EASY = 5
    EASY = 10
    MODERATE = 15
    HARD = 20
    VERY_HARD = 25
    NEARLY_IMPOSSIBLE = 30

@dataclass
class D20Challenge:
    """Represents a single D20-based challenge in a mission."""
    challenge_id: str
    title: str
    description: str
    difficulty: DifficultyLevel
    primary_skill: SkillType
    secondary_skill: Optional[SkillType] = None
    challenge_type: ChallengeType = ChallengeType.COMBAT
    enemy_level: Optional[int] = None
    enemy_stats: Optional[Dict[str, int]] = None
    success_message: str = "You succeeded in the challenge!"
    failure_message: str = "You failed the challenge."
    critical_success_message: Optional[str] = None
    critical_failure_message: Optional[str] = None
    rewards: Dict[str, Any] = field(default_factory=dict)
    required_items: List[str] = field(default_factory=list)

@dataclass
class D20Mission:
    """Represents a D20-based mission with multiple challenges."""
    mission_id: str
    title: str
    description: str
    rank: str
    location: str
    challenges: List[D20Challenge]
    time_limit: str = "1 day"
    reward_exp: int = 100
    reward_ryo: int = 100
    required_items: List[str] = field(default_factory=list)
    required_jutsu: List[str] = field(default_factory=list)
    required_level: int = 1
    required_rank: str = "Academy Student"

class D20MissionRunner:
    """Handles the execution of D20-based missions."""
    
    def __init__(self):
        """Initialize the mission runner."""
        self.active_missions: Dict[str, Dict[str, Any]] = {}  # User ID -> Mission Data
    
    def roll_d20(self) -> int:
        """Roll a d20 dice."""
        return random.randint(1, 20)
    
    def roll_with_modifier(self, character: Character, skill: SkillType) -> Tuple[int, int, int]:
        """
        Roll d20 with a character's skill modifier.
        
        Returns:
            Tuple of (roll, modifier, total)
        """
        roll = self.roll_d20()
        
        # Calculate modifier based on character attribute
        modifier = 0
        if skill == SkillType.STRENGTH:
            modifier = (character.strength - 10) // 2
        elif skill == SkillType.SPEED:
            modifier = (character.speed - 10) // 2
        elif skill == SkillType.NINJUTSU:
            modifier = (character.ninjutsu - 10) // 2
        elif skill == SkillType.TAIJUTSU:
            modifier = (character.taijutsu - 10) // 2
        elif skill == SkillType.GENJUTSU:
            modifier = (character.genjutsu - 10) // 2
        elif skill == SkillType.INTELLIGENCE:
            modifier = (character.intelligence - 10) // 2
        elif skill == SkillType.PERCEPTION:
            modifier = (character.perception - 10) // 2
        elif skill == SkillType.WILLPOWER:
            modifier = (character.willpower - 10) // 2
        elif skill == SkillType.CHAKRA_CONTROL:
            modifier = (character.chakra_control - 10) // 2
        elif skill == SkillType.DEFENSE:
            modifier = (character.defense - 10) // 2
        
        # Apply level-based proficiency bonus
        proficiency_bonus = (character.level - 1) // 4 + 2  # +2 at level 1, +3 at level 5, etc.
        
        # Final calculation
        total = roll + modifier + proficiency_bonus
        return roll, modifier, total
    
    def skill_check(self, character: Character, difficulty: DifficultyLevel, 
                   primary_skill: SkillType, secondary_skill: Optional[SkillType] = None) -> Dict[str, Any]:
        """
        Perform a skill check for a character.
        
        Args:
            character: The character attempting the check
            difficulty: The difficulty level as an enum
            primary_skill: The main skill being tested
            secondary_skill: An optional secondary skill that can help
            
        Returns:
            Dict with results including success, critical hit/miss, and roll details
        """
        # Primary skill roll
        roll, modifier, total = self.roll_with_modifier(character, primary_skill)
        
        # Secondary skill can provide advantage (roll twice, take better)
        secondary_result = None
        if secondary_skill:
            second_roll, second_mod, second_total = self.roll_with_modifier(character, secondary_skill)
            secondary_result = {
                "roll": second_roll,
                "modifier": second_mod,
                "total": second_total
            }
            
            # If secondary roll is better, use it
            if second_total > total:
                roll, modifier, total = second_roll, second_mod, second_total
        
        # Determine outcome
        difficulty_value = difficulty.value
        success = total >= difficulty_value
        critical_success = roll == 20
        critical_failure = roll == 1
        
        # Critical success always succeeds, critical failure always fails
        if critical_success:
            success = True
        elif critical_failure:
            success = False
        
        return {
            "success": success,
            "critical_success": critical_success,
            "critical_failure": critical_failure,
            "roll": roll,
            "modifier": modifier,
            "total": total,
            "difficulty": difficulty_value,
            "primary_skill": primary_skill.name,
            "secondary_skill": secondary_skill.name if secondary_skill else None,
            "secondary_result": secondary_result
        }
    
    def combat_round(self, character: Character, enemy_stats: Dict[str, int]) -> Dict[str, Any]:
        """
        Conduct a single round of combat.
        
        Args:
            character: The player character
            enemy_stats: Dictionary of enemy statistics
            
        Returns:
            Dict with combat results
        """
        # Initiative roll
        character_initiative = self.roll_d20() + (character.speed - 10) // 2
        enemy_initiative = self.roll_d20() + (enemy_stats.get("speed", 10) - 10) // 2
        
        # Determine who goes first
        character_first = character_initiative >= enemy_initiative
        
        # Combat results
        results = {
            "character_damage_dealt": 0,
            "enemy_damage_dealt": 0,
            "character_hp_remaining": character.hp,
            "enemy_hp_remaining": enemy_stats.get("hp", 100),
            "rounds": 1,
            "character_first": character_first,
            "initiative": {
                "character": character_initiative,
                "enemy": enemy_initiative
            },
            "combat_log": [],
            "outcome": "ongoing"
        }
        
        # Initial attacker
        attacker = "character" if character_first else "enemy"
        
        # Combat log entry
        if character_first:
            results["combat_log"].append(f"{character.name} reacts quickly with {character_initiative} initiative!")
        else:
            results["combat_log"].append(f"The enemy acts first with {enemy_initiative} initiative!")
        
        # First attack
        if attacker == "character":
            self._process_character_attack(character, enemy_stats, results)
            if results["enemy_hp_remaining"] <= 0:
                results["outcome"] = "victory"
                results["combat_log"].append(f"{character.name} defeats the enemy!")
                return results
            attacker = "enemy"
        
        if attacker == "enemy":
            self._process_enemy_attack(character, enemy_stats, results)
            if results["character_hp_remaining"] <= 0:
                results["outcome"] = "defeat"
                results["combat_log"].append(f"{character.name} was defeated!")
                return results
        
        return results
    
    def _process_character_attack(self, character: Character, enemy_stats: Dict[str, int], results: Dict[str, Any]):
        """Process the character's attack on the enemy."""
        # Attack roll with appropriate skill
        skill = SkillType.TAIJUTSU  # Default
        if character.taijutsu > character.ninjutsu and character.taijutsu > character.genjutsu:
            skill = SkillType.TAIJUTSU
        elif character.ninjutsu > character.genjutsu:
            skill = SkillType.NINJUTSU
        else:
            skill = SkillType.GENJUTSU
        
        roll, modifier, total = self.roll_with_modifier(character, skill)
        
        # Enemy AC calculation (based on speed and defense)
        enemy_ac = 10 + (enemy_stats.get("speed", 10) - 10) // 2 + (enemy_stats.get("defense", 10) - 10) // 2
        
        # Hit or miss
        if roll == 20 or total >= enemy_ac:
            # Critical hit on natural 20
            is_critical = roll == 20
            
            # Damage calculation
            damage_mod = 0
            if skill == SkillType.TAIJUTSU:
                damage_mod = (character.strength - 10) // 2
            elif skill == SkillType.NINJUTSU or skill == SkillType.GENJUTSU:
                damage_mod = (character.chakra_control - 10) // 2
            
            # Base damage roll depends on level
            damage_dice = min(character.level, 10)  # Cap at 10d4
            damage_roll = sum(random.randint(1, 4) for _ in range(damage_dice))
            
            # Critical hits deal double damage
            if is_critical:
                damage_roll *= 2
                results["combat_log"].append(f"Critical hit! {character.name} strikes with devastating force!")
            
            # Total damage
            damage = damage_roll + damage_mod
            damage = max(1, damage)  # Minimum 1 damage
            
            results["character_damage_dealt"] += damage
            results["enemy_hp_remaining"] -= damage
            
            # Combat log
            if is_critical:
                results["combat_log"].append(f"{character.name} deals {damage} damage with a powerful attack!")
            else:
                results["combat_log"].append(f"{character.name} hits for {damage} damage.")
        else:
            results["combat_log"].append(f"{character.name}'s attack misses!")
    
    def _process_enemy_attack(self, character: Character, enemy_stats: Dict[str, int], results: Dict[str, Any]):
        """Process the enemy's attack on the character."""
        # Attack roll for enemy
        enemy_roll = self.roll_d20()
        enemy_attack_mod = (enemy_stats.get("strength", 10) - 10) // 2
        enemy_level_mod = (enemy_stats.get("level", 1) - 1) // 4 + 2
        enemy_total = enemy_roll + enemy_attack_mod + enemy_level_mod
        
        # Character AC calculation
        character_ac = 10 + (character.speed - 10) // 2 + (character.defense - 10) // 2
        
        # Hit or miss
        if enemy_roll == 20 or enemy_total >= character_ac:
            # Critical hit on natural 20
            is_critical = enemy_roll == 20
            
            # Damage calculation
            enemy_damage_mod = (enemy_stats.get("strength", 10) - 10) // 2
            
            # Base damage roll depends on enemy level
            enemy_level = enemy_stats.get("level", 1)
            damage_dice = min(enemy_level, 10)  # Cap at 10d4
            damage_roll = sum(random.randint(1, 4) for _ in range(damage_dice))
            
            # Critical hits deal double damage
            if is_critical:
                damage_roll *= 2
                results["combat_log"].append("Critical hit! The enemy lands a devastating blow!")
            
            # Total damage
            damage = damage_roll + enemy_damage_mod
            damage = max(1, damage)  # Minimum 1 damage
            
            results["enemy_damage_dealt"] += damage
            results["character_hp_remaining"] -= damage
            
            # Combat log
            if is_critical:
                results["combat_log"].append(f"The enemy deals {damage} damage with a powerful strike!")
            else:
                results["combat_log"].append(f"The enemy hits for {damage} damage.")
        else:
            results["combat_log"].append("The enemy's attack misses!")
    
    def process_challenge(self, character: Character, challenge: D20Challenge) -> Dict[str, Any]:
        """
        Process a single challenge.
        
        Args:
            character: The character attempting the challenge
            challenge: The challenge to attempt
            
        Returns:
            Dict with challenge results
        """
        # Handle different challenge types
        if challenge.challenge_type == ChallengeType.COMBAT:
            if not challenge.enemy_stats:
                logger.warning(f"Combat challenge {challenge.challenge_id} has no enemy stats, falling back to skill check")
                return self.skill_check(character, challenge.difficulty, challenge.primary_skill, challenge.secondary_skill)
                
            return self.combat_round(character, challenge.enemy_stats)
        else:
            # Standard skill check for non-combat challenges
            return self.skill_check(character, challenge.difficulty, challenge.primary_skill, challenge.secondary_skill)
    
    def start_mission(self, character: Character, mission: D20Mission) -> Dict[str, Any]:
        """
        Start a new mission.
        
        Args:
            character: The character starting the mission
            mission: The mission to start
            
        Returns:
            Dict with mission initialization status
        """
        user_id = str(character.id)
        
        # Check if character is already on a mission
        if user_id in self.active_missions:
            return {
                "success": False,
                "message": "You already have an active mission. Complete or abandon it first."
            }
        
        # Verify character meets requirements
        if character.level < mission.required_level:
            return {
                "success": False,
                "message": f"This mission requires level {mission.required_level}. You are only level {character.level}."
            }
        
        # Check rank requirement
        rank_levels = {
            "Academy Student": 1,
            "Genin": 2,
            "Chunin": 3,
            "Jonin": 4,
            "ANBU": 5,
            "Kage": 6
        }
        
        character_rank_level = rank_levels.get(character.rank, 0)
        required_rank_level = rank_levels.get(mission.required_rank, 0)
        
        if character_rank_level < required_rank_level:
            return {
                "success": False,
                "message": f"This mission requires the rank of {mission.required_rank}. You are only {character.rank}."
            }
        
        # Initialize mission progress
        self.active_missions[user_id] = {
            "mission_id": mission.mission_id,
            "title": mission.title,
            "current_challenge_index": 0,
            "completed_challenges": [],
            "rewards_collected": {"exp": 0, "ryo": 0, "items": []},
            "mission_log": [f"Mission started: {mission.title} in {mission.location}"]
        }
        
        return {
            "success": True,
            "message": f"Mission '{mission.title}' started. Your first objective: {mission.challenges[0].title}",
            "mission": mission,
            "first_challenge": mission.challenges[0]
        }
    
    def get_current_challenge(self, character: Character) -> Optional[Tuple[D20Challenge, int]]:
        """
        Get the current challenge for a character's active mission.
        
        Args:
            character: The character to check
            
        Returns:
            Tuple of (current challenge, challenge index) or None if no active mission
        """
        user_id = str(character.id)
        if user_id not in self.active_missions:
            return None
            
        mission_data = self.active_missions[user_id]
        mission_id = mission_data["mission_id"]
        current_index = mission_data["current_challenge_index"]
        
        # Get mission definition (this would come from your mission system)
        # For now, we'll assume we have a reference to the mission
        mission = self._get_mission_by_id(mission_id)
        if not mission:
            logger.error(f"Mission {mission_id} not found for character {user_id}")
            return None
            
        if current_index >= len(mission.challenges):
            return None  # All challenges completed
            
        return mission.challenges[current_index], current_index
    
    def _get_mission_by_id(self, mission_id: str) -> Optional[D20Mission]:
        """
        Get a mission by ID. This should integrate with your mission system.
        For now, it's a placeholder that would need to be implemented.
        """
        # This would need to be implemented to retrieve the mission from your system
        logger.warning("_get_mission_by_id is not implemented and should be integrated with the mission system")
        return None
    
    def process_current_challenge(self, character: Character) -> Dict[str, Any]:
        """
        Process the current challenge for a character's active mission.
        
        Args:
            character: The character attempting the challenge
            
        Returns:
            Dict with challenge results
        """
        challenge_data = self.get_current_challenge(character)
        if not challenge_data:
            return {
                "success": False,
                "message": "No active challenge found."
            }
            
        challenge, challenge_index = challenge_data
        user_id = str(character.id)
        mission_data = self.active_missions[user_id]
        
        # Process the challenge
        result = self.process_challenge(character, challenge)
        
        # Update mission progress
        mission_data["completed_challenges"].append({
            "challenge_id": challenge.challenge_id,
            "result": result
        })
        
        # Add to mission log
        success = result.get("success", False)
        if challenge.challenge_type == ChallengeType.COMBAT:
            success = result.get("outcome", "") == "victory"
            
        if success:
            if result.get("critical_success", False):
                log_message = challenge.critical_success_message or challenge.success_message
            else:
                log_message = challenge.success_message
        else:
            if result.get("critical_failure", False):
                log_message = challenge.critical_failure_message or challenge.failure_message
            else:
                log_message = challenge.failure_message
                
        mission_data["mission_log"].append(log_message)
        
        # Move to next challenge if successful
        if success:
            mission_data["current_challenge_index"] += 1
            
            # Check if mission is complete
            mission = self._get_mission_by_id(mission_data["mission_id"])
            if mission and mission_data["current_challenge_index"] >= len(mission.challenges):
                return self.complete_mission(character)
                
            # Get next challenge
            next_challenge = self.get_current_challenge(character)
            if next_challenge:
                next_challenge_obj, _ = next_challenge
                result["next_challenge"] = {
                    "title": next_challenge_obj.title,
                    "description": next_challenge_obj.description
                }
        
        return {
            "success": True,
            "challenge_result": result,
            "mission_progress": {
                "current_challenge": challenge_index + 1,
                "total_challenges": len(self._get_mission_by_id(mission_data["mission_id"]).challenges),
                "mission_log": mission_data["mission_log"]
            }
        }
    
    def complete_mission(self, character: Character) -> Dict[str, Any]:
        """
        Complete a mission and award rewards.
        
        Args:
            character: The character completing the mission
            
        Returns:
            Dict with mission completion results
        """
        user_id = str(character.id)
        if user_id not in self.active_missions:
            return {
                "success": False,
                "message": "No active mission found."
            }
            
        mission_data = self.active_missions[user_id]
        mission_id = mission_data["mission_id"]
        
        # Get mission definition
        mission = self._get_mission_by_id(mission_id)
        if not mission:
            logger.error(f"Mission {mission_id} not found for character {user_id}")
            return {
                "success": False,
                "message": "Mission data not found."
            }
            
        # Calculate rewards
        rewards = {
            "exp": mission.reward_exp,
            "ryo": mission.reward_ryo,
            "items": []  # Add any item rewards here
        }
        
        # Add mission completion to log
        mission_data["mission_log"].append(f"Mission complete: {mission.title}")
        
        # Remove from active missions
        self.active_missions.pop(user_id)
        
        return {
            "success": True,
            "message": f"Mission '{mission.title}' completed successfully!",
            "rewards": rewards,
            "mission_log": mission_data["mission_log"]
        } 