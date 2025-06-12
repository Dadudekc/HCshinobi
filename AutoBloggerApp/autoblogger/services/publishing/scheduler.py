import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from ..worker.worker_thread import WorkerThread
from .base import PostPublisher


@dataclass
class ScheduledPost:
    """Represents a post scheduled for publishing."""

    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    platforms: List[str]  # List of platform IDs to publish to
    scheduled_time: datetime
    status: str = "pending"  # pending, published, failed
    error: Optional[str] = None


class PublishingScheduler(WorkerThread):
    """
    Manages scheduled posts across multiple publishing platforms.
    Runs as a background thread to handle publishing tasks.
    """

    def __init__(self):
        super().__init__()
        self.publishers: Dict[str, PostPublisher] = {}
        self.scheduled_posts: Dict[str, ScheduledPost] = {}
        self.running = False

    def add_publisher(self, platform_id: str, publisher: PostPublisher):
        """Add a publisher for a specific platform."""
        if publisher.validate_credentials():
            self.publishers[platform_id] = publisher
            logging.info(f"Added publisher for platform: {platform_id}")
        else:
            logging.error(f"Failed to validate credentials for platform: {platform_id}")

    def schedule_post(self, post: ScheduledPost) -> bool:
        """
        Schedule a post for publishing.

        Args:
            post: The post to schedule

        Returns:
            bool: True if successfully scheduled
        """
        try:
            # Validate platforms
            for platform in post.platforms:
                if platform not in self.publishers:
                    raise ValueError(f"Unknown platform: {platform}")

            # Validate scheduled time
            if post.scheduled_time < datetime.now():
                raise ValueError("Scheduled time must be in the future")

            self.scheduled_posts[post.id] = post
            logging.info(f"Scheduled post '{post.title}' for {post.scheduled_time}")
            return True

        except Exception as e:
            logging.error(f"Failed to schedule post: {e}")
            return False

    def cancel_post(self, post_id: str) -> bool:
        """Cancel a scheduled post."""
        if post_id in self.scheduled_posts:
            del self.scheduled_posts[post_id]
            logging.info(f"Cancelled post: {post_id}")
            return True
        return False

    def get_post_status(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a scheduled post."""
        post = self.scheduled_posts.get(post_id)
        if not post:
            return None

        return {
            "id": post.id,
            "title": post.title,
            "scheduled_time": post.scheduled_time.isoformat(),
            "status": post.status,
            "error": post.error,
            "platforms": post.platforms,
        }

    def run(self):
        """Main scheduler loop."""
        self.running = True
        while self.running:
            try:
                now = datetime.now()

                # Check for posts to publish
                for post_id, post in list(self.scheduled_posts.items()):
                    if post.status != "pending":
                        continue

                    if now >= post.scheduled_time:
                        self._publish_post(post)

                # Sleep for a bit
                self.msleep(1000)  # Check every second

            except Exception as e:
                logging.error(f"Error in publishing scheduler: {e}")
                self.msleep(5000)  # Sleep longer on error

    def _publish_post(self, post: ScheduledPost):
        """Publish a post to all specified platforms."""
        success = True
        errors = []

        for platform_id in post.platforms:
            publisher = self.publishers[platform_id]
            try:
                if publisher.publish(post.metadata, post.content):
                    logging.info(f"Successfully published to {platform_id}")
                else:
                    success = False
                    errors.append(f"Failed to publish to {platform_id}")
            except Exception as e:
                success = False
                errors.append(f"Error publishing to {platform_id}: {e}")

        # Update post status
        post.status = "published" if success else "failed"
        post.error = "; ".join(errors) if errors else None

        # Emit status update
        self.log.emit(f"Post '{post.title}' {post.status}")
        if post.error:
            self.log.emit(f"Error: {post.error}")

    def stop(self):
        """Stop the scheduler."""
        self.running = False
        self.wait()  # Wait for thread to finish
