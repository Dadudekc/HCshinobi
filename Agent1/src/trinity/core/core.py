"""
Core functionality for Trinity Core
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any

class TrinityCore:
    """Main class for Trinity Core functionality"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'config.json')
        self.base_path = Path(__file__).parent.parent
        self._setup_paths()
    
    def _setup_paths(self):
        """Set up system paths for Trinity Core"""
        if str(self.base_path) not in sys.path:
            sys.path.insert(0, str(self.base_path))
    
    def get_project_root(self) -> Path:
        """Get the project root directory"""
        return self.base_path
    
    def get_config(self) -> Dict[str, Any]:
        """Get Trinity Core configuration"""
        # Implement config loading logic here
        return {}
    
    def get_version(self) -> str:
        """Get Trinity Core version"""
        from . import __version__
        return __version__ 