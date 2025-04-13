"""
Unit tests for InstagramStrategy class
"""

import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import json
from typing import Dict, Any, List

from ..instagram_strategy import InstagramStrategy

class TestInstagramStrategy(unittest.TestCase):
    """Test cases for InstagramStrategy class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.driver = MagicMock()
        self.strategy = InstagramStrategy(self.driver)
        
    def test_initialization(self):
        """Test InstagramStrategy initialization"""
        self.assertEqual(self.strategy.platform, "instagram")
        self.assertEqual(self.strategy.driver, self.driver)
        self.assertIsNotNone(self.strategy.ig_config)
        self.assertIsInstance(self.strategy.hashtag_db, Path)
        self.assertIsInstance(self.strategy.location_db, Path)
        
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({
        "categories": {"test": ["#test1", "#test2"]},
        "performance": {"#test1": [0.5, 0.6]}
    }))
    def test_load_hashtags(self, mock_file):
        """Test loading hashtags from file"""
        strategy = InstagramStrategy(self.driver)
        self.assertEqual(strategy.hashtags["categories"]["test"], ["#test1", "#test2"])
        self.assertEqual(strategy.hashtags["performance"]["#test1"], [0.5, 0.6])
        
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps({
        "categories": {"test": [{"name": "Location1", "coordinates": [1.0, 2.0]}]},
        "performance": {"Location1": [0.5, 0.6]}
    }))
    def test_load_locations(self, mock_file):
        """Test loading locations from file"""
        strategy = InstagramStrategy(self.driver)
        self.assertEqual(strategy.locations["categories"]["test"][0]["name"], "Location1")
        self.assertEqual(strategy.locations["performance"]["Location1"], [0.5, 0.6])
        
    def test_add_hashtags(self):
        """Test adding hashtags to a category"""
        self.strategy.hashtags = {"categories": {}, "performance": {}}
        self.strategy.add_hashtags("test", ["#test1", "#test2"])
        self.assertEqual(self.strategy.hashtags["categories"]["test"], ["#test1", "#test2"])
        
    def test_get_hashtags(self):
        """Test getting hashtags from a category"""
        self.strategy.hashtags = {
            "categories": {"test": ["#test1", "#test2", "#test3"]},
            "performance": {}
        }
        hashtags = self.strategy.get_hashtags("test", 2)
        self.assertEqual(len(hashtags), 2)
        self.assertTrue(all(tag in ["#test1", "#test2", "#test3"] for tag in hashtags))
        
    def test_track_hashtag_performance(self):
        """Test tracking hashtag performance"""
        self.strategy.hashtags = {"categories": {}, "performance": {}}
        self.strategy.track_hashtag_performance("#test1", 0.5)
        self.assertEqual(self.strategy.hashtags["performance"]["#test1"], [0.5])
        
    def test_add_location(self):
        """Test adding a location"""
        self.strategy.locations = {"categories": {}, "performance": {}}
        self.strategy.add_location("Location1", "test", (1.0, 2.0))
        self.assertEqual(len(self.strategy.locations["categories"]["test"]), 1)
        self.assertEqual(self.strategy.locations["categories"]["test"][0]["name"], "Location1")
        
    def test_get_locations(self):
        """Test getting locations from a category"""
        self.strategy.locations = {
            "categories": {
                "test": [{"name": "Location1", "coordinates": [1.0, 2.0]}]
            },
            "performance": {}
        }
        locations = self.strategy.get_locations("test")
        self.assertEqual(len(locations), 1)
        self.assertEqual(locations[0]["name"], "Location1")
        
    def test_track_location_performance(self):
        """Test tracking location performance"""
        self.strategy.locations = {"categories": {}, "performance": {}}
        self.strategy.track_location_performance("Location1", 0.5)
        self.assertEqual(self.strategy.locations["performance"]["Location1"], [0.5])
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_post_content_with_hashtags(self, mock_is_logged_in):
        """Test posting content with hashtags"""
        mock_is_logged_in.return_value = True
        self.strategy.post_content("Test content", hashtags=["#test1", "#test2"])
        self.driver.get.assert_called_with("https://www.instagram.com/")
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_post_content_with_location(self, mock_is_logged_in):
        """Test posting content with location"""
        mock_is_logged_in.return_value = True
        self.strategy.post_content("Test content", location="Test Location")
        self.driver.get.assert_called_with("https://www.instagram.com/")
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_post_content_with_mentions(self, mock_is_logged_in):
        """Test posting content with mentions"""
        mock_is_logged_in.return_value = True
        self.strategy.post_content("Test content", mentions=["@user1", "@user2"])
        self.driver.get.assert_called_with("https://www.instagram.com/")
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_analyze_post_engagement(self, mock_is_logged_in):
        """Test analyzing post engagement"""
        mock_is_logged_in.return_value = True
        self.driver.find_element.return_value.text = "100"
        metrics = self.strategy.analyze_post_engagement("https://instagram.com/p/test")
        self.assertIn("likes", metrics)
        self.assertIn("comments", metrics)
        self.assertIn("saves", metrics)
        self.assertIn("shares", metrics)
        self.assertIn("engagement_rate", metrics)
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_get_hashtag_suggestions(self, mock_is_logged_in):
        """Test getting hashtag suggestions"""
        mock_is_logged_in.return_value = True
        self.driver.find_elements.return_value = [
            MagicMock(get_attribute=lambda x: "/explore/tags/test1/"),
            MagicMock(get_attribute=lambda x: "/explore/tags/test2/")
        ]
        suggestions = self.strategy.get_hashtag_suggestions("test")
        self.assertTrue(all(s.startswith("test") for s in suggestions))
        
    @patch.object(InstagramStrategy, 'is_logged_in')
    def test_get_location_suggestions(self, mock_is_logged_in):
        """Test getting location suggestions"""
        mock_is_logged_in.return_value = True
        mock_element = MagicMock()
        mock_element.text = "Test Location"
        mock_element.get_attribute.return_value = "/explore/locations/123/"
        self.driver.find_elements.return_value = [mock_element]
        suggestions = self.strategy.get_location_suggestions("test")
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0]["name"], "Test Location")
        
if __name__ == '__main__':
    unittest.main() 