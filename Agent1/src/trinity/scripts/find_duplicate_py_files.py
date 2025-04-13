import os
import hashlib
import collections
from pathlib import Path

# --- Configuration ---
TARGET_DIR = Path("chat_mate") # Directory to scan
FILE_EXTENSION = ".py"        # File type to check
CHUNK_SIZE = 8192             # Read files in chunks for efficiency

# Directories to exclude (relative to TARGET_DIR or absolute)
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
    ".pytest_cache",
    ".cursor-cache",
    "tests",        # Exclude tests by default
    "tests_legacy", # Exclude legacy tests
    "outputs",
    "reports",
    "docs",
    "logs",
    "dist",
    "build",
    "htmlcov",      # Often from coverage reports
    "trash_unused", # Directory from previous script
    "core_old",     # Exclude the old core
    "trinity",      # Exclude trinity for now unless specified
}

# Specific files to exclude
EXCLUDE_FILES = {
    "__init__.py", # Often empty or boilerplate
}
# ---------------------

def get_file_hash(file_path: Path) -> str:
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except OSError as e:
        print(f"Error reading file {file_path}: {e}")
        return "" # Return empty string on error

def find_duplicates(target_dir: Path):
    """Finds duplicate files based on content hash."""
    hashes = collections.defaultdict(list)
    total_files_scanned = 0
    print(f"Scanning directory: {target_dir.resolve()}")

    for root, dirs, files in os.walk(target_dir):
        root_path = Path(root)

        # Filter excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for filename in files:
            if not filename.endswith(FILE_EXTENSION):
                continue

            if filename in EXCLUDE_FILES:
                continue

            file_path = root_path / filename
            relative_path = file_path.relative_to(target_dir)

            # Check if the file is within any excluded directory path components
            is_excluded = False
            for part in relative_path.parts:
                if part in EXCLUDE_DIRS:
                    is_excluded = True
                    break
            if is_excluded:
                continue

            total_files_scanned += 1
            file_hash = get_file_hash(file_path)
            if file_hash: # Only add if hashing was successful
                hashes[file_hash].append(str(relative_path))

    print(f"Scanned {total_files_scanned} '{FILE_EXTENSION}' files.")

    duplicates_found = False
    print("\n--- Duplicate File Groups ---")
    for file_hash, paths in hashes.items():
        if len(paths) > 1:
            duplicates_found = True
            print(f"\nHash: {file_hash[:8]}...") # Print partial hash for brevity
            for path in sorted(paths):
                print(f"  - {path}")

    if not duplicates_found:
        print("No duplicate files found.")

if __name__ == "__main__":
    if not TARGET_DIR.is_dir():
        print(f"Error: Target directory '{TARGET_DIR}' not found or is not a directory.")
    else:
        find_duplicates(TARGET_DIR) 