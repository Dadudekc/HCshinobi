"""
Consolidated logging utilities for consistent event tracking.
"""

import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def log_event(
    event_type: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    level: str = "info"
) -> None:
    """Log an event with consistent formatting.
    
    Args:
        event_type: Type of event (e.g., "error", "navigation", "selenium")
        message: Event description
        metadata: Optional additional data
        level: Logging level (debug, info, warning, error, critical)
    """
    logger = logging.getLogger(metadata.get("source", "App") if metadata else "App")
    
    event_data = {
        "type": event_type,
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        **(metadata or {})
    }
    
    log_method = getattr(logger, level.lower())
    log_method(json.dumps(event_data))

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with consistent configuration.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name) 