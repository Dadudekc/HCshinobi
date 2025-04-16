"""Template engine for rendering prompts and other templates."""
import os
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, StrictUndefined

class TemplateEngine:
    """Engine for rendering Jinja2 templates."""
    
    def __init__(self, template_dir: str = None):
        """Initialize the template engine."""
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), '..', 'templates'
        )
        self._ensure_template_dir()
        self._setup_environment()
        
    def _ensure_template_dir(self) -> None:
        """Ensure template directory exists."""
        os.makedirs(self.template_dir, exist_ok=True)
        
    def _setup_environment(self) -> None:
        """Set up the Jinja2 environment."""
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with given context."""
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            print(f"Error rendering template {template_name}: {e}")
            raise
            
    def add_filter(self, name: str, filter_func: callable) -> None:
        """Add a custom filter to the environment."""
        self.env.filters[name] = filter_func
        
    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable to the environment."""
        self.env.globals[name] = value

# Create a default instance
default_template_engine = TemplateEngine() 