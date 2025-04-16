import pytest
from unittest.mock import Mock, patch
from core.strategies.facebook_strategy import FacebookStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError

@pytest.fixture
def mock_config():
    return {
        "credentials": {
            "facebook": {
                "app_id": "test_app_id",
                "app_secret": "test_app_secret",
                "access_token": "test_access_token"
            }
        }
    }

@pytest.fixture
def facebook_strategy(mock_config):
    with patch('social.strategies.facebook_strategy.FacebookAPI') as mock_api:
        strategy = FacebookStrategy(mock_config)
        strategy.api = mock_api
        yield strategy

class TestFacebookStrategy:
    def test_reply_posting_success(self, facebook_strategy):
        """Test successful reply posting to a comment"""
        # Arrange
        post_id = "123456789"
        reply_text = "Thank you for your feedback!"
        facebook_strategy.api.post_comment.return_value = {"id": "987654321"}

        # Act
        result = facebook_strategy.post_reply(post_id, reply_text)

        # Assert
        assert result["id"] == "987654321"
        facebook_strategy.api.post_comment.assert_called_once_with(
            post_id=post_id,
            message=reply_text
        )

    def test_reply_posting_failure(self, facebook_strategy):
        """Test handling of failed reply posting"""
        # Arrange
        post_id = "123456789"
        reply_text = "Thank you for your feedback!"
        facebook_strategy.api.post_comment.side_effect = Exception("API Error")

        # Act & Assert
        with pytest.raises(Exception):
            facebook_strategy.post_reply(post_id, reply_text)

    def test_reward_mechanism(self, facebook_strategy):
        """Test reward calculation and application"""
        # Arrange
        engagement_data = {
            "likes": 100,
            "comments": 20,
            "shares": 5
        }
        
        # Act
        reward = facebook_strategy.calculate_engagement_reward(engagement_data)

        # Assert
        assert reward > 0
        assert isinstance(reward, float)

    def test_missing_credentials(self):
        """Test handling of missing credentials"""
        config = {"credentials": {"facebook": {}}}
        
        with pytest.raises(MissingCredentialsError):
            FacebookStrategy(config)

    @pytest.mark.integration
    def test_end_to_end_post_and_reply(self, facebook_strategy):
        """Integration test for posting and replying workflow"""
        # Arrange
        post_content = "Test post content"
        reply_text = "Test reply"
        
        facebook_strategy.api.create_post.return_value = {"id": "123456789"}
        facebook_strategy.api.post_comment.return_value = {"id": "987654321"}

        # Act
        post_result = facebook_strategy.create_post(post_content)
        reply_result = facebook_strategy.post_reply(post_result["id"], reply_text)

        # Assert
        assert post_result["id"] == "123456789"
        assert reply_result["id"] == "987654321"

    def test_sentiment_integration(self, facebook_strategy):
        """Test sentiment analysis integration"""
        # Arrange
        comment_text = "This is a positive comment!"
        
        with patch('social.services.sentiment_analyzer.analyze') as mock_analyze:
            mock_analyze.return_value = 0.8  # Positive sentiment
            
            # Act
            sentiment = facebook_strategy.analyze_comment_sentiment(comment_text)
            
            # Assert
            assert sentiment > 0.5  # Positive threshold
            mock_analyze.assert_called_once_with(comment_text) 