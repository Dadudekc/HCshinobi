from ..constants import (
    JSON_INDENT,
    WAIT_TIME_SHORT,
    WAIT_TIME_MEDIUM,
    WAIT_TIME_LONG
)

import os
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class PromptEngine:
    """
    Manages and generates AI prompts with context-aware templating and dynamic variable substitution.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = templates_dir or os.path.join(os.getcwd(), "prompts")
        self.templates = {}
        self._ensure_templates_dir()
        self._load_templates()

    def _ensure_templates_dir(self):
        """Ensure the templates directory exists."""
        os.makedirs(self.templates_dir, exist_ok=True)

    def _load_templates(self):
        """Load prompt templates from JSON files."""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return

        for file in os.listdir(self.templates_dir):
            if file.endswith('.json'):
                try:
                    with open(os.path.join(self.templates_dir, file), 'r', encoding='utf-8') as f:
                        category = file[:-5]  # Remove .json extension
                        self.templates[category] = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load template file {file}: {e}")

    def get_prompt(self, category: str, template_name: str, variables: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get a prompt template and substitute variables.
        
        Args:
            category: The category of the prompt (e.g., 'social', 'analysis')
            template_name: The name of the specific template
            variables: Dictionary of variables to substitute in the template
        
        Returns:
            The formatted prompt string, or None if template not found
        """
        if category not in self.templates:
            logger.error(f"Template category not found: {category}")
            return None

        template = self.templates[category].get(template_name)
        if not template:
            logger.error(f"Template not found: {template_name} in category {category}")
            return None

        if variables:
            try:
                return template.format(**variables)
            except KeyError as e:
                logger.error(f"Missing required variable in template: {e}")
                return None
            except Exception as e:
                logger.error(f"Error formatting template: {e}")
                return None

        return template

    def add_template(self, category: str, template_name: str, template: str):
        """Add a new prompt template."""
        if category not in self.templates:
            self.templates[category] = {}

        self.templates[category][template_name] = template
        self._save_templates(category)
        logger.info(f"Added template {template_name} to category {category}")

    def remove_template(self, category: str, template_name: str):
        """Remove a prompt template."""
        if category in self.templates and template_name in self.templates[category]:
            del self.templates[category][template_name]
            self._save_templates(category)
            logger.info(f"Removed template {template_name} from category {category}")

    def _save_templates(self, category: str):
        """Save templates for a category to file."""
        if category not in self.templates:
            return

        file_path = os.path.join(self.templates_dir, f"{category}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.templates[category], f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save templates for category {category}: {e}")

    def list_categories(self) -> List[str]:
        """List all available template categories."""
        return list(self.templates.keys())

    def list_templates(self, category: str) -> List[str]:
        """List all templates in a category."""
        return list(self.templates.get(category, {}).keys())

def _save_prompt_history(self) -> None:
    """Save prompt history to persistent storage."""
    try:
        history_path = self.path_manager.get_prompt_history_path()
        with open(history_path, 'w') as f:
            json.dump(self.prompt_history, f, indent=JSON_INDENT)
    except Exception as e:
        self.logger.error(f"Failed to save prompt history: {e}")

def _wait_random(self, wait_time: Tuple[int, int]) -> None:
    """Wait for a random amount of time between min and max seconds."""
    min_wait, max_wait = wait_time
    time.sleep(random.uniform(min_wait, max_wait))

def _normalize_prompt(self, prompt: str) -> str:
    """Normalize prompt by removing extra whitespace and newlines."""
    return ' '.join(prompt.split()) 