import os
import json
import logging
import functools
from typing import Optional
from datetime import datetime

# -------------------------------------------------------------------
# Directory Setup
# -------------------------------------------------------------------

BASE_DIR = os.getcwd()  # Could use PathManager if available
UTILS_LOG_DIR = os.path.join(BASE_DIR, "utils", "logs")
JSON_LOG_DIR = os.path.join(UTILS_LOG_DIR, "json_logs")

os.makedirs(JSON_LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# Logger Setup
# -------------------------------------------------------------------

def setup_logging(
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        logger_name: Name of the logger
        log_level: Logging level (default: INFO)
        log_to_console: Whether to log to console (default: True)
        log_to_file: Whether to log to file (default: False)
        log_file: Path to log file (default: None)
        log_format: Log message format (default: None)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    logger.handlers = []
    
    # Default format if none provided
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format)
    
    # Console handler
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_to_file:
        if log_file is None:
            log_file = os.path.join(UTILS_LOG_DIR, f"{logger_name}.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

@functools.lru_cache(maxsize=None) # Ensure logger is configured only once
def get_utils_logger() -> logging.Logger:
    """Gets and configures the AletheiaUtilsLogs logger."""
    logger_instance = logging.getLogger("AletheiaUtilsLogs")
    # Prevent adding handlers multiple times if called again (though lru_cache helps)
    if not logger_instance.handlers: 
        logger_instance.setLevel(logging.DEBUG)  # Capture all levels for flexibility

        # File handler for persistent logs
        plain_log_file = os.path.join(UTILS_LOG_DIR, "utils_activity.log")
        file_handler = logging.FileHandler(plain_log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger_instance.addHandler(file_handler)

        # Note: Console handler removed previously for pytest compatibility

        # Initial log message (only runs once due to lru_cache)
        # logger_instance.debug(f" AletheiaUtilsLogs logger initialized at {UTILS_LOG_DIR}")
        
    return logger_instance

# -------------------------------------------------------------------
# Aletheia JSON Log Writer
# -------------------------------------------------------------------

def write_json_log(
    component: str,
    result: str,
    tags=None,
    ai_output=None,
    event_type="system",
    log_file="utils_activity.jsonl"
):
    """
    Unified JSON logger for all utility events.
    """
    logger = get_utils_logger() # Get logger instance
    tags = tags or []
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "component": component.lower(),
        "event_type": event_type.lower(),
        "result": result.lower(),
        "tags": tags,
        "ai_output": ai_output or ""
    }

    file_path = os.path.join(JSON_LOG_DIR, log_file)

    try:
        with open(file_path, "a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")
        logger.debug(f" JSON log recorded: {component.upper()} [{event_type.upper()}]")

    except Exception as e:
        logger.exception(f" Failed to write JSON log for {component.upper()}: {e}")

    # Synchronous plain-text INFO log
    logger.info(f"[{component.upper()}] {event_type.upper()} | Result: {result.upper()} | Tags: {tags} | AI Output: {ai_output or 'N/A'}")

# -------------------------------------------------------------------
# Shortcuts for Common Log Events
# -------------------------------------------------------------------

def log_success(component, message, tags=None, ai_output=None):
    # message param seems unused, keeping signature for now
    write_json_log(component, "successful", tags or ["success"], ai_output, event_type="success")

def log_error(component, error_msg, tags=None):
    logger = get_utils_logger() # Get logger instance
    write_json_log(component, "failed", tags or ["error"], ai_output=error_msg, event_type="error")
    logger.error(f"[{component.upper()}] ERROR: {error_msg}")

# -------------------------------------------------------------------
# Basic Logging Setup Wrapper
# -------------------------------------------------------------------

def setup_basic_logging(
    logger_name: str,
    log_level: int = logging.INFO,
    log_to_console: bool = True,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """A simple wrapper around setup_logging."""
    return setup_logging(
        logger_name=logger_name,
        log_level=log_level,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
        log_file=log_file,
        log_format=log_format
    )
