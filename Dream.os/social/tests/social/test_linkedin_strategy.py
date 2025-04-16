import pytest
from core.strategies.linkedin_strategy import LinkedInStrategy
from core.exceptions.strategy_exceptions import MissingCredentialsError, MetricGatheringError
from unittest.mock import Mock, patch
from core.services.feedback_engine import FeedbackEngine

@pytest.fixture
def mock_config():
    return {
        "credentials": {
            "linkedin": {
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "access_token": "test_access_token"
            }
        },
        "metric_thresholds": {
            "engagement_rate": 0.05,
            "connection_growth": 10
        }
    }

@pytest.fixture
def linkedin_strategy(mock_config):
    with patch('social.strategies.linkedin_strategy.LinkedInAPI') as mock_api:
        strategy = LinkedInStrategy(mock_config)
        strategy.api = mock_api
        yield strategy

class TestLinkedInStrategy(unittest.TestCase):
    def test_post_creation_success(self, linkedin_strategy):
        """Test successful post creation"""
        # Arrange
        post_content = "Test post #career"
        linkedin_strategy.api.create_post.return_value = {"id": "123456789"}

        # Act
        result = linkedin_strategy.create_post(post_content)

        # Assert
        assert result["id"] == "123456789"
        linkedin_strategy.api.create_post.assert_called_once_with(
            content=post_content
        )

    def test_metric_gathering_success(self, linkedin_strategy):
        """Test successful metric gathering implementation"""
        # Arrange
        post_id = "123456789"
        mock_metrics = {
            "impressions": 1000,
            "engagement_rate": 0.06,
            "clicks": 50,
            "reactions": 30,
            "comments": 10
        }
        linkedin_strategy.api.get_post_metrics.return_value = mock_metrics

        # Act
        metrics = linkedin_strategy.gather_post_metrics(post_id)

        # Assert
        assert metrics == mock_metrics
        assert metrics["engagement_rate"] > linkedin_strategy.config["metric_thresholds"]["engagement_rate"]
        linkedin_strategy.api.get_post_metrics.assert_called_once_with(post_id)

    def test_metric_gathering_failure(self, linkedin_strategy):
        """Test handling of metric gathering failures"""
        # Arrange
        post_id = "123456789"
        linkedin_strategy.api.get_post_metrics.side_effect = MetricGatheringError("API Error")

        # Act & Assert
        with self.assertRaises(MetricGatheringError):
            linkedin_strategy.gather_post_metrics(post_id)

        # Verify feedback was sent
        with patch.object(FeedbackEngine, 'process_feedback') as mock_feedback:
            try:
                linkedin_strategy.gather_post_metrics(post_id)
            except MetricGatheringError:
                pass
            
            mock_feedback.assert_called_once_with(
                strategy_name="linkedin",
                error_severity="medium",
                message="Failed to gather metrics for post 123456789"
            )

    def test_connection_growth_tracking(self, linkedin_strategy):
        """Test tracking of connection growth metrics"""
        # Arrange
        mock_growth_data = {
            "new_connections": 15,
            "connection_requests_sent": 20,
            "connection_requests_received": 8,
            "acceptance_rate": 0.75
        }
        linkedin_strategy.api.get_connection_metrics.return_value = mock_growth_data

        # Act
        growth_metrics = linkedin_strategy.track_connection_growth()

        # Assert
        assert growth_metrics == mock_growth_data
        assert growth_metrics["new_connections"] > linkedin_strategy.config["metric_thresholds"]["connection_growth"]

    def test_sentiment_analysis_integration(self, linkedin_strategy):
        """Test sentiment analysis for posts and comments"""
        # Arrange
        post_text = "Excited to announce our new product launch! #innovation"
        
        with patch('social.services.sentiment_analyzer.analyze') as mock_analyze:
            mock_analyze.return_value = 0.9  # Very positive sentiment
            
            # Act
            sentiment = linkedin_strategy.analyze_post_sentiment(post_text)
            
            # Assert
            assert sentiment > 0.5
            mock_analyze.assert_called_once_with(post_text)

    def test_missing_credentials(self):
        """Test handling of missing credentials"""
        config = {"credentials": {"linkedin": {}}}
        
        with self.assertRaises(MissingCredentialsError):
            LinkedInStrategy(config)

    @pytest.mark.integration
    def test_end_to_end_post_workflow(self, linkedin_strategy):
        """Integration test for post creation and metric gathering"""
        # Arrange
        post_content = "Test post"
        post_metrics = {
            "impressions": 500,
            "engagement_rate": 0.07
        }
        
        linkedin_strategy.api.create_post.return_value = {"id": "123456789"}
        linkedin_strategy.api.get_post_metrics.return_value = post_metrics

        # Act
        post_result = linkedin_strategy.create_post(post_content)
        metrics = linkedin_strategy.gather_post_metrics(post_result["id"])

        # Assert
        assert post_result["id"] == "123456789"
        assert metrics["engagement_rate"] > linkedin_strategy.config["metric_thresholds"]["engagement_rate"]

    @pytest.mark.snapshot
    def test_post_template_snapshot(self, snapshot, linkedin_strategy):
        """Test post template rendering"""
        # Arrange
        template_data = {
            "content": "Exciting news!",
            "hashtags": ["#innovation", "#tech"],
            "company_mention": "@TechCorp"
        }
        
        # Act
        rendered = linkedin_strategy.render_post_template(template_data)
        
        # Assert
        snapshot.assert_match(rendered, "linkedin_post.html") 