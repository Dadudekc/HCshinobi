#!/usr/bin/env python3
"""
TRINITY - Task Resolution and Integration for Network-based Task Yielding

TRINITY is a system for automated TODO resolution and task processing,
designed to integrate with various systems and provide a seamless
experience for developers.
"""

import os
import sys
import argparse
import logging
import json
import yaml
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure the parent directory of 'trinity' package is in sys.path
# This helps resolve imports when running trinity.py directly
current_script_path = Path(__file__).resolve()
trinity_package_dir = current_script_path.parent
project_root = trinity_package_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- Directory Setup --- moved before logging configuration
def ensure_directories() -> None:
    """
    Ensure necessary directories exist relative to project root.
    """
    directories = [
        project_root / '.trinity',
        project_root / '.trinity' / 'logs',
        project_root / '.trinity' / 'cycle_memory',
        project_root / '.trinity' / 'review_queue',
        project_root / '.trinity' / 'snapshots',
        project_root / '.trinity' / 'snapshots' / 'claude',
        project_root / '.trinity' / 'control',
        project_root / 'trinity_output'
    ]

    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as e:
            # Use a basic print here as logging might not be configured yet
            print(f"FATAL: Failed to create essential directory {directory}: {e}", file=sys.stderr)
            sys.exit(1) # Exit if essential directories can't be created

# Create directories BEFORE setting up logging that depends on them
ensure_directories()

# --- Logging Setup ---
log_file_path = project_root / '.trinity' / 'logs' / 'trinity.log'
logging.basicConfig(
    level=logging.INFO, # Default level, can be changed by args later
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TRINITY")
logger.info(f"Logging initialized. Log file: {log_file_path}") # Log confirmation

# Import TRINITY components using the corrected package path
try:
    # Import command functions from their respective modules
    from trinity.commands.scan_cmd import configure_scan_command, run_scan_command
    from trinity.commands.process_cmd import configure_process_command, run_process_command
    from trinity.commands.validate_cmd import configure_validate_command, run_validate_command
    from trinity.commands.inject_cmd import configure_inject_command, run_inject_command
    # Import core components
    from trinity.core.validation import validate_system
    # Import SubconsciousEngine and run function directly if possible
    from trinity.core.subconscious.engine import SubconsciousEngine, get_subconscious_engine, run_subconscious_engine

except ImportError as e:
    logger.critical(f"Error importing TRINITY components: {e}") # Use critical for import errors
    logger.critical("Make sure TRINITY is properly installed or check module paths.")
    sys.exit(1)

def configure_parser() -> argparse.ArgumentParser:
    """
    Configure the main argument parser for TRINITY.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="TRINITY - Task Resolution and Integration for Network-based Task Yielding"
    )

    # Global options
    parser.add_argument(
        "--config",
        help="Path to configuration file relative to project root",
        default="config.yaml"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level"
    )
    parser.add_argument(
        "--dynamic",
        action="store_true",
        help="Enable dynamic behavior adaptation"
    )
    parser.add_argument(
        "--supervised",
        action="store_true",
        help="Run in supervised mode (requires user confirmation)"
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch for file changes"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute", required=True)

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for TODOs")
    configure_scan_command(scan_parser)
    # Add scan-specific args back here
    scan_parser.add_argument(
        "--loop",
        action="store_true",
        help="Run in continuous loop mode"
    )
    scan_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Interval between scans in seconds (default: 300)"
    )
    scan_parser.add_argument(
        "--subconscious",
        action="store_true",
        help="Enable subconscious processing during scan"
    )

    # Inject command
    inject_parser = subparsers.add_parser("inject", help="Inject memory data")
    configure_inject_command(inject_parser)

    # Process command
    process_parser = subparsers.add_parser("process", help="Process TODOs")
    configure_process_command(process_parser)

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate system")
    configure_validate_command(validate_parser)

    return parser


def configure_logging(log_level: str) -> None:
    """
    Configure logging level AFTER initial basicConfig.

    Args:
        log_level: Logging level to set
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        logger.warning(f"Invalid log level: {log_level}. Using previous level.")
        return # Don't change level if invalid

    # Get root logger and set level
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Update handlers' levels
    for handler in root_logger.handlers:
        handler.setLevel(numeric_level)

    logger.info(f"Logging level updated to {log_level}")

# Removed ensure_directories from here as it's called before logging setup now

def load_config(config_path: str) -> Dict:
    """
    Load configuration from file relative to project root.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    absolute_config_path = project_root / config_path
    if not absolute_config_path.exists():
        logger.warning(f"Configuration file not found: {absolute_config_path}. Using default settings.")
        return {}

    try:
        with open(absolute_config_path, 'r') as f:
            if config_path.endswith('.json'):
                return json.load(f)
            elif config_path.endswith(('.yaml', '.yml')):
                 return yaml.safe_load(f)
            else:
                logger.warning(f"Unsupported config file format: {config_path}. Must be JSON or YAML.")
                return {}
    except Exception as e:
        logger.error(f"Error loading configuration from {absolute_config_path}: {e}")
        return {}

def main() -> Optional[int]:
    """
    Main entry point for TRINITY.
    """
    parser = configure_parser()
    args = parser.parse_args()

    # Configure logging level based on args (updates level set initially)
    configure_logging(args.log_level)

    try:
        # Directories are already ensured before logging setup

        # Load configuration
        config = load_config(args.config)

        # Validate system (consider passing config if needed)
        if not validate_system():
            logger.error("System validation failed. Exiting.")
            return 1

        # Execute command based on subparser chosen
        # Ensure the run_* functions are imported correctly at the top
        if args.command == "scan":
            return run_scan_command(args, config)
        elif args.command == "inject":
            return run_inject_command(args, config)
        elif args.command == "process":
            return run_process_command(args, config)
        elif args.command == "validate":
            return run_validate_command(args, config)
        else:
            # This case should not be reached due to `required=True` in subparsers
            logger.error(f"Unknown command: {args.command}")
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting gracefully.")
        return 0
    except ImportError as e:
         # This error should ideally be caught at the top-level import
         logger.critical(f"Late Import Error: {e}. Dependency issue?")
         return 1
    except Exception as e:
        logger.exception(f"An unexpected error occurred during command execution: {e}")
        return 1

# NOTE: The actual run_*_command functions MUST reside in their respective
# command modules (e.g., trinity/trinity/commands/scan_cmd.py) and be imported above.
# Having placeholder definitions here will cause issues if not removed.

if __name__ == '__main__':
    sys.exit(main()) 