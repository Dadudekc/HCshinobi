"""Debug script to check Python path and imports."""

import os
import sys

def print_python_path():
    """Print the Python path."""
    print("Python Path:")
    for path in sys.path:
        print(f"  - {path}")

def check_module_structure():
    """Check the module structure."""
    print("\nModule Structure:")
    for root, dirs, files in os.walk("."):
        if "__pycache__" in root:
            continue
        level = root.count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        for file in files:
            if file.endswith(".py"):
                print(f"{indent}  {file}")

if __name__ == "__main__":
    print_python_path()
    check_module_structure() 