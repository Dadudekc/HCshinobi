import logging
import requests
from typing import Dict, Any, Optional, List
from .base import PostPublisher


class MediumPublisher(PostPublisher):
    """
    Publishes posts to Medium via the official API.
    Requires an integration token with "Publish to Medium" scope.
    """

    def __init__(self, integration_token: str, user_id: str):
        """
        Initialize the Medium publisher.

        Args:
            integration_token: Your Medium integration token
            user_id: Your Medium user ID (can fetch via API)
        """
        self.token = integration_token
        self.user_id = user_id
        self.base_url = "https://api.medium.com/v1"
        self._last_post_id = None
        self._last_post_url = None

        # Validate credentials on init
        if not self.validate_credentials():
            raise ValueError("Invalid Medium credentials")

    def validate_credentials(self) -> bool:
        """
        Check that the token and user_id are valid by fetching user details.

        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = requests.get(
                f"{self.base_url}/users/{self.user_id}", headers=headers
            )

            if resp.ok:
                logging.info("Medium credentials validated successfully")
                return True

            logging.error(
                f"Medium credentials validation failed: {resp.status_code} {resp.text}"
            )
            return False

        except Exception as e:
            logging.error(f"Medium credentials validation error: {e}")
            return False

    def publish(self, metadata: Dict[str, Any], content: str) -> bool:
        """
        Publish content on Medium.

        Args:
            metadata: Dictionary containing post metadata:
                - title (str): Post title
                - content_format (str): 'markdown' or 'html'
                - tags (List[str]): Up to 5 tags
                - publish_status (str): 'public', 'draft', or 'unlisted'
                - canonical_url (str, optional): Original post URL
                - license (str, optional): Post license
            content: The post content in the specified format

        Returns:
            bool: True if publish was successful, False otherwise
        """
        try:
            url = f"{self.base_url}/users/{self.user_id}/posts"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            }

            # Validate and prepare payload
            tags = metadata.get("tags", [])[:5]  # Medium limits to 5 tags
            publish_status = metadata.get("publish_status", "public")
            if publish_status not in ["public", "draft", "unlisted"]:
                publish_status = "public"

            payload = {
                "title": metadata["title"],
                "contentFormat": metadata.get("content_format", "markdown"),
                "content": content,
                "tags": tags,
                "publishStatus": publish_status,
            }

            # Add optional fields if present
            if "canonical_url" in metadata:
                payload["canonicalUrl"] = metadata["canonical_url"]
            if "license" in metadata:
                payload["license"] = metadata["license"]

            resp = requests.post(url, headers=headers, json=payload)

            if resp.ok:
                data = resp.json().get("data", {})
                self._last_post_id = data.get("id")
                self._last_post_url = data.get("url")
                logging.info(f"Successfully published to Medium: {self._last_post_url}")
                return True

            logging.error(f"Medium publish failed: {resp.status_code} {resp.text}")
            return False

        except Exception as e:
            logging.error(f"Failed to publish to Medium: {e}")
            return False

    def get_publish_status(
        self, post_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch details of a published post.

        Args:
            post_id: Medium post ID. If None, uses the last published post ID.

        Returns:
            Optional[Dict[str, Any]]: Post details or None if not found
        """
        try:
            pid = post_id or self._last_post_id
            if not pid:
                return None

            headers = {"Authorization": f"Bearer {self.token}"}
            resp = requests.get(f"{self.base_url}/posts/{pid}", headers=headers)

            if resp.ok:
                data = resp.json().get("data", {})
                return {
                    "id": data.get("id"),
                    "url": data.get("url"),
                    "title": data.get("title"),
                    "status": data.get("publishStatus"),
                    "published_at": data.get("publishedAt"),
                    "modified_at": data.get("modifiedAt"),
                }

            logging.error(
                f"Failed to get Medium post status: {resp.status_code} {resp.text}"
            )
            return None

        except Exception as e:
            logging.error(f"Error getting Medium post status: {e}")
            return None
