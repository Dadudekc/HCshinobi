"""
Tests for the AutoReply class.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from autoblogger.services.auto_reply import AutoReply


@pytest.fixture
def mock_credentials():
    """Fixture for mock credentials."""
    return {"api_key": "test_api_key", "api_secret": "test_api_secret"}


@pytest.fixture
def auto_reply(mock_credentials):
    """Fixture for AutoReply instance."""
    return AutoReply("twitter", mock_credentials)


def test_auto_reply_initialization(mock_credentials):
    """Test AutoReply initialization."""
    auto_reply = AutoReply("twitter", mock_credentials)

    assert auto_reply.platform == "twitter"
    assert auto_reply.credentials == mock_credentials
    assert auto_reply.reply_history == []


def test_generate_reply(auto_reply):
    """Test reply generation."""
    post_content = "This is a test post"
    context = {"topic": "AI", "sentiment": "positive"}

    with patch("autoblogger.services.blog_generator.BlogGenerator") as mock_generator:
        # Setup mock generator
        mock_instance = mock_generator.return_value
        mock_instance._generate_content.return_value = "Generated reply content"
        
        # Test reply generation
        reply = auto_reply.generate_reply(post_content, context)
        assert reply == "Generated reply content"


def test_generate_reply_error(auto_reply):
    """Test reply generation with error."""
    with patch("autoblogger.services.blog_generator.BlogGenerator") as mock_generator:
        # Setup mock generator to raise an error
        mock_generator.side_effect = Exception("Generation error")
        
        # Test error handling
        reply = auto_reply.generate_reply("Test post")
        assert reply is None


def test_post_reply(auto_reply):
    """Test posting a reply."""
    post_id = "123"
    reply_text = "Test reply"

    with patch("autoblogger.services.auto_reply.AutoReply._post_twitter_reply") as mock_post:
        mock_post.return_value = True
        success = auto_reply.post_reply(post_id, reply_text)
        assert success
        assert len(auto_reply.reply_history) == 1
        assert auto_reply.reply_history[0]["post_id"] == post_id
        assert auto_reply.reply_history[0]["reply"] == reply_text


def test_post_reply_linkedin(auto_reply):
    """Test posting reply to LinkedIn."""
    auto_reply.platform = "linkedin"
    with patch.object(auto_reply, "_post_linkedin_reply") as mock_post:
        mock_post.return_value = True
        success = auto_reply.post_reply("123456", "Test reply")

        assert success is True
        mock_post.assert_called_once_with("123456", "Test reply")


def test_post_reply_unsupported_platform(auto_reply):
    """Test posting reply to unsupported platform."""
    auto_reply.platform = "unsupported"
    success = auto_reply.post_reply("123456", "Test reply")

    assert success is False


def test_post_reply_error(auto_reply):
    """Test posting reply with error."""
    with patch.object(auto_reply, "_post_twitter_reply") as mock_post:
        mock_post.side_effect = Exception("Posting error")
        success = auto_reply.post_reply("123456", "Test reply")

        assert success is False


def test_save_reply_history(auto_reply, tmp_path):
    """Test saving reply history."""
    # Add some test data
    auto_reply.reply_history = [
        {"post_id": "123", "reply": "Test reply 1"},
        {"post_id": "456", "reply": "Test reply 2"},
    ]

    filepath = tmp_path / "reply_history.json"
    auto_reply.save_reply_history(filepath)

    # Verify file contents
    with open(filepath) as f:
        saved_data = json.load(f)
    assert saved_data == auto_reply.reply_history


def test_load_reply_history(auto_reply, tmp_path):
    """Test loading reply history."""
    history_data = [
        {"post_id": "123", "reply": "Test reply 1"},
        {"post_id": "456", "reply": "Test reply 2"},
    ]

    filepath = tmp_path / "reply_history.json"
    with open(filepath, "w") as f:
        json.dump(history_data, f)

    auto_reply.load_reply_history(filepath)
    assert auto_reply.reply_history == history_data


def test_load_reply_history_invalid_file(auto_reply, tmp_path):
    """Test loading reply history from invalid file."""
    filepath = tmp_path / "invalid.json"
    with open(filepath, "w") as f:
        f.write("invalid json")

    auto_reply.load_reply_history(filepath)
    assert auto_reply.reply_history == []


def test_post_twitter_reply(auto_reply):
    """Test Twitter-specific reply posting."""
    # This is a placeholder test since the actual implementation is TODO
    success = auto_reply._post_twitter_reply("123456", "Test reply")
    assert success is True


def test_post_linkedin_reply(auto_reply):
    """Test LinkedIn-specific reply posting."""
    # This is a placeholder test since the actual implementation is TODO
    success = auto_reply._post_linkedin_reply("123456", "Test reply")
    assert success is True
