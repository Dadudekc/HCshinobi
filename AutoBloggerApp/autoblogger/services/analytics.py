import json
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BlogStats:
    total_posts: int
    total_words: int
    avg_words_per_post: float
    posts_by_style: Dict[str, int]
    posts_by_model: Dict[str, int]
    recent_posts: List[Dict]
    engagement_metrics: Dict[str, float]


class AnalyticsService:
    def __init__(self):
        self.data_file = Path("data/analytics.json")
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_data()

    def load_data(self):
        """Load analytics data from JSON file."""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r") as f:
                    self.data = json.load(f)
            else:
                self.data = {
                    "posts": [],
                    "posts_by_style": {},
                    "posts_by_model": {},
                    "engagement_metrics": {
                        "total_views": 0,
                        "total_likes": 0,
                        "total_comments": 0,
                    },
                }
                self.save_data()
        except Exception as e:
            logging.error(f"Error loading analytics data: {e}")
            self.data = {
                "posts": [],
                "posts_by_style": {},
                "posts_by_model": {},
                "engagement_metrics": {
                    "total_views": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                },
            }

    def save_data(self):
        """Save analytics data to JSON file."""
        try:
            with open(self.data_file, "w") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving analytics data: {e}")

    def add_post(self, post_data):
        """Add a new post to analytics."""
        try:
            # Add post to list
            self.data["posts"].append(post_data)

            # Update style distribution
            style = post_data["style"]
            if style not in self.data["posts_by_style"]:
                self.data["posts_by_style"][style] = {
                    "count": 0,
                    "engagement": {"views": 0, "likes": 0, "comments": 0},
                }
            self.data["posts_by_style"][style]["count"] += 1

            # Update model distribution
            model = post_data["model"]
            if model not in self.data["posts_by_model"]:
                self.data["posts_by_model"][model] = {
                    "count": 0,
                    "engagement": {"views": 0, "likes": 0, "comments": 0},
                }
            self.data["posts_by_model"][model]["count"] += 1

            self.save_data()
        except Exception as e:
            logging.error(f"Error adding post to analytics: {e}")

    def update_engagement(self, post_id, engagement_data):
        """Update engagement metrics for a post."""
        try:
            # Find post
            for post in self.data["posts"]:
                if post["id"] == post_id:
                    # Update post engagement
                    post["engagement"] = engagement_data

                    # Update style engagement
                    style = post["style"]
                    self.data["posts_by_style"][style]["engagement"][
                        "views"
                    ] += engagement_data["views"]
                    self.data["posts_by_style"][style]["engagement"][
                        "likes"
                    ] += engagement_data["likes"]
                    self.data["posts_by_style"][style]["engagement"][
                        "comments"
                    ] += engagement_data["comments"]

                    # Update model engagement
                    model = post["model"]
                    self.data["posts_by_model"][model]["engagement"][
                        "views"
                    ] += engagement_data["views"]
                    self.data["posts_by_model"][model]["engagement"][
                        "likes"
                    ] += engagement_data["likes"]
                    self.data["posts_by_model"][model]["engagement"][
                        "comments"
                    ] += engagement_data["comments"]

                    # Update total engagement
                    self.data["engagement_metrics"]["total_views"] += engagement_data[
                        "views"
                    ]
                    self.data["engagement_metrics"]["total_likes"] += engagement_data[
                        "likes"
                    ]
                    self.data["engagement_metrics"][
                        "total_comments"
                    ] += engagement_data["comments"]

                    self.save_data()
                    break
        except Exception as e:
            logging.error(f"Error updating engagement: {e}")

    def get_current_stats(self):
        """Get current statistics for dashboard display."""
        try:
            # Calculate total posts
            total_posts = len(self.data["posts"])

            # Get engagement metrics
            total_views = self.data["engagement_metrics"]["total_views"]
            total_likes = self.data["engagement_metrics"]["total_likes"]
            total_comments = self.data["engagement_metrics"]["total_comments"]

            # Calculate engagement rate
            engagement_rate = 0
            if total_views > 0:
                engagement_rate = ((total_likes + total_comments) / total_views) * 100

            # Get recent posts (last 5)
            recent_posts = sorted(
                self.data["posts"],
                key=lambda x: datetime.fromisoformat(x["date"]),
                reverse=True,
            )[:5]

            # Prepare trends data
            trends = defaultdict(lambda: defaultdict(int))
            for post in self.data["posts"]:
                date = datetime.fromisoformat(post["date"]).strftime("%Y-%m-%d")
                trends[date]["posts"] += 1
                trends[date]["views"] += post["engagement"]["views"]
                trends[date]["likes"] += post["engagement"]["likes"]
                trends[date]["comments"] += post["engagement"]["comments"]

            # Calculate engagement rate for each date
            for date in trends:
                if trends[date]["views"] > 0:
                    trends[date]["engagement_rate"] = (
                        (trends[date]["likes"] + trends[date]["comments"])
                        / trends[date]["views"]
                        * 100
                    )
                else:
                    trends[date]["engagement_rate"] = 0

            return {
                "total_posts": total_posts,
                "total_views": total_views,
                "engagement_rate": engagement_rate,
                "recent_posts": recent_posts,
                "trends": dict(trends),
                "distribution": {
                    "posts_by_style": self.data["posts_by_style"],
                    "posts_by_model": self.data["posts_by_model"],
                },
            }
        except Exception as e:
            logging.error(f"Error getting current stats: {e}")
            return {
                "total_posts": 0,
                "total_views": 0,
                "engagement_rate": 0,
                "recent_posts": [],
                "trends": {},
                "distribution": {"posts_by_style": {}, "posts_by_model": {}},
            }

    def get_stats(self) -> BlogStats:
        """Get current analytics statistics."""
        try:
            # Calculate posts by style and model
            posts_by_style = defaultdict(int)
            posts_by_model = defaultdict(int)

            for post in self.data["posts"]:
                posts_by_style[post["style"]] += 1
                posts_by_model[post["model"]] += 1

            # Get recent posts (last 5)
            recent_posts = sorted(
                self.data["posts"], key=lambda x: x["date"], reverse=True
            )[:5]

            # Calculate engagement metrics
            total_views = sum(p["engagement"]["views"] for p in self.data["posts"])
            total_likes = sum(p["engagement"]["likes"] for p in self.data["posts"])
            total_comments = sum(
                p["engagement"]["comments"] for p in self.data["posts"]
            )

            engagement_metrics = {
                "avg_views": total_views / max(1, len(self.data["posts"])),
                "avg_likes": total_likes / max(1, len(self.data["posts"])),
                "avg_comments": total_comments / max(1, len(self.data["posts"])),
                "engagement_rate": (total_likes + total_comments)
                / max(1, total_views)
                * 100,
            }

            return BlogStats(
                total_posts=len(self.data["posts"]),
                total_words=sum(p["word_count"] for p in self.data["posts"]),
                avg_words_per_post=sum(p["word_count"] for p in self.data["posts"])
                / max(1, len(self.data["posts"])),
                posts_by_style=dict(posts_by_style),
                posts_by_model=dict(posts_by_model),
                recent_posts=recent_posts,
                engagement_metrics=engagement_metrics,
            )

        except Exception as e:
            logging.error(f"Error getting stats: {e}")
            return BlogStats(0, 0, 0, {}, {}, [], {})

    def get_trends(self, days: int = 30) -> Dict:
        """Get posting and engagement trends over time."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Initialize daily stats
            daily_stats = defaultdict(
                lambda: {"posts": 0, "words": 0, "views": 0, "likes": 0, "comments": 0}
            )

            # Aggregate stats by day
            for post in self.data["posts"]:
                post_date = datetime.fromisoformat(post["date"])
                if start_date <= post_date <= end_date:
                    day_key = post_date.strftime("%Y-%m-%d")
                    daily_stats[day_key]["posts"] += 1
                    daily_stats[day_key]["words"] += post["word_count"]
                    daily_stats[day_key]["views"] += post["engagement"]["views"]
                    daily_stats[day_key]["likes"] += post["engagement"]["likes"]
                    daily_stats[day_key]["comments"] += post["engagement"]["comments"]

            return dict(daily_stats)

        except Exception as e:
            logging.error(f"Error getting trends: {e}")
            return {}
