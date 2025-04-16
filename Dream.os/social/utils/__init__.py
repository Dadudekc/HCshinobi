"""
Dream.OS social media pipeline utilities.
"""

# Import from correct submodules
from .logging_utils import log_event, get_logger # Added get_logger if needed elsewhere
from .selenium_utils import (
    wait_for_element as wait_and_find_element, # Renamed for consistency if desired
    safe_click as wait_and_click, # Renamed for consistency if desired
    safe_send_keys as wait_and_send_keys, # Renamed for consistency if desired
    is_element_present # Assuming this exists or similar functionality
)
from .common import retry_on_exception # Keep retry_on_exception from common

from .cursor import (
    CursorState,
    ChatContext
)

from .devlog_generator import DevLogGenerator
from .devlog_analyzer import DevLogAnalyzer
from .devlog_dispatcher import DevLogDispatcher
from .chatgpt_scraper import ChatGPTScraper

__all__ = [
    # Logging
    'log_event',
    'get_logger',
    
    # Selenium helpers (adjust names based on actual definition in selenium_utils)
    'wait_and_find_element',
    'wait_and_click',
    'wait_and_send_keys',
    'is_element_present',

    # Common utilities
    'retry_on_exception',
    
    # Cursor management
    'CursorState',
    'ChatContext',
    
    # Core services
    'DevLogGenerator',
    'DevLogAnalyzer',
    'DevLogDispatcher',
    'ChatGPTScraper'
] 