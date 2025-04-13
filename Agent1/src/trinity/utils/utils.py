"""
Utility functions for Trinity Core
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent

def setup_python_path(additional_paths: Optional[List[str]] = None):
    """Set up Python path for the project"""
    base_path = get_project_root()
    paths_to_add = [str(base_path)]
    
    if additional_paths:
        paths_to_add.extend(additional_paths)
    
    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing invalid characters"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()

def ensure_dir_exists(path: str) -> None:
    """Ensure a directory exists, create it if it doesn't"""
    os.makedirs(path, exist_ok=True)

def load_json_config(config_path: str) -> Dict[str, Any]:
    """Load a JSON configuration file"""
    import json
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {} 