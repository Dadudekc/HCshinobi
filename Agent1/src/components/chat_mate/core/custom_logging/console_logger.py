import sys
from datetime import datetime
from .constants import (
    INFO, DEBUG, WARNING, ERROR, CRITICAL,
    RESET, BLACK, RED, GREEN, YELLOW, BLUE,
    MAGENTA, CYAN, WHITE, BOLD
)

class ConsoleLogger:
    """
    A logger that outputs messages to the console with color formatting.
    """
    
    # ANSI color codes
    RESET = RESET
    BLACK = BLACK
    RED = RED
    GREEN = GREEN
    YELLOW = YELLOW
    BLUE = BLUE
    MAGENTA = MAGENTA
    CYAN = CYAN
    WHITE = WHITE
    BOLD = BOLD
    
    def __init__(self, name="ConsoleLogger", level=INFO):
        """
        Initialize the console logger.
        
        Args:
            name (str): Name of the logger
            level (int): Logging level
        """
        self.name = name
        self.level = level
        self._setup_colors()
        
        # Configure logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Create console handler if not already exists
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            self.logger.addHandler(console_handler)
    
    def _setup_colors(self):
        """Set up color formatting for different log levels."""
        self._colors = {
            DEBUG: self.BLUE,
            INFO: self.GREEN,
            WARNING: self.YELLOW,
            ERROR: self.RED,
            CRITICAL: self.RED + self.BOLD
        }
    
    def _format_message(self, level, message):
        """Format a log message with timestamp and color."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_name = {
            DEBUG: "DEBUG",
            INFO: "INFO",
            WARNING: "WARNING",
            ERROR: "ERROR",
            CRITICAL: "CRITICAL"
        }.get(level, "UNKNOWN")
        
        color = self._colors.get(level, self.WHITE)
        return f"{color}[{timestamp}] [{level_name}] {message}{self.RESET}"
    
    def debug(self, message):
        """Log a debug message."""
        if self.level <= DEBUG:
            print(self._format_message(DEBUG, message), file=sys.stdout)
    
    def info(self, message):
        """Log an info message."""
        if self.level <= INFO:
            print(self._format_message(INFO, message), file=sys.stdout)
    
    def warning(self, message):
        """Log a warning message."""
        if self.level <= WARNING:
            print(self._format_message(WARNING, message), file=sys.stderr)
    
    def error(self, message):
        """Log an error message."""
        if self.level <= ERROR:
            print(self._format_message(ERROR, message), file=sys.stderr)
    
    def critical(self, message):
        """Log a critical message."""
        if self.level <= CRITICAL:
            print(self._format_message(CRITICAL, message), file=sys.stderr)
    
    def log(self, level, message):
        """Log a message with the specified level."""
        if self.level <= level:
            print(self._format_message(level, message), file=sys.stderr)
