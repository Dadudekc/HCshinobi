#!/usr/bin/env python3
"""
Progress Updater for Dream.OS Deduplication
Handles progress tracking and status updates during the deduplication process.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class ProgressUpdater:
    """Manages progress tracking and status updates for the deduplication process."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the progress updater."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        self.agent_statuses: Dict[str, Dict[str, Any]] = {}
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []
        self._initialize_status_file()
    
    def _initialize_status_file(self) -> None:
        """Initialize or load the status file."""
        status_file = self.log_dir / "dedup_status.json"
        if status_file.exists():
            try:
                with open(status_file, 'r') as f:
                    data = json.load(f)
                    self.agent_statuses = data.get("agents", {})
                    self.checkpoints = data.get("checkpoints", {})
                    self.errors = data.get("errors", [])
            except Exception as e:
                self.logger.error(f"Failed to load status file: {str(e)}")
                self._create_new_status_file()
        else:
            self._create_new_status_file()
    
    def _create_new_status_file(self) -> None:
        """Create a new status file with default values."""
        self.agent_statuses = {}
        self.checkpoints = {
            "functional_grouping": {"status": "pending", "details": {}},
            "origin_tracking": {"status": "pending", "details": {}},
            "dependency_mapping": {"status": "pending", "details": {}}
        }
        self.errors = []
        self._save_status()
    
    def _save_status(self) -> None:
        """Save current status to the status file."""
        status_data = {
            "last_updated": datetime.now().isoformat(),
            "agents": self.agent_statuses,
            "checkpoints": self.checkpoints,
            "errors": self.errors
        }
        
        try:
            status_file = self.log_dir / "dedup_status.json"
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save status: {str(e)}")
    
    def update_agent_status(
        self,
        agent_name: str,
        status: str,
        activity: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status of an agent."""
        self.agent_statuses[agent_name] = {
            "status": status,
            "activity": activity,
            "details": details or {},
            "last_updated": datetime.now().isoformat()
        }
        self._save_status()
        self.logger.info(f"Agent {agent_name} status updated: {status} - {activity}")
    
    def update_checkpoint(
        self,
        checkpoint: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update the status of a checkpoint."""
        if checkpoint not in self.checkpoints:
            self.logger.warning(f"Unknown checkpoint: {checkpoint}")
            return
        
        self.checkpoints[checkpoint] = {
            "status": status,
            "details": details or {},
            "last_updated": datetime.now().isoformat()
        }
        self._save_status()
        self.logger.info(f"Checkpoint {checkpoint} status updated: {status}")
    
    def add_error(self, error_message: str) -> None:
        """Add an error message to the log."""
        timestamp = datetime.now().isoformat()
        error_entry = {
            "timestamp": timestamp,
            "message": error_message
        }
        self.errors.append(error_entry)
        self._save_status()
        self.logger.error(f"Error logged: {error_message}")
    
    def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get the current status of an agent."""
        return self.agent_statuses.get(agent_name, {
            "status": "unknown",
            "activity": "none",
            "details": {},
            "last_updated": None
        })
    
    def get_checkpoint_status(self, checkpoint: str) -> Dict[str, Any]:
        """Get the current status of a checkpoint."""
        return self.checkpoints.get(checkpoint, {
            "status": "unknown",
            "details": {},
            "last_updated": None
        })
    
    def get_all_errors(self) -> List[Dict[str, Any]]:
        """Get all logged errors."""
        return self.errors
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of the current progress."""
        total_checkpoints = len(self.checkpoints)
        completed_checkpoints = sum(
            1 for cp in self.checkpoints.values()
            if cp.get("status") == "completed"
        )
        
        active_agents = sum(
            1 for agent in self.agent_statuses.values()
            if agent.get("status") == "active"
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "checkpoints": {
                "total": total_checkpoints,
                "completed": completed_checkpoints,
                "progress_percentage": (completed_checkpoints / total_checkpoints * 100)
                if total_checkpoints > 0 else 0
            },
            "agents": {
                "total": len(self.agent_statuses),
                "active": active_agents
            },
            "errors": len(self.errors)
        }
    
    def clear_errors(self) -> None:
        """Clear all logged errors."""
        self.errors = []
        self._save_status()
        self.logger.info("Error log cleared")

def main():
    """Main entry point for the progress updater."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize updater
    updater = ProgressUpdater()
    
    # Example updates
    updater.update_checkpoint(
        "file_inventory",
        "in_progress",
        {"files_processed": 100, "total_files": 1000}
    )
    
    updater.update_agent_status(
        "CodeIntelAgent",
        "active",
        "hashing_files",
        {"files_processed": 50, "hashes_computed": 50}
    )
    
    updater.update_zone_status(
        "src/",
        "in_progress",
        {"files_processed": 25, "duplicates_found": 5}
    )

if __name__ == "__main__":
    main() 