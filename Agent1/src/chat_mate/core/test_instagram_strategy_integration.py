"""
Integration tests for InstagramStrategy class
"""

import unittest
from unittest.mock import MagicMock, patch
import os
from pathlib import Path
import json
import tempfile
from typing import Dict, Any, List

from ..instagram_strategy import InstagramStrategy

class TestInstagramStrategyIntegration(unittest.TestCase):
    """Integration test cases for InstagramStrategy class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.driver = MagicMock()
        self.strategy = InstagramStrategy(self.driver)
        
        # Create temporary directories for test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)
        
        # Create test data files
        self.hashtag_db = self.test_data_dir / "instagram_hashtags.json"
        self.location_db = self.test_data_dir / "instagram_locations.json"
        
        # Initialize test data
        self.test_hashtags = {
            "categories": {
                "travel": ["#travel", "#wanderlust", "#adventure"],
                "food": ["#food", "#foodie", "#yummy"]
            },
            "performance": {
                "#travel": [0.5, 0.6],
                "#food": [0.4, 0.5]
            }
        }
        
        self.test_locations = {
            "categories": {
                "cities": [
                    {"name": "New York", "coordinates": [40.7128, -74.0060]},
                    {"name": "London", "coordinates": [51.5074, -0.1278]}
                ]
            },
            "performance": {
                "New York": [0.7, 0.8],
                "London": [0.6, 0.7]
            }
        }
        
        # Write test data to files
        with open(self.hashtag_db, 'w') as f:
            json.dump(self.test_hashtags, f)
            
        with open(self.location_db, 'w') as f:
            json.dump(self.test_locations, f)
            
        # Patch the file paths
        self.strategy.hashtag_db = self.hashtag_db
        self.strategy.location_db = self.location_db
        
    def tearDown(self):
        """Clean up test fixtures"""
        self.temp_dir.cleanup()
        
    def test_hashtag_management_integration(self):
        """Test hashtag management workflow"""
        # Load existing hashtags
        self.strategy._load_hashtags()
        self.assertEqual(self.strategy.hashtags, self.test_hashtags)
        
        # Add new hashtags
        self.strategy.add_hashtags("travel", ["#explore", "#vacation"])
        self.assertIn("#explore", self.strategy.hashtags["categories"]["travel"])
        self.assertIn("#vacation", self.strategy.hashtags["categories"]["travel"])
        
        # Get hashtags
        hashtags = self.strategy.get_hashtags("travel", 2)
        self.assertEqual(len(hashtags), 2)
        self.assertTrue(all(tag.startswith("#") for tag in hashtags))
        
        # Track performance
        self.strategy.track_hashtag_performance("#travel", 0.7)
        self.assertEqual(len(self.strategy.hashtags["performance"]["#travel"]), 3)
        
    def test_location_management_integration(self):
        """Test location management workflow"""
        # Load existing locations
        self.strategy._load_locations()
        self.assertEqual(self.strategy.locations, self.test_locations)
        
        # Add new location
        self.strategy.add_location("Paris", "cities", (48.8566, 2.3522))
        self.assertEqual(len(self.strategy.locations["categories"]["cities"]), 3)
        
        # Get locations
        locations = self.strategy.get_locations("cities")
        self.assertEqual(len(locations), 3)
        self.assertTrue(all("name" in loc for loc in locations))
        
        # Track performance
        self.strategy.track_location_performance("Paris", 0.8)
        self.assertEqual(len(self.strategy.locations["performance"]["Paris"]), 1)
        
    def test_post_workflow_integration(self):
        """Test complete post workflow"""
        # Mock login
        self.strategy.is_logged_in = MagicMock(return_value=True)
        
        # Create test image files
        image_paths = []
        for i in range(3):
            image_path = self.test_data_dir / f"test_image_{i}.jpg"
            with open(image_path, 'w') as f:
                f.write("test image content")
            image_paths.append(str(image_path))
            
        # Test carousel post
        success = self.strategy.post_carousel(
            "Test carousel post",
            image_paths,
            hashtags=["#test", "#integration"],
            location="New York"
        )
        self.assertTrue(success)
        
        # Test post editing
        success = self.strategy.edit_carousel(
            "https://instagram.com/p/test",
            new_content="Updated caption",
            new_image_paths=image_paths[:2]
        )
        self.assertTrue(success)
        
    def test_story_workflow_integration(self):
        """Test complete story workflow"""
        # Mock login
        self.strategy.is_logged_in = MagicMock(return_value=True)
        
        # Create test image file
        image_path = self.test_data_dir / "test_story.jpg"
        with open(image_path, 'w') as f:
            f.write("test story content")
            
        # Test story post
        success = self.strategy.post_story(
            "Test story",
            str(image_path)
        )
        self.assertTrue(success)
        
        # Test highlight creation
        success = self.strategy.create_story_highlight(
            "Test Highlight",
            ["story1", "story2"],
            str(image_path)
        )
        self.assertTrue(success)
        
    def test_engagement_analysis_integration(self):
        """Test engagement analysis workflow"""
        # Mock login
        self.strategy.is_logged_in = MagicMock(return_value=True)
        
        # Mock engagement metrics
        self.driver.find_element.return_value.text = "100"
        
        # Test engagement analysis
        metrics = self.strategy.analyze_post_engagement(
            "https://instagram.com/p/test"
        )
        self.assertIn("likes", metrics)
        self.assertIn("comments", metrics)
        self.assertIn("saves", metrics)
        self.assertIn("shares", metrics)
        self.assertIn("engagement_rate", metrics)
        
        # Test hashtag suggestions
        suggestions = self.strategy.get_hashtag_suggestions("travel")
        self.assertTrue(all(isinstance(s, str) for s in suggestions))
        
        # Test location suggestions
        suggestions = self.strategy.get_location_suggestions("New")
        self.assertTrue(all("name" in s for s in suggestions))
        
if __name__ == '__main__':
    unittest.main() 