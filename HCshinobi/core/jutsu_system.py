"""
Comprehensive Jutsu System for HCShinobi
Handles jutsu unlocking, progression, and database management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import random

@dataclass
class Jutsu:
    """Jutsu definition with comprehensive properties."""
    name: str
    chakra_cost: int
    damage: int
    accuracy: int
    range: str
    element: str
    description: str
    level_requirement: int = 1
    stat_requirements: Dict[str, int] = field(default_factory=dict)
    achievement_requirements: List[str] = field(default_factory=list)
    special_effects: List[str] = field(default_factory=list)
    cooldown: int = 0
    rarity: str = "Common"  # Common, Uncommon, Rare, Epic, Legendary

class JutsuSystem:
    """Comprehensive jutsu system for character progression."""
    
    def __init__(self):
        self.jutsu_database = self._load_jutsu_database()
    
    def _load_jutsu_database(self) -> Dict[str, Jutsu]:
        """Load comprehensive jutsu database with progression requirements."""
        return {
            # Basic Jutsu (Level 1-5) - Taijutsu focused
            "basic_attack": Jutsu(
                name="Basic Attack",
                chakra_cost=0,
                damage=10,
                accuracy=90,
                range="close",
                element="none",
                description="A basic physical attack",
                level_requirement=1,
                stat_requirements={"strength": 5},
                rarity="Common"
            ),
            "punch": Jutsu(
                name="Punch",
                chakra_cost=5,
                damage=15,
                accuracy=85,
                range="close",
                element="none",
                description="A powerful punch",
                level_requirement=1,
                stat_requirements={"strength": 8, "speed": 6},
                rarity="Common"
            ),
            "kick": Jutsu(
                name="Kick",
                chakra_cost=8,
                damage=20,
                accuracy=80,
                range="close",
                element="none",
                description="A swift kick",
                level_requirement=2,
                stat_requirements={"strength": 10, "speed": 8},
                rarity="Common"
            ),
            "dodge": Jutsu(
                name="Dodge",
                chakra_cost=3,
                damage=0,
                accuracy=95,
                range="close",
                element="none",
                description="Quickly dodge an attack",
                level_requirement=1,
                stat_requirements={"speed": 10, "dexterity": 8},
                special_effects=["evasion"],
                rarity="Common"
            ),
            
            # Fire Release Jutsu (Level 3-15) - Ninjutsu focused
            "fireball": Jutsu(
                name="Fireball Jutsu",
                chakra_cost=30,
                damage=40,
                accuracy=85,
                range="medium",
                element="fire",
                description="Launches a ball of fire",
                level_requirement=3,
                stat_requirements={"ninjutsu": 15, "chakra_control": 12, "intelligence": 10},
                special_effects=["burn_chance"],
                rarity="Uncommon"
            ),
            "great_fireball": Jutsu(
                name="Great Fireball Jutsu",
                chakra_cost=50,
                damage=60,
                accuracy=80,
                range="medium",
                element="fire",
                description="A larger, more powerful fireball",
                level_requirement=8,
                stat_requirements={"ninjutsu": 25, "chakra_control": 20, "intelligence": 15},
                special_effects=["burn_chance", "area_damage"],
                rarity="Rare"
            ),
            "dragon_flame": Jutsu(
                name="Dragon Flame Jutsu",
                chakra_cost=80,
                damage=90,
                accuracy=75,
                range="long",
                element="fire",
                description="Creates a dragon-shaped flame",
                level_requirement=12,
                stat_requirements={"ninjutsu": 35, "chakra_control": 30, "intelligence": 20},
                special_effects=["burn_chance", "piercing"],
                rarity="Epic"
            ),
            
            # Water Release Jutsu (Level 4-18) - Ninjutsu focused
            "water_dragon": Jutsu(
                name="Water Dragon Jutsu",
                chakra_cost=40,
                damage=45,
                accuracy=80,
                range="medium",
                element="water",
                description="Creates a dragon of water",
                level_requirement=4,
                stat_requirements={"ninjutsu": 18, "chakra_control": 15, "intelligence": 12},
                special_effects=["knockback"],
                rarity="Uncommon"
            ),
            "water_shark": Jutsu(
                name="Water Shark Jutsu",
                chakra_cost=60,
                damage=70,
                accuracy=75,
                range="medium",
                element="water",
                description="Creates a shark made of water",
                level_requirement=10,
                stat_requirements={"ninjutsu": 30, "chakra_control": 25, "intelligence": 18},
                special_effects=["knockback", "piercing"],
                rarity="Rare"
            ),
            
            # Earth Release Jutsu (Level 5-20) - Ninjutsu focused
            "earth_wall": Jutsu(
                name="Earth Wall Jutsu",
                chakra_cost=25,
                damage=0,
                accuracy=95,
                range="close",
                element="earth",
                description="Creates a defensive wall of earth",
                level_requirement=5,
                stat_requirements={"ninjutsu": 20, "defense": 15, "constitution": 12},
                special_effects=["defense_boost"],
                rarity="Uncommon"
            ),
            "stone_pillars": Jutsu(
                name="Stone Pillars Jutsu",
                chakra_cost=45,
                damage=55,
                accuracy=70,
                range="medium",
                element="earth",
                description="Summons stone pillars from the ground",
                level_requirement=9,
                stat_requirements={"ninjutsu": 28, "defense": 20, "constitution": 15},
                special_effects=["area_damage", "terrain_alteration"],
                rarity="Rare"
            ),
            
            # Lightning Release Jutsu (Level 10-25) - Ninjutsu + Speed focused
            "lightning_bolt": Jutsu(
                name="Lightning Bolt Jutsu",
                chakra_cost=60,
                damage=70,
                accuracy=75,
                range="long",
                element="lightning",
                description="Fires a bolt of lightning",
                level_requirement=10,
                stat_requirements={"ninjutsu": 30, "speed": 25, "dexterity": 20},
                special_effects=["stun_chance"],
                rarity="Rare"
            ),
            "chidori": Jutsu(
                name="Chidori",
                chakra_cost=100,
                damage=120,
                accuracy=85,
                range="close",
                element="lightning",
                description="A powerful lightning technique",
                level_requirement=20,
                stat_requirements={"ninjutsu": 50, "speed": 40, "chakra_control": 45, "dexterity": 35},
                achievement_requirements=["Lightning Master"],
                special_effects=["piercing", "stun_chance"],
                rarity="Epic"
            ),
            
            # Wind Release Jutsu (Level 8-22) - Ninjutsu + Speed focused
            "wind_scythe": Jutsu(
                name="Wind Scythe Jutsu",
                chakra_cost=45,
                damage=55,
                accuracy=80,
                range="medium",
                element="wind",
                description="Creates blades of wind",
                level_requirement=8,
                stat_requirements={"ninjutsu": 25, "speed": 20, "dexterity": 18},
                special_effects=["piercing"],
                rarity="Rare"
            ),
            "wind_dragon": Jutsu(
                name="Wind Dragon Jutsu",
                chakra_cost=70,
                damage=85,
                accuracy=70,
                range="long",
                element="wind",
                description="Creates a dragon of wind",
                level_requirement=15,
                stat_requirements={"ninjutsu": 40, "speed": 35, "dexterity": 30},
                special_effects=["knockback", "area_damage"],
                rarity="Epic"
            ),
            
            # Shadow Techniques (Level 6-18) - Genjutsu focused
            "shadow_clone": Jutsu(
                name="Shadow Clone Technique",
                chakra_cost=20,
                damage=0,
                accuracy=90,
                range="close",
                element="none",
                description="Creates physical clones",
                level_requirement=6,
                stat_requirements={"ninjutsu": 22, "chakra_control": 18, "intelligence": 15},
                special_effects=["clone_creation"],
                rarity="Uncommon"
            ),
            "shadow_possession": Jutsu(
                name="Shadow Possession Jutsu",
                chakra_cost=35,
                damage=0,
                accuracy=70,
                range="medium",
                element="none",
                description="Controls target through shadows",
                level_requirement=11,
                stat_requirements={"genjutsu": 30, "intelligence": 25, "willpower": 20},
                special_effects=["control"],
                rarity="Rare"
            ),
            
            # Genjutsu Techniques (Level 7-20) - Willpower/Constitution focused
            "illusion": Jutsu(
                name="Basic Illusion",
                chakra_cost=25,
                damage=0,
                accuracy=75,
                range="medium",
                element="none",
                description="Creates a simple illusion",
                level_requirement=7,
                stat_requirements={"genjutsu": 20, "willpower": 15, "intelligence": 18},
                special_effects=["illusion"],
                rarity="Uncommon"
            ),
            "mind_control": Jutsu(
                name="Mind Control Jutsu",
                chakra_cost=50,
                damage=0,
                accuracy=60,
                range="medium",
                element="none",
                description="Attempts to control target's mind",
                level_requirement=14,
                stat_requirements={"genjutsu": 35, "willpower": 30, "intelligence": 25},
                special_effects=["mind_control"],
                rarity="Rare"
            ),
            
            # Advanced Taijutsu (Level 5-18) - Speed/Dexterity focused
            "flying_kick": Jutsu(
                name="Flying Kick",
                chakra_cost=15,
                damage=30,
                accuracy=75,
                range="close",
                element="none",
                description="A powerful aerial kick",
                level_requirement=5,
                stat_requirements={"speed": 20, "dexterity": 18, "strength": 15},
                special_effects=["knockback"],
                rarity="Uncommon"
            ),
            "pressure_point": Jutsu(
                name="Pressure Point Strike",
                chakra_cost=20,
                damage=25,
                accuracy=70,
                range="close",
                element="none",
                description="Strikes vital pressure points",
                level_requirement=8,
                stat_requirements={"dexterity": 25, "intelligence": 20, "speed": 22},
                special_effects=["paralysis_chance"],
                rarity="Rare"
            ),
            
            # Advanced Techniques (Level 15-30) - Mixed requirements
            "rasengan": Jutsu(
                name="Rasengan",
                chakra_cost=80,
                damage=100,
                accuracy=90,
                range="close",
                element="none",
                description="A powerful spinning chakra sphere",
                level_requirement=15,
                stat_requirements={"ninjutsu": 45, "chakra_control": 40, "dexterity": 35},
                achievement_requirements=["Chakra Master"],
                special_effects=["piercing", "area_damage"],
                rarity="Epic"
            ),
            "amaterasu": Jutsu(
                name="Amaterasu",
                chakra_cost=150,
                damage=200,
                accuracy=95,
                range="long",
                element="fire",
                description="Black flames that never extinguish",
                level_requirement=25,
                stat_requirements={"ninjutsu": 70, "chakra_control": 65, "willpower": 50},
                achievement_requirements=["Sharingan Master", "Fire Master"],
                special_effects=["burn_chance", "piercing", "persistent_damage"],
                rarity="Legendary"
            ),
            "kamui": Jutsu(
                name="Kamui",
                chakra_cost=120,
                damage=0,
                accuracy=100,
                range="any",
                element="none",
                description="Teleports target to another dimension",
                level_requirement=28,
                stat_requirements={"ninjutsu": 75, "chakra_control": 70, "intelligence": 60},
                achievement_requirements=["Sharingan Master", "Space Master"],
                special_effects=["teleport", "dimensional"],
                rarity="Legendary"
            ),
            
            # Clan-Specific Jutsu
            "byakugan": Jutsu(
                name="Byakugan",
                chakra_cost=10,
                damage=0,
                accuracy=100,
                range="close",
                element="none",
                description="Activates the Byakugan eye technique",
                level_requirement=5,
                stat_requirements={"perception": 20, "intelligence": 15},
                achievement_requirements=["Hyuga Clan Member"],
                special_effects=["enhanced_vision", "chakra_sight"],
                rarity="Epic"
            ),
            "sharingan": Jutsu(
                name="Sharingan",
                chakra_cost=15,
                damage=0,
                accuracy=100,
                range="close",
                element="none",
                description="Activates the Sharingan eye technique",
                level_requirement=8,
                stat_requirements={"perception": 25, "intelligence": 20},
                achievement_requirements=["Uchiha Clan Member"],
                special_effects=["enhanced_vision", "predictive_combat"],
                rarity="Epic"
            ),
            
            # Charisma-based Techniques (Level 3-15) - Social/Intimidation
            "intimidation": Jutsu(
                name="Intimidation Technique",
                chakra_cost=5,
                damage=0,
                accuracy=80,
                range="close",
                element="none",
                description="Intimidates enemies with presence",
                level_requirement=3,
                stat_requirements={"charisma": 15, "willpower": 12},
                special_effects=["fear", "morale_penalty"],
                rarity="Common"
            ),
            "persuasion": Jutsu(
                name="Persuasion Jutsu",
                chakra_cost=10,
                damage=0,
                accuracy=70,
                range="close",
                element="none",
                description="Attempts to persuade enemies to surrender",
                level_requirement=6,
                stat_requirements={"charisma": 20, "intelligence": 15},
                special_effects=["surrender_chance"],
                rarity="Uncommon"
            ),
            "deception": Jutsu(
                name="Deception Technique",
                chakra_cost=8,
                damage=0,
                accuracy=75,
                range="close",
                element="none",
                description="Creates false information to confuse enemies",
                level_requirement=4,
                stat_requirements={"charisma": 18, "intelligence": 16},
                special_effects=["confusion", "misinformation"],
                rarity="Uncommon"
            ),
            "leadership": Jutsu(
                name="Leadership Aura",
                chakra_cost=20,
                damage=0,
                accuracy=100,
                range="medium",
                element="none",
                description="Inspires allies with leadership presence",
                level_requirement=10,
                stat_requirements={"charisma": 30, "willpower": 25},
                special_effects=["ally_buff", "morale_boost"],
                rarity="Rare"
            )
        }
    
    def get_available_jutsu(self, character_data: Dict[str, Any]) -> List[str]:
        """Get all jutsu available to a character based on their stats and achievements."""
        available_jutsu = []
        
        for jutsu_id, jutsu in self.jutsu_database.items():
            if self._can_learn_jutsu(character_data, jutsu):
                available_jutsu.append(jutsu.name)
        
        return available_jutsu
    
    def _can_learn_jutsu(self, character_data: Dict[str, Any], jutsu: Jutsu) -> bool:
        """Check if a character can learn a specific jutsu."""
        # Level requirement
        if character_data.get("level", 1) < jutsu.level_requirement:
            return False
        
        # Stat requirements
        for stat, required_value in jutsu.stat_requirements.items():
            if character_data.get(stat, 0) < required_value:
                return False
        
        # Achievement requirements
        character_achievements = character_data.get("achievements", [])
        for achievement in jutsu.achievement_requirements:
            if achievement not in character_achievements:
                return False
        
        return True
    
    def get_unlockable_jutsu(self, character_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get jutsu that the character is close to unlocking."""
        unlockable = []
        
        for jutsu_id, jutsu in self.jutsu_database.items():
            if jutsu.name not in character_data.get("jutsu", []):
                # Check what's missing
                missing_requirements = []
                
                if character_data.get("level", 1) < jutsu.level_requirement:
                    missing_requirements.append(f"Level {jutsu.level_requirement}")
                
                for stat, required_value in jutsu.stat_requirements.items():
                    current_value = character_data.get(stat, 0)
                    if current_value < required_value:
                        missing_requirements.append(f"{stat.title()} {required_value}")
                
                for achievement in jutsu.achievement_requirements:
                    if achievement not in character_data.get("achievements", []):
                        missing_requirements.append(f"Achievement: {achievement}")
                
                if missing_requirements:
                    unlockable.append({
                        "name": jutsu.name,
                        "description": jutsu.description,
                        "rarity": jutsu.rarity,
                        "missing_requirements": missing_requirements,
                        "element": jutsu.element,
                        "damage": jutsu.damage
                    })
        
        return unlockable
    
    def unlock_jutsu_for_character(self, character_data: Dict[str, Any], jutsu_name: str) -> bool:
        """Unlock a jutsu for a character if they meet requirements."""
        # Find jutsu by name
        jutsu = None
        for jutsu_id, j in self.jutsu_database.items():
            if j.name == jutsu_name:
                jutsu = j
                break
        
        if not jutsu:
            return False
        
        # Check if already learned
        if jutsu_name in character_data.get("jutsu", []):
            return False
        
        # Check requirements
        if not self._can_learn_jutsu(character_data, jutsu):
            return False
        
        # Add jutsu to character
        if "jutsu" not in character_data:
            character_data["jutsu"] = []
        character_data["jutsu"].append(jutsu_name)
        
        return True
    
    def get_jutsu_info(self, jutsu_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a jutsu."""
        for jutsu_id, jutsu in self.jutsu_database.items():
            if jutsu.name == jutsu_name:
                return {
                    "name": jutsu.name,
                    "chakra_cost": jutsu.chakra_cost,
                    "damage": jutsu.damage,
                    "accuracy": jutsu.accuracy,
                    "range": jutsu.range,
                    "element": jutsu.element,
                    "description": jutsu.description,
                    "level_requirement": jutsu.level_requirement,
                    "stat_requirements": jutsu.stat_requirements,
                    "achievement_requirements": jutsu.achievement_requirements,
                    "special_effects": jutsu.special_effects,
                    "rarity": jutsu.rarity
                }
        return None
    
    def get_jutsu_by_element(self, element: str) -> List[str]:
        """Get all jutsu of a specific element."""
        jutsu_list = []
        for jutsu_id, jutsu in self.jutsu_database.items():
            if jutsu.element == element:
                jutsu_list.append(jutsu.name)
        return jutsu_list
    
    def get_jutsu_by_rarity(self, rarity: str) -> List[str]:
        """Get all jutsu of a specific rarity."""
        jutsu_list = []
        for jutsu_id, jutsu in self.jutsu_database.items():
            if jutsu.rarity == rarity:
                jutsu_list.append(jutsu.name)
        return jutsu_list 