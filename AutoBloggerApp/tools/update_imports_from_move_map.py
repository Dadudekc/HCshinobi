#!/usr/bin/env python3
# tools/update_imports_from_move_map.py

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_move_map(map_path: str) -> Dict[str, str]:
    """Load the file move map from JSON."""
    try:
        with open(map_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load move map: {e}")
        sys.exit(1)


def find_python_files(root_dir: str) -> List[Path]:
    """Find all Python files in the project."""
    root = Path(root_dir)
    return list(root.rglob("*.py"))


def parse_imports(file_path: Path) -> List[Tuple[str, int]]:
    """Parse imports from a Python file."""
    imports = []
    with open(file_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            # Match both import and from ... import statements
            if line.strip().startswith(("import ", "from ")):
                imports.append((line.strip(), i))
    return imports


def update_imports(file_path: Path, move_map: Dict[str, str]) -> bool:
    """Update imports in a file based on the move map."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Track if we made any changes
        modified = False

        # Update import statements
        for old_path, new_path in move_map.items():
            # Convert paths to Python module notation
            old_module = (
                old_path.replace("/", ".").replace("\\", ".").replace(".py", "")
            )
            new_module = (
                new_path.replace("/", ".").replace("\\", ".").replace(".py", "")
            )

            # Handle both import and from ... import statements
            patterns = [
                (rf"\bimport\s+{re.escape(old_module)}\b", f"import {new_module}"),
                (
                    rf"\bfrom\s+{re.escape(old_module)}\s+import\b",
                    f"from {new_module} import",
                ),
                (rf"\bfrom\s+{re.escape(old_module)}\.", f"from {new_module}."),
            ]

            for old_pattern, new_pattern in patterns:
                if re.search(old_pattern, content):
                    content = re.sub(old_pattern, new_pattern, content)
                    modified = True
                    logger.info(
                        f"Updated import in {file_path}: {old_pattern} -> {new_pattern}"
                    )

        if modified:
            # Write back the modified content
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        logger.error(f"Error updating imports in {file_path}: {e}")
        return False


def run_formatter():
    """Run black or ruff formatter if available."""
    try:
        # Try black first
        subprocess.run(["black", "."], check=True)
        logger.info("Formatted code with black")
    except subprocess.CalledProcessError:
        try:
            # Fall back to ruff
            subprocess.run(["ruff", "format", "."], check=True)
            logger.info("Formatted code with ruff")
        except subprocess.CalledProcessError:
            logger.warning("No formatter found (black or ruff)")


def run_tests():
    """Run pytest to verify changes."""
    try:
        subprocess.run(["pytest", "-q"], check=True)
        logger.info("✅ All tests passed")
    except subprocess.CalledProcessError:
        logger.error("❌ Tests failed after import updates")
        sys.exit(1)


def main():
    """Main function to update imports across the codebase."""
    # Get project root
    project_root = Path(__file__).parent.parent

    # Load move map
    map_path = project_root / "tools" / "file_move_map.json"
    if not map_path.exists():
        logger.error(f"Move map not found at {map_path}")
        sys.exit(1)

    move_map = load_move_map(str(map_path))

    # Find all Python files
    python_files = find_python_files(str(project_root))
    logger.info(f"Found {len(python_files)} Python files")

    # Update imports
    modified_files = 0
    for file_path in python_files:
        if update_imports(file_path, move_map):
            modified_files += 1

    logger.info(f"Updated imports in {modified_files} files")

    # Format code
    run_formatter()

    # Run tests
    run_tests()


if __name__ == "__main__":
    main()
