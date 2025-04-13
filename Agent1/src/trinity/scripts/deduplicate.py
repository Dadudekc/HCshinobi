#!/usr/bin/env python3
"""
File System Cleanup and Deduplication Script
Identifies and removes duplicate files and unnecessary files, keeping only essential ones.
"""

import os
import sys
import json
import logging
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class FileEntry:
    """Represents a file and its metadata."""
    path: Path
    size: int
    hash: str = field(default="")
    
    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the first 8KB of file contents."""
        if not self.hash:
            try:
                with open(self.path, 'rb') as f:
                    # Read only the first 8KB for partial hashing
                    chunk = f.read(8192)
                    self.hash = hashlib.sha256(chunk).hexdigest()
            except Exception as e:
                logger.error(f"Failed to hash file {self.path}: {e}")
                self.hash = ""
        return self.hash

class FileCleanup:
    """Handles cleanup and deduplication of files in a directory structure."""
    
    def __init__(self, 
                 root_dir: str,
                 exclude_dirs: Set[str] = None,
                 exclude_extensions: Set[str] = None):
        """Initialize the cleanup handler.
        
        Args:
            root_dir: Root directory to start cleanup from
            exclude_dirs: Set of directory names to exclude
            exclude_extensions: Set of file extensions to exclude
        """
        self.root_dir = Path(root_dir)
        
        # Directories to exclude
        self.exclude_dirs = exclude_dirs or {
            '.git', '__pycache__', 'node_modules', 'venv', '.env',
            'build', 'dist', '.idea', '.vscode', '.pytest_cache'
        }
        
        # File extensions to exclude from deduplication
        self.exclude_extensions = exclude_extensions or {
            # '.pyc', '.pyo', '.pyd', # Removed for more thorough check
            '.obj', '.exe', '.dll',
            # '.cache', '.log', # Removed for more thorough check
            '.tmp', '.temp'
        }
        
        # Patterns for unnecessary files
        self.unnecessary_patterns = {
            # Backup files
            r'.*\.bak$', r'.*\.backup$', r'.*\.old$', r'.*~$',
            r'.*\.swp$', r'.*\.swo$',
            # Temporary files
            r'.*\.tmp$', r'.*\.temp$', r'.*\.cache$',
            # Log files
            r'.*\.log$', r'.*\.log\.\d+$',
            # Debug files
            r'.*\.debug$', r'.*\.dmp$',
            # Build artifacts
            r'.*\.pyc$', r'.*\.pyo$', r'.*\.pyd$',
            # Backup JSON files
            r'.*\.json_backup_\d+$',
            # Test coverage
            r'\.coverage$', r'coverage\.xml$',
            # Package files
            r'.*\.egg-info$', r'.*\.dist-info$',
        }
        
        # Group files by size first (files of different sizes cannot be duplicates)
        self.size_groups: Dict[int, List[FileEntry]] = defaultdict(list)
        # Then group actual duplicates by their hash
        self.duplicates: Dict[str, List[FileEntry]] = defaultdict(list)
        # Track unnecessary files
        self.unnecessary_files: List[Path] = []
        
        self.stats = {
            'total_files_scanned': 0,
            'total_size_scanned': 0,
            'duplicate_sets': 0,
            'total_duplicates': 0,
            'unnecessary_files': 0,
            'space_saved': 0,
            'errors': 0
        }
        
        self.log_dir = self.root_dir / 'logs' # Define logs directory path
        logger.info(f"Cleanup initialized for {root_dir}")
    
    def is_unnecessary_file(self, path: Path) -> bool:
        """Check if a file matches unnecessary file patterns."""
        # Special check: Do not mark files within the designated logs directory as unnecessary
        try:
            if path.is_relative_to(self.log_dir):
                return False
        except ValueError: # For Python < 3.9 compatibility if is_relative_to fails
            try:
                relative_path = path.relative_to(self.root_dir)
                if relative_path.parts[0] == 'logs':
                    return False
            except (ValueError, IndexError): # Handle files directly in root or errors
                pass 
                    
        file_str = str(path)
        return any(re.match(pattern, file_str, re.IGNORECASE) for pattern in self.unnecessary_patterns)
    
    def should_process_file(self, path: Path) -> bool:
        """Check if a file should be processed based on exclusion rules."""
        try:
            # Skip excluded directories
            if any(part in self.exclude_dirs for part in path.parts):
                return False
            
            # Skip excluded extensions for deduplication
            if path.suffix.lower() in self.exclude_extensions:
                return False
            
            # Skip non-regular files (symlinks, etc)
            if not path.is_file():
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking file {path}: {e}")
            return False
    
    def scan_directory(self) -> None:
        """Scan directory and categorize files."""
        try:
            for root, dirs, files in os.walk(self.root_dir):
                # Remove excluded dirs from dirs list to prevent walking into them
                dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
                
                for filename in files:
                    path = Path(root) / filename
                    
                    try:
                        # Check if it's an unnecessary file
                        if self.is_unnecessary_file(path):
                            self.unnecessary_files.append(path)
                            self.stats['unnecessary_files'] += 1
                            continue
                        
                        # Process file for deduplication
                        if self.should_process_file(path):
                            size = path.stat().st_size
                            self.size_groups[size].append(FileEntry(path, size))
                            self.stats['total_files_scanned'] += 1
                            self.stats['total_size_scanned'] += size
                            
                    except Exception as e:
                        logger.error(f"Error processing file {path}: {e}")
                        self.stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"Error scanning directory {self.root_dir}: {e}")
            self.stats['errors'] += 1
    
    def find_duplicates(self) -> None:
        """Find duplicates by comparing file hashes within size groups."""
        for size, files in self.size_groups.items():
            if len(files) < 2:  # Skip unique sizes
                continue
            
            # Group by hash
            hash_groups: Dict[str, List[FileEntry]] = defaultdict(list)
            for file_entry in files:
                file_hash = file_entry.compute_hash()
                if file_hash:  # Only group if hash computation succeeded
                    hash_groups[file_hash].append(file_entry)
            
            # Add to duplicates if more than one file has the same hash
            for file_hash, entries in hash_groups.items():
                if len(entries) > 1:
                    self.duplicates[file_hash] = entries
                    self.stats['duplicate_sets'] += 1
                    self.stats['total_duplicates'] += len(entries) - 1
                    self.stats['space_saved'] += size * (len(entries) - 1)
    
    def cleanup_files(self, dry_run: bool = True) -> None:
        """Remove unnecessary files and duplicates.
        
        Args:
            dry_run: If True, only print what would be done without actual deletion
        """
        action = "Would remove" if dry_run else "Removing"
        kept_files = []
        removed_files = []
        unnecessary_removed = []
        
        # Handle unnecessary files
        for path in self.unnecessary_files:
            logger.info(f"{action} unnecessary file: {path}")
            unnecessary_removed.append(str(path))
            if not dry_run:
                try:
                    path.unlink()
                except Exception as e:
                    logger.error(f"Failed to remove {path}: {e}")
                    self.stats['errors'] += 1
        
        # Handle duplicates
        for file_hash, entries in self.duplicates.items():
            # Sort by path length to keep the shortest path
            entries.sort(key=lambda x: len(str(x.path)))
            kept = entries[0]
            kept_files.append(str(kept.path))
            
            # Remove all other copies
            for entry in entries[1:]:
                logger.info(f"{action} duplicate: {entry.path} (keeping {kept.path})")
                removed_files.append(str(entry.path))
                if not dry_run:
                    try:
                        entry.path.unlink()
                    except Exception as e:
                        logger.error(f"Failed to remove {entry.path}: {e}")
                        self.stats['errors'] += 1
        
        # Write report
        report = {
            'stats': self.stats,
            'kept_files': kept_files,
            'removed_duplicates': removed_files,
            'removed_unnecessary': unnecessary_removed
        }
        
        with open('cleanup_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Log summary
        logger.info(f"Scanned {self.stats['total_files_scanned']} files "
                   f"({self.stats['total_size_scanned'] / 1024 / 1024:.2f} MB)")
        logger.info(f"Found {self.stats['unnecessary_files']} unnecessary files")
        logger.info(f"Found {self.stats['duplicate_sets']} sets of duplicates "
                   f"with {self.stats['total_duplicates']} total duplicate files")
        logger.info(f"Potential space savings: {self.stats['space_saved'] / 1024 / 1024:.2f} MB")
        if self.stats['errors'] > 0:
            logger.warning(f"Encountered {self.stats['errors']} errors during processing")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "."
    
    cleanup = FileCleanup(root_dir)
    
    # First scan and find files to clean
    logger.info("Scanning for files to clean...")
    cleanup.scan_directory()
    cleanup.find_duplicates()
    
    # First do a dry run
    logger.info("Performing dry run...")
    cleanup.cleanup_files(dry_run=True)
    
    # Directly proceed with cleanup after logging dry run results
    logger.info("Proceeding with file removal...")
    cleanup.cleanup_files(dry_run=False)
    logger.info("Cleanup completed")

if __name__ == '__main__':
    main() 