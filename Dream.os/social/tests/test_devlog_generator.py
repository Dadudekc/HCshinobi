"""
Test suite for DevLog Generator functionality.
"""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path

from utils.devlog_generator import DevLogGenerator, DevLogPost, ContentBlock

@pytest.fixture
def mock_chat_data():
    """Load mock chat data for testing."""
    with open("tests/mock_data/sample_chat.json", "r") as f:
        return json.load(f)

@pytest.fixture
def generator():
    """Create a DevLogGenerator instance for testing."""
    return DevLogGenerator(template_dir="templates")

def test_process_conversation(generator, mock_chat_data):
    """Test processing a conversation into a DevLogPost."""
    post = generator.process_conversation(mock_chat_data)
    
    # Validate post structure
    assert isinstance(post, DevLogPost)
    assert post.title == "How can I implement a retry mechanism with exponential backoff in Python?"
    assert len(post.content_blocks) > 0
    assert len(post.code_snippets) == 3
    assert len(post.challenges) == 1
    assert len(post.solutions) == 1
    
    # Validate extracted tags
    assert "python" in post.tags
    
    # Validate key learnings
    assert len(post.key_learnings) > 0
    assert any("decorator" in learning.lower() for learning in post.key_learnings)

def test_generate_blog_post(generator, mock_chat_data, tmp_path):
    """Test generating a markdown blog post."""
    post = generator.process_conversation(mock_chat_data)
    output_file = tmp_path / "test-blog-post.md"
    
    success = generator.generate_blog_post(post, str(output_file))
    assert success
    assert output_file.exists()
    
    # Validate blog post content
    content = output_file.read_text()
    assert "# How can I implement a retry mechanism" in content
    assert "```python" in content
    assert "Challenge Encountered" in content
    assert "#python" in content

def test_generate_social_content(generator, mock_chat_data):
    """Test generating social media content."""
    post = generator.process_conversation(mock_chat_data)
    
    # Test Twitter content
    twitter_posts = generator.generate_social_content(post, "twitter")
    assert len(twitter_posts) > 0
    assert "🔧 New DevLog:" in twitter_posts[0]["content"]
    assert len(twitter_posts[0]["content"]) <= 280  # Twitter character limit
    
    # Test LinkedIn content
    linkedin_posts = generator.generate_social_content(post, "linkedin")
    assert len(linkedin_posts) > 0
    assert "🚀 New Development Log:" in linkedin_posts[0]["content"]
    assert "Technical Highlights:" in linkedin_posts[0]["content"]

def test_content_block_processing(generator):
    """Test processing of individual content blocks."""
    code_message = {
        "content": "```python\nprint('hello')\n```",
        "timestamp": datetime.now().isoformat()
    }
    
    block = generator._process_message(code_message)
    assert block.type == "code"
    assert block.metadata["language"] == "python"
    
    error_message = {
        "content": "Error: Connection failed",
        "timestamp": datetime.now().isoformat()
    }
    
    block = generator._process_message(error_message)
    assert block.type == "error"

def main():
    """Run the tests with mock data."""
    # Create necessary directories
    os.makedirs("content/posts", exist_ok=True)
    os.makedirs("content/social/twitter", exist_ok=True)
    os.makedirs("content/social/linkedin", exist_ok=True)
    
    # Initialize generator
    generator = DevLogGenerator()
    
    # Load and process mock data
    with open("tests/mock_data/sample_chat.json", "r") as f:
        chat_data = json.load(f)
    
    # Process conversation
    post = generator.process_conversation(chat_data)
    
    # Generate blog post
    output_file = f"content/posts/{post.date.strftime('%Y-%m-%d')}-python-retry-mechanism.md"
    generator.generate_blog_post(post, output_file)
    
    # Generate social content
    for platform in ["twitter", "linkedin"]:
        social_posts = generator.generate_social_content(post, platform)
        output_dir = Path(f"content/social/{platform}")
        with open(output_dir / f"{post.date.strftime('%Y-%m-%d')}-posts.json", "w") as f:
            json.dump(social_posts, f, indent=2)
    
    print("✅ DevLog generation complete!")
    print(f"📝 Blog post: {output_file}")
    print("🐦 Twitter posts: content/social/twitter/")
    print("🔗 LinkedIn posts: content/social/linkedin/")

if __name__ == "__main__":
    main() 