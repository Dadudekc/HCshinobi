"""Logging utilities for DreamOS agent coordination.

This module provides standardized logging configuration and helper functions
to ensure consistent logging across the system.
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .base import Singleton

class LogFormatter(logging.Formatter):
    """Custom log formatter that includes timestamp, level, component, and structured data."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with additional context and structured data."""
        # Extract or create extra fields
        extra = getattr(record, 'extra', {})
        component = getattr(record, 'component', 'unknown')
        
        # Create base log entry
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'component': component,
            'message': record.getMessage(),
            'logger': record.name
        }
        
        # Add location info for ERROR and above
        if record.levelno >= logging.ERROR:
            log_entry.update({
                'file': record.filename,
                'line': record.lineno,
                'function': record.funcName
            })
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add any extra fields
        if extra:
            log_entry['extra'] = extra
            
        return json.dumps(log_entry)

class LogManager(metaclass=Singleton):
    """Manages logging configuration and provides helper functions for logging."""
    
    def __init__(self):
        """Initialize the log manager."""
        self.root_logger = logging.getLogger()
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_dir: Optional[Path] = None
        
    def configure(self, 
                 log_dir: Union[str, Path],
                 console_level: int = logging.INFO,
                 file_level: int = logging.DEBUG,
                 max_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5) -> None:
        """Configure logging with console and file handlers.
        
        Args:
            log_dir: Directory to store log files
            console_level: Logging level for console output
            file_level: Logging level for file output
            max_size: Maximum size of each log file in bytes
            backup_count: Number of backup files to keep
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Clear any existing handlers
        self.root_logger.handlers.clear()
        
        # Configure root logger
        self.root_logger.setLevel(logging.DEBUG)
        
        # Create formatters
        json_formatter = LogFormatter()
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        self.root_logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / 'agent.log',
            maxBytes=max_size,
            backupCount=backup_count
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(json_formatter)
        self.root_logger.addHandler(file_handler)
        
    def get_logger(self, name: str, component: str = None) -> logging.Logger:
        """Get or create a logger with the given name and component.
        
        Args:
            name: Logger name (typically __name__ of the module)
            component: Component name for structured logging
            
        Returns:
            Logger instance configured with the given name and component
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            
            # Add component context
            if component:
                logger = logging.LoggerAdapter(logger, {'component': component})
            
            self.loggers[name] = logger
            
        return self.loggers[name]
    
    def set_level(self, level: Union[int, str]) -> None:
        """Set logging level for all handlers.
        
        Args:
            level: Logging level (can be integer or string name)
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper())
            
        for handler in self.root_logger.handlers:
            handler.setLevel(level)

def get_logger(name: str = None, component: str = None) -> logging.Logger:
    """Convenience function to get a logger from the LogManager.
    
    Args:
        name: Logger name (defaults to calling module's name)
        component: Component name for structured logging
        
    Returns:
        Configured logger instance
    """
    if name is None:
        # Get the calling module's name
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'root')
        
    return LogManager().get_logger(name, component) 