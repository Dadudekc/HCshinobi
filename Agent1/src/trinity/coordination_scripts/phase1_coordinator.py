#!/usr/bin/env python3
"""
Dream.OS Phase 1 Coordinator
Coordinates agent activities during the Sweep phase of deduplication.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from progress_updater import ProgressUpdater
from file_hasher import FileHasher

class Phase1Coordinator:
    """Coordinates Phase 1 (Sweep) activities."""
    
    def __init__(self, plan_path: str = "deduplication_plan.json"):
        """Initialize the Phase 1 coordinator."""
        self.plan_path = Path(plan_path)
        self.plan = self._load_plan()
        self.progress_updater = ProgressUpdater()
        self.logger = logging.getLogger(__name__)
        self.file_hasher = FileHasher(self.plan['target_zones'])
    
    def _load_plan(self) -> Dict[str, Any]:
        """Load the deduplication plan."""
        try:
            with open(self.plan_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load plan: {str(e)}")
            raise
    
    def _initialize_agents(self) -> None:
        """Initialize all agents for Phase 1."""
        # CodeIntelAgent starts file hashing
        self.progress_updater.update_agent_status(
            "CodeIntelAgent",
            "active",
            "initializing_file_hasher",
            {"files_processed": 0, "hashes_computed": 0}
        )
        
        # FileWatcher starts monitoring
        self.progress_updater.update_agent_status(
            "FileWatcher",
            "active",
            "monitoring_drift",
            {"alerts": []}
        )
        
        # SecurityAgent starts scanning
        self.progress_updater.update_agent_status(
            "SecurityAgent",
            "active",
            "scanning_sensitive",
            {"sensitive_files_found": 0}
        )
        
        # SchemaAgent starts indexing
        self.progress_updater.update_agent_status(
            "SchemaAgent",
            "active",
            "indexing_schemas",
            {"schemas_indexed": 0}
        )
        
        # Other agents in standby
        for agent in ["TestingAgent", "GitAgent"]:
            self.progress_updater.update_agent_status(
                agent,
                "standby",
                f"awaiting_phase_{2 if agent == 'TestingAgent' else 4}"
            )
    
    def _process_target_zone(self, zone: Dict[str, Any]) -> None:
        """Process a single target zone."""
        path = Path(zone['path'])
        if not path.exists():
            self.logger.warning(f"Zone does not exist: {path}")
            self.progress_updater.update_zone_status(
                zone['path'],
                "skipped",
                {"error": "Zone does not exist"}
            )
            return
        
        self.progress_updater.update_zone_status(
            zone['path'],
            "in_progress",
            {"files_processed": 0, "duplicates_found": 0}
        )
        
        try:
            # Update progress for file inventory
            self.progress_updater.update_checkpoint(
                "file_inventory",
                "in_progress",
                {"zone": zone['path'], "status": "scanning"}
            )
            
            # Scan directory and compute hashes
            self.file_hasher.scan_directory(path)
            
            # Update progress for hash calculation
            self.progress_updater.update_checkpoint(
                "hash_calculation",
                "in_progress",
                {"zone": zone['path'], "status": "computing"}
            )
            
            # Find duplicates in this zone
            duplicates = self.file_hasher.find_duplicates()
            
            # Update progress for initial grouping
            self.progress_updater.update_checkpoint(
                "initial_grouping",
                "in_progress",
                {
                    "zone": zone['path'],
                    "groups_formed": len(duplicates),
                    "total_duplicates": sum(len(paths) - 1 for paths in duplicates.values())
                }
            )
            
            # Update zone status
            self.progress_updater.update_zone_status(
                zone['path'],
                "completed",
                {
                    "files_processed": len(self.file_hasher.file_metadata),
                    "duplicates_found": sum(len(paths) - 1 for paths in duplicates.values())
                }
            )
            
            # Save zone-specific results
            output_path = Path(f"logs/phase1_zone_{path.name}_results.json")
            self.file_hasher.save_results(output_path)
            
        except Exception as e:
            self.logger.error(f"Failed to process zone {path}: {str(e)}")
            self.progress_updater.update_zone_status(
                zone['path'],
                "failed",
                {"error": str(e)}
            )
            self.progress_updater.add_error(f"Failed to process zone {path}: {str(e)}")
    
    def _save_global_results(self) -> None:
        """Save global results and update progress."""
        try:
            # Get global duplicates
            duplicates = self.file_hasher.find_global_duplicates()
            total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
            
            # Update final metrics
            self.progress_updater.update_checkpoint(
                "file_inventory",
                "completed",
                {
                    "total_files": len(self.file_hasher.global_metadata),
                    "files_processed": len(self.file_hasher.global_metadata)
                }
            )
            
            self.progress_updater.update_checkpoint(
                "hash_calculation",
                "completed",
                {
                    "total_files": len(self.file_hasher.global_metadata),
                    "files_hashed": len(self.file_hasher.global_metadata)
                }
            )
            
            self.progress_updater.update_checkpoint(
                "initial_grouping",
                "completed",
                {
                    "groups_formed": len(duplicates),
                    "total_duplicates": total_duplicates
                }
            )
            
            # Save global results
            output_path = Path("logs/phase1_global_results.json")
            self.file_hasher.save_global_results(output_path)
            
            # Update CodeIntelAgent metrics
            self.progress_updater.update_agent_status(
                "CodeIntelAgent",
                "completed",
                "file_hashing_complete",
                {
                    "files_processed": len(self.file_hasher.global_metadata),
                    "hashes_computed": len(self.file_hasher.global_metadata),
                    "groups_formed": len(duplicates),
                    "total_duplicates": total_duplicates
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to save global results: {str(e)}")
            self.progress_updater.add_error(f"Failed to save global results: {str(e)}")
    
    def run(self) -> None:
        """Run Phase 1 coordination."""
        try:
            # Initialize agents
            self._initialize_agents()
            
            # Process each target zone
            for zone in self.plan['target_zones']:
                self._process_target_zone(zone)
            
            # Save global results and update final status
            self._save_global_results()
            
            # Notify completion
            self.logger.info("Phase 1 (Sweep) completed successfully")
            
        except Exception as e:
            self.logger.error(f"Phase 1 failed: {str(e)}")
            self.progress_updater.add_error(f"Phase 1 failed: {str(e)}")
            raise

def main():
    """Main entry point for Phase 1 coordination."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize and run coordinator
    coordinator = Phase1Coordinator()
    coordinator.run()

if __name__ == "__main__":
    main() 