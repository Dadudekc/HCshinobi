"""
Blog content generation service.

This module provides functionality to generate blog content using AI models,
including post generation, topic suggestions, and content optimization.
"""

import subprocess
import json
from jinja2 import Environment, FileSystemLoader
import os
import shlex
import time
import markdown
import logging
import requests
from requests.auth import HTTPBasicAuth
import configparser
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
from string import Template
import openai
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv  # For environment variable management
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import re
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from mistralai.client import MistralClient
from .outline_service import OutlineService, Outline
from .draft_service import DraftService, Draft
from .polish_service import PolishService, PolishedPost
from .devlog_service import DevlogService, DevlogEntry
from .vector_db import VectorDB
from .utils import extract_title, extract_introduction
from autoblogger.scrapers.chatgpt import ChatGPTScraper
from dataclasses import dataclass
import uuid

from autoblogger.models.blog_post import BlogPost

# Load environment variables from a .env file
load_dotenv()

# Configure logging
LOG_FILE = "autoblogger.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logging.info("Starting autoblogger configuration setup.")

# Set BASE_DIR to the directory of this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔹 Use the correct config file path: autoblogger/config/config.ini
CONFIG_FILE = os.path.join(BASE_DIR, "config", "config.ini")
config = configparser.ConfigParser()

if not os.path.exists(CONFIG_FILE):
    logging.critical(f"Configuration file not found: {CONFIG_FILE}")
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")

logging.info(f"Loading configuration from: {CONFIG_FILE}")
config.read(CONFIG_FILE)

# WordPress configuration
try:
    WORDPRESS_URL = config.get("wordpress", "url")
    WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME") or config.get(
        "wordpress", "username"
    )
    WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD") or config.get(
        "wordpress", "password"
    )
    DEFAULT_CATEGORIES = json.loads(
        config.get("wordpress", "categories", fallback="[]")
    )
    DEFAULT_TAGS = json.loads(config.get("wordpress", "tags", fallback="[]"))
    POST_STATUS = config.get("wordpress", "status", fallback="draft").strip().lower()

    if POST_STATUS not in ["publish", "draft"]:
        logging.error(
            f"Invalid POST_STATUS value: {POST_STATUS}. Defaulting to 'draft'."
        )
        POST_STATUS = "draft"

    logging.info("WordPress configuration loaded successfully.")
except configparser.NoSectionError as e:
    logging.critical(f"Missing required section in configuration file: {e}")
    raise
except configparser.NoOptionError as e:
    logging.critical(f"Missing required option in configuration file: {e}")
    raise
except json.JSONDecodeError as e:
    logging.critical(f"Error parsing JSON fields in configuration file: {e}")
    raise

# Vector database configuration
try:
    VECTOR_DB_DIMENSION = config.getint("vector_db", "dimension", fallback=768)
    VECTOR_DB_INDEX_FILE = os.path.join(
        BASE_DIR,
        "vector_db",
        config.get("vector_db", "index_file", fallback="vector_store.index").strip(),
    )
    VECTOR_DB_METADATA_FILE = os.path.join(
        BASE_DIR,
        "vector_db",
        config.get(
            "vector_db", "metadata_file", fallback="vector_metadata.json"
        ).strip(),
    )

    if VECTOR_DB_DIMENSION <= 0:
        logging.error(
            f"Invalid VECTOR_DB_DIMENSION value: {VECTOR_DB_DIMENSION}. Defaulting to 768."
        )
        VECTOR_DB_DIMENSION = 768

    logging.info("Vector database configuration loaded successfully.")
except configparser.NoSectionError as e:
    logging.critical(f"Missing required section in configuration file: {e}")
    raise
except configparser.NoOptionError as e:
    logging.critical(f"Missing required option in configuration file: {e}")
    raise
except ValueError as e:
    logging.critical(f"Invalid value in configuration file: {e}")
    raise

# OpenAI configuration
try:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or config.get("openai", "api_key")
    if not OPENAI_API_KEY:
        logging.critical(
            "OpenAI API key is missing in the configuration file or environment variables."
        )
        raise ValueError(
            "OpenAI API key is missing in the configuration file or environment variables."
        )
    openai.api_key = OPENAI_API_KEY
    logging.info("OpenAI configuration loaded successfully.")
except configparser.NoSectionError as e:
    logging.critical(f"Missing 'openai' section in configuration file: {e}")
    raise
except configparser.NoOptionError as e:
    logging.critical(f"Missing 'api_key' option in 'openai' section: {e}")
    raise
except Exception as e:
    logging.critical(f"Error loading OpenAI configuration: {e}")
    raise

logging.info("Configuration setup completed successfully.")

# Initialize a session with retry strategy for robust API calls
session = requests.Session()
retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Initialize model and tokenizer
MODEL_NAME = "mistralai/Mistral-7B-v0.1"
model = None
tokenizer = None


def load_model():
    """Load the AI model and tokenizer."""
    global model, tokenizer

    if model is None or tokenizer is None:
        try:
            # Load tokenizer
            tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            special_tokens = {
                "pad_token": "[PAD]",
                "bos_token": "[START]",
                "eos_token": "[END]",
            }
            tokenizer.add_special_tokens(special_tokens)

            # Load model optimized for CPU
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.float16,
                device_map="cpu",
                offload_folder="./offload_weights",
                use_flash_attention_2=False,
            )

            # Optimize for large vocabulary
            model.tie_weights()
            model.resize_token_embeddings(len(tokenizer))

            logging.info("Model and tokenizer loaded successfully")
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            raise


def initialize_faiss():
    """
    Initializes or loads the FAISS index.
    """
    if os.path.exists(VECTOR_DB_INDEX_FILE):
        try:
            index = faiss.read_index(VECTOR_DB_INDEX_FILE)
            logging.info("FAISS index loaded successfully.")
        except Exception as e:
            logging.error(f"Error loading FAISS index: {e}. Initializing a new index.")
            index = faiss.IndexFlatIP(VECTOR_DB_DIMENSION)
            faiss.write_index(index, VECTOR_DB_INDEX_FILE)
            logging.info("FAISS index initialized and saved.")
    else:
        index = faiss.IndexFlatIP(VECTOR_DB_DIMENSION)
        faiss.write_index(index, VECTOR_DB_INDEX_FILE)
        logging.info("FAISS index initialized and saved.")
    return index


def load_metadata():
    """
    Loads the metadata associated with the vector database.
    """
    if os.path.exists(VECTOR_DB_METADATA_FILE):
        try:
            with open(VECTOR_DB_METADATA_FILE, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            logging.info("Metadata loaded successfully.")
        except json.JSONDecodeError as e:
            logging.error(
                f"Error decoding metadata JSON: {e}. Initializing empty metadata."
            )
            metadata = []
            save_metadata(metadata)
    else:
        metadata = []
        save_metadata(metadata)
        logging.info("Metadata file initialized.")
    return metadata


def save_metadata(metadata):
    """
    Saves the metadata to a JSON file.
    """
    try:
        with open(VECTOR_DB_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        logging.info("Metadata saved successfully.")
    except Exception as e:
        logging.error(f"Error saving metadata: {e}")


def generate_embeddings(texts):
    """
    Generates embeddings for a list of texts using Sentence Transformers.
    """
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings
    except Exception as e:
        logging.error(f"Error generating embeddings: {e}")
        return None


def run_ollama(prompt):
    """
    Runs the Ollama Mistral model with the given prompt and returns the response.
    Implements retry logic for robustness.
    """
    try:
        command = f'ollama run mistral:latest "{prompt}"'
        logging.info(f"Running command: {command}")
        args = shlex.split(command)
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            check=True,
        )
        response = result.stdout.strip()
        logging.info("Ollama response received successfully.")
        return response
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running Ollama: {e.stderr.strip()}")
        return ""
    except Exception as e:
        logging.error(f"Unexpected error running Ollama: {e}")
        return ""


def generate_image(prompt):
    """
    Generates an image using OpenAI's DALL-E based on the provided prompt.
    Returns the URL of the generated image.
    """
    try:
        logging.info("Generating image with OpenAI DALL-E.")
        response = openai.Image.create(
            prompt=prompt, n=1, size="800x400", response_format="url"
        )
        image_url = response["data"][0]["url"]
        logging.info(f"Image generated successfully: {image_url}")
        return image_url
    except Exception as e:
        logging.error(f"Error generating image with OpenAI: {e}")
        fallback_url = "https://via.placeholder.com/800x400.png?text=AI+Driven+Trading+and+Content+Automation"
        logging.info(f"Using fallback image: {fallback_url}")
        return fallback_url


def generate_content():
    """
    Generates content for different sections of the blog post using Ollama prompts.
    Incorporates content categorization and interactive elements.
    """
    content = {}

    base_prompt = Template(
        """
You are a seasoned professional content writer with expertise in day trading and fintech.
Your goal is to produce high-quality, engaging, and SEO-optimized content for the FreeRideInvestor community.
Maintain a transparent, educational, and community-driven tone.

$instruction
"""
    )

    prompts = {
        "post_title": base_prompt.substitute(
            instruction=(
                "Generate a compelling and SEO-friendly blog post title about automating blog posts with AI for day traders and investors, specifically targeting FreeRideInvestor. "
                "Ensure the title is concise (under 70 characters) and evokes curiosity."
            )
        ),
        "post_subtitle": base_prompt.substitute(
            instruction=(
                "Create a subtitle for the blog post titled '{post_title}' that explains the benefits of AI in automating content creation for trading strategies. "
                "Keep it under 120 characters."
            )
        ),
        "introduction": base_prompt.substitute(
            instruction=(
                "Write a 200-word introduction for a blog post on automating blog posts with AI, targeted at day traders and investors. "
                "Highlight the importance of AI in enhancing trading strategies and content creation."
            )
        ),
        "sections": [
            {
                "title": "Enhancing Trading Strategies with AI Automation",
                "prompt": base_prompt.substitute(
                    instruction=(
                        "Explain how AI automation can enhance trading strategies for day traders and investors. "
                        "Include examples, best practices, and benefits."
                    )
                ),
            },
            {
                "title": "Integrating AI Tools into Your Trading Workflow",
                "prompt": base_prompt.substitute(
                    instruction=(
                        "Describe the process of integrating AI tools such as Mistral into a day trader's workflow. "
                        "Discuss challenges and solutions for real-time market analysis."
                    )
                ),
            },
            {
                "title": "Automating Content Creation for FreeRideInvestor",
                "prompt": base_prompt.substitute(
                    instruction=(
                        "Provide a detailed explanation of how automating blog content creation with AI can benefit day traders and investors, including efficiency and consistency improvements."
                    )
                ),
            },
            {
                "title": "Leveraging Algorithmic Trading for Better Results",
                "prompt": base_prompt.substitute(
                    instruction=(
                        "Discuss the role of algorithmic trading in achieving better trading outcomes. "
                        "Include examples of successful strategies and tips for developing your own."
                    )
                ),
            },
        ],
        "image": {
            "title": "Visual Representation of AI-Driven Trading and Content Automation",
            "prompt": base_prompt.substitute(
                instruction=(
                    "Describe an image that represents the integration of AI in day trading and automated content creation. "
                    "Include elements like AI models analyzing stock data, algorithmic trading interfaces, and content workflows."
                )
            ),
        },
        "conclusion": base_prompt.substitute(
            instruction=(
                "Write a 150-word conclusion summarizing the benefits of automating blog posts with AI for day traders and investors, and include a call-to-action."
            )
        ),
        "cta": {
            "title": "Join the FreeRideInvestor Community",
            "content": (
                "Subscribe to FreeRideInvestor for the latest updates, trading strategies, and insights on AI automation in content creation."
            ),
            "form_action": "/subscribe",
        },
        "interactive_question": base_prompt.substitute(
            instruction=(
                "Generate a conversational question to engage readers about their thoughts on integrating AI in trading strategies."
            )
        ),
    }

    try:
        content["post_title"] = (
            run_ollama(prompts["post_title"])
            or "Automating Blog Posts with AI: Enhancing Trading Strategies"
        )
        logging.info(f"Generated post title: {content['post_title']}")
    except Exception as e:
        logging.error(f"Error generating post title: {e}")
        content[
            "post_title"
        ] = "Automating Blog Posts with AI: Enhancing Trading Strategies"

    subtitle_prompt = prompts["post_subtitle"].replace(
        "{post_title}", content["post_title"]
    )
    try:
        content["post_subtitle"] = (
            run_ollama(subtitle_prompt)
            or "Leveraging AI to Optimize Trading and Content Creation"
        )
        logging.info(f"Generated post subtitle: {content['post_subtitle']}")
    except Exception as e:
        logging.error(f"Error generating post subtitle: {e}")
        content[
            "post_subtitle"
        ] = "Leveraging AI to Optimize Trading and Content Creation"

    try:
        introduction_text = run_ollama(prompts["introduction"])
        content["introduction"] = {
            "title": "Introduction",
            "content": introduction_text
            or (
                "Welcome to our guide on automating blog posts with AI. In this post, we explore how day traders and investors can leverage AI to enhance trading strategies and streamline content creation, saving time and boosting productivity."
            ),
        }
        logging.info("Generated introduction.")
    except Exception as e:
        logging.error(f"Error generating introduction: {e}")
        content["introduction"] = {
            "title": "Introduction",
            "content": (
                "Welcome to our guide on automating blog posts with AI. In this post, we explore how day traders and investors can leverage AI to enhance trading strategies and streamline content creation, saving time and boosting productivity."
            ),
        }

    content["sections"] = []
    for section in prompts["sections"]:
        section_title = section["title"]
        try:
            section_content = run_ollama(section["prompt"])
            if not section_content:
                logging.warning(
                    f"Failed to generate content for section: {section_title}. Using fallback content."
                )
                section_content = f"Content for '{section_title}' will be updated soon."
            else:
                logging.info(f"Generated content for section: {section_title}")
        except Exception as e:
            logging.error(f"Error generating content for section {section_title}: {e}")
            section_content = f"Content for '{section_title}' will be updated soon."
        content["sections"].append({"title": section_title, "content": section_content})
        time.sleep(1)

    try:
        image_description = run_ollama(prompts["image"]["prompt"])
        if not image_description:
            logging.warning(
                "Failed to generate image description with Ollama. Using fallback description."
            )
            image_description = "An illustrative diagram showing AI integration in trading strategies and automated content creation."
        logging.info("Generated image description.")
    except Exception as e:
        logging.error(f"Error generating image description: {e}")
        image_description = "An illustrative diagram showing AI integration in trading strategies and automated content creation."

    image_url = generate_image(image_description)
    content["image"] = {
        "title": prompts["image"]["title"],
        "url": image_url,
        "alt": image_description
        or "Illustrative diagram of AI-driven trading and content automation.",
    }

    try:
        conclusion_text = run_ollama(prompts["conclusion"])
        content["conclusion"] = {
            "title": "Conclusion",
            "content": conclusion_text
            or (
                "In conclusion, automating your blog posts with AI can revolutionize your trading and content creation strategies. "
                "Embrace AI to stay ahead in the dynamic world of day trading and investment, and unlock new opportunities for growth."
            ),
        }
        logging.info("Generated conclusion.")
    except Exception as e:
        logging.error(f"Error generating conclusion: {e}")
        content["conclusion"] = {
            "title": "Conclusion",
            "content": (
                "In conclusion, automating your blog posts with AI can revolutionize your trading and content creation strategies. "
                "Embrace AI to stay ahead in the dynamic world of day trading and investment, and unlock new opportunities for growth."
            ),
        }

    try:
        interactive_question = (
            run_ollama(prompts["interactive_question"])
            or "What are your thoughts on integrating AI into your trading strategies? Share your experiences below!"
        )
        content["interactive_question"] = interactive_question
        logging.info("Generated interactive question.")
    except Exception as e:
        logging.error(f"Error generating interactive question: {e}")
        content[
            "interactive_question"
        ] = "What are your thoughts on integrating AI into your trading strategies? Share your experiences below!"

    content["cta"] = prompts["cta"]
    return content


def render_template(content):
    """
    Renders the blog_template.html with the provided content.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(base_dir)
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("blog_template.html")
        logging.info("Rendering template with content.")

        for section in content["sections"]:
            section["content"] = markdown.markdown(section["content"])
        content["introduction"]["content"] = markdown.markdown(
            content["introduction"]["content"]
        )
        content["conclusion"]["content"] = markdown.markdown(
            content["conclusion"]["content"]
        )
        content["interactive_question"] = markdown.markdown(
            content["interactive_question"]
        )

        rendered_html = template.render(content)
        logging.info("Template rendered successfully.")
        return rendered_html
    except Exception as e:
        logging.error(f"Error rendering template: {e}")
        return ""


def save_output(rendered_html, post_title):
    """
    Saves the rendered HTML to the output directory with a filename based on the post title.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        safe_title = "".join(
            c for c in post_title if c.isalnum() or c in (" ", "_")
        ).rstrip()
        safe_title = safe_title.strip().replace(" ", "_").lower()
        max_length = 100
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length].rstrip("_")
        timestamp = time.strftime("%Y%m%d%H%M%S")
        filename = f"{safe_title}_{timestamp}.html"
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        logging.info(f"Blog post generated successfully: {output_path}")
        print(f"Blog post generated successfully: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"Error saving output file: {e}")
        return ""


def get_or_create_term(endpoint, name):
    """
    Retrieves the term ID from WordPress or creates it if it doesn't exist.
    """
    try:
        term_url = f"{WORDPRESS_URL}/wp-json/wp/v2/{endpoint}"
        params = {"search": name}
        response = session.get(term_url, params=params)
        if response.status_code == 200:
            terms = response.json()
            for term in terms:
                if term["name"].lower() == name.lower():
                    return term["id"]
            payload = {"name": name}
            response = session.post(term_url, json=payload)
            if response.status_code == 201:
                return response.json()["id"]
            else:
                logging.error(f"Failed to create term '{name}': {response.text}")
        else:
            logging.error(f"Failed to get term '{name}': {response.text}")
    except Exception as e:
        logging.error(f"Exception in get_or_create_term: {e}")
    return None


def post_to_wordpress(title, content, excerpt, categories, tags, image_url=None):
    """
    Posts the generated blog content to a WordPress site using the REST API.
    """
    try:
        wordpress_api_url = f"{WORDPRESS_URL}/wp-json/wp/v2/posts"
        auth = HTTPBasicAuth(WORDPRESS_USERNAME, WORDPRESS_PASSWORD)

        category_ids = [get_or_create_term("categories", cat) for cat in categories]
        tag_ids = [get_or_create_term("tags", tag) for tag in tags]

        post_data = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "status": POST_STATUS,
            "categories": [cid for cid in category_ids if cid],
            "tags": [tid for tid in tag_ids if tid],
        }

        if image_url:
            image_response = session.get(image_url)
            if image_response.status_code == 200:
                media_headers = {
                    "Content-Disposition": 'attachment; filename="feature_image.jpg"',
                    "Content-Type": "image/jpeg",
                }
                media_data = image_response.content
                media_response = session.post(
                    f"{WORDPRESS_URL}/wp-json/wp/v2/media",
                    data=media_data,
                    headers=media_headers,
                )
                if media_response.status_code == 201:
                    media_id = media_response.json().get("id")
                    post_data["featured_media"] = media_id
                    logging.info("Featured image uploaded successfully.")
                else:
                    logging.error(
                        f"Failed to upload feature image: {media_response.text}"
                    )
            else:
                logging.error(f"Failed to download image from URL: {image_url}")

        response = session.post(wordpress_api_url, json=post_data)
        if response.status_code in [200, 201]:
            logging.info(
                f"Blog post published to WordPress: {response.json().get('link')}"
            )
            return response.json()
        else:
            logging.error(f"Failed to publish post: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Exception in post_to_wordpress: {e}")
        return None


def generate_blog():
    """
    Orchestrates the blog generation process.
    """
    try:
        index = initialize_faiss()
        metadata = load_metadata()

        content = generate_content()
        if not content:
            logging.error("Failed to generate content.")
            return None

        rendered_html = render_template(content)
        if not rendered_html:
            logging.error("Failed to render template.")
            return None

        post_title = content.get("post_title", "blog_post")
        post_excerpt = markdown.markdown(content["introduction"]["content"])[:150]
        output_path = save_output(rendered_html, post_title)

        texts = [post_title, content["introduction"]["content"]]
        embeddings = generate_embeddings(texts)
        if embeddings is not None:
            faiss.normalize_L2(embeddings)
            try:
                index.add(embeddings)
                faiss.write_index(index, VECTOR_DB_INDEX_FILE)
                logging.info("Embeddings added to FAISS index successfully.")
            except Exception as e:
                logging.error(f"Error adding embeddings to FAISS index: {e}")
                embeddings = None

            if embeddings is not None:
                metadata_entry = {
                    "title": post_title,
                    "excerpt": post_excerpt,
                    "link": WORDPRESS_URL.replace("/wp-json/wp/v2/posts", "")
                    + f"/{post_title.replace(' ', '-').lower()}/",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                if not any(
                    entry["title"].lower() == metadata_entry["title"].lower()
                    for entry in metadata
                ):
                    metadata.append(metadata_entry)
                    save_metadata(metadata)
                    logging.info("Metadata updated successfully.")
                else:
                    logging.warning(f"Duplicate metadata entry for title: {post_title}")
        else:
            logging.error(
                "Embeddings generation failed; skipping vector database entry."
            )

        try:
            wordpress_response = post_to_wordpress(
                title=post_title,
                content=rendered_html,
                excerpt=post_excerpt,
                categories=DEFAULT_CATEGORIES,
                tags=DEFAULT_TAGS,
                image_url=content.get("image", {}).get("url"),
            )
            if wordpress_response:
                logging.info(
                    f"Blog post published: {wordpress_response.get('link', 'No Link Provided')}"
                )
                print(
                    f"Blog post published: {wordpress_response.get('link', 'No Link Provided')}"
                )
            else:
                logging.error("Failed to publish to WordPress.")
                print("Failed to publish to WordPress.")
        except Exception as e:
            logging.error(f"Failed to publish to WordPress: {e}")
            print(f"Failed to publish to WordPress: {e}")

        return output_path

    except Exception as e:
        logging.error(f"Exception in generate_blog: {e}")
        return None


@dataclass
class BlogPost:
    """Data class for blog post content and metadata."""

    content: str
    metadata: Dict
    post_id: str = str(uuid.uuid4())
    timestamp: datetime = datetime.now()


class BlogGenerator:
    """Orchestrates the blog post generation pipeline."""

    def __init__(
        self,
        mistral_client: MistralClient,
        vector_db: VectorDB,
        devlog_service: Optional[DevlogService] = None,
        chatgpt_mode: str = "api",
    ):
        """
        Initialize the blog generator.

        Args:
            mistral_client: Initialized Mistral client
            vector_db: Vector database instance
            devlog_service: Optional devlog service for tracking
            chatgpt_mode: Mode for ChatGPT scraper ("browser" or "api")
        """
        self.mistral_client = mistral_client
        self.vector_db = vector_db

        # Initialize ChatGPT scraper
        self.chatgpt = ChatGPTScraper(mode=chatgpt_mode)

        # Initialize services
        self.outline_service = OutlineService(mistral_client)
        self.draft_service = DraftService(mistral_client)
        self.polish_service = PolishService(mistral_client)
        self.devlog_service = devlog_service or DevlogService(self.chatgpt)

    def generate_post(
        self, prompt: str, style: str = "informative", target_length: int = 1000
    ) -> BlogPost:
        """
        Generate a complete blog post.

        Args:
            prompt: The main topic/prompt
            style: Writing style (e.g., "informative", "conversational")
            target_length: Target word count

        Returns:
            BlogPost object with content and metadata
        """
        try:
            # Generate outline
            logger.info("Generating outline...")
            outline = self.outline_service.generate_outline(
                prompt=prompt, style=style, target_length=target_length
            )

            # Generate draft
            logger.info("Generating draft...")
            draft = self.draft_service.generate_draft(
                outline=outline, style=style, target_length=target_length
            )

            # Polish content
            logger.info("Polishing content...")
            polished = self.polish_service.polish_content(draft=draft, style=style)

            # Create blog post object
            post = BlogPost(
                content=polished,
                metadata={
                    "prompt": prompt,
                    "style": style,
                    "target_length": target_length,
                    "outline": outline,
                    "draft": draft,
                    "word_count": len(polished.split()),
                },
            )

            # Log generation
            self.devlog_service.log_generation(
                post_id=post.post_id,
                prompt=prompt,
                outline=outline,
                draft=draft,
                final_content=polished,
            )

            # Store in vector DB
            self.vector_db.store_post(post)

            return post

        except Exception as e:
            logger.error(f"Error generating blog post: {e}")
            raise

    def regenerate_devlog(self, post_id: str) -> str:
        """
        Regenerate devlog entry for a post.

        Args:
            post_id: ID of the post to regenerate devlog for

        Returns:
            Updated devlog entry
        """
        try:
            # Get post from vector DB
            post = self.vector_db.get_post(post_id)
            if not post:
                raise ValueError(f"Post not found: {post_id}")

            # Regenerate devlog
            return self.devlog_service.regenerate_entry(
                post_id=post_id,
                prompt=post.metadata["prompt"],
                outline=post.metadata["outline"],
                draft=post.metadata["draft"],
                final_content=post.content,
            )

        except Exception as e:
            logger.error(f"Error regenerating devlog: {e}")
            raise

    def close(self):
        """Clean up resources."""
        try:
            self.chatgpt.close()
        except Exception as e:
            logger.error(f"Error closing ChatGPT scraper: {e}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def generate_content(prompt: str, max_length: int = 1000) -> str:
    """
    Generate content from a prompt.

    Args:
        prompt (str): The prompt to generate from
        max_length (int): Maximum length of generated content

    Returns:
        str: Generated content

    Raises:
        ValueError: If prompt is empty or max_length is invalid
        RuntimeError: If generation fails
    """
    try:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        if max_length < 1:
            raise ValueError("Max length must be positive")

        # Initialize clients
        mistral_client = MistralClient()
        vector_db = VectorDB()

        generator = BlogGenerator(mistral_client=mistral_client, vector_db=vector_db)
        return generator._generate_content(
            topic=prompt, style="professional", length="medium"
        )
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise RuntimeError(f"Failed to generate content: {str(e)}")


def generate_blog(
    prompt: str,
    model_name: str = "GPT-4",
    style: str = "Professional",
    length: int = 1000,
) -> str:
    """
    Generate a blog post using the AI model.

    Args:
        prompt (str): The topic or prompt for the blog post
        model_name (str): The AI model to use (currently only supports Mistral)
        style (str): The writing style to use
        length (int): The target length of the blog post

    Returns:
        str: The generated blog post content in HTML format
    """
    try:
        # Load model if not already loaded
        load_model()

        # Prepare the prompt with style guidance
        style_guidance = {
            "Professional": "Write in a formal, business-like tone with clear structure and professional language.",
            "Casual": "Write in a friendly, conversational tone that's easy to read and engaging.",
            "Technical": "Write with precise technical details, code examples where relevant, and clear explanations.",
            "Creative": "Write with an engaging narrative style, using metaphors and storytelling techniques.",
        }

        full_prompt = f"""Write a blog post about {prompt}.
Style: {style_guidance[style]}
Length: Approximately {length} words.
Format: Include a title, introduction, main sections with headings, and a conclusion.

[START]"""

        # Generate content
        inputs = tokenizer(
            full_prompt, return_tensors="pt", truncation=True, max_length=512
        )
        outputs = model.generate(
            inputs["input_ids"],
            max_length=length * 4,  # Approximate tokens per word
            num_return_sequences=1,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
        )

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract title and content
        lines = generated_text.split("\n")
        title = lines[0].strip()
        content = "\n".join(lines[1:]).strip()

        # Format as HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    line-height: 1.6; 
                    max-width: 800px; 
                    margin: 0 auto; 
                    padding: 20px;
                    color: #333;
                }}
                h1 {{ 
                    color: #2c3e50;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 10px;
                }}
                h2 {{ 
                    color: #34495e;
                    margin-top: 30px;
                }}
                p {{ 
                    margin-bottom: 1.5em;
                    text-align: justify;
                }}
                .meta {{
                    color: #7f8c8d;
                    font-size: 0.9em;
                    margin-bottom: 30px;
                }}
                .conclusion {{
                    background: #f9f9f9;
                    padding: 20px;
                    border-left: 4px solid #3498db;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>
            <div class="meta">
                <p>Generated with {model_name} | Style: {style} | Target Length: {length} words</p>
            </div>
            {content}
            <div class="conclusion">
                <p>This blog post was generated using AI technology. The content is based on the provided prompt and style guidelines.</p>
            </div>
        </body>
        </html>
        """

        return html_content

    except Exception as e:
        logging.error(f"Error generating blog post: {e}")
        raise


if __name__ == "__main__":
    generate_blog()
