"""
Custom exceptions for platform strategies.
"""

class StrategyError(Exception):
    """Base class for strategy-related errors."""
    def __init__(self, message="Strategy action failed", platform=None, action=None, original_exception=None):
        self.platform = platform
        self.action = action
        self.original_exception = original_exception
        full_message = f"[{platform or 'Platform'}] {action or 'Action'} failed: {message}"
        if original_exception:
            full_message += f" | Original error: {type(original_exception).__name__}: {original_exception}"
        super().__init__(full_message)

class LoginError(StrategyError):
    """Error during platform login."""
    def __init__(self, message="Login failed", platform=None, action="login", original_exception=None):
        super().__init__(message, platform, action, original_exception)

class PostError(StrategyError):
    """Error during posting content."""
    def __init__(self, message="Posting failed", platform=None, action="post", original_exception=None):
        super().__init__(message, platform, action, original_exception)

class ScrapeError(StrategyError):
    """Error during scraping content."""
    def __init__(self, message="Scraping failed", platform=None, action="scrape", original_exception=None):
        super().__init__(message, platform, action, original_exception)

class RateLimitError(StrategyError):
    """Error due to hitting API rate limits."""
    def __init__(self, message="Rate limit possibly exceeded", platform=None, action=None, original_exception=None):
        super().__init__(message, platform, action, original_exception)

class AuthenticationError(LoginError):
    """Error specifically related to invalid credentials or auth failure."""
    def __init__(self, message="Authentication failed (check credentials/cookies)", platform=None, action="login", original_exception=None):
        super().__init__(message, platform, action, original_exception)

class ContentError(StrategyError):
    """Error related to invalid or rejected content."""
    def __init__(self, message="Content rejected or invalid", platform=None, action=None, original_exception=None):
        super().__init__(message, platform, action, original_exception) 