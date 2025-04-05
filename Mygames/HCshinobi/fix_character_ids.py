import os
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_character_files():
    """Add missing 'id' field to all character files."""
    data_dir = Path("data/characters")
    
    if not data_dir.exists():
        logger.error(f"Character directory not found: {data_dir}")
        return
        
    for file_path in data_dir.glob("*.json"):
        try:
            # Read the current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Get the character ID from the filename (without .json extension)
            character_id = file_path.stem
            
            # Add or update the id field
            data['id'] = character_id
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            logger.info(f"Added 'id' field to {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")

if __name__ == "__main__":
    fix_character_files() 