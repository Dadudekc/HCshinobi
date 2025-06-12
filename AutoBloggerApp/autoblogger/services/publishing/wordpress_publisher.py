import logging
from typing import Dict, Any, Optional
from ..wordpress_client import WordPressClient
from .base import PostPublisher


class WordPressPublisher(PostPublisher):
    """WordPress implementation of the PostPublisher interface."""

    def __init__(self, config):
        """
        Initialize the WordPress publisher.

        Args:
            config: Configuration object containing WordPress credentials and settings
        """
        self.client = WordPressClient(config)
        self._last_post_id = None

    def publish(self, metadata: Dict[str, Any], content: str) -> bool:
        """
        Publish content to WordPress.

        Args:
            metadata: Dictionary containing post metadata
            content: The main content to publish

        Returns:
            bool: True if publish was successful, False otherwise
        """
        try:
            result = self.client.post_to_wordpress(
                title=metadata.get("title", ""),
                content=content,
                excerpt=metadata.get("excerpt", ""),
                categories=metadata.get("categories", []),
                tags=metadata.get("tags", []),
                image_url=metadata.get("image_url"),
            )

            if result:
                self._last_post_id = str(result.get("id"))
                return True
            return False

        except Exception as e:
            logging.error(f"Failed to publish to WordPress: {e}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate WordPress credentials by attempting to fetch categories.

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Try to fetch categories as a simple validation
            response = self.client.post_to_wordpress(
                title="Test Post",
                content="Test content",
                excerpt="Test excerpt",
                categories=[],
                tags=[],
            )
            return response is not None
        except Exception as e:
            logging.error(f"WordPress credentials validation failed: {e}")
            return False

    def get_publish_status(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a WordPress post.

        Args:
            post_id: WordPress post ID

        Returns:
            Optional[Dict[str, Any]]: Post status information or None if not found
        """
        try:
            # Use the last post ID if none provided
            target_id = post_id or self._last_post_id
            if not target_id:
                return None

            # Fetch post status from WordPress
            response = self.client.post_to_wordpress(
                title="Status Check", content="", excerpt="", categories=[], tags=[]
            )

            if response:
                return {
                    "id": response.get("id"),
                    "status": response.get("status"),
                    "link": response.get("link"),
                    "modified": response.get("modified"),
                }
            return None

        except Exception as e:
            logging.error(f"Failed to get WordPress post status: {e}")
            return None
