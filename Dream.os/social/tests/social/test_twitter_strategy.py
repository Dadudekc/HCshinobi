import unittest
from core.strategies.twitter_strategy import TwitterStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError, RateLimitError
from unittest.mock import Mock, patch

@pytest.fixture
def mock_config():
    return {
        "credentials": {
            "twitter": {
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "access_token": "test_access_token",
                "access_token_secret": "test_token_secret"
            }
        }
    }

@pytest.fixture
def twitter_strategy(mock_config):
    with patch('core.strategies.twitter_strategy.TwitterAPI') as mock_api:
        strategy = TwitterStrategy(mock_config)
        strategy.api = mock_api
        yield strategy

class TestTwitterStrategy:
    def test_tweet_posting_success(self, twitter_strategy):
        """Test successful tweet posting"""
        # Arrange
        tweet_text = "Test tweet #automation"
        twitter_strategy.api.create_tweet.return_value = {"id": "123456789"}

        # Act
        result = twitter_strategy.post_tweet(tweet_text)

        # Assert
        assert result["id"] == "123456789"
        twitter_strategy.api.create_tweet.assert_called_once_with(
            text=tweet_text
        )

    def test_reply_posting_success(self, twitter_strategy):
        """Test successful reply to a tweet"""
        # Arrange
        tweet_id = "123456789"
        reply_text = "Thank you for your feedback!"
        twitter_strategy.api.create_reply.return_value = {"id": "987654321"}

        # Act
        result = twitter_strategy.post_reply(tweet_id, reply_text)

        # Assert
        assert result["id"] == "987654321"
        twitter_strategy.api.create_reply.assert_called_once_with(
            tweet_id=tweet_id,
            text=reply_text
        )

    def test_rate_limit_handling(self, twitter_strategy):
        """Test handling of rate limit errors"""
        # Arrange
        tweet_text = "Test tweet"
        twitter_strategy.api.create_tweet.side_effect = RateLimitError("Rate limit exceeded")

        # Act & Assert
        with pytest.raises(RateLimitError):
            twitter_strategy.post_tweet(tweet_text)

        # Verify feedback was sent
        with patch('social.services.feedback_engine.FeedbackEngine.process_feedback') as mock_feedback:
            twitter_strategy.post_tweet(tweet_text)
            mock_feedback.assert_called_once_with(
                strategy_name="twitter",
                error_severity="high",
                message="Rate limit exceeded"
            )

    def test_intermediate_screen_handling(self, twitter_strategy):
        """Test handling of intermediate screens during login"""
        # Arrange
        mock_screen = Mock()
        mock_screen.find_element.return_value.is_displayed.return_value = True
        
        # Act
        result = twitter_strategy._detect_and_handle_intermediate_screens(mock_screen)
        
        # Assert
        assert result is True
        mock_screen.find_element.assert_called()

    def test_sentiment_analysis_integration(self, twitter_strategy):
        """Test sentiment analysis for tweets"""
        # Arrange
        tweet_text = "This is a positive tweet!"
        
        with patch('social.services.sentiment_analyzer.analyze') as mock_analyze:
            mock_analyze.return_value = 0.8  # Positive sentiment
            
            # Act
            sentiment = twitter_strategy.analyze_tweet_sentiment(tweet_text)
            
            # Assert
            assert sentiment > 0.5
            mock_analyze.assert_called_once_with(tweet_text)

    def test_missing_credentials(self):
        """Test handling of missing credentials"""
        config = {"credentials": {"twitter": {}}}
        
        with pytest.raises(MissingCredentialsError):
            TwitterStrategy(config)

    @pytest.mark.integration
    def test_end_to_end_tweet_workflow(self, twitter_strategy):
        """Integration test for tweet and reply workflow"""
        # Arrange
        tweet_text = "Initial tweet"
        reply_text = "Test reply"
        
        twitter_strategy.api.create_tweet.return_value = {"id": "123456789"}
        twitter_strategy.api.create_reply.return_value = {"id": "987654321"}

        # Act
        tweet_result = twitter_strategy.post_tweet(tweet_text)
        reply_result = twitter_strategy.post_reply(tweet_result["id"], reply_text)

        # Assert
        assert tweet_result["id"] == "123456789"
        assert reply_result["id"] == "987654321"

    @pytest.mark.snapshot
    def test_tweet_template_snapshot(self, snapshot, twitter_strategy):
        """Test tweet template rendering"""
        # Arrange
        template_data = {
            "content": "Testing snapshot!",
            "hashtags": ["#test", "#automation"]
        }
        
        # Act
        rendered = twitter_strategy.render_tweet_template(template_data)
        
        # Assert
        snapshot.assert_match(rendered, "twitter_tweet.txt") 