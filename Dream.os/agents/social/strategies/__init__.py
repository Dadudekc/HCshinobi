"""
Social media platform strategies package.
"""

from abc import ABC, abstractmethod

class SocialStrategy(ABC):
    """Base class for all social media platform strategies."""
    
    def __init__(self, env):
        self.env = env
        
    @abstractmethod
    def generate_content(self, memory_update: dict) -> str:
        """Generate platform-specific content from memory update."""
        pass
        
    @abstractmethod
    def dispatch_content(self, content: str) -> bool:
        """Dispatch content to the platform."""
        pass 