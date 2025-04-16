# _agent_coordination/mailbox_utils.py

import time
import shutil
import logging
import threading # Import threading for Event
import asyncio  # Import asyncio for Event
from pathlib import Path
from typing import Callable, Optional, Union

logger = logging.getLogger("MailboxUtils")

def process_directory_loop(
    watch_dir: Path,
    process_func: Callable[[Path], bool],
    success_dir: Path,
    error_dir: Path,
    file_suffix: str = ".json",
    poll_interval: int = 10,
    log_prefix: str = "DirMonitor",
    stop_event: Optional[Union[threading.Event, asyncio.Event]] = None # Use specific Event types
):
    """Continuously scans a directory, processes files, moves them, and sleeps.

    Args:
        watch_dir: The directory to monitor.
        process_func: A function that takes a file Path and returns True for success,
                      False for failure. This dictates where the file is moved.
        success_dir: Directory to move successfully processed files to.
        error_dir: Directory to move unsuccessfully processed files to.
        file_suffix: The file extension to look for (case-insensitive).
        poll_interval: Seconds to sleep between scans.
        log_prefix: Prefix for log messages.
        stop_event: An optional threading.Event or asyncio.Event to signal shutdown.
    """
    logger.info(f"[{log_prefix}] Starting monitor for {watch_dir}...")
    watch_dir.mkdir(parents=True, exist_ok=True)
    success_dir.mkdir(parents=True, exist_ok=True)
    error_dir.mkdir(parents=True, exist_ok=True)

    while True:
        if stop_event and stop_event.is_set():
            logger.info(f"[{log_prefix}] Stop event received. Exiting loop for {watch_dir}.")
            break
            
        logger.debug(f"[{log_prefix}] Scanning {watch_dir}...")
        processed_count = 0
        try:
            items_in_dir = list(watch_dir.iterdir()) # List once
            for item in items_in_dir:
                if stop_event and stop_event.is_set(): break # Check again before processing item
                
                if item.is_file():
                    if item.suffix.lower() == file_suffix.lower():
                        logger.debug(f"[{log_prefix}] Found file: {item.name}")
                        success = False # Default to failure
                        try:
                            success = process_func(item)
                            logger.debug(f"[{log_prefix}] Processing function returned {success} for {item.name}")
                        except Exception as processing_e:
                            logger.error(f"[{log_prefix}] Unhandled exception in process_func for {item.name}: {processing_e}", exc_info=True)
                            success = False # Ensure it moves to error dir
                            
                        target_dir = success_dir if success else error_dir
                        try:
                            move_target = target_dir / item.name
                            # Basic check to prevent overwriting? Less likely with UUIDs
                            # if move_target.exists(): 
                            #    logger.warning(f"[{log_prefix}] Target exists, not moving: {move_target}")
                            # else:    
                            shutil.move(str(item), str(move_target))
                            logger.debug(f"[{log_prefix}] Moved {item.name} to {target_dir.name}")
                            processed_count += 1
                        except Exception as move_e:
                            logger.error(f"[{log_prefix}] Failed to move file {item.name} to {target_dir.name}: {move_e}")
                    elif item.name != ".placeholder": # Ignore placeholders
                        logger.warning(f"[{log_prefix}] Found file with unexpected suffix in {watch_dir}: {item.name}. Ignoring.")
                        # Optionally move ignored files elsewhere?
                        
        except FileNotFoundError:
            logger.warning(f"[{log_prefix}] Watch directory {watch_dir} disappeared? Re-checking next cycle.")
        except Exception as loop_e:
            logger.error(f"[{log_prefix}] Error during directory scan for {watch_dir}: {loop_e}", exc_info=True)

        # --- Sleep --- 
        if processed_count == 0:
            logger.debug(f"[{log_prefix}] No new '{file_suffix}' files found in {watch_dir}. Sleeping for {poll_interval} seconds.")
            
        # Sleep for the poll interval, checking stop event periodically
        sleep_end_time = time.time() + poll_interval
        while time.time() < sleep_end_time:
            if stop_event and stop_event.is_set():
                break
            # Check if stop_event is asyncio.Event and use await if needed?
            # For now, assume polling is sufficient given the time.sleep
            time.sleep(min(1, sleep_end_time - time.time())) # Sleep in 1s increments or less 