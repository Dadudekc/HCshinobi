from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class PostPublisher(ABC):
    """Base interface for all platform-specific post publishers."""

    @abstractmethod
    def publish(self, metadata: Dict[str, Any], content: str) -> bool:
        """
        Publish content to the target platform.

        Args:
            metadata: Dictionary containing post metadata (title, tags, etc.)
            content: The main content to publish

        Returns:
            bool: True if publish was successful, False otherwise
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """
        Validate that the publisher's credentials are valid.

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        pass

    @abstractmethod
    def get_publish_status(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a published post.

        Args:
            post_id: Platform-specific identifier for the post

        Returns:
            Optional[Dict[str, Any]]: Post status information or None if not found
        """
        pass
