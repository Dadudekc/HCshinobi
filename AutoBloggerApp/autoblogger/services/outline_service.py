#!/usr/bin/env python3
# autoblogger/services/outline_service.py

import os
import json
import logging
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

from autoblogger.scrapers.chatgpt import ChatGPTScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class Outline:
    """Data class for blog post outlines."""

    title: str
    sections: List[str]
    keywords: List[str]
    style: str
    tone: str


class OutlineService:
    """Service for generating blog post outlines."""

    def __init__(self, scraper: ChatGPTScraper):
        """
        Initialize the outline service.

        Args:
            scraper: ChatGPT scraper instance for AI queries
        """
        self.scraper = scraper
        self.output_dir = Path("output/outlines")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_outline(self, prompt: str) -> Outline:
        """
        Generate a blog post outline from a prompt.

        Args:
            prompt: The blog post prompt

        Returns:
            Outline object with title, sections, and metadata
        """
        try:
            # Generate outline
            outline_prompt = (
                "Create a detailed outline for a blog post based on this prompt:\n\n"
                f"{prompt}\n\n"
                "Include:\n"
                "1. A catchy title\n"
                "2. Main sections with bullet points\n"
                "3. Key technical terms to include\n"
                "4. Writing style (e.g. tutorial, reference, narrative)\n"
                "5. Tone (e.g. formal, conversational, technical)\n\n"
                "Format as JSON with these fields:\n"
                "{\n"
                '  "title": "string",\n'
                '  "sections": ["string"],\n'
                '  "keywords": ["string"],\n'
                '  "style": "string",\n'
                '  "tone": "string"\n'
                "}"
            )

            response = self.scraper.query_ai(outline_prompt)

            # Parse response
            try:
                outline_data = json.loads(response)
                outline = Outline(
                    title=outline_data["title"],
                    sections=outline_data["sections"],
                    keywords=outline_data["keywords"],
                    style=outline_data["style"],
                    tone=outline_data["tone"],
                )
            except json.JSONDecodeError:
                logger.error("Failed to parse outline JSON")
                raise

            # Save outline
            self._save_outline(outline)

            return outline

        except Exception as e:
            logger.error(f"Error generating outline: {e}")
            raise

    def _save_outline(self, outline: Outline):
        """Save an outline to file."""
        try:
            filename = f"{outline.title.lower().replace(' ', '-')}.json"
            output_file = self.output_dir / filename

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(outline.__dict__, f, indent=2)

            logger.info(f"Saved outline to {output_file}")

        except Exception as e:
            logger.error(f"Error saving outline: {e}")
            raise
