"""
Test suite for DevLog Analyzer functionality.
"""

import os
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from utils.devlog_analyzer import DevLogAnalyzer

@pytest.fixture
def test_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    analyzer = DevLogAnalyzer(str(db_path))
    return analyzer

@pytest.fixture
def sample_post_data():
    """Create sample post data for testing."""
    return {
        "post_id": "test123",
        "platform": "twitter",
        "post_type": "main",
        "content": "Test post #python #testing",
        "tags": ["python", "testing"],
        "url": "https://example.com/test"
    }

@pytest.fixture
def sample_metrics():
    """Create sample metrics data for testing."""
    return {
        "likes": 10,
        "shares": 5,
        "comments": 3
    }

def test_track_post(test_db, sample_post_data):
    """Test tracking a new post."""
    test_db.track_post(**sample_post_data)
    
    # Verify post was tracked
    with test_db._get_connection() as conn:
        cursor = conn.execute("SELECT * FROM posts WHERE id = ?", (sample_post_data["post_id"],))
        post = cursor.fetchone()
        
        assert post is not None
        assert post[1] == sample_post_data["platform"]
        assert post[2] == sample_post_data["post_type"]
        assert post[3] == sample_post_data["content"]

def test_update_metrics(test_db, sample_post_data, sample_metrics):
    """Test updating post metrics."""
    # First track the post
    test_db.track_post(**sample_post_data)
    
    # Update metrics
    test_db.update_metrics(sample_post_data["post_id"], sample_metrics)
    
    # Verify metrics were updated
    with test_db._get_connection() as conn:
        cursor = conn.execute(
            "SELECT metric_type, value FROM metrics WHERE post_id = ?",
            (sample_post_data["post_id"],)
        )
        metrics = {row[0]: row[1] for row in cursor.fetchall()}
        
        assert metrics["likes"] == sample_metrics["likes"]
        assert metrics["shares"] == sample_metrics["shares"]
        assert metrics["comments"] == sample_metrics["comments"]

def test_get_best_posting_times(test_db):
    """Test getting best posting times."""
    # Add some test posts with metrics
    now = datetime.now()
    
    # Create posts at different times
    for hour in [9, 12, 15, 18]:
        post_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        post_id = f"test_post_{hour}"
        
        test_db.track_post(
            post_id=post_id,
            platform="twitter",
            post_type="main",
            content=f"Test post at {hour}:00",
            publish_time=post_time
        )
        
        # Add metrics (higher engagement during business hours)
        engagement = 100 if 9 <= hour <= 17 else 50
        test_db.update_metrics(post_id, {"likes": engagement})
    
    # Get best posting times
    best_times = test_db.get_best_posting_times("twitter", days=1)
    
    # Verify results
    assert best_times
    assert len(best_times[now.strftime("%A")]) > 0

def test_get_top_performing_tags(test_db):
    """Test getting top performing tags."""
    # Add posts with different tags and engagement levels
    tags_data = [
        (["python", "coding"], 100),
        (["javascript", "webdev"], 75),
        (["python", "testing"], 50)
    ]
    
    for i, (tags, engagement) in enumerate(tags_data):
        post_id = f"test_post_{i}"
        test_db.track_post(
            post_id=post_id,
            platform="twitter",
            post_type="main",
            content=f"Test post with tags {' '.join(f'#{tag}' for tag in tags)}",
            tags=tags
        )
        test_db.update_metrics(post_id, {"likes": engagement})
    
    # Get top tags
    top_tags = test_db.get_top_performing_tags("twitter", days=1)
    
    # Verify results
    assert "python" in top_tags  # Should be first due to highest total engagement
    assert len(top_tags) > 0

def test_get_content_insights(test_db):
    """Test getting content performance insights."""
    # Add posts of different types with varying engagement
    post_types = ["main", "thread", "article"]
    
    for post_type in post_types:
        post_id = f"test_{post_type}"
        content = "Test " * (50 if post_type == "article" else 20)
        
        test_db.track_post(
            post_id=post_id,
            platform="linkedin",
            post_type=post_type,
            content=content,
            tags=["test"]
        )
        
        # Add metrics
        engagement = {
            "main": 50,
            "thread": 75,
            "article": 100
        }[post_type]
        
        test_db.update_metrics(post_id, {"likes": engagement})
    
    # Get insights
    insights = test_db.get_content_insights("linkedin", days=1)
    
    # Verify results
    assert "optimal_lengths" in insights
    assert "best_times" in insights
    assert "top_tags" in insights
    assert len(insights["optimal_lengths"]) > 0 