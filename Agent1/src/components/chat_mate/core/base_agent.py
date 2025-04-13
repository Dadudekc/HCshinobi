"""
Thea Task Engine - Base Agent
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    def execute_task(self, task: Dict[str, Any]) -> bool:
        """Execute a task and return success status"""
        pass 