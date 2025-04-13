"""
AI Output Logger Wrapper

This module provides a wrapper around logging utilities to maintain
backward compatibility while avoiding circular dependencies.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from chat_mate.utils.path_manager import PathManager
from chat_mate.utils.logging_utils import write_json_log, setup_basic_logging
from datetime import datetime

# Initialize the logger
logger = setup_basic_logging("ai_output_logger")

# Get base log directory from PathManager
path_manager = PathManager()
BASE_LOG_DIR = path_manager.get_path('reinforcement_logs')

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename by removing or replacing invalid characters."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def log_ai_output(
    context: str,
    input_prompt: str,
    ai_output: str,
    tags: Optional[List[str]] = None,
    result: Optional[str] = None,
    enable_reinforcement: bool = True,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Log AI output with metadata and optional reinforcement processing.
    
    Args:
        context: String indicating which system or module generated the output
        input_prompt: The prompt used to generate the output
        ai_output: The AI's generated output
        tags: Optional list of tags for categorizing this log entry
        result: Optional result (e.g., "executed", "failed") for additional context
        enable_reinforcement: If True, triggers post-processing reinforcement logic
        metadata: Optional dictionary with additional metadata
        
    Returns:
        Optional[str]: Path to the saved log file if successful
    """
    # Create a unique filename based on context and timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{sanitize_filename(context)}_{timestamp}.json"
    log_file_path = os.path.join(BASE_LOG_DIR, filename)
    
    # Ensure the log directory exists
    os.makedirs(BASE_LOG_DIR, exist_ok=True)
    
    # Write the log entry
    try:
        write_json_log(
            component=context,
            result=result or "logged",
            tags=tags,
            ai_output=ai_output,
            event_type="ai_output",
            log_file=log_file_path
        )
        
        # Handle reinforcement processing if needed
        if enable_reinforcement:
            try:
                from chat_mate.utils.reinforcement_trainer import process_feedback
                process_feedback(log_file_path)
            except Exception as e:
                logger.error(f"Error in reinforcement processing: {e}")
        
        return log_file_path
    except Exception as e:
        logger.error(f"Error logging AI output: {e}")
        return None
