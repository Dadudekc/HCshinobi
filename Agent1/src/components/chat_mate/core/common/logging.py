import logging
import sys
from typing import Any, Dict, Optional, List
from datetime import datetime

from .interfaces import ILogger

class UnifiedLogger(ILogger):
    """Unified logging implementation."""
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers: Optional[List[logging.Handler]] = None
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not handlers:
            # Default handlers
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(format))
            handlers = [console_handler]
        
        for handler in handlers:
            self.logger.addHandler(handler)
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self.logger.critical(message, extra=kwargs)

class FileLogger(UnifiedLogger):
    """File-based logging implementation."""
    
    def __init__(
        self,
        name: str,
        filename: str,
        level: int = logging.INFO,
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler(
            filename,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(logging.Formatter(format))
        
        super().__init__(
            name=name,
            level=level,
            format=format,
            handlers=[file_handler]
        )

class JsonLogger(UnifiedLogger):
    """JSON-formatted logging implementation."""
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        handlers: Optional[List[logging.Handler]] = None
    ):
        super().__init__(
            name=name,
            level=level,
            format="%(message)s",  # Raw JSON
            handlers=handlers
        )
    
    def _format_message(self, level: str, message: str, **kwargs: Any) -> Dict[str, Any]:
        """Format message as JSON."""
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs
        }
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(
            self._format_message("DEBUG", message, **kwargs)
        )
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(
            self._format_message("INFO", message, **kwargs)
        )
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(
            self._format_message("WARNING", message, **kwargs)
        )
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(
            self._format_message("ERROR", message, **kwargs)
        )
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message."""
        self.logger.critical(
            self._format_message("CRITICAL", message, **kwargs)
        ) 