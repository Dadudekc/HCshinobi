from pathlib import Path
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from ..scrapers.chatgpt import ChatGPTScraper, ChatMetadata


@dataclass
class DevlogEntry:
    """Represents a generated devlog entry."""

    title: str
    content: str
    source_chat: ChatMetadata
    template: str
    generated_at: datetime
    published: bool = False
    published_at: Optional[datetime] = None
    platforms: List[str] = None

    def __post_init__(self):
        if self.platforms is None:
            self.platforms = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "title": self.title,
            "content": self.content,
            "source_chat": asdict(self.source_chat),
            "template": self.template,
            "generated_at": self.generated_at.isoformat(),
            "published": self.published,
            "published_at": self.published_at.isoformat()
            if self.published_at
            else None,
            "platforms": self.platforms,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DevlogEntry":
        """Create from dictionary."""
        return cls(
            title=data["title"],
            content=data["content"],
            source_chat=ChatMetadata(**data["source_chat"]),
            template=data["template"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            published=data["published"],
            published_at=datetime.fromisoformat(data["published_at"])
            if data["published_at"]
            else None,
            platforms=data["platforms"],
        )


class DevlogHarvester:
    """Manages the process of harvesting and generating devlogs from ChatGPT conversations."""

    def __init__(self, output_dir: str = "output/devlogs"):
        """Initialize the harvester."""
        self.logger = logging.getLogger(__name__)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.scraper = None
        self.history_file = self.output_dir / "devlog_history.json"
        self.history: List[DevlogEntry] = []
        self._load_history()

    def _load_history(self):
        """Load devlog generation history."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [DevlogEntry.from_dict(entry) for entry in data]
            except Exception as e:
                self.logger.error(f"Failed to load devlog history: {str(e)}")
                self.history = []

    def _save_history(self):
        """Save devlog generation history."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([entry.to_dict() for entry in self.history], f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save devlog history: {str(e)}")

    def start(self):
        """Start the ChatGPT scraper."""
        if not self.scraper:
            self.scraper = ChatGPTScraper(headless=True)
            self.scraper.start()

    def stop(self):
        """Stop the ChatGPT scraper."""
        if self.scraper:
            self.scraper.close()
            self.scraper = None

    def get_chat_list(self) -> List[ChatMetadata]:
        """Get list of available ChatGPT conversations."""
        if not self.scraper:
            self.start()
        return self.scraper.extract_chat_list()

    def generate_devlog(
        self, chat_url: str, template: str = "technical"
    ) -> Optional[DevlogEntry]:
        """
        Generate a devlog from a ChatGPT conversation.

        Args:
            chat_url: URL of the chat to process
            template: Devlog style template to use

        Returns:
            DevlogEntry if successful, None if failed
        """
        try:
            if not self.scraper:
                self.start()

            # Get chat metadata
            metadata = self.scraper._extract_chat_metadata(chat_url)
            if not metadata:
                self.logger.error("Failed to extract chat metadata")
                return None

            # Generate devlog content
            content = self.scraper.generate_devlog(chat_url, template)
            if not content:
                self.logger.error("Failed to generate devlog content")
                return None

            # Create devlog entry
            entry = DevlogEntry(
                title=metadata.title,
                content=content,
                source_chat=metadata,
                template=template,
                generated_at=datetime.now(),
            )

            # Save to file
            if self.scraper.save_devlog(metadata, content):
                # Add to history
                self.history.append(entry)
                self._save_history()
                return entry

            return None

        except Exception as e:
            self.logger.error(f"Failed to generate devlog: {str(e)}")
            return None

    def get_history(
        self,
        published_only: bool = False,
        template: Optional[str] = None,
        technology: Optional[str] = None,
    ) -> List[DevlogEntry]:
        """
        Get devlog generation history with optional filters.

        Args:
            published_only: Only return published devlogs
            template: Filter by template type
            technology: Filter by technology mentioned

        Returns:
            List of matching DevlogEntry objects
        """
        filtered = self.history

        if published_only:
            filtered = [entry for entry in filtered if entry.published]

        if template:
            filtered = [entry for entry in filtered if entry.template == template]

        if technology:
            filtered = [
                entry
                for entry in filtered
                if technology.lower()
                in [t.lower() for t in entry.source_chat.technologies]
            ]

        return filtered

    def mark_as_published(self, entry: DevlogEntry, platforms: List[str]):
        """
        Mark a devlog as published.

        Args:
            entry: DevlogEntry to mark as published
            platforms: List of platforms where it was published
        """
        entry.published = True
        entry.published_at = datetime.now()
        entry.platforms = platforms
        self._save_history()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about generated devlogs.

        Returns:
            Dictionary containing various statistics
        """
        stats = {
            "total_devlogs": len(self.history),
            "published_devlogs": len([e for e in self.history if e.published]),
            "templates_used": {},
            "technologies": {},
            "platforms": {},
            "generation_timeline": [],
        }

        # Count templates
        for entry in self.history:
            stats["templates_used"][entry.template] = (
                stats["templates_used"].get(entry.template, 0) + 1
            )

            # Count technologies
            for tech in entry.source_chat.technologies:
                stats["technologies"][tech] = stats["technologies"].get(tech, 0) + 1

            # Count platforms
            for platform in entry.platforms:
                stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1

            # Add to timeline
            stats["generation_timeline"].append(
                {
                    "date": entry.generated_at.isoformat(),
                    "title": entry.title,
                    "template": entry.template,
                    "published": entry.published,
                }
            )

        # Sort timeline by date
        stats["generation_timeline"].sort(key=lambda x: x["date"])

        return stats
