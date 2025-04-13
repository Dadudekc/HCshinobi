#!/usr/bin/env python3
"""
Script to find duplicate files by content hash
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import json

def compute_file_hash(file_path):
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error hashing {file_path}: {e}")
        return None

def find_duplicates(directory):
    """Find duplicate files in directory and subdirectories."""
    hash_map = defaultdict(list)
    
    # Skip certain directories and files
    skip_patterns = {
        "__pycache__",
        ".git",
        ".pytest_cache",
        "venv",
        ".venv",
        ".coverage",
        ".DS_Store",
        "node_modules"
    }
    
    # Walk through directory
    for root, dirs, files in os.walk(directory):
        # Skip directories we want to ignore
        dirs[:] = [d for d in dirs if d not in skip_patterns]
        
        for filename in files:
            file_path = os.path.join(root, filename)
            file_hash = compute_file_hash(file_path)
            if file_hash:
                hash_map[file_hash].append(file_path)
    
    # Filter for duplicates only
    duplicates = {
        hash_val: paths
        for hash_val, paths in hash_map.items()
        if len(paths) > 1
    }
    
    return duplicates

def main():
    # Directories to check
    directories = [
        "consolidated",
        "Agent2",
        "overnight_scripts",
        "src"
    ]
    
    all_duplicates = {}
    
    # Find duplicates in each directory
    for directory in directories:
        if os.path.exists(directory):
            print(f"\nChecking {directory}...")
            duplicates = find_duplicates(directory)
            if duplicates:
                all_duplicates[directory] = duplicates
                print(f"Found {len(duplicates)} sets of duplicates in {directory}")
                
                # Print first few duplicates as example
                for hash_val, paths in list(duplicates.items())[:3]:
                    print(f"\nDuplicate set (hash: {hash_val[:8]}...):")
                    for path in paths:
                        print(f"  {path}")
            else:
                print(f"No duplicates found in {directory}")
    
    # Save full results to file
    if all_duplicates:
        with open("duplicate_files_report.json", "w") as f:
            json.dump(all_duplicates, f, indent=2)
        print("\nFull report saved to duplicate_files_report.json")

if __name__ == "__main__":
    main() 