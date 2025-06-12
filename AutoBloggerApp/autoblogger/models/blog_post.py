# autoblogger/models/blog_post.py

"""
Blog post model for AutoBlogger.

This module defines the BlogPost class which represents a blog post in the system.
It handles the structure and validation of blog posts, as well as conversion
to various formats for different platforms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class BlogPost:
    """
    Represents a blog post in the system.

    Attributes:
        title (str): The title of the blog post
        content (str): The main content of the blog post
        author (str): The author of the blog post
        excerpt (Optional[str]): A short summary of the blog post
        publish_date (datetime): When the post was/will be published
        categories (List[str]): Categories the post belongs to
        tags (List[str]): Tags associated with the post
        featured_image (Optional[str]): Path to the featured image
        status (str): Current status of the post (draft, published, etc.)
        metadata (Dict[str, Any]): Additional metadata about the post
    """

    title: str
    content: str
    author: str
    excerpt: Optional[str] = None
    publish_date: datetime = field(default_factory=datetime.now)
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    featured_image: Optional[str] = None
    status: str = "draft"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        Validate the blog post data after initialization.

        Raises:
            ValueError: If required fields are empty or invalid
        """
        try:
            if not self.title.strip():
                raise ValueError("Title cannot be empty")
            if not self.content.strip():
                raise ValueError("Content cannot be empty")
            if not self.author.strip():
                raise ValueError("Author cannot be empty")

            # Normalize status
            self.status = self.status.lower()
            if self.status not in ["draft", "published", "scheduled", "archived"]:
                raise ValueError(f"Invalid status: {self.status}")

        except Exception as e:
            logger.error(f"Error initializing blog post: {e}")
            raise

    def to_wordpress_format(self) -> Dict[str, Any]:
        """
        Convert the blog post to WordPress API format.

        Returns:
            Dict[str, Any]: Blog post data in WordPress format

        Raises:
            ValueError: If required fields are missing
        """
        try:
            return {
                "title": self.title,
                "content": self.content,
                "excerpt": self.excerpt or "",
                "author": self.author,
                "date": self.publish_date.isoformat(),
                "status": self.status,
                "categories": self.categories,
                "tags": self.tags,
                "featured_image": self.featured_image,
                "meta": self.metadata,
            }
        except Exception as e:
            logger.error(f"Error converting to WordPress format: {e}")
            raise

    def validate(self) -> bool:
        """
        Validate the blog post data.

        Returns:
            bool: True if the post is valid

        Raises:
            ValueError: If the post is invalid
        """
        try:
            if not self.title.strip():
                raise ValueError("Title cannot be empty")
            if not self.content.strip():
                raise ValueError("Content cannot be empty")
            if not self.author.strip():
                raise ValueError("Author cannot be empty")
            if self.status not in ["draft", "published", "scheduled", "archived"]:
                raise ValueError(f"Invalid status: {self.status}")
            return True
        except Exception as e:
            logger.error(f"Validation error: {e}")
            raise

    def add_category(self, category: str) -> None:
        """
        Add a category to the blog post.

        Args:
            category (str): Category to add

        Raises:
            ValueError: If category is empty
        """
        try:
            if not category.strip():
                raise ValueError("Category cannot be empty")
            if category not in self.categories:
                self.categories.append(category)
        except Exception as e:
            logger.error(f"Error adding category: {e}")
            raise

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the blog post.

        Args:
            tag (str): Tag to add

        Raises:
            ValueError: If tag is empty
        """
        try:
            if not tag.strip():
                raise ValueError("Tag cannot be empty")
            if tag not in self.tags:
                self.tags.append(tag)
        except Exception as e:
            logger.error(f"Error adding tag: {e}")
            raise

    def set_featured_image(self, image_path: str) -> None:
        """
        Set the featured image for the blog post.

        Args:
            image_path (str): Path to the featured image

        Raises:
            ValueError: If image path is empty
        """
        try:
            if not image_path.strip():
                raise ValueError("Image path cannot be empty")
            self.featured_image = image_path
        except Exception as e:
            logger.error(f"Error setting featured image: {e}")
            raise

    def update_metadata(self, new_metadata: Dict[str, Any]) -> None:
        """
        Update the blog post metadata.

        Args:
            new_metadata (Dict[str, Any]): New metadata to add/update

        Raises:
            ValueError: If metadata is not a dictionary
        """
        try:
            if not isinstance(new_metadata, dict):
                raise ValueError("Metadata must be a dictionary")
            self.metadata.update(new_metadata)
        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            raise

    def __str__(self) -> str:
        """Return a string representation of the blog post."""
        return f"{self.title} by {self.author}"

    def __repr__(self) -> str:
        """Return a detailed string representation of the blog post."""
        return f"BlogPost(title='{self.title}', author='{self.author}', status='{self.status}')"
