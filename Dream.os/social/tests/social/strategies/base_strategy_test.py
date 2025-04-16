"""Base test class for social media strategy tests."""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional, Type

from core.exceptions.strategy_exceptions import StrategyError
from core.services.feedback_engine import FeedbackEngine

class BaseStrategyTest:
    """Base test class for all social media strategy tests."""
    
    # To be overridden by subclasses
    strategy_class = None
    platform_name = None
    required_credentials = []
    
    @pytest.fixture
    def mock_config(self):
        """Fixture for valid configuration."""
        return {
            "credentials": {
                self.platform_name: {
                    cred: f"test_{cred}" for cred in self.required_credentials
                }
            }
        }

    @pytest.fixture
    def mock_api(self):
        """Fixture for mocked API client."""
        return Mock()

    @pytest.fixture
    def strategy(self, mock_config, mock_api):
        """Fixture for initialized strategy."""
        strategy = self.strategy_class(mock_config)
        strategy.api = mock_api
        return strategy

    @pytest.fixture
    def snapshot_dir(self, request):
        """Fixture for snapshot directory."""
        return os.path.join(os.path.dirname(__file__), "snapshots", self.platform_name)

    def save_snapshot(self, snapshot_dir: str, name: str, data: Dict[str, Any]) -> None:
        """Save snapshot data to file."""
        os.makedirs(snapshot_dir, exist_ok=True)
        path = os.path.join(snapshot_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load_snapshot(self, snapshot_dir: str, name: str) -> Optional[Dict[str, Any]]:
        """Load snapshot data from file."""
        path = os.path.join(snapshot_dir, f"{name}.json")
        try:
            with open(path) as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def test_init_with_valid_credentials(self, mock_config):
        """Test successful initialization with valid credentials."""
        strategy = self.strategy_class(mock_config)
        assert strategy.config == mock_config
        assert isinstance(strategy.feedback_engine, FeedbackEngine)

    def test_init_with_missing_credentials(self):
        """Test initialization fails with missing credentials."""
        invalid_config = {"credentials": {self.platform_name: {}}}
        with pytest.raises(StrategyError) as exc_info:
            self.strategy_class(invalid_config)
        assert "Missing required" in str(exc_info.value)

    def test_feedback_on_rate_limit(self, strategy):
        """Test feedback is properly recorded on rate limit."""
        strategy.api.create_tweet.side_effect = Exception("Rate limit exceeded")
        
        try:
            strategy.post_tweet("Test message")
        except StrategyError:
            pass
        
        feedback_data = strategy.feedback_engine.feedback_data
        assert len(feedback_data) == 1
        assert feedback_data[0]["strategy"] == self.platform_name
        assert feedback_data[0]["severity"] == "high"
        assert feedback_data[0]["message"] == "Rate limit exceeded"

    def verify_template_rendering(self, strategy, template_data: Dict[str, Any], 
                                snapshot_name: str, snapshot_dir: str) -> None:
        """Helper method to verify template rendering with snapshots."""
        result = strategy.render_template(template_data)
        
        # Compare with snapshot
        snapshot = self.load_snapshot(snapshot_dir, snapshot_name)
        if snapshot is None:
            self.save_snapshot(snapshot_dir, snapshot_name, {
                "template_data": template_data,
                "expected_output": result
            })
        else:
            assert result == snapshot["expected_output"]
            assert template_data == snapshot["template_data"] 