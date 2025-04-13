#!/usr/bin/env python3
"""
Dream.OS File Hasher
Handles file hashing and duplicate detection for Phase 1 of deduplication.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import defaultdict

class FileHasher:
    """Handles file hashing and duplicate detection."""
    
    def __init__(self, target_zones: List[Dict[str, Any]]):
        """Initialize the file hasher with target zones."""
        self.target_zones = target_zones
        self.file_hashes: Dict[str, List[str]] = defaultdict(list)
        self.file_metadata: Dict[str, Dict] = {}
        self.logger = logging.getLogger(__name__)
        self.global_hashes: Dict[str, List[str]] = defaultdict(list)
        self.global_metadata: Dict[str, Dict] = {}
    
    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Failed to hash {file_path}: {str(e)}")
            return ""
    
    def _get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Get metadata for a file."""
        try:
            stat = file_path.stat()
            return {
                "path": str(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:],
                "owner": stat.st_uid,
                "group": stat.st_gid
            }
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {file_path}: {str(e)}")
            return {}
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                return b'\0' in f.read(1024)
        except Exception:
            return True
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        # Skip directories
        if file_path.is_dir():
            return False
            
        # Skip binary files
        if self._is_binary_file(file_path):
            self.logger.debug(f"Skipping binary file: {file_path}")
            return False
            
        # Skip hidden files
        if file_path.name.startswith('.'):
            return False
            
        return True
    
    def scan_directory(self, directory: Path) -> None:
        """Scan a directory for files and compute hashes."""
        try:
            for item in directory.rglob('*'):
                if self._should_process_file(item):
                    file_hash = self._compute_hash(item)
                    if file_hash:
                        self.file_hashes[file_hash].append(str(item))
                        self.file_metadata[str(item)] = self._get_file_metadata(item)
                        # Add to global hashes and metadata
                        self.global_hashes[file_hash].append(str(item))
                        self.global_metadata[str(item)] = self.file_metadata[str(item)]
        except Exception as e:
            self.logger.error(f"Failed to scan {directory}: {str(e)}")
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        """Find duplicate files based on hash values."""
        return {
            hash_value: paths
            for hash_value, paths in self.file_hashes.items()
            if len(paths) > 1
        }
    
    def find_global_duplicates(self) -> Dict[str, List[str]]:
        """Find duplicate files across all zones."""
        return {
            hash_value: paths
            for hash_value, paths in self.global_hashes.items()
            if len(paths) > 1
        }
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get metadata for a specific file."""
        return self.file_metadata.get(file_path, {})
    
    def save_results(self, output_path: Path) -> None:
        """Save scan results to a JSON file."""
        results = {
            "duplicates": self.find_duplicates(),
            "metadata": self.file_metadata,
            "scan_time": str(datetime.now())
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Results saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")
    
    def save_global_results(self, output_path: Path) -> None:
        """Save global scan results to a JSON file."""
        results = {
            "duplicates": self.find_global_duplicates(),
            "metadata": self.global_metadata,
            "scan_time": str(datetime.now()),
            "summary": {
                "total_files": len(self.global_metadata),
                "duplicate_sets": len(self.find_global_duplicates()),
                "total_duplicates": sum(len(paths) - 1 for paths in self.find_global_duplicates().values())
            }
        }
        
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            self.logger.info(f"Global results saved to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to save global results: {str(e)}")

def main():
    """Main entry point for the file hasher."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load target zones from plan
    with open('deduplication_plan.json', 'r') as f:
        plan = json.load(f)
        target_zones = plan['target_zones']
    
    # Initialize hasher
    hasher = FileHasher(target_zones)
    
    # Process each target zone
    for zone in target_zones:
        path = Path(zone['path'])
        if path.exists():
            logging.info(f"Scanning zone: {path}")
            hasher.scan_directory(path)
        else:
            logging.warning(f"Zone does not exist: {path}")
    
    # Save zone-specific results
    output_path = Path('logs/phase1_scan_results.json')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    hasher.save_results(output_path)
    
    # Save global results
    global_output_path = Path('logs/phase1_global_results.json')
    hasher.save_global_results(global_output_path)
    
    # Report findings
    duplicates = hasher.find_global_duplicates()
    total_duplicates = sum(len(paths) - 1 for paths in duplicates.values())
    logging.info(f"Found {len(duplicates)} duplicate sets")
    logging.info(f"Total duplicate files: {total_duplicates}")

if __name__ == "__main__":
    main() 