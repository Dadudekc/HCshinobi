"""
DevLog Analyzer - Tracks and analyzes post performance across platforms.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import pandas as pd

logger = logging.getLogger('DevLogAnalyzer')

class DevLogAnalyzer:
    """Analyzes post performance and provides optimization insights."""
    
    def __init__(self, db_path: str = "data/analytics.db"):
        """
        Initialize the analyzer.
        
        Args:
            db_path: Path to SQLite database for storing analytics
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        logger.info("Initialized DevLog Analyzer")
    
    def _get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    publish_time TIMESTAMP NOT NULL,
                    tags TEXT,
                    url TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    post_id TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    metric_type TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts(id)
                )
            """)
    
    def track_post(
        self,
        post_id: str,
        platform: str,
        post_type: str,
        content: str,
        tags: Optional[List[str]] = None,
        url: Optional[str] = None,
        publish_time: Optional[datetime] = None
    ):
        """
        Track a new post.
        
        Args:
            post_id: Unique identifier for the post
            platform: Platform where post was published
            post_type: Type of post (main, thread, article)
            content: Post content
            tags: List of tags used
            url: URL to the post
            publish_time: Time when post was published (defaults to current time)
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO posts (id, platform, post_type, content, publish_time, tags, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post_id,
                        platform,
                        post_type,
                        content,
                        (publish_time or datetime.now()).isoformat(),
                        json.dumps(tags or []),
                        url
                    )
                )
            logger.info(f"Tracked new post: {post_id} on {platform}")
        except Exception as e:
            logger.error(f"Failed to track post {post_id}: {str(e)}")
            raise
    
    def update_metrics(
        self,
        post_id: str,
        metrics: Dict[str, int]
    ):
        """
        Update metrics for a post.
        
        Args:
            post_id: Post identifier
            metrics: Dictionary of metric_type: value pairs
        """
        try:
            timestamp = datetime.now().isoformat()
            with self._get_connection() as conn:
                for metric_type, value in metrics.items():
                    conn.execute(
                        """
                        INSERT INTO metrics (post_id, timestamp, metric_type, value)
                        VALUES (?, ?, ?, ?)
                        """,
                        (post_id, timestamp, metric_type, value)
                    )
            logger.info(f"Updated metrics for post {post_id}")
        except Exception as e:
            logger.error(f"Failed to update metrics for post {post_id}: {str(e)}")
            raise
    
    def get_best_posting_times(self, platform: str, days: int = 30) -> Dict[str, List[str]]:
        """
        Get best posting times based on engagement metrics.
        
        Args:
            platform: Platform to analyze
            days: Number of days to look back
            
        Returns:
            Dictionary mapping days to best posting hours
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            query = """
                SELECT 
                    strftime('%w', p.publish_time) as day_of_week,
                    strftime('%H', p.publish_time) as hour,
                    AVG(m.value) as avg_engagement
                FROM posts p
                JOIN metrics m ON p.id = m.post_id
                WHERE p.platform = ? AND p.publish_time >= ?
                GROUP BY day_of_week, hour
                ORDER BY avg_engagement DESC
            """
            
            with self._get_connection() as conn:
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(platform, cutoff.isoformat())
                )
            
            # Convert day numbers to names and format hours
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            result = {day: [] for day in days}
            
            for _, row in df.iterrows():
                day = days[int(row['day_of_week'])]
                hour = f"{int(row['hour']):02d}:00"
                result[day].append(hour)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get best posting times for {platform}: {str(e)}")
            raise
    
    def get_top_performing_tags(self, platform: str, days: int = 30) -> List[str]:
        """
        Get top performing tags based on engagement metrics.
        
        Args:
            platform: Platform to analyze
            days: Number of days to look back
            
        Returns:
            List of tags sorted by engagement
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            query = """
                SELECT 
                    json_each.value as tag,
                    AVG(m.value) as avg_engagement
                FROM posts p
                JOIN metrics m ON p.id = m.post_id
                JOIN json_each(p.tags) 
                WHERE p.platform = ? AND p.publish_time >= ?
                GROUP BY tag
                ORDER BY avg_engagement DESC
            """
            
            with self._get_connection() as conn:
                return [row[0] for row in conn.execute(query, (platform, cutoff.isoformat()))]
                
        except Exception as e:
            logger.error(f"Failed to get top performing tags for {platform}: {str(e)}")
            raise
    
    def get_content_insights(self, platform: str, days: int = 30) -> Dict[str, any]:
        """
        Get insights about content performance.
        
        Args:
            platform: Platform to analyze
            days: Number of days to look back
            
        Returns:
            Dictionary containing various insights about content performance
        """
        try:
            cutoff = datetime.now() - timedelta(days=days)
            query = """
                SELECT 
                    p.post_type,
                    LENGTH(p.content) as content_length,
                    AVG(m.value) as avg_engagement
                FROM posts p
                JOIN metrics m ON p.id = m.post_id
                WHERE p.platform = ? AND p.publish_time >= ?
                GROUP BY p.post_type
                ORDER BY avg_engagement DESC
            """
            
            with self._get_connection() as conn:
                df = pd.read_sql_query(
                    query,
                    conn,
                    params=(platform, cutoff.isoformat())
                )
            
            insights = {
                "optimal_lengths": {
                    row['post_type']: row['content_length']
                    for _, row in df.iterrows()
                },
                "best_times": self.get_best_posting_times(platform, days),
                "top_tags": self.get_top_performing_tags(platform, days)[:5]
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get content insights for {platform}: {str(e)}")
            raise 