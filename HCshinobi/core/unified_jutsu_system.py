"""
Unified Jutsu System for HCShinobi
Consolidated jutsu system that uses the unified jutsu database.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class UnifiedJutsu:
    """Unified jutsu definition with all properties."""
    id: str
    name: str
    rank: str = "E"
    type: str = "Ninjutsu"
    element: str = "None"
    description: str = "No description available."
    chakra_cost: int = 0
    stamina_cost: int = 0
    damage: int = 0
    accuracy: int = 100
    range: str = "close"
    target_type: str = "opponent"
    can_miss: bool = True
    shop_cost: int = 0
    level_requirement: int = 1
    stat_requirements: Dict[str, int] = field(default_factory=dict)
    achievement_requirements: List[str] = field(default_factory=list)
    special_effects: List[str] = field(default_factory=list)
    cooldown: int = 0
    rarity: str = "Common"
    clan_restrictions: List[str] = field(default_factory=list)
    phase_requirements: int = 0
    save_dc: int = 0
    save_type: str = ""
    source_system: str = "unknown"

class UnifiedJutsuSystem:
    """Unified jutsu system that consolidates all jutsu sources."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.jutsu_database: Dict[str, UnifiedJutsu] = {}
        self._load_unified_database()
    
    def _load_unified_database(self) -> None:
        """Load the unified jutsu database."""
        try:
            jutsu_file = self.data_dir / "jutsu" / "unified_jutsu_database.json"
            if not jutsu_file.exists():
                logger.warning(f"Unified jutsu database not found at {jutsu_file}")
                logger.info("Falling back to core jutsu system...")
                self._load_fallback_database()
                return
            
            with open(jutsu_file, 'r', encoding='utf-8') as f:
                jutsu_list = json.load(f)
            
            for jutsu_data in jutsu_list:
                jutsu = UnifiedJutsu(**jutsu_data)
                self.jutsu_database[jutsu.id] = jutsu
            
            logger.info(f"✅ Loaded {len(self.jutsu_database)} jutsu from unified database")
            
        except Exception as e:
            logger.error(f"❌ Error loading unified jutsu database: {e}")
            logger.info("Falling back to core jutsu system...")
            self._load_fallback_database()
    
    def _load_fallback_database(self) -> None:
        """Load fallback jutsu database from core system."""
        try:
            from .jutsu_system import JutsuSystem
            core_system = JutsuSystem()
            
            for jutsu_id, jutsu in core_system.jutsu_database.items():
                unified_jutsu = UnifiedJutsu(
                    id=jutsu_id,
                    name=jutsu.name,
                    chakra_cost=jutsu.chakra_cost,
                    damage=jutsu.damage,
                    accuracy=jutsu.accuracy,
                    range=jutsu.range,
                    element=jutsu.element,
                    description=jutsu.description,
                    level_requirement=jutsu.level_requirement,
                    stat_requirements=jutsu.stat_requirements,
                    achievement_requirements=jutsu.achievement_requirements,
                    special_effects=jutsu.special_effects,
                    cooldown=jutsu.cooldown,
                    rarity=jutsu.rarity,
                    source_system="fallback"
                )
                self.jutsu_database[jutsu_id] = unified_jutsu
            
            logger.info(f"✅ Loaded {len(self.jutsu_database)} jutsu from fallback system")
            
        except Exception as e:
            logger.error(f"❌ Error loading fallback jutsu database: {e}")
            # Create minimal database with basic jutsu
            self._create_minimal_database()
    
    def _create_minimal_database(self) -> None:
        """Create a minimal jutsu database with basic jutsu."""
        basic_jutsu = [
            UnifiedJutsu(
                id="basic_attack",
                name="Basic Attack",
                description="A basic physical attack",
                chakra_cost=0,
                damage=10,
                accuracy=90,
                range="close",
                element="none",
                level_requirement=1,
                stat_requirements={"strength": 5},
                source_system="minimal"
            ),
            UnifiedJutsu(
                id="punch",
                name="Punch",
                description="A powerful punch",
                chakra_cost=5,
                damage=15,
                accuracy=85,
                range="close",
                element="none",
                level_requirement=1,
                stat_requirements={"strength": 8, "speed": 6},
                source_system="minimal"
            )
        ]
        
        for jutsu in basic_jutsu:
            self.jutsu_database[jutsu.id] = jutsu
        
        logger.info(f"✅ Created minimal jutsu database with {len(self.jutsu_database)} jutsu")
    
    def get_jutsu(self, jutsu_id: str) -> Optional[UnifiedJutsu]:
        """Get a jutsu by ID."""
        return self.jutsu_database.get(jutsu_id)
    
    def get_jutsu_by_name(self, name: str) -> Optional[UnifiedJutsu]:
        """Get a jutsu by name (case-insensitive)."""
        name_lower = name.lower()
        for jutsu in self.jutsu_database.values():
            if jutsu.name.lower() == name_lower:
                return jutsu
        return None
    
    def get_all_jutsu(self) -> List[UnifiedJutsu]:
        """Get all jutsu in the database."""
        return list(self.jutsu_database.values())
    
    def get_jutsu_by_element(self, element: str) -> List[UnifiedJutsu]:
        """Get all jutsu of a specific element."""
        element_lower = element.lower()
        return [
            jutsu for jutsu in self.jutsu_database.values()
            if jutsu.element and jutsu.element.lower() == element_lower
        ]
    
    def get_jutsu_by_rank(self, rank: str) -> List[UnifiedJutsu]:
        """Get all jutsu of a specific rank."""
        return [
            jutsu for jutsu in self.jutsu_database.values()
            if jutsu.rank == rank
        ]
    
    def get_jutsu_by_type(self, jutsu_type: str) -> List[UnifiedJutsu]:
        """Get all jutsu of a specific type."""
        type_lower = jutsu_type.lower()
        return [
            jutsu for jutsu in self.jutsu_database.values()
            if jutsu.type.lower() == type_lower
        ]
    
    def get_available_jutsu(self, character_data: Dict[str, Any]) -> List[UnifiedJutsu]:
        """Get all jutsu that a character can learn."""
        available = []
        
        for jutsu in self.jutsu_database.values():
            if self._can_learn_jutsu(character_data, jutsu):
                available.append(jutsu)
        
        return available
    
    def get_learned_jutsu(self, character_data: Dict[str, Any]) -> List[UnifiedJutsu]:
        """Get all jutsu that a character has learned."""
        learned = []
        character_jutsu = character_data.get("jutsu", [])
        
        for jutsu_name in character_jutsu:
            jutsu = self.get_jutsu_by_name(jutsu_name)
            if jutsu:
                learned.append(jutsu)
        
        return learned
    
    def _can_learn_jutsu(self, character_data: Dict[str, Any], jutsu: UnifiedJutsu) -> bool:
        """Check if a character can learn a specific jutsu."""
        # Check if already learned
        character_jutsu = character_data.get("jutsu", [])
        if jutsu.name in character_jutsu:
            return False
        
        # Check level requirement
        character_level = character_data.get("level", 1)
        if character_level < jutsu.level_requirement:
            return False
        
        # Check stat requirements
        for stat, required_value in jutsu.stat_requirements.items():
            character_stat = character_data.get(stat, 0)
            if character_stat < required_value:
                return False
        
        # Check achievement requirements
        character_achievements = character_data.get("achievements", [])
        for achievement in jutsu.achievement_requirements:
            if achievement not in character_achievements:
                return False
        
        # Check clan restrictions
        if jutsu.clan_restrictions:
            character_clan = character_data.get("clan", "")
            if character_clan not in jutsu.clan_restrictions:
                return False
        
        return True
    
    def unlock_jutsu_for_character(self, character_data: Dict[str, Any], jutsu_name: str) -> bool:
        """Unlock a jutsu for a character if they meet requirements."""
        jutsu = self.get_jutsu_by_name(jutsu_name)
        if not jutsu:
            return False
        
        if not self._can_learn_jutsu(character_data, jutsu):
            return False
        
        # Add jutsu to character
        if "jutsu" not in character_data:
            character_data["jutsu"] = []
        character_data["jutsu"].append(jutsu.name)
        
        return True
    
    def get_jutsu_info(self, jutsu_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a jutsu."""
        jutsu = self.get_jutsu_by_name(jutsu_name)
        if not jutsu:
            return None
        
        return {
            "id": jutsu.id,
            "name": jutsu.name,
            "rank": jutsu.rank,
            "type": jutsu.type,
            "element": jutsu.element,
            "description": jutsu.description,
            "chakra_cost": jutsu.chakra_cost,
            "stamina_cost": jutsu.stamina_cost,
            "damage": jutsu.damage,
            "accuracy": jutsu.accuracy,
            "range": jutsu.range,
            "target_type": jutsu.target_type,
            "can_miss": jutsu.can_miss,
            "shop_cost": jutsu.shop_cost,
            "level_requirement": jutsu.level_requirement,
            "stat_requirements": jutsu.stat_requirements,
            "achievement_requirements": jutsu.achievement_requirements,
            "special_effects": jutsu.special_effects,
            "cooldown": jutsu.cooldown,
            "rarity": jutsu.rarity,
            "clan_restrictions": jutsu.clan_restrictions,
            "phase_requirements": jutsu.phase_requirements,
            "save_dc": jutsu.save_dc,
            "save_type": jutsu.save_type
        }
    
    def search_jutsu(self, query: str) -> List[UnifiedJutsu]:
        """Search jutsu by name or description."""
        query_lower = query.lower()
        results = []
        
        for jutsu in self.jutsu_database.values():
            if (query_lower in jutsu.name.lower() or 
                query_lower in jutsu.description.lower() or
                (jutsu.element and query_lower in jutsu.element.lower())):
                results.append(jutsu)
        
        return results
    
    def get_jutsu_statistics(self) -> Dict[str, Any]:
        """Get statistics about the jutsu database."""
        stats = {
            "total_jutsu": len(self.jutsu_database),
            "by_rank": {},
            "by_element": {},
            "by_type": {},
            "by_rarity": {},
            "by_source": {}
        }
        
        for jutsu in self.jutsu_database.values():
            # Count by rank
            stats["by_rank"][jutsu.rank] = stats["by_rank"].get(jutsu.rank, 0) + 1
            
            # Count by element
            stats["by_element"][jutsu.element] = stats["by_element"].get(jutsu.element, 0) + 1
            
            # Count by type
            stats["by_type"][jutsu.type] = stats["by_type"].get(jutsu.type, 0) + 1
            
            # Count by rarity
            stats["by_rarity"][jutsu.rarity] = stats["by_rarity"].get(jutsu.rarity, 0) + 1
            
            # Count by source
            stats["by_source"][jutsu.source_system] = stats["by_source"].get(jutsu.source_system, 0) + 1
        
        return stats 