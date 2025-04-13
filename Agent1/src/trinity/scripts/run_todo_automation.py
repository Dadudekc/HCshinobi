#!/usr/bin/env python3
"""
TODO Automation Runner

This script coordinates the automated TODO resolution workflow by:
1. Running the TODO scanner to find TODOs in the codebase
2. Running the Cursor dispatcher to automatically address TODOs

It provides a single entry point for the automation pipeline and supports
various configuration options for controlling the execution.
"""

import os
import sys
import argparse
import subprocess
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("todo_automation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TodoAutomation")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="TODO Automation Runner")
    
    parser.add_argument("--scan-only", action="store_true",
                        help="Only run the scanner, don't dispatch tasks")
    
    parser.add_argument("--dispatch-only", action="store_true",
                        help="Only run the dispatcher, don't scan")
    
    parser.add_argument("-d", "--directory", default=".",
                        help="Directory to scan for TODOs (default: current directory)")
    
    parser.add_argument("-o", "--output", default="todo_report.md",
                        help="Output file for the TODO report (default: todo_report.md)")
    
    parser.add_argument("-j", "--json-output", default="todo_tasks.json",
                        help="JSON output file for TODO tasks (default: todo_tasks.json)")
    
    parser.add_argument("-c", "--categories", nargs="+",
                        help="Categories to process (default: all)")
    
    parser.add_argument("-m", "--max-tasks", type=int, default=10,
                        help="Maximum number of tasks to process (default: 10)")
    
    parser.add_argument("-b", "--batch-size", type=int, default=5,
                        help="Batch size for processing tasks (default: 5)")
    
    parser.add_argument("-p", "--pause", type=int, default=5,
                        help="Pause between tasks in seconds (default: 5)")
    
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't actually execute dispatcher tasks, just log")
    
    return parser.parse_args()

def run_scanner(args):
    """Run the TODO scanner."""
    logger.info("Running TODO scanner...")
    
    command = [
        "python", "find_todos.py",
        args.directory,
        args.output,
    ]
    
    try:
        logger.info(f"Executing command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Scanner completed successfully")
        print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Scanner failed with code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        print(e.stdout)
        return False
        
    except Exception as e:
        logger.error(f"Error running scanner: {str(e)}")
        return False

def run_dispatcher(args):
    """Run the Cursor dispatcher."""
    logger.info("Running Cursor dispatcher...")
    
    command = [
        "python", "cursor_dispatcher.py",
        "--task-file", args.json_output,
        "--max-tasks", str(args.max_tasks),
        "--batch-size", str(args.batch_size),
        "--pause", str(args.pause)
    ]
    
    if args.categories:
        command.extend(["--categories"] + args.categories)
        
    if args.dry_run:
        command.append("--dry-run")
    
    try:
        logger.info(f"Executing command: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Dispatcher completed successfully")
        print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Dispatcher failed with code {e.returncode}")
        logger.error(f"Error: {e.stderr}")
        print(e.stdout)
        return False
        
    except Exception as e:
        logger.error(f"Error running dispatcher: {str(e)}")
        return False

def main():
    """Main entry point."""
    args = parse_args()
    
    logger.info(f"Starting TODO automation: {datetime.now().isoformat()}")
    
    scanner_success = True
    dispatcher_success = True
    
    # Run the scanner if needed
    if not args.dispatch_only:
        scanner_success = run_scanner(args)
        
        if not scanner_success:
            logger.error("Scanner failed, stopping automation")
            sys.exit(1)
    
    # Run the dispatcher if needed
    if not args.scan_only and scanner_success:
        dispatcher_success = run_dispatcher(args)
        
        if not dispatcher_success:
            logger.error("Dispatcher failed")
            sys.exit(1)
    
    logger.info(f"TODO automation completed: {datetime.now().isoformat()}")
    
    if args.scan_only:
        print("\nScanner completed successfully. Dispatcher was not run (scan-only mode).")
    elif args.dispatch_only:
        print("\nDispatcher completed successfully. Scanner was not run (dispatch-only mode).")
    else:
        print("\nFull automation pipeline completed successfully.")
    
    print("\nSummary:")
    print(f"- Scanner: {'SUCCESS' if scanner_success else 'SKIPPED' if args.dispatch_only else 'FAILED'}")
    print(f"- Dispatcher: {'SUCCESS' if dispatcher_success else 'SKIPPED' if args.scan_only else 'FAILED'}")
    
    sys.exit(0)

if __name__ == "__main__":
    main() 