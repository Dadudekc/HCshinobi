"""Jutsu data management for the HCshinobi project."""
import json
import os
import logging
from typing import Dict, Any, Optional, List

from .constants import _DATA_DIR

logger = logging.getLogger(__name__)

class JutsuData:
    """Manages jutsu data and operations."""
    
    def __init__(self):
        """Initialize the jutsu data system."""
        self.jutsu_file = os.path.join(_DATA_DIR, "naruto_elemental_jutsu.json")
        self.jutsu_data = self._load_jutsu_data()
        
    def _load_jutsu_data(self) -> Dict[str, Any]:
        """Load jutsu data from the JSON file."""
        try:
            with open(self.jutsu_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Jutsu data file not found at {self.jutsu_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding jutsu data file: {e}")
            return {}
            
    def get_jutsu_info(self, jutsu_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific jutsu.
        
        Args:
            jutsu_name: Name of the jutsu to look up
            
        Returns:
            Jutsu information if found, None otherwise
        """
        # Check in detailed_jutsu sections
        for element in self.jutsu_data.get('detailed_jutsu', {}).values():
            for rank in element.values():
                for jutsu in rank:
                    if jutsu['name'].lower() == jutsu_name.lower():
                        return jutsu
                        
        # Check in combination_jutsu
        for jutsu in self.jutsu_data.get('combination_jutsu', []):
            if jutsu['name'].lower() == jutsu_name.lower():
                return jutsu
                
        return None
        
    def get_jutsu_chakra_cost(self, jutsu_name: str) -> int:
        """Get the chakra cost of a jutsu.
        
        Args:
            jutsu_name: Name of the jutsu
            
        Returns:
            Chakra cost if found, 0 otherwise
        """
        jutsu_info = self.get_jutsu_info(jutsu_name)
        return jutsu_info.get('chakra_cost', 0) if jutsu_info else 0
        
    def get_jutsu_rank(self, jutsu_name: str) -> str:
        """Get the rank of a jutsu.
        
        Args:
            jutsu_name: Name of the jutsu
            
        Returns:
            Rank if found, 'E' (Entry Level) otherwise
        """
        jutsu_info = self.get_jutsu_info(jutsu_name)
        return jutsu_info.get('rank', 'E') if jutsu_info else 'E'
        
    def get_jutsu_description(self, jutsu_name: str) -> str:
        """Get the description of a jutsu.
        
        Args:
            jutsu_name: Name of the jutsu
            
        Returns:
            Description if found, empty string otherwise
        """
        jutsu_info = self.get_jutsu_info(jutsu_name)
        return jutsu_info.get('description', '') if jutsu_info else ''
        
    def get_jutsu_hand_seals(self, jutsu_name: str) -> List[str]:
        """Get the hand seals required for a jutsu.
        
        Args:
            jutsu_name: Name of the jutsu
            
        Returns:
            List of hand seals if found, empty list otherwise
        """
        jutsu_info = self.get_jutsu_info(jutsu_name)
        return jutsu_info.get('hand_seals', []) if jutsu_info else []
        
    def get_jutsu_by_rank(self, rank: str) -> List[str]:
        """Get all jutsu of a specific rank.
        
        Args:
            rank: Rank to filter by (E, D, C, B, A, S)
            
        Returns:
            List of jutsu names
        """
        jutsu_list = []
        
        # Check in detailed_jutsu sections
        for element in self.jutsu_data.get('detailed_jutsu', {}).values():
            for rank_jutsu in element.get(rank, []):
                jutsu_list.append(rank_jutsu['name'])
                
        # Check in combination_jutsu
        for jutsu in self.jutsu_data.get('combination_jutsu', []):
            if jutsu['rank'] == rank:
                jutsu_list.append(jutsu['name'])
                
        return jutsu_list 