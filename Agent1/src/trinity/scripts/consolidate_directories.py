"""
Directory Consolidation Script
Handles the consolidation of duplicate directories and files across the project.
"""

import os
import shutil
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List, Tuple

class DirectoryConsolidator:
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.logger = self._setup_logging()
        self.file_hashes: Dict[str, List[str]] = {}
        self.consolidated_files: Dict[str, str] = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("consolidator")
        logger.setLevel(logging.INFO)
        
        handler = logging.FileHandler("consolidation.log")
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        
        return logger
        
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to hash {file_path}: {e}")
            return ""
            
    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        if file_path.is_dir():
            return False
            
        # Skip certain files and directories
        skip_patterns = {
            "__pycache__",
            ".git",
            ".pytest_cache",
            "venv",
            ".venv",
            ".coverage",
            ".DS_Store"
        }
        
        return not any(pattern in str(file_path) for pattern in skip_patterns)
        
    def scan_directory(self, directory: Path) -> None:
        """Scan a directory and record file hashes."""
        try:
            for item in directory.rglob("*"):
                if self._should_process_file(item):
                    file_hash = self._compute_file_hash(item)
                    if file_hash:
                        if file_hash not in self.file_hashes:
                            self.file_hashes[file_hash] = []
                        self.file_hashes[file_hash].append(str(item))
        except Exception as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
            
    def find_duplicates(self) -> Dict[str, List[str]]:
        """Find duplicate files based on hash values."""
        return {
            hash_value: paths
            for hash_value, paths in self.file_hashes.items()
            if len(paths) > 1
        }
        
    def consolidate_directories(
        self,
        source_dirs: List[str],
        target_dir: str
    ) -> None:
        """Consolidate multiple directories into a target directory."""
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        # Scan all source directories
        for source_dir in source_dirs:
            self.scan_directory(Path(source_dir))
            
        duplicates = self.find_duplicates()
        
        # Process each set of duplicate files
        for hash_value, file_paths in duplicates.items():
            try:
                # Choose the file with the most recent modification time
                source_file = max(
                    file_paths,
                    key=lambda p: os.path.getmtime(p)
                )
                
                # Determine the relative path structure
                rel_path = os.path.relpath(
                    source_file,
                    os.path.commonpath(file_paths)
                )
                
                # Create the target path
                target_file = target_path / rel_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy the file if it doesn't exist
                if not target_file.exists():
                    shutil.copy2(source_file, target_file)
                    self.logger.info(f"Consolidated {source_file} -> {target_file}")
                    
                # Record the consolidation
                self.consolidated_files[hash_value] = str(target_file)
                
                # Remove duplicate files
                for file_path in file_paths:
                    if file_path != str(target_file):
                        Path(file_path).unlink()
                        self.logger.info(f"Removed duplicate: {file_path}")
                        
            except Exception as e:
                self.logger.error(f"Error consolidating {file_paths}: {e}")
                
    def save_report(self, output_file: str = "consolidation_report.json") -> None:
        """Save consolidation report to a JSON file."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "duplicates_found": self.find_duplicates(),
            "consolidated_files": self.consolidated_files,
            "statistics": {
                "total_files_processed": sum(len(paths) for paths in self.file_hashes.values()),
                "duplicate_sets": len(self.find_duplicates()),
                "files_consolidated": len(self.consolidated_files)
            }
        }
        
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
            
def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize consolidator
        consolidator = DirectoryConsolidator()
        
        # Define source and target directories
        source_dirs = [
            "Agent2/Agent3/Agent4/overnight_scripts",
            "Agent2/src/core",
            "overnight_scripts"
        ]
        
        target_dir = "consolidated"
        
        # Perform consolidation
        consolidator.consolidate_directories(source_dirs, target_dir)
        
        # Save report
        consolidator.save_report()
        
        logger.info("Consolidation completed successfully")
        
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        raise

if __name__ == "__main__":
    main() 