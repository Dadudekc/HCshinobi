#!/usr/bin/env python3
"""
Jutsu System Consolidation Script
Merges all jutsu from different systems into a unified database.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@dataclass
class UnifiedJutsu:
    """Unified jutsu schema that accommodates all jutsu types."""
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
    stat_requirements: Dict[str, int] = None
    achievement_requirements: List[str] = None
    special_effects: List[str] = None
    cooldown: int = 0
    rarity: str = "Common"
    clan_restrictions: List[str] = None
    phase_requirements: int = 0
    save_dc: int = 0
    save_type: str = ""
    source_system: str = "unknown"
    
    def __post_init__(self):
        if self.stat_requirements is None:
            self.stat_requirements = {}
        if self.achievement_requirements is None:
            self.achievement_requirements = []
        if self.special_effects is None:
            self.special_effects = []
        if self.clan_restrictions is None:
            self.clan_restrictions = []

class JutsuConsolidator:
    """Consolidates jutsu from multiple sources into a unified database."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.jutsu_dir = self.data_dir / "jutsu"
        self.consolidated_jutsu: Dict[str, UnifiedJutsu] = {}
        self.duplicates: List[str] = []
        self.errors: List[str] = []
        
    def load_master_jutsu_list(self) -> List[Dict[str, Any]]:
        """Load jutsu from master_jutsu_list.json."""
        logger.info("Loading master jutsu list...")
        try:
            file_path = self.jutsu_dir / "master_jutsu_list.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                jutsu_list = json.load(f)
            logger.info(f"Loaded {len(jutsu_list)} jutsu from master list")
            return jutsu_list
        except Exception as e:
            logger.error(f"Error loading master jutsu list: {e}")
            return []
    
    def load_solomon_jutsu(self) -> Dict[str, Any]:
        """Load jutsu from solomon_jutsu.json."""
        logger.info("Loading Solomon jutsu...")
        try:
            file_path = self.jutsu_dir / "solomon_jutsu.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract jutsu from Solomon's data structure
            jutsu_data = {}
            if "solomon_jutsu" in data:
                jutsu_data = data["solomon_jutsu"]
            
            logger.info(f"Loaded {len(jutsu_data)} jutsu from Solomon")
            return jutsu_data
        except Exception as e:
            logger.error(f"Error loading Solomon jutsu: {e}")
            return {}
    
    def load_core_jutsu_system(self) -> List[Dict[str, Any]]:
        """Load jutsu from the core jutsu system (Python code)."""
        logger.info("Loading core jutsu system...")
        try:
            # Import the core jutsu system
            sys.path.insert(0, str(Path.cwd()))
            from HCshinobi.core.jutsu_system import JutsuSystem
            
            jutsu_system = JutsuSystem()
            jutsu_list = []
            
            for jutsu_id, jutsu in jutsu_system.jutsu_database.items():
                jutsu_dict = {
                    "id": jutsu_id,
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
                    "cooldown": jutsu.cooldown,
                    "rarity": jutsu.rarity
                }
                jutsu_list.append(jutsu_dict)
            
            logger.info(f"Loaded {len(jutsu_list)} jutsu from core system")
            return jutsu_list
        except Exception as e:
            logger.error(f"Error loading core jutsu system: {e}")
            return []
    
    def load_shinobios_jutsu(self) -> List[Dict[str, Any]]:
        """Load jutsu from ShinobiOS engine."""
        logger.info("Loading ShinobiOS jutsu...")
        try:
            # Import the ShinobiOS engine
            sys.path.insert(0, str(Path.cwd()))
            from HCshinobi.core.missions.shinobios_engine import ShinobiOSEngine
            
            engine = ShinobiOSEngine()
            jutsu_list = []
            
            for jutsu_id, jutsu in engine.jutsu_database.items():
                jutsu_dict = {
                    "id": jutsu_id,
                    "name": jutsu.name,
                    "chakra_cost": jutsu.chakra_cost,
                    "damage": jutsu.damage,
                    "accuracy": jutsu.accuracy,
                    "range": jutsu.range,
                    "element": jutsu.element,
                    "description": jutsu.description,
                    "special_effects": jutsu.special_effects,
                    "cooldown": jutsu.cooldown
                }
                jutsu_list.append(jutsu_dict)
            
            logger.info(f"Loaded {len(jutsu_list)} jutsu from ShinobiOS")
            return jutsu_list
        except Exception as e:
            logger.error(f"Error loading ShinobiOS jutsu: {e}")
            return []
    
    def convert_master_jutsu(self, jutsu_data: Dict[str, Any]) -> UnifiedJutsu:
        """Convert master jutsu list format to unified format."""
        return UnifiedJutsu(
            id=jutsu_data.get("id", ""),
            name=jutsu_data.get("name", ""),
            rank=jutsu_data.get("rank", "E"),
            type=jutsu_data.get("type", "Ninjutsu"),
            element=jutsu_data.get("element", "None"),
            description=jutsu_data.get("description", "No description available."),
            chakra_cost=jutsu_data.get("chakra_cost", 0),
            damage=jutsu_data.get("damage", 0),
            accuracy=jutsu_data.get("accuracy", 100),
            target_type=jutsu_data.get("target_type", "opponent"),
            can_miss=jutsu_data.get("can_miss", True),
            shop_cost=jutsu_data.get("shop_cost", 0),
            source_system="master_list"
        )
    
    def convert_solomon_jutsu(self, jutsu_id: str, jutsu_data: Dict[str, Any]) -> UnifiedJutsu:
        """Convert Solomon jutsu format to unified format."""
        return UnifiedJutsu(
            id=jutsu_id,
            name=jutsu_data.get("name", ""),
            rank=jutsu_data.get("rank", "S"),
            type=jutsu_data.get("type", "Ninjutsu"),
            element=jutsu_data.get("element", "None"),
            description=jutsu_data.get("description", "No description available."),
            chakra_cost=jutsu_data.get("chakra_cost", 0),
            stamina_cost=jutsu_data.get("stamina_cost", 0),
            damage=jutsu_data.get("damage", 0),
            accuracy=jutsu_data.get("accuracy", 100),
            special_effects=jutsu_data.get("effects", []),
            phase_requirements=jutsu_data.get("phase_requirement", 0),
            save_dc=jutsu_data.get("save_dc", 0),
            save_type=jutsu_data.get("save_type", ""),
            source_system="solomon"
        )
    
    def convert_core_jutsu(self, jutsu_data: Dict[str, Any]) -> UnifiedJutsu:
        """Convert core jutsu system format to unified format."""
        return UnifiedJutsu(
            id=jutsu_data.get("id", ""),
            name=jutsu_data.get("name", ""),
            element=jutsu_data.get("element", "None"),
            description=jutsu_data.get("description", "No description available."),
            chakra_cost=jutsu_data.get("chakra_cost", 0),
            damage=jutsu_data.get("damage", 0),
            accuracy=jutsu_data.get("accuracy", 100),
            range=jutsu_data.get("range", "close"),
            level_requirement=jutsu_data.get("level_requirement", 1),
            stat_requirements=jutsu_data.get("stat_requirements", {}),
            achievement_requirements=jutsu_data.get("achievement_requirements", []),
            special_effects=jutsu_data.get("special_effects", []),
            cooldown=jutsu_data.get("cooldown", 0),
            rarity=jutsu_data.get("rarity", "Common"),
            source_system="core"
        )
    
    def convert_shinobios_jutsu(self, jutsu_data: Dict[str, Any]) -> UnifiedJutsu:
        """Convert ShinobiOS jutsu format to unified format."""
        return UnifiedJutsu(
            id=jutsu_data.get("id", ""),
            name=jutsu_data.get("name", ""),
            element=jutsu_data.get("element", "None"),
            description=jutsu_data.get("description", "No description available."),
            chakra_cost=jutsu_data.get("chakra_cost", 0),
            damage=jutsu_data.get("damage", 0),
            accuracy=jutsu_data.get("accuracy", 100),
            range=jutsu_data.get("range", "close"),
            special_effects=jutsu_data.get("special_effects", []),
            cooldown=jutsu_data.get("cooldown", 0),
            source_system="shinobios"
        )
    
    def add_jutsu(self, jutsu: UnifiedJutsu) -> bool:
        """Add a jutsu to the consolidated database, handling duplicates."""
        if jutsu.id in self.consolidated_jutsu:
            existing = self.consolidated_jutsu[jutsu.id]
            if existing.name != jutsu.name:
                # Different jutsu with same ID - create unique ID
                jutsu.id = f"{jutsu.id}_{jutsu.source_system}"
                logger.warning(f"Duplicate ID resolved: {jutsu.id}")
            else:
                # Same jutsu - merge properties
                self.merge_jutsu_properties(existing, jutsu)
                self.duplicates.append(jutsu.id)
                return False
        
        self.consolidated_jutsu[jutsu.id] = jutsu
        return True
    
    def merge_jutsu_properties(self, existing: UnifiedJutsu, new: UnifiedJutsu):
        """Merge properties from new jutsu into existing one."""
        # Merge descriptions if one is better
        if len(new.description) > len(existing.description) and new.description != "No description available.":
            existing.description = new.description
        
        # Merge special effects
        for effect in new.special_effects:
            if effect not in existing.special_effects:
                existing.special_effects.append(effect)
        
        # Merge stat requirements
        for stat, value in new.stat_requirements.items():
            if stat not in existing.stat_requirements or value > existing.stat_requirements[stat]:
                existing.stat_requirements[stat] = value
        
        # Merge achievement requirements
        for achievement in new.achievement_requirements:
            if achievement not in existing.achievement_requirements:
                existing.achievement_requirements.append(achievement)
        
        # Update source system
        existing.source_system = f"{existing.source_system}+{new.source_system}"
    
    def consolidate_all_jutsu(self):
        """Consolidate all jutsu from all sources."""
        logger.info("Starting jutsu consolidation...")
        
        # Load jutsu from all sources
        master_jutsu = self.load_master_jutsu_list()
        solomon_jutsu = self.load_solomon_jutsu()
        core_jutsu = self.load_core_jutsu_system()
        shinobios_jutsu = self.load_shinobios_jutsu()
        
        # Convert and add master jutsu
        logger.info("Processing master jutsu list...")
        for jutsu_data in master_jutsu:
            try:
                jutsu = self.convert_master_jutsu(jutsu_data)
                self.add_jutsu(jutsu)
            except Exception as e:
                self.errors.append(f"Error converting master jutsu {jutsu_data.get('id', 'unknown')}: {e}")
        
        # Convert and add Solomon jutsu
        logger.info("Processing Solomon jutsu...")
        for jutsu_id, jutsu_data in solomon_jutsu.items():
            try:
                jutsu = self.convert_solomon_jutsu(jutsu_id, jutsu_data)
                self.add_jutsu(jutsu)
            except Exception as e:
                self.errors.append(f"Error converting Solomon jutsu {jutsu_id}: {e}")
        
        # Convert and add core jutsu
        logger.info("Processing core jutsu system...")
        for jutsu_data in core_jutsu:
            try:
                jutsu = self.convert_core_jutsu(jutsu_data)
                self.add_jutsu(jutsu)
            except Exception as e:
                self.errors.append(f"Error converting core jutsu {jutsu_data.get('id', 'unknown')}: {e}")
        
        # Convert and add ShinobiOS jutsu
        logger.info("Processing ShinobiOS jutsu...")
        for jutsu_data in shinobios_jutsu:
            try:
                jutsu = self.convert_shinobios_jutsu(jutsu_data)
                self.add_jutsu(jutsu)
            except Exception as e:
                self.errors.append(f"Error converting ShinobiOS jutsu {jutsu_data.get('id', 'unknown')}: {e}")
        
        logger.info(f"Consolidation complete: {len(self.consolidated_jutsu)} unique jutsu")
        logger.info(f"Duplicates merged: {len(self.duplicates)}")
        if self.errors:
            logger.warning(f"Errors encountered: {len(self.errors)}")
    
    def save_consolidated_jutsu(self, output_file: str = "data/jutsu/unified_jutsu_database.json"):
        """Save the consolidated jutsu database to a JSON file."""
        logger.info(f"Saving consolidated jutsu to {output_file}...")
        
        # Convert to JSON-serializable format
        jutsu_list = []
        for jutsu in self.consolidated_jutsu.values():
            jutsu_dict = asdict(jutsu)
            jutsu_list.append(jutsu_dict)
        
        # Sort by ID for consistent output
        jutsu_list.sort(key=lambda x: x["id"])
        
        # Create output directory if it doesn't exist
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(jutsu_list, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(jutsu_list)} jutsu to {output_file}")
    
    def generate_report(self):
        """Generate a consolidation report."""
        logger.info("Generating consolidation report...")
        
        report = {
            "summary": {
                "total_jutsu": len(self.consolidated_jutsu),
                "duplicates_merged": len(self.duplicates),
                "errors": len(self.errors)
            },
            "by_source": {},
            "by_element": {},
            "by_rank": {},
            "duplicates": self.duplicates,
            "errors": self.errors
        }
        
        # Count by source system
        for jutsu in self.consolidated_jutsu.values():
            source = jutsu.source_system
            report["by_source"][source] = report["by_source"].get(source, 0) + 1
            
            element = jutsu.element
            report["by_element"][element] = report["by_element"].get(element, 0) + 1
            
            rank = jutsu.rank
            report["by_rank"][rank] = report["by_rank"].get(rank, 0) + 1
        
        # Save report
        report_file = "data/jutsu/consolidation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Report saved to {report_file}")
        return report

def main():
    """Main consolidation function."""
    logger.info("🥷 Starting Jutsu System Consolidation")
    logger.info("=" * 50)
    
    # Create consolidator
    consolidator = JutsuConsolidator()
    
    # Perform consolidation
    consolidator.consolidate_all_jutsu()
    
    # Save results
    consolidator.save_consolidated_jutsu()
    
    # Generate report
    report = consolidator.generate_report()
    
    # Print summary
    logger.info("=" * 50)
    logger.info("🎯 CONSOLIDATION COMPLETE!")
    logger.info(f"📊 Total Jutsu: {report['summary']['total_jutsu']}")
    logger.info(f"🔄 Duplicates Merged: {report['summary']['duplicates_merged']}")
    logger.info(f"❌ Errors: {report['summary']['errors']}")
    
    logger.info("\n📈 By Source System:")
    for source, count in report["by_source"].items():
        logger.info(f"   {source}: {count} jutsu")
    
    logger.info("\n🌪️ By Element:")
    for element, count in report["by_element"].items():
        logger.info(f"   {element}: {count} jutsu")
    
    logger.info("\n⭐ By Rank:")
    for rank, count in report["by_rank"].items():
        logger.info(f"   {rank}: {count} jutsu")
    
    if consolidator.errors:
        logger.warning("\n⚠️ Errors encountered:")
        for error in consolidator.errors[:5]:  # Show first 5 errors
            logger.warning(f"   {error}")
        if len(consolidator.errors) > 5:
            logger.warning(f"   ... and {len(consolidator.errors) - 5} more")
    
    logger.info("\n✅ Consolidation script completed successfully!")

if __name__ == "__main__":
    main() 