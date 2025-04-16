"""
Test suite for DevLog Dispatcher functionality.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from utils.devlog_dispatcher import DevLogDispatcher, ContentHandler

@pytest.fixture
def mock_twitter():
    """Create a mock Twitter strategy."""
    mock = Mock()
    mock.post_update = Mock()
    mock.post_thread = Mock()
    return mock

@pytest.fixture
def mock_linkedin():
    """Create a mock LinkedIn strategy."""
    mock = Mock()
    mock.post_update = Mock()
    mock.post_article = Mock()
    return mock

@pytest.fixture
def test_content_dir(tmp_path):
    """Create a temporary content directory structure."""
    content_dir = tmp_path / "content"
    posts_dir = content_dir / "posts"
    social_dir = content_dir / "social"
    (social_dir / "twitter").mkdir(parents=True)
    (social_dir / "linkedin").mkdir(parents=True)
    return content_dir

@pytest.fixture
def dispatcher(test_content_dir, mock_twitter, mock_linkedin):
    """Create a DevLogDispatcher instance with mock strategies."""
    with patch('utils.devlog_dispatcher.TwitterStrategy', return_value=mock_twitter), \
         patch('utils.devlog_dispatcher.LinkedInStrategy', return_value=mock_linkedin):
        dispatcher = DevLogDispatcher(
            content_dir=str(test_content_dir),
            twitter_config={"api_key": "test"},
            linkedin_config={"client_id": "test"}
        )
        return dispatcher

def test_handle_new_blog_post(dispatcher, test_content_dir):
    """Test handling of new blog posts."""
    post_path = test_content_dir / "posts" / "test-post.md"
    post_path.parent.mkdir(exist_ok=True)
    post_path.write_text("# Test Post\nContent")
    
    dispatcher.handle_new_blog_post(str(post_path))
    assert str(post_path) in dispatcher.published["blog"]

def test_handle_new_twitter_content(dispatcher, test_content_dir, mock_twitter):
    """Test handling of new Twitter content."""
    content_path = test_content_dir / "social" / "twitter" / "test-posts.json"
    content_path.parent.mkdir(exist_ok=True)
    
    posts = [
        {"type": "main", "content": "Main tweet"},
        {"type": "thread", "content": "Thread content"}
    ]
    
    with open(content_path, 'w') as f:
        json.dump(posts, f)
    
    dispatcher.handle_new_social_content(str(content_path))
    
    mock_twitter.post_update.assert_called_once_with("Main tweet")
    mock_twitter.post_thread.assert_called_once_with("Thread content")
    assert str(content_path) in dispatcher.published["twitter"]

def test_handle_new_linkedin_content(dispatcher, test_content_dir, mock_linkedin):
    """Test handling of new LinkedIn content."""
    content_path = test_content_dir / "social" / "linkedin" / "test-posts.json"
    content_path.parent.mkdir(exist_ok=True)
    
    posts = [
        {"type": "main", "content": "Main post"},
        {"type": "thread", "content": "Article content"}
    ]
    
    with open(content_path, 'w') as f:
        json.dump(posts, f)
    
    dispatcher.handle_new_social_content(str(content_path))
    
    mock_linkedin.post_update.assert_called_once_with("Main post")
    mock_linkedin.post_article.assert_called_once_with("Article content")
    assert str(content_path) in dispatcher.published["linkedin"]

def test_content_handler(dispatcher):
    """Test the ContentHandler file system event handling."""
    handler = ContentHandler(dispatcher)
    
    # Mock file system events
    class MockEvent:
        def __init__(self, path, is_directory=False):
            self.src_path = path
            self.is_directory = is_directory
    
    # Test blog post event
    blog_event = MockEvent("test.md")
    with patch.object(dispatcher, 'handle_new_blog_post') as mock_handle_blog:
        handler.on_created(blog_event)
        mock_handle_blog.assert_called_once_with("test.md")
    
    # Test social content event
    social_event = MockEvent("test-posts.json")
    with patch.object(dispatcher, 'handle_new_social_content') as mock_handle_social:
        handler.on_created(social_event)
        mock_handle_social.assert_called_once_with("test-posts.json")
    
    # Test directory event (should be ignored)
    dir_event = MockEvent("test_dir", is_directory=True)
    with patch.object(dispatcher, 'handle_new_blog_post') as mock_handle_blog:
        handler.on_created(dir_event)
        mock_handle_blog.assert_not_called()

def test_schedule_post(dispatcher):
    """Test post scheduling functionality."""
    post_path = "test-post.md"
    publish_time = datetime.now() + timedelta(hours=1)
    
    # This is a placeholder test since scheduling is not fully implemented
    dispatcher.schedule_post(post_path, publish_time)
    # In the future, we would assert that the post was properly scheduled

def test_duplicate_handling(dispatcher, test_content_dir):
    """Test that duplicate content is not published multiple times."""
    post_path = test_content_dir / "posts" / "test-post.md"
    post_path.parent.mkdir(exist_ok=True)
    post_path.write_text("# Test Post\nContent")
    
    # First attempt should work
    dispatcher.handle_new_blog_post(str(post_path))
    assert str(post_path) in dispatcher.published["blog"]
    
    # Reset the mock to check if it's called again
    dispatcher.handle_new_blog_post(str(post_path))
    assert len([p for p in dispatcher.published["blog"] if p == str(post_path)]) == 1 