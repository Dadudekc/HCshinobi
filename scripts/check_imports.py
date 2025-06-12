"""
Import validation script for HCShinobi.
This script checks that all Python files in the project can be imported without errors.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Tuple

def validate_import(path: str) -> Tuple[bool, str]:
    """Validate that a Python file can be imported without errors."""
    try:
        spec = importlib.util.spec_from_file_location("module", path)
        if spec is None:
            return False, f"Could not create spec for {path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Check if the module is trying to access HCshinobi.commands.Bot
        if hasattr(module, 'HCshinobi') and hasattr(module.HCshinobi, 'commands'):
            if not hasattr(module.HCshinobi.commands, 'Bot'):
                # This is not an error - the Bot attribute is not required
                return True, "OK"
        
        return True, "OK"
    except Exception as e:
        return False, str(e)

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the given directory and its subdirectories."""
    python_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))
    return python_files

def main():
    """Main entry point for the import validation script."""
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    # Find all Python files
    python_files = find_python_files(str(project_root))
    
    # Validate each file
    failed_files = []
    for file_path in python_files:
        success, message = validate_import(file_path)
        if not success:
            failed_files.append((file_path, message))
            print(f"[❌] {file_path}: {message}")
        else:
            print(f"[✅] {file_path}")
    
    # Print summary
    print("\n=== Import Validation Summary ===")
    print(f"Total files checked: {len(python_files)}")
    print(f"Failed imports: {len(failed_files)}")
    
    if failed_files:
        print("\nFailed imports:")
        for file_path, error in failed_files:
            print(f"\n{file_path}:")
            print(f"  Error: {error}")
        sys.exit(1)
    else:
        print("\nAll imports validated successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main() 