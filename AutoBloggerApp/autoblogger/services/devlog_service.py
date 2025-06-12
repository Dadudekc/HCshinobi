#!/usr/bin/env python3
# autoblogger/services/devlog_service.py

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from autoblogger.scrapers.chatgpt import ChatGPTScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class DevlogEntry:
    """Data class for devlog entries."""

    post_id: str
    prompt: str
    outline: List[str]
    draft: str
    final_content: str
    ai_summary: str
    timestamp: datetime = datetime.now()
    metrics: Optional[Dict] = None


class DevlogService:
    """Service for generating devlogs about content generation workflows."""

    def __init__(self, scraper: ChatGPTScraper):
        self.scraper = scraper
        self.logger = logging.getLogger(__name__)

    def _build_prompt(self, context: dict) -> str:
        """Build the prompt for generating a devlog about the content generation process."""
        return (
            f"You are a devlog narrator helping Victor summarize his content generation workflow.\n\n"
            f"Here is the session context:\n"
            f"- Topic: {context['topic']}\n"
            f"- Style: {context['style']}\n"
            f"- Length: {context['length']} words\n"
            f"- Input keywords: {context.get('keywords', '')}\n"
            f"- Generator used: ChatGPTScraper (browser)\n"
            f"- UI: DevLog Generator tab\n\n"
            f"Describe what was generated, how it was structured, and reflect in Victor's tone on any interesting architecture decisions, inspirations, or quirks in the output. "
            f"Use short paragraphs and a bit of personality. Format it like a devlog suitable for public sharing.\n\n"
            f"Remember to:\n"
            f"- Be casual but architecturally aware\n"
            f"- Focus on strategic decisions and tradeoffs\n"
            f"- Highlight any breakthroughs or interesting patterns\n"
            f"- Keep it clear, precise, and authentic to Victor's voice\n"
            f"- No fluff - just the essence of the generation process"
        )

    def generate_devlog(self, context: Dict[str, Any]) -> str:
        """
        Generate a devlog about the content generation process.

        Args:
            context: Dictionary containing generation context
                - topic: The main topic
                - style: Content style (Technical, Tutorial, etc.)
                - length: Target length in words
                - keywords: Optional keywords for generation

        Returns:
            str: Generated devlog content
        """
        try:
            # Build the prompt
            prompt = self._build_prompt(context)

            # Query ChatGPT for the devlog
            devlog = self.scraper.query_ai(prompt)

            # Add timestamp and metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            metadata = f"Generated: {timestamp}\n"
            metadata += f"Topic: {context['topic']}\n"
            metadata += f"Style: {context['style']}\n"
            metadata += f"Length: {context['length']} words\n"
            metadata += "-" * 40 + "\n\n"

            return metadata + devlog

        except Exception as e:
            self.logger.error(f"Error generating devlog: {str(e)}")
            return f"Error generating devlog: {str(e)}"

    def save_devlog(self, devlog: str, output_path: str) -> bool:
        """
        Save the generated devlog to a file.

        Args:
            devlog: The devlog content to save
            output_path: Path to save the devlog

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(devlog)
            return True
        except Exception as e:
            self.logger.error(f"Error saving devlog: {str(e)}")
            return False

    def log_generation(
        self,
        post_id: str,
        prompt: str,
        outline: List[str],
        draft: str,
        final_content: str,
    ) -> DevlogEntry:
        """
        Log a blog post generation run.

        Args:
            post_id: Unique ID for the post
            prompt: Original prompt
            outline: Generated outline
            draft: Initial draft
            final_content: Polished content

        Returns:
            DevlogEntry with AI-generated summary
        """
        try:
            # Generate AI summary
            summary_prompt = (
                "Summarize this blog post generation process as a devlog entry. "
                "Include key decisions, challenges, and insights. "
                "Use a technical but engaging tone."
            )

            ai_summary = self.scraper.query_ai(summary_prompt)

            # Create entry
            entry = DevlogEntry(
                post_id=post_id,
                prompt=prompt,
                outline=outline,
                draft=draft,
                final_content=final_content,
                ai_summary=ai_summary,
            )

            # Save to file
            self._save_entry(entry)

            return entry

        except Exception as e:
            logger.error(f"Error logging generation: {e}")
            raise

    def regenerate_entry(
        self,
        post_id: str,
        prompt: str,
        outline: List[str],
        draft: str,
        final_content: str,
    ) -> str:
        """
        Regenerate the AI summary for a devlog entry.

        Args:
            post_id: ID of the post
            prompt: Original prompt
            outline: Generated outline
            draft: Initial draft
            final_content: Polished content

        Returns:
            New AI-generated summary
        """
        try:
            # Generate new summary
            summary_prompt = (
                "Regenerate the devlog summary for this blog post generation. "
                "Focus on technical insights and key decisions. "
                "Use a clear, professional tone."
            )

            new_summary = self.scraper.query_ai(summary_prompt)

            # Update entry
            entry = self.get_entry_by_post_id(post_id)
            if entry:
                entry.ai_summary = new_summary
                self._save_entry(entry)

            return new_summary

        except Exception as e:
            logger.error(f"Error regenerating entry: {e}")
            raise

    def get_entry_by_post_id(self, post_id: str) -> Optional[DevlogEntry]:
        """Get a devlog entry by post ID."""
        try:
            log_file = self.log_dir / f"{post_id}.json"
            if not log_file.exists():
                return None

            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return DevlogEntry(**data)

        except Exception as e:
            logger.error(f"Error getting entry: {e}")
            return None

    def _save_entry(self, entry: DevlogEntry):
        """Save a devlog entry to file."""
        try:
            log_file = self.log_dir / f"{entry.post_id}.json"

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(entry.__dict__, f, indent=2, default=str)

        except Exception as e:
            logger.error(f"Error saving entry: {e}")
            raise
