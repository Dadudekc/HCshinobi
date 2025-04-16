import pytest
import sqlite3
from datetime import datetime, timedelta
import os

# Update import path
from core.utils.devlog_analyzer import DevLogAnalyzer


# Helper function to create sample data
def create_sample_data(conn):
    cursor = conn.cursor()
    # Add sample data creation logic here if needed
    # Example:
    # cursor.execute("INSERT INTO posts (post_id, platform, content, publish_time) VALUES (?, ?, ?, ?)",
    #                ('test_post_1', 'twitter', 'Test content 1', datetime.now().isoformat()))
    # cursor.execute("INSERT INTO metrics (post_id, likes, comments, shares, timestamp) VALUES (?, ?, ?, ?, ?)",
    #                ('test_post_1', 10, 2, 1, datetime.now().isoformat()))
    conn.commit()

def test_track_post_with_publish_time(analyzer: DevLogAnalyzer, db_conn: sqlite3.Connection):
    """Test tracking a post with a specific publish time."""
    publish_time = datetime.now() - timedelta(days=1)
    analyzer.track_post("test_post_2", "facebook", "Another test post", publish_time=publish_time)
    cursor = db_conn.cursor()
    cursor.execute("SELECT post_id, platform, content, publish_time FROM posts WHERE post_id=?", ("test_post_2",))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "test_post_2"
    assert result[1] == "facebook"
    assert result[2] == "Another test post"
    # Check if publish_time matches approximately due to potential DB precision differences
    assert abs(datetime.fromisoformat(result[3]) - publish_time) < timedelta(seconds=1)

def test_get_best_posting_times_no_data(analyzer: DevLogAnalyzer):
    """Test getting best posting times when there is no data."""
    times = analyzer.get_best_posting_times()
    assert times == {} 