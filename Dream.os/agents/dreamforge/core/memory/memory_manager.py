from typing import Dict, Any, List
import json
import os
from datetime import datetime

class MemoryManager:
    """Manages persistent memory storage for agents."""
    
    def __init__(self, storage_dir: str = "memory"):
        """Initialize the memory manager."""
        self.storage_dir = storage_dir
        self._ensure_storage_exists()
        self._feedback_history = []
        
    def _ensure_storage_exists(self) -> None:
        """Ensure storage directory exists."""
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def store_feedback(self, feedback: Dict[str, Any]) -> None:
        """Store feedback in memory."""
        feedback['timestamp'] = datetime.now().isoformat()
        self._feedback_history.append(feedback)
        self._save_feedback()
        
    def get_feedback_history(self) -> List[Dict[str, Any]]:
        """Get all stored feedback."""
        return self._feedback_history.copy()
        
    def _save_feedback(self) -> None:
        """Save feedback to persistent storage."""
        feedback_file = os.path.join(self.storage_dir, 'feedback_history.json')
        with open(feedback_file, 'w') as f:
            json.dump(self._feedback_history, f, indent=2)
            
    def _load_feedback(self) -> None:
        """Load feedback from persistent storage."""
        feedback_file = os.path.join(self.storage_dir, 'feedback_history.json')
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                self._feedback_history = json.load(f)
                
    def clear_feedback(self) -> None:
        """Clear all stored feedback."""
        self._feedback_history = []
        feedback_file = os.path.join(self.storage_dir, 'feedback_history.json')
        if os.path.exists(feedback_file):
            os.remove(feedback_file) 