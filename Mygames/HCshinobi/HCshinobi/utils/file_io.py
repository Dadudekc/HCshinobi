"""
File I/O utilities for HCShinobi bot.
"""

import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> None:
    """Ensure a directory exists and has proper permissions."""
    try:
        os.makedirs(path, exist_ok=True)
        # On Windows, we don't need to set permissions explicitly
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def load_json(path: str) -> Optional[Any]:
    """Load JSON data from a file.
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Loaded JSON data or None if loading fails
    """
    try:
        # Ensure the directory exists
        directory = os.path.dirname(path)
        if directory:
            ensure_directory(directory)
            
        # If the file doesn't exist, return None
        if not os.path.exists(path):
            logger.warning(f"File not found: {path}")
            return None
            
        # Try to load the file
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        # Check if error is related to BOM and try with utf-8-sig encoding
        if "BOM" in str(e):
            try:
                logger.info(f"Retrying with utf-8-sig encoding for {path}")
                with open(path, 'r', encoding='utf-8-sig') as f:
                    return json.load(f)
            except Exception as inner_e:
                logger.error(f"Failed to parse JSON with utf-8-sig in {path}: {inner_e}")
                return None
        logger.error(f"Invalid JSON in {path}: {e}")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied accessing {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading JSON from {path}: {e}")
        return None

def save_json(path: str, data: Any) -> bool:
    """Save data to a JSON file.
    
    Args:
        path: Path to save the JSON file
        data: Data to save
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Ensure the directory exists
        directory = os.path.dirname(path)
        if directory:
            ensure_directory(directory)
            
        # Save the file with pretty printing
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except PermissionError as e:
        logger.error(f"Permission denied saving to {path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error saving JSON to {path}: {e}")
        return False
