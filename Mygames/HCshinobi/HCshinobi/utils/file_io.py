"""
File I/O utilities for the HCShinobi application.
Contains functions for loading and saving JSON data, both synchronously and asynchronously.
"""

import os
import json
import logging
import aiofiles
from typing import Any, Optional, Dict, Union

logger = logging.getLogger(__name__)

def ensure_directory(path: str) -> None:
    """Ensure a directory exists and has proper permissions."""
    try:
        os.makedirs(path, exist_ok=True)
        # On Windows, we don't need to set permissions explicitly
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def load_json(file_path: str, default=None) -> Optional[Dict[str, Any]]:
    """
    Load data from a JSON file (synchronous).
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid JSON
        
    Returns:
        Loaded JSON data as dictionary, or default value if file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return default
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return default
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return default

def save_json(file_path: str, data, indent=4) -> bool:
    """
    Save data to a JSON file (synchronous).
    
    Args:
        file_path: Path to save the JSON file
        data: Data to save (must be JSON serializable)
        indent: Number of spaces for indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            logger.debug(f"Data saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

async def async_load_json(file_path: str, default=None) -> Optional[Dict[str, Any]]:
    """
    Load data from a JSON file (asynchronous).
    
    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid JSON
        
    Returns:
        Loaded JSON data as dictionary, or default value if file doesn't exist
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return default
            
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            data = json.loads(content)
            return data
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in file: {file_path}")
        return default
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return default

async def async_save_json(file_path: str, data, indent=4) -> bool:
    """
    Save data to a JSON file (asynchronous).
    
    Args:
        file_path: Path to save the JSON file
        data: Data to save (must be JSON serializable)
        indent: Number of spaces for indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        content = json.dumps(data, indent=indent, ensure_ascii=False)
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
            logger.debug(f"Data saved to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False
