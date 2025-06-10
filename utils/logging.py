"""
Logging utility module for the Naruto MMO Discord game.
Handles logging of various events for monitoring and debugging.
"""
import os
import json
import logging
import sys # Import sys
from typing import Dict, Any, Optional
from datetime import datetime

def setup_logging():
    """Configures the root logger and handlers with UTF-8 encoding."""
    # Determine log level from environment variable, default to INFO
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    os.makedirs(os.path.join(log_dir, "events"), exist_ok=True)
    log_file_path = os.path.join(log_dir, "game.log")

    # Create handlers with UTF-8 encoding
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    stream_handler = logging.StreamHandler(sys.stdout) # Use sys.stdout
    # For StreamHandler, Python 3.7+ uses sys.stdout.reconfigure(encoding='utf-8') if possible,
    # but configuring the handler itself is usually sufficient if the terminal supports UTF-8.
    # If encoding issues persist on the console, environment configuration (like PYTHONIOENCODING=utf-8)
    # might be needed before running the script.

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            file_handler,
            stream_handler
        ],
        # force=True # Use force=True in Python 3.8+ if reconfiguring logging multiple times
    )
    logger = logging.getLogger("HCshinobi") # Get root logger used in other functions
    logger.info(f"Logging setup complete. Level: {log_level_str}. Log file: {log_file_path}")

# Ensure logs directory exists (Redundant if setup_logging is called first, but safe)
# os.makedirs("logs", exist_ok=True)
# os.makedirs("logs/events", exist_ok=True)


def log_event(
    event_type: str,
    **event_data: Any
) -> None:
    """
    Log a game event with additional data.
    Saves to both the Python logging system and a structured JSON file.
    
    Args:
        event_type: Type of the event (e.g., "clan_assignment", "token_transaction")
        **event_data: Additional event data as keyword arguments
    """
    logger = logging.getLogger("HCshinobi") # Ensure we get the configured logger
    # Add timestamp if not provided
    if "timestamp" not in event_data:
        event_data["timestamp"] = datetime.now().isoformat()
    
    # Prepare the full event data
    full_event = {
        "type": event_type,
        **event_data
    }
    
    # Log to standard Python logger
    # Use repr for data to avoid potential encoding issues in the log message itself if data has unicode
    logger.info(f"Event: {event_type} - {repr(event_data)}") 
    
    # Save to JSON file
    event_log_file = os.path.join(
        "logs/events", 
        f"{event_type}_{datetime.now().strftime('%Y%m%d')}.json"
    )
    
    # Load existing events for today if file exists
    events = []
    if os.path.exists(event_log_file):
        try:
            # Ensure reading/writing JSON uses UTF-8
            with open(event_log_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode JSON from {event_log_file}. Starting fresh.")
            events = []
        except Exception as e:
             logger.error(f"Error reading event log {event_log_file}: {e}", exc_info=True)
             events=[] # Avoid corrupting on write
    
    # Add new event and save
    events.append(full_event)
    try:
        with open(event_log_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False) # ensure_ascii=False preserves unicode
    except Exception as e:
         logger.error(f"Error writing event log {event_log_file}: {e}", exc_info=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with a specific name, inheriting root config.
    
    Args:
        name: Name of the logger
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(f"HCshinobi.{name}") # Will inherit handlers/level from root


def log_error(
    error_type: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with structured details.
    
    Args:
        error_type: Type of the error
        message: Error message
        details: Additional error details
    """
    logger = logging.getLogger("HCshinobi") # Ensure we get the configured logger
    # Log to standard Python logger
    logger.error(f"Error: {error_type} - {message}", exc_info=True if details else False) # Add traceback if details exist
    
    # Prepare error data
    error_data = {
        "type": error_type,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if details:
        # Ensure details are serializable, convert if necessary
        try:
            json.dumps(details)
            error_data["details"] = details
        except TypeError:
             logger.warning(f"Non-serializable details provided for error {error_type}. Converting to string.")
             error_data["details"] = repr(details)
    
    # Save to JSON file
    error_log_file = os.path.join(
        "logs", 
        "errors.json"
    )
    
    # Load existing errors if file exists
    errors = []
    if os.path.exists(error_log_file):
        try:
            with open(error_log_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode JSON from {error_log_file}. Starting fresh.")
            errors = []
        except Exception as e:
             logger.error(f"Error reading error log {error_log_file}: {e}", exc_info=True)
             errors=[] # Avoid corrupting on write
    
    # Add new error and save
    errors.append(error_data)
    try:
        with open(error_log_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error writing error log {error_log_file}: {e}", exc_info=True)


def log_command(
    command_name: str,
    user_id: str,
    user_name: str,
    success: bool,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Any] = None,
    error: Optional[str] = None
) -> None:
    """
    Log a Discord command execution.
    
    Args:
        command_name: Name of the command
        user_id: Discord ID of the user
        user_name: Display name of the user
        success: Whether the command was successful
        parameters: Command parameters
        result: Command result
        error: Error message if the command failed
    """
    # Prepare command data
    command_data = {
        "type": "command_execution",
        "command": command_name,
        "user_id": user_id,
        "user_name": user_name,
        "success": success,
        "timestamp": datetime.now().isoformat()
    }
    
    if parameters:
        command_data["parameters"] = parameters
    
    if result and success:
        command_data["result"] = result
    
    if error and not success:
        command_data["error"] = error
    
    # Log to standard Python logger
    if success:
        logger.info(f"Command: {command_name} by {user_name} - Success")
    else:
        logger.warning(f"Command: {command_name} by {user_name} - Failed: {error}")
    
    # Log as event
    log_event("command_execution", **command_data) 