#!/usr/bin/env python3
# autoblogger/cli/generate_blog.py

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
from mistralai.client import MistralClient
from autoblogger.services.blog_generator import BlogGenerator
from autoblogger.services.vector_db import VectorDB

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_environment() -> Dict:
    """Load environment variables and setup services."""
    # Load environment variables
    load_dotenv()

    # Get API key
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY not found in environment variables")

    # Initialize Mistral client
    client = MistralClient(api_key=api_key)

    # Initialize VectorDB
    vector_db = VectorDB()

    return {"client": client, "vector_db": vector_db}


def generate_blog(
    topic: str, style: str = "informative", target_length: int = 1000
) -> Dict:
    """Generate a blog post using the modular pipeline."""
    try:
        # Setup services
        services = setup_environment()
        generator = BlogGenerator(
            mistral_client=services["client"], vector_db=services["vector_db"]
        )

        # Generate post
        logger.info(f"Generating blog post about: {topic}")
        polished = generator.generate_post(
            prompt=topic, style=style, target_length=target_length
        )

        # Get devlog entry
        devlog_entry = generator.devlog_service.get_entry_by_post_id(
            polished.metadata.get("post_id", "")
        )

        return {
            "topic": topic,
            "outline": polished.metadata.get("outline", []),
            "draft": polished.metadata.get("draft", ""),
            "polished_post": polished.content,
            "devlog": devlog_entry.ai_summary if devlog_entry else "",
        }

    except Exception as e:
        logger.error(f"Error generating blog post: {e}")
        raise


def main():
    """Main CLI entry point."""
    try:
        # Get user input
        print("\n🤖 AutoBlogger CLI")
        print("------------------")
        topic = input("\nEnter topic: ").strip()
        style = input("Enter style (default: informative): ").strip() or "informative"
        length = input("Enter target length (default: 1000): ").strip()
        target_length = int(length) if length.isdigit() else 1000

        # Generate blog post
        print("\nGenerating blog post...")
        result = generate_blog(topic, style, target_length)

        # Display results
        print("\n📝 Final Output:")
        print("----------------")
        print(result["polished_post"])

        print("\n📓 Devlog Summary:")
        print("-----------------")
        print(result["devlog"])

        # Save to file
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        filename = f"blog_{topic.lower().replace(' ', '_')}.md"
        output_path = output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {result['topic']}\n\n")
            f.write(result["polished_post"])

        print(f"\n✅ Blog post saved to: {output_path}")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
