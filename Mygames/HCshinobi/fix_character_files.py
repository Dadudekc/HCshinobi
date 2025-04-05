import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_character_files():
    """Update all character files to include all required fields."""
    data_dir = Path("data/characters")
    
    if not data_dir.exists():
        logger.error(f"Character directory not found: {data_dir}")
        return
        
    # Default character structure
    default_structure = {
        "id": "",
        "name": "",
        "clan": "",
        "level": 1,
        "exp": 0,
        "ryo": 0,
        "hp": 100,
        "chakra": 100,
        "stamina": 100,
        "strength": 10,
        "speed": 10,
        "defense": 10,
        "willpower": 10,
        "chakra_control": 10,
        "intelligence": 10,
        "perception": 10,
        "ninjutsu": 10,
        "taijutsu": 10,
        "genjutsu": 10,
        "jutsu": [],
        "equipment": {},
        "inventory": [],
        "is_active": True,
        "status_effects": [],
        "active_effects": {},
        "status_conditions": {},
        "buffs": {},
        "debuffs": {},
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "max_hp": 100,
        "max_chakra": 100,
        "max_stamina": 100,
        "completed_missions": []
    }
    
    for file_path in data_dir.glob("*.json"):
        try:
            # Read the current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the character ID from the filename (without .json extension)
            character_id = file_path.stem
            
            # Create a new data structure with defaults
            new_data = default_structure.copy()
            
            # Update with existing data
            for key, value in data.items():
                if key in new_data:
                    new_data[key] = value
            
            # Ensure ID matches filename
            new_data['id'] = character_id
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Updated {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    fix_character_files() 