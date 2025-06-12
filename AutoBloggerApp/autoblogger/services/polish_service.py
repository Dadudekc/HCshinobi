from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from mistralai.client import MistralClient

# from mistralai.models.chat_completion import ChatMessage  # REMOVED for mistralai>=1.8.x
from .draft_service import Draft


@dataclass
class PolishedPost:
    """Data class for polished blog post."""

    title: str
    content: str
    word_count: int
    style: str
    tone: str
    keywords: List[str]
    metadata: Dict[str, str]
    seo_meta: Dict[str, str]
    readability_score: float


class PolishService:
    """Service for refining and optimizing blog post drafts."""

    def __init__(self, mistral_client: MistralClient):
        self.client = mistral_client
        self.logger = logging.getLogger(__name__)

    def refine(
        self, draft: Draft, seo_meta: Optional[Dict[str, str]] = None
    ) -> PolishedPost:
        """Refine and optimize a blog post draft."""
        try:
            # Construct the refinement prompt
            refine_prompt = self._build_refine_prompt(draft, seo_meta)

            # Get refined content from Mistral
            response = self.client.chat(
                model="mistral-tiny",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional blog post editor and SEO expert.",
                    },
                    {"role": "user", "content": refine_prompt},
                ],
            )

            # Parse the response into a PolishedPost object
            polished = self._parse_refine_response(
                response.choices[0].message.content, draft, seo_meta
            )

            return polished

        except Exception as e:
            self.logger.error(f"Error refining draft: {e}")
            raise

    def _build_refine_prompt(
        self, draft: Draft, seo_meta: Optional[Dict[str, str]] = None
    ) -> str:
        """Build the prompt for draft refinement."""
        prompt = f"""Refine and optimize this blog post draft:

TITLE: {draft.title}

STYLE: {draft.style}
TONE: {draft.tone}
KEYWORDS: {', '.join(draft.keywords)}

CONTENT:
{draft.content}

Please:
1. Improve readability and flow
2. Optimize for SEO
3. Ensure consistent tone and style
4. Add engaging transitions
5. Strengthen the conclusion
6. Calculate a readability score (0-100)

Format the response as:
TITLE: [Optimized title]

[Refined content]

SEO META:
- Title: [SEO-optimized title]
- Description: [Meta description]
- Keywords: [Comma-separated keywords]

READABILITY: [score]"""

        return prompt

    def _parse_refine_response(
        self, response: str, draft: Draft, seo_meta: Optional[Dict[str, str]] = None
    ) -> PolishedPost:
        """Parse the AI response into a PolishedPost object."""
        try:
            # Split response into sections
            sections = response.split("\n\n")

            # Extract title and content
            title = sections[0].replace("TITLE:", "").strip()
            content = sections[1].strip()

            # Extract SEO meta
            seo_section = next(s for s in sections if s.startswith("SEO META:"))
            seo_lines = seo_section.split("\n")[1:]
            seo_meta = {
                "title": seo_lines[0].replace("- Title:", "").strip(),
                "description": seo_lines[1].replace("- Description:", "").strip(),
                "keywords": seo_lines[2].replace("- Keywords:", "").strip(),
            }

            # Extract readability score
            readability_line = next(s for s in sections if s.startswith("READABILITY:"))
            readability_score = float(
                readability_line.replace("READABILITY:", "").strip()
            )

            # Calculate word count
            word_count = len(content.split())

            return PolishedPost(
                title=title,
                content=content,
                word_count=word_count,
                style=draft.style,
                tone=draft.tone,
                keywords=draft.keywords,
                metadata=draft.metadata,
                seo_meta=seo_meta,
                readability_score=readability_score,
            )

        except Exception as e:
            self.logger.error(f"Error parsing refine response: {e}")
            raise
