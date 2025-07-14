#!/usr/bin/env python3
"""
Legacy Content Cleanup Script
Removes old exam references and updates battle logs to modern format.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any

def cleanup_battle_logs():
    """Clean up battle logs and remove legacy references."""
    data_dir = Path("data")
    battles_dir = data_dir / "battles"
    
    if not battles_dir.exists():
        print("No battles directory found.")
        return
    
    legacy_patterns = [
        r"Academy Entrance Test",
        r"Instructor Ayame",
        r"entrance exam",
        r"academy exam",
        r"test instructor"
    ]
    
    cleaned_count = 0
    
    for battle_file in battles_dir.glob("*.json"):
        try:
            with open(battle_file, 'r', encoding='utf-8') as f:
                battle_data = json.load(f)
            
            # Check if this is a legacy battle log
            needs_update = False
            
            # Look for legacy patterns in battle data
            battle_str = json.dumps(battle_data, ensure_ascii=False)
            for pattern in legacy_patterns:
                if re.search(pattern, battle_str, re.IGNORECASE):
                    needs_update = True
                    break
            
            if needs_update:
                print(f"Cleaning up legacy battle log: {battle_file.name}")
                
                # Update battle log entries
                if "battle_log" in battle_data:
                    updated_log = []
                    for entry in battle_data["battle_log"]:
                        # Replace legacy references
                        updated_entry = entry
                        for pattern in legacy_patterns:
                            updated_entry = re.sub(
                                pattern, 
                                "Modern Combat Mission", 
                                updated_entry, 
                                flags=re.IGNORECASE
                            )
                        updated_log.append(updated_entry)
                    battle_data["battle_log"] = updated_log
                
                # Update mission name if present
                if "mission_name" in battle_data:
                    battle_data["mission_name"] = "Modern Combat Mission"
                
                # Save updated battle data
                with open(battle_file, 'w', encoding='utf-8') as f:
                    json.dump(battle_data, f, indent=2, ensure_ascii=False)
                
                cleaned_count += 1
        
        except Exception as e:
            print(f"Error processing {battle_file}: {e}")
    
    print(f"Cleaned up {cleaned_count} legacy battle logs.")

def cleanup_character_data():
    """Clean up character data files for legacy references."""
    data_dir = Path("data")
    characters_dir = data_dir / "characters"
    
    if not characters_dir.exists():
        print("No characters directory found.")
        return
    
    legacy_patterns = [
        r"Academy Entrance Test",
        r"Instructor Ayame",
        r"entrance exam",
        r"academy exam"
    ]
    
    cleaned_count = 0
    
    for char_file in characters_dir.glob("*.json"):
        try:
            with open(char_file, 'r', encoding='utf-8') as f:
                char_data = json.load(f)
            
            # Check for legacy references
            needs_update = False
            char_str = json.dumps(char_data, ensure_ascii=False)
            
            for pattern in legacy_patterns:
                if re.search(pattern, char_str, re.IGNORECASE):
                    needs_update = True
                    break
            
            if needs_update:
                print(f"Cleaning up legacy character data: {char_file.name}")
                
                # Update achievements
                if "achievements" in char_data:
                    updated_achievements = []
                    for achievement in char_data["achievements"]:
                        updated_achievement = achievement
                        for pattern in legacy_patterns:
                            updated_achievement = re.sub(
                                pattern,
                                "Modern Combat Mission",
                                updated_achievement,
                                flags=re.IGNORECASE
                            )
                        updated_achievements.append(updated_achievement)
                    char_data["achievements"] = updated_achievements
                
                # Update mission history
                if "mission_history" in char_data:
                    updated_history = []
                    for mission in char_data["mission_history"]:
                        if isinstance(mission, dict) and "name" in mission:
                            for pattern in legacy_patterns:
                                mission["name"] = re.sub(
                                    pattern,
                                    "Modern Combat Mission",
                                    mission["name"],
                                    flags=re.IGNORECASE
                                )
                        updated_history.append(mission)
                    char_data["mission_history"] = updated_history
                
                # Save updated character data
                with open(char_file, 'w', encoding='utf-8') as f:
                    json.dump(char_data, f, indent=2, ensure_ascii=False)
                
                cleaned_count += 1
        
        except Exception as e:
            print(f"Error processing {char_file}: {e}")
    
    print(f"Cleaned up {cleaned_count} character data files.")

def update_mission_definitions():
    """Update mission definitions to modern format."""
    mission_file = Path("data/missions/mission_definitions.json")
    
    if not mission_file.exists():
        print("Mission definitions file not found.")
        return
    
    try:
        with open(mission_file, 'r', encoding='utf-8') as f:
            missions = json.load(f)
        
        # Check for legacy missions
        legacy_missions = []
        for mission_id, mission_data in missions.items():
            if any(pattern in mission_data.get("name", "").lower() 
                   for pattern in ["entrance", "exam", "test", "academy"]):
                legacy_missions.append(mission_id)
        
        if legacy_missions:
            print(f"Found {len(legacy_missions)} legacy missions to update:")
            for mission_id in legacy_missions:
                print(f"  - {mission_id}: {missions[mission_id]['name']}")
            
            # Update legacy missions to modern format
            for mission_id in legacy_missions:
                old_name = missions[mission_id]["name"]
                missions[mission_id]["name"] = f"Modern {missions[mission_id]['rank']}-Rank Mission"
                missions[mission_id]["description"] = f"Updated mission replacing legacy content: {old_name}"
                print(f"Updated {mission_id}: {old_name} → {missions[mission_id]['name']}")
            
            # Save updated missions
            with open(mission_file, 'w', encoding='utf-8') as f:
                json.dump(missions, f, indent=2, ensure_ascii=False)
            
            print("Mission definitions updated successfully.")
        else:
            print("No legacy missions found in definitions.")
    
    except Exception as e:
        print(f"Error updating mission definitions: {e}")

def create_modern_battle_template():
    """Create a modern battle template for new battles."""
    template = {
        "battle_id": "modern_battle_template",
        "mission_name": "Modern Combat Mission",
        "mission_type": "elimination",
        "difficulty": "C",
        "environment": "forest",
        "participants": {
            "player": {
                "name": "Player Character",
                "hp": 100,
                "max_hp": 100,
                "chakra": 100,
                "max_chakra": 100,
                "level": 1,
                "rank": "Genin"
            },
            "enemy": {
                "name": "Enemy Shinobi",
                "hp": 50,
                "max_hp": 50,
                "chakra": 40,
                "max_chakra": 40,
                "level": 1,
                "rank": "Enemy"
            }
        },
        "battle_log": [
            {
                "turn": 1,
                "actor": "Player Character",
                "target": "Enemy Shinobi",
                "jutsu": "Basic Attack",
                "damage": 25,
                "success": True,
                "narration": "Player Character attacks Enemy Shinobi for 25 damage!"
            }
        ],
        "current_turn": 1,
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
    
    # Save template
    template_file = Path("data/battles/modern_battle_template.json")
    template_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(template_file, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    
    print("Created modern battle template.")

def main():
    """Main cleanup function."""
    print("🧹 HCShinobi Legacy Content Cleanup")
    print("=" * 50)
    
    print("\n1. Cleaning up battle logs...")
    cleanup_battle_logs()
    
    print("\n2. Cleaning up character data...")
    cleanup_character_data()
    
    print("\n3. Updating mission definitions...")
    update_mission_definitions()
    
    print("\n4. Creating modern battle template...")
    create_modern_battle_template()
    
    print("\n✅ Legacy content cleanup complete!")
    print("\n📋 Summary of changes:")
    print("• Removed 'Academy Entrance Test' references")
    print("• Updated battle logs to modern format")
    print("• Cleaned up character achievement data")
    print("• Updated mission definitions")
    print("• Created modern battle template")
    print("\n🎯 All systems now use modern, unified content!")

if __name__ == "__main__":
    main() 