from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from mistralai.client import MistralClient

# from mistralai.models.chat_completion import ChatMessage  # REMOVED for mistralai>=1.8.x
from .outline_service import Outline


@dataclass
class Draft:
    """Data class for blog post draft."""

    title: str
    content: str
    word_count: int
    style: str
    tone: str
    keywords: List[str]
    metadata: Dict[str, str]


class DraftService:
    """Service for generating blog post drafts from outlines."""

    def __init__(self, mistral_client: MistralClient):
        self.client = mistral_client
        self.logger = logging.getLogger(__name__)

    def create_draft(self, outline: Outline, context: Optional[Dict] = None) -> Draft:
        """Generate a blog post draft from an outline."""
        try:
            # Construct the draft generation prompt
            draft_prompt = self._build_draft_prompt(outline, context)

            # Get draft from Mistral
            response = self.client.chat(
                model="mistral-tiny",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional blog post writer.",
                    },
                    {"role": "user", "content": draft_prompt},
                ],
            )

            # Parse the response into a Draft object
            draft = self._parse_draft_response(
                response.choices[0].message.content, outline
            )

            return draft

        except Exception as e:
            self.logger.error(f"Error generating draft: {e}")
            raise

    def _build_draft_prompt(
        self, outline: Outline, context: Optional[Dict] = None
    ) -> str:
        """Build the prompt for draft generation."""
        prompt = f"""Write a blog post based on this outline:

TITLE: {outline.title}

STYLE: {outline.style}
TONE: {outline.tone}
TARGET LENGTH: {outline.target_length} words

SECTIONS:
"""

        # Add sections from outline
        for section in outline.sections:
            prompt += f"\n{section['heading']}\n{section['content']}"

        # Add keywords
        prompt += f"\n\nKEYWORDS: {', '.join(outline.keywords)}"

        # Add context if provided
        if context:
            prompt += "\n\nCONTEXT:\n"
            for key, value in context.items():
                prompt += f"{key}: {value}\n"

        prompt += """\n\nPlease write a complete blog post that:
1. Follows the outline structure
2. Maintains the specified style and tone
3. Incorporates the keywords naturally
4. Includes engaging transitions between sections
5. Ends with a strong conclusion and call-to-action

Format the response as:
TITLE: [Your title]

[Your blog post content]

WORD COUNT: [number]"""

        return prompt

    def _parse_draft_response(self, response: str, outline: Outline) -> Draft:
        """Parse the AI response into a Draft object."""
        try:
            # Split response into title and content
            parts = response.split("\n\n", 1)
            title = parts[0].replace("TITLE:", "").strip()
            content = parts[1].split("\n\nWORD COUNT:")[0].strip()

            # Extract word count
            word_count = int(response.split("WORD COUNT:")[1].strip())

            # Create metadata
            metadata = {
                "style": outline.style,
                "tone": outline.tone,
                "target_length": str(outline.target_length),
            }

            return Draft(
                title=title,
                content=content,
                word_count=word_count,
                style=outline.style,
                tone=outline.tone,
                keywords=outline.keywords,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Error parsing draft response: {e}")
            raise
