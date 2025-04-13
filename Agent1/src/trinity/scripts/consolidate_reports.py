#!/usr/bin/env python3

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple
import logging
from dataclasses import dataclass, asdict
import hashlib
import fnmatch
import subprocess

@dataclass
class ReportMetadata:
    file_path: str
    file_size: int
    created_time: float
    modified_time: float
    report_type: str
    content_hash: str

class ReportConsolidator:
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = Path(workspace_dir)
        self.setup_logging()
        
        # Define report categories
        self.report_categories = {
            "deduplication": ["deduplication_report.json", "duplicates_report.json", "duplicate_files_report.json"],
            "context": ["chatgpt_project_context.json", "chatgpt_project_context_dedup.json", "chatgpt_project_context_merged.json"],
            "analysis": ["project_analysis.json", "dependency_cache.json"],
            "cleanup": ["cleanup_report.json"],
            "consolidation": ["consolidation_report.json", "deduplication_plan.json"]
        }
        
        # Define directories to consolidate
        self.redundant_dirs = [
            "backup_before_consolidation",
            "archive",
            "old",
            "legacy",
            ".cache",
            "chrome_profile",
            "chat_mate.egg-info",
            "__pycache__"
        ]
        
        # Define cache directories to clean
        self.cache_dirs = [
            ".pytest_cache",
            "__pycache__",
            ".cache"
        ]
        
        # Define temporary file patterns
        self.temp_file_patterns = [
            "f_[0-9a-f]*",  # Matches patterns like f_000a0c
            "*_backup_*",    # Matches backup files
            "*.pyc",         # Python bytecode files
            "*.pyo",         # Python optimized bytecode
            "*.pyd",         # Python DLL files
            "*.egg-info",    # Python egg metadata
            "*.bak",         # Backup files
            "*.tmp",         # Temporary files
            "*.temp",        # Temporary files
            "*.cache"        # Cache files
        ]
        
        # Define log patterns
        self.log_patterns = [
            "*.log",
            "logs/*.log"
        ]
        
        # Setup archive directory
        self.archive_dir = self.workspace_dir / "archived_reports" / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Define overnight script clutter patterns for archiving
        self.overnight_scripts_path = os.path.join(self.workspace_dir, "scripts", "overnight_scripts")
        # Expand patterns for overnight scripts clutter
        self.overnight_clutter_patterns = [
            # Config/Metadata/Build related
            "__config__.py", "__diff.py", "__info__.py", "__pkginfo__.py", "__version__.py",
            "*.ini", "*.cfg", "*.toml", "*.yaml", "*.yml", "*.json", "*.xml", "*.csv", "*.tsv",
            "*.egg-info", "PKG-INFO", "setup.py", "pyproject.toml", "MANIFEST.in", "requirements.txt",
            "*.pth", "*.dist-info", "pyvenv.cfg", "*.pyx", "*.pxd", "*.pxi",
            "meson.build", "meson.build.template",
            "*.idl", "*.tlb", "*.chm", "*.sql", "*.proto", "*.pem", "*.gbnf", "*.xslt",
            "*.lua", "*.asm", "*.cmd", "*.exe", "*.mod",
            # Cache/Temp
            "*.pyc", "*.pyo", "*.pyd", "*.py~", "*.bak", "*.tmp", "*.temp", "*.cache",
            ".pytest_cache/", "__pycache__/", "*.coverage", ".coverage", "*.log", "logs/",
            "f_[0-9a-f]*", "*_backup_*", "crash-*.testcase",
            # Docs/Licenses/Examples/Tests
            "LICENSE*", "README*", "AUTHORS", "CONTRIBUTING*", "CHANGELOG*", "NEWS*", "docs/", "examples/", "tests/", "test/",
            "*.rst", "*.md", "*.markdown", "*.txt", "*.html", "*.css", "*.js",
            "*.doctest", "*.testcase", "*.ipynb", "*.pkl", "*.npz", "*.npy", "*.gz", "*.bz2", "*.xz", "*.z", "*.zip", "*.tar",
            "*.fits", "*.A99", "*.B99", "*.onnx", "*.gpickle.bz2", "*.xrc",
            # Fortran specific
            "*.f", "*.f77", "*.f90", "*.f95",
            # Plotting/Graphics/Fonts
            "*.mplstyle", "*.afm", "*.ttf", "*.otf", "*.woff", "*.woff2", "*.eot", "*.svg",
            "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.ico", "*.icns", "*.pdf", "*.ps", "*.eps",
             # Specific directories often containing package internals
            "chat_mate/", "tools/", "site-packages/", "dist-packages/",
            # Files starting with underscore (often internal)
            "_[a-zA-Z0-9_]*.py",
            # Common library/tool specific files/dirs (add more as needed)
             "venv*", "env/", ".git/", ".hg/", ".svn/", ".vscode/", ".idea/", "*.egg",
             "*.dll", "*.so", "*.dylib", # Shared libraries
             "DELVEWHEEL", # Windows specific wheel helper
             "Nuitka*.py", # Nuitka specific
             "zip-safe", # Setuptools metadata
             "lastfailed", # Pytest cache file
             "mypy-*.xslt", # Mypy report formats
             "t32.exe", "t64*.exe", "w32.exe", "w64*.exe", # Console launchers
        ]
        # Exact filenames to keep (consider adding essential __init__.py if needed)
        self.overnight_keep_files = [
            "__init__.py", # Keep top-level init if it exists and is needed
            # Add any other essential files by exact name if known
        ]

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('report_consolidation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file contents."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def get_report_metadata(self, file_path: Path) -> ReportMetadata:
        """Get metadata for a report file."""
        stats = file_path.stat()
        report_type = next(
            (cat for cat, files in self.report_categories.items() 
             if file_path.name in files),
            "unknown"
        )
        
        return ReportMetadata(
            file_path=str(file_path),
            file_size=stats.st_size,
            created_time=stats.st_ctime,
            modified_time=stats.st_mtime,
            report_type=report_type,
            content_hash=self.compute_file_hash(file_path)
        )

    def find_report_files(self) -> Dict[str, List[ReportMetadata]]:
        """Find all report files and categorize them."""
        report_files: Dict[str, List[ReportMetadata]] = {
            category: [] for category in self.report_categories
        }
        
        for file_path in self.workspace_dir.glob("*.json"):
            for category, patterns in self.report_categories.items():
                if file_path.name in patterns:
                    metadata = self.get_report_metadata(file_path)
                    report_files[category].append(metadata)
                    self.logger.info(f"Found {category} report: {file_path.name}")
        
        return report_files

    def merge_deduplication_reports(self, reports: List[ReportMetadata]) -> Dict:
        """Merge multiple deduplication reports into a single comprehensive report."""
        merged_data = {
            "merged_timestamp": datetime.now().isoformat(),
            "source_reports": [report.file_path for report in reports],
            "duplicates": {},
            "statistics": {
                "total_files_processed": 0,
                "total_duplicates_found": 0,
                "total_space_saved": 0
            }
        }
        
        for report in reports:
            try:
                with open(report.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        if "duplicates" in data:
                            merged_data["duplicates"].update(data["duplicates"])
                        if "statistics" in data:
                            for key, value in data["statistics"].items():
                                if isinstance(value, (int, float)):
                                    merged_data["statistics"][key] = merged_data["statistics"].get(key, 0) + value
            except Exception as e:
                self.logger.error(f"Error processing {report.file_path}: {str(e)}")
        
        return merged_data

    def archive_reports(self, reports: List[ReportMetadata]) -> None:
        """Archive old report files."""
        for report in reports:
            source_path = Path(report.file_path)
            dest_path = self.archive_dir / source_path.name
            try:
                shutil.move(str(source_path), str(dest_path))
                self.logger.info(f"Archived {source_path.name} to {dest_path}")
            except Exception as e:
                self.logger.error(f"Error archiving {source_path.name}: {str(e)}")

    def cleanup_cache_directories(self) -> None:
        """Remove cache directories."""
        for cache_dir in self.cache_dirs:
            for path in self.workspace_dir.rglob(cache_dir):
                try:
                    shutil.rmtree(path)
                    self.logger.info(f"Removed cache directory: {path}")
                except Exception as e:
                    self.logger.error(f"Error removing cache directory {path}: {str(e)}")

    def consolidate_redundant_directories(self) -> None:
        """Consolidate redundant directories into the archive."""
        for dir_name in self.redundant_dirs:
            dir_path = self.workspace_dir / dir_name
            if dir_path.exists():
                archive_path = self.archive_dir / dir_name
                try:
                    shutil.move(str(dir_path), str(archive_path))
                    self.logger.info(f"Archived directory {dir_name} to {archive_path}")
                except Exception as e:
                    self.logger.error(f"Error archiving directory {dir_name}: {str(e)}")

    def archive_old_logs(self) -> None:
        """Archive old log files."""
        log_files = []
        for pattern in self.log_patterns:
            log_files.extend(self.workspace_dir.glob(pattern))
        
        for log_file in log_files:
            if log_file.stat().st_size > 1024 * 1024:  # Larger than 1MB
                try:
                    dest_path = self.archive_dir / log_file.name
                    shutil.move(str(log_file), str(dest_path))
                    self.logger.info(f"Archived large log file: {log_file} to {dest_path}")
                except Exception as e:
                    self.logger.error(f"Error archiving log file {log_file}: {str(e)}")

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files matching defined patterns."""
        import fnmatch
        
        # Get all files in consolidated directory
        consolidated_dir = self.workspace_dir / "consolidated"
        if not consolidated_dir.exists():
            return
            
        for pattern in self.temp_file_patterns:
            for root, _, files in os.walk(str(consolidated_dir)):
                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        file_path = Path(root) / filename
                        try:
                            # Archive files larger than 1MB, delete others
                            if file_path.stat().st_size > 1024 * 1024:
                                dest_path = self.archive_dir / "temp_files" / file_path.relative_to(consolidated_dir)
                                dest_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(file_path), str(dest_path))
                                self.logger.info(f"Archived temp file: {file_path} to {dest_path}")
                            else:
                                file_path.unlink()
                                self.logger.info(f"Removed temp file: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Error handling temp file {file_path}: {str(e)}")

    def archive_overnight_scripts_clutter(self, archive_dir):
        """Archives unnecessary files and directories from scripts/overnight_scripts."""
        logging.info(f"Starting cleanup of {self.overnight_scripts_path}...")
        if not os.path.exists(self.overnight_scripts_path):
            logging.warning(f"Directory not found: {self.overnight_scripts_path}")
            return 0

        archive_target_base = os.path.join(archive_dir, "overnight_scripts_clutter")
        os.makedirs(archive_target_base, exist_ok=True)
        archived_count = 0
        total_size = 0

        # Use a set for faster lookup of files to keep
        keep_files_set = set(self.overnight_keep_files)

        # Walk through the directory
        items_to_process = list(os.scandir(self.overnight_scripts_path))
        processed_paths = set() # Keep track of processed paths to avoid redundant checks

        while items_to_process:
            entry = items_to_process.pop(0)
            if entry.path in processed_paths:
                continue
            processed_paths.add(entry.path)

            # Check if the item should be kept based on exact name
            if entry.name in keep_files_set:
                logging.debug(f"Keeping essential file: {entry.path}")
                continue

            # Check if the item matches any clutter pattern
            should_archive = False
            matched_pattern = None
            for pattern in self.overnight_clutter_patterns:
                try:
                    if fnmatch.fnmatch(entry.name, pattern):
                        should_archive = True
                        matched_pattern = pattern
                        break
                except Exception as e:
                    logging.error(f"Error matching pattern '{pattern}' with '{entry.name}': {e}")
                    continue # Skip this pattern if invalid

            if should_archive:
                try:
                    target_path = os.path.join(archive_target_base, os.path.relpath(entry.path, self.overnight_scripts_path))
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)

                    item_size = 0
                    if entry.is_file():
                        item_size = entry.stat().st_size
                        logging.info(f"Archiving file '{entry.name}' (matches '{matched_pattern}') to {target_path} ({self.sizeof_fmt(item_size)})")
                        shutil.move(entry.path, target_path)
                        archived_count += 1
                        total_size += item_size
                    elif entry.is_dir():
                         # Calculate size before moving
                        dir_size = sum(f.stat().st_size for f in Path(entry.path).rglob('*') if f.is_file())
                        logging.info(f"Archiving directory '{entry.name}' (matches '{matched_pattern}') to {target_path} ({self.sizeof_fmt(dir_size)})")
                        # Use robocopy for robust directory move on Windows
                        # Ensure robocopy exists or provide fallback? For now, assume it exists
                        try:
                           subprocess.run(
                               ['robocopy', entry.path, target_path, '/E', '/MOVE', '/NFL', '/NDL', '/NJH', '/NJS', '/nc', '/ns', '/np'],
                               check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore'
                           )
                           archived_count += 1 # Count dir as one item
                           total_size += dir_size
                        except FileNotFoundError:
                           logging.error("robocopy command not found. Falling back to shutil.move for directory.")
                           shutil.move(entry.path, target_path)
                           archived_count += 1
                           total_size += dir_size
                        except subprocess.CalledProcessError as e:
                           logging.error(f"robocopy failed for '{entry.path}' -> '{target_path}'. Error: {e.stderr}")
                           # Optionally attempt shutil.move as fallback on error?
                        except Exception as e:
                            logging.error(f"Error moving directory {entry.path} to {target_path}: {e}")

                except Exception as e:
                    logging.error(f"Failed to archive {entry.path}: {e}")
            elif entry.is_dir():
                # If it's a directory that doesn't match a clutter pattern, add its contents to be checked
                logging.debug(f"Scanning contents of directory: {entry.path}")
                try:
                    for sub_entry in os.scandir(entry.path):
                         if sub_entry.path not in processed_paths:
                             items_to_process.append(sub_entry)
                except OSError as e:
                    logging.error(f"Could not scan directory {entry.path}: {e}")
            else:
                 logging.debug(f"Keeping item (no pattern match): {entry.path}")


        logging.info(f"Archived {archived_count} items from {self.overnight_scripts_path}, totaling {self.sizeof_fmt(total_size)}.")
        return archived_count

    def consolidate_reports(self) -> None:
        """Main method to consolidate all reports."""
        self.logger.info("Starting report consolidation process...")
        
        # Find all report files
        report_files = self.find_report_files()
        
        # Process each category
        for category, reports in report_files.items():
            if not reports:
                continue
                
            self.logger.info(f"\nProcessing {category} reports...")
            
            # Sort reports by modified time
            reports.sort(key=lambda x: x.modified_time, reverse=True)
            
            # Merge reports if needed
            if category == "deduplication" and len(reports) > 1:
                merged_data = self.merge_deduplication_reports(reports)
                output_path = self.workspace_dir / f"consolidated_{category}_report.json"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, indent=2)
                self.logger.info(f"Created consolidated report: {output_path}")
                
                # Archive old reports
                self.archive_reports(reports[1:])  # Keep the most recent one
            
            # For other categories, keep the most recent and archive others
            elif len(reports) > 1:
                self.logger.info(f"Keeping most recent {category} report: {Path(reports[0].file_path).name}")
                self.archive_reports(reports[1:])

        # Additional cleanup tasks
        self.logger.info("\nPerforming additional cleanup tasks...")
        self.cleanup_cache_directories()
        self.consolidate_redundant_directories()
        self.archive_old_logs()
        self.cleanup_temp_files()  # Added temp file cleanup

        # Archive clutter from scripts/overnight_scripts
        archived_overnight_count = self.archive_overnight_scripts_clutter(self.archive_dir)

        # Generate consolidation summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "archived_reports": [str(p.relative_to(self.workspace_dir)) for p in self.archive_dir.glob("**/*")],
            "retained_reports": [str(p.relative_to(self.workspace_dir)) for p in self.workspace_dir.glob("*.json")],
            "archive_location": str(self.archive_dir),
            "cleaned_cache_dirs": self.cache_dirs,
            "consolidated_dirs": self.redundant_dirs,
            "archived_logs": [str(p.relative_to(self.workspace_dir)) for p in self.archive_dir.glob("*.log")],
            "temp_file_patterns": self.temp_file_patterns,
            "archived_overnight_items": archived_overnight_count
        }
        
        with open(self.workspace_dir / "report_consolidation_summary.json", 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.info("\nReport consolidation and cleanup completed!")
        self.logger.info(f"Archive directory: {self.archive_dir}")
        self.logger.info("See report_consolidation_summary.json for details")

    def sizeof_fmt(self, num, suffix='B'):
        """Converts a number of bytes into a human-readable format."""
        for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
            if abs(num) < 1024.0:
                return f"{num:3.2f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.2f}Yi{suffix}"

def main():
    consolidator = ReportConsolidator()
    consolidator.consolidate_reports()

if __name__ == "__main__":
    main() 