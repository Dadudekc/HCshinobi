import logging
import requests
from typing import Dict, Any, Optional
from .base import PostPublisher


class DiscordPublisher(PostPublisher):
    """Discord implementation of the PostPublisher interface."""

    def __init__(self, webhook_url: str):
        """
        Initialize the Discord publisher.

        Args:
            webhook_url: Discord webhook URL for posting messages
        """
        self.webhook_url = webhook_url
        self._last_message_id = None

    def publish(self, metadata: Dict[str, Any], content: str) -> bool:
        """
        Publish content to Discord via webhook.

        Args:
            metadata: Dictionary containing post metadata
            content: The main content to publish

        Returns:
            bool: True if publish was successful, False otherwise
        """
        try:
            # Format the message with metadata
            message = {
                "content": f"**{metadata.get('title', 'New Post')}**\n\n{content}",
                "username": metadata.get("author", "AutoBlogger"),
                "avatar_url": metadata.get("avatar_url"),
                "embeds": [],
            }

            # Add any images as embeds
            if metadata.get("image_url"):
                message["embeds"].append({"image": {"url": metadata.get("image_url")}})

            response = requests.post(self.webhook_url, json=message)
            if response.status_code == 204:  # Discord returns 204 on success
                self._last_message_id = response.headers.get("X-Webhook-Id")
                return True

            logging.error(f"Discord webhook failed: {response.text}")
            return False

        except Exception as e:
            logging.error(f"Failed to publish to Discord: {e}")
            return False

    def validate_credentials(self) -> bool:
        """
        Validate Discord webhook URL by sending a test message.

        Returns:
            bool: True if webhook is valid, False otherwise
        """
        try:
            response = requests.post(
                self.webhook_url, json={"content": "Testing webhook connection..."}
            )
            return response.status_code == 204
        except Exception as e:
            logging.error(f"Discord webhook validation failed: {e}")
            return False

    def get_publish_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a Discord message.
        Note: Discord webhooks don't provide a way to fetch message status,
        so this always returns basic info if the message was sent.

        Args:
            message_id: Discord message ID (webhook ID in this case)

        Returns:
            Optional[Dict[str, Any]]: Basic message info or None if not found
        """
        if message_id or self._last_message_id:
            return {
                "id": message_id or self._last_message_id,
                "status": "sent",  # Discord webhooks don't provide delivery status
                "platform": "discord",
            }
        return None
