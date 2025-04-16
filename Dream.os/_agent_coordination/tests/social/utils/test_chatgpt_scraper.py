import pytest
from unittest.mock import Mock, patch, MagicMock
from social.utils.chatgpt_scraper import ChatGPTScraper  # Assuming this is the main class

@pytest.fixture
def mock_session():
    """Create a mock session with required attributes."""
    session = Mock()
    session.get = Mock()
    session.post = Mock()
    # Add headers as a MagicMock to support item assignment
    session.headers = MagicMock()
    return session

@pytest.fixture
def scraper(mock_session):
    """Create a ChatGPTScraper instance with mocked session."""
    with patch('social.utils.chatgpt_scraper.requests.Session', return_value=mock_session):
        scraper = ChatGPTScraper()
        scraper.session = mock_session
        return scraper

class TestChatGPTScraper:
    """Test suite for ChatGPT scraping functionality."""

    def test_initialization(self):
        """Test scraper initialization and configuration."""
        with patch('social.utils.chatgpt_scraper.requests.Session') as mock_session:
            scraper = ChatGPTScraper()
            assert scraper.session is not None
            assert scraper.base_url == "https://chat.openai.com"
            mock_session.assert_called_once()

    def test_login_success(self, scraper, mock_session):
        """Test successful login flow."""
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"accessToken": "test_token"}

        result = scraper.login("test@example.com", "password123")

        assert result is True
        assert scraper.access_token == "test_token"
        mock_session.post.assert_called_once()

    def test_login_failure(self, scraper, mock_session):
        """Test login failure handling."""
        mock_session.post.return_value.status_code = 401
        mock_session.post.return_value.json.return_value = {"error": "Invalid credentials"}

        result = scraper.login("test@example.com", "wrong_password")

        assert result is False
        assert not hasattr(scraper, 'access_token')
        mock_session.post.assert_called_once()

    @pytest.mark.parametrize("status_code,expected_result", [
        (200, True),
        (401, False),
        (500, False)
    ])
    def test_verify_session(self, scraper, mock_session, status_code, expected_result):
        """Test session verification with different status codes."""
        mock_session.get.return_value.status_code = status_code
        
        result = scraper.verify_session()
        
        assert result == expected_result
        mock_session.get.assert_called_once()

    def test_get_conversation_history(self, scraper, mock_session):
        """Test fetching conversation history."""
        mock_response = {
            "items": [
                {"id": "conv1", "title": "Test Conversation 1"},
                {"id": "conv2", "title": "Test Conversation 2"}
            ],
            "total": 2
        }
        mock_session.get.return_value.json.return_value = mock_response
        mock_session.get.return_value.status_code = 200

        history = scraper.get_conversation_history()

        assert len(history) == 2
        assert history[0]["id"] == "conv1"
        assert history[1]["title"] == "Test Conversation 2"
        mock_session.get.assert_called_once()

    def test_get_conversation_messages(self, scraper, mock_session):
        """Test fetching messages from a specific conversation."""
        conversation_id = "test_conv_id"
        mock_response = {
            "messages": [
                {"id": "msg1", "content": "Hello"},
                {"id": "msg2", "content": "World"}
            ]
        }
        mock_session.get.return_value.json.return_value = mock_response
        mock_session.get.return_value.status_code = 200

        messages = scraper.get_conversation_messages(conversation_id)

        assert len(messages) == 2
        assert messages[0]["content"] == "Hello"
        assert messages[1]["id"] == "msg2"
        mock_session.get.assert_called_once_with(
            f"{scraper.base_url}/conversation/{conversation_id}"
        )

    def test_send_message(self, scraper, mock_session):
        """Test sending a new message."""
        conversation_id = "test_conv_id"
        message = "Hello ChatGPT"
        mock_response = {
            "message": {"id": "response1", "content": "Hello human"}
        }
        mock_session.post.return_value.json.return_value = mock_response
        mock_session.post.return_value.status_code = 200

        response = scraper.send_message(conversation_id, message)

        assert response["message"]["content"] == "Hello human"
        mock_session.post.assert_called_once()

    def test_rate_limit_handling(self, scraper, mock_session):
        """Test handling of rate limit responses."""
        mock_session.post.return_value.status_code = 429
        mock_session.post.return_value.json.return_value = {
            "error": "Rate limit exceeded"
        }

        with pytest.raises(Exception, match="Rate limit exceeded"):
            scraper.send_message("test_conv_id", "test message")

    def test_error_response_handling(self, scraper, mock_session):
        """Test handling of error responses."""
        mock_session.get.return_value.status_code = 500
        mock_session.get.return_value.json.return_value = {
            "error": "Internal server error"
        }

        with pytest.raises(Exception, match="Failed to fetch conversation history"):
            scraper.get_conversation_history()

    @patch('social.utils.chatgpt_scraper.time.sleep')
    def test_retry_mechanism(self, mock_sleep, scraper, mock_session):
        """Test retry mechanism for failed requests."""
        # First two calls fail, third succeeds
        mock_session.get.side_effect = [
            Mock(status_code=500),
            Mock(status_code=500),
            Mock(status_code=200, json=lambda: {"items": []})
        ]

        history = scraper.get_conversation_history()

        assert mock_session.get.call_count == 3
        assert mock_sleep.call_count == 2
        assert isinstance(history, list)

    def test_cleanup(self, scraper, mock_session):
        """Test cleanup and session handling."""
        scraper.cleanup()
        
        mock_session.close.assert_called_once()
        assert not hasattr(scraper, 'access_token') 