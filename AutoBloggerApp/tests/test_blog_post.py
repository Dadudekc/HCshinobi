"""
Tests for the BlogPost model.
"""

import pytest
from datetime import datetime
from autoblogger.models.blog_post import BlogPost


def test_blog_post_creation():
    """Test creating a new blog post with basic attributes."""
    post = BlogPost(
        title="Test Post", content="This is a test post content.", author="Test Author"
    )

    assert post.title == "Test Post"
    assert post.content == "This is a test post content."
    assert post.author == "Test Author"
    assert isinstance(post.publish_date, datetime)
    assert post.categories == []
    assert post.tags == []
    assert post.status == "draft"
    assert post.metadata == {}


def test_blog_post_with_optional_fields():
    """Test creating a blog post with optional fields."""
    post = BlogPost(
        title="Test Post",
        content="Test content",
        author="Test Author",
        excerpt="Test excerpt",
        categories=["Tech", "AI"],
        tags=["python", "testing"],
        featured_image="test.jpg",
        status="published",
    )

    assert post.excerpt == "Test excerpt"
    assert post.categories == ["Tech", "AI"]
    assert post.tags == ["python", "testing"]
    assert post.featured_image == "test.jpg"
    assert post.status == "published"


def test_blog_post_validation():
    """Test blog post validation."""
    # Test with missing required fields
    with pytest.raises(ValueError):
        BlogPost(title="", content="Test content", author="Test Author")

    with pytest.raises(ValueError):
        BlogPost(title="Test", content="", author="Test Author")

    with pytest.raises(ValueError):
        BlogPost(title="Test", content="Test content", author="")


def test_blog_post_methods():
    """Test blog post methods."""
    post = BlogPost(title="Test Post", content="Test content", author="Test Author")

    # Test adding categories
    post.add_category("Tech")
    assert "Tech" in post.categories

    # Test adding tags
    post.add_tag("python")
    assert "python" in post.tags

    # Test setting featured image
    post.set_featured_image("new_image.jpg")
    assert post.featured_image == "new_image.jpg"

    # Test updating metadata
    post.update_metadata({"views": 100, "likes": 50})
    assert post.metadata["views"] == 100
    assert post.metadata["likes"] == 50


def test_wordpress_format():
    """Test conversion to WordPress format."""
    post = BlogPost(
        title="Test Post",
        content="Test content",
        author="Test Author",
        excerpt="Test excerpt",
        categories=["Tech"],
        tags=["python"],
    )

    wp_format = post.to_wordpress_format()

    assert wp_format["title"] == "Test Post"
    assert wp_format["content"] == "Test content"
    assert wp_format["excerpt"] == "Test excerpt"
    assert wp_format["categories"] == ["Tech"]
    assert wp_format["tags"] == ["python"]
    assert "date" in wp_format
    assert "status" in wp_format


def test_blog_post_equality():
    """Test blog post equality comparison."""
    from datetime import datetime
    dt = datetime(2025, 6, 12, 0, 27, 25, 646433)
    post1 = BlogPost(title="Test Post", content="Test content", author="Test Author", publish_date=dt)
    post2 = BlogPost(title="Test Post", content="Test content", author="Test Author", publish_date=dt)
    post3 = BlogPost(title="Different Post", content="Test content", author="Test Author", publish_date=dt)
    assert post1 == post2
    assert post1 != post3


def test_blog_post_str_representation():
    """Test string representation of blog post."""
    post = BlogPost(title="Test Post", content="Test content", author="Test Author")

    assert str(post) == "Test Post by Test Author"
    assert (
        repr(post)
        == f"BlogPost(title='Test Post', author='Test Author', status='draft')"
    )
