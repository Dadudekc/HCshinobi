import os
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
import sys
import traceback

# --- Add project root for governance logger import ---
script_dir = os.path.dirname(__file__)  # This file is located in dreamforge/core
PROJECT_ROOT = os.path.abspath(os.path.join(script_dir, '..', '..'))  # Two levels up to project root
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Import Governance Logger ---
try:
    from dreamforge.core.governance_memory_engine import log_event
    _gme_ready = True
except ImportError:
    _gme_ready = False
    # Fallback dummy logger if log_event is not available
    def log_event(event_type, source, details):
        print(f"[Dummy Logger - TemplateEngine] Event: {event_type}, Source: {source}, Details: {details}")
        return False

# --- Configuration ---
# Set TEMPLATE_DIR to the corrected templates directory
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "dreamforge", "templates")
_SOURCE_ID = "TemplateEngine"

# --- Setup Jinja2 Environment ---
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

def render(template_name: str, context: dict) -> str:
    """
    Renders a template given its name and a context dictionary.

    Args:
        template_name: The name of the template file, relative to TEMPLATE_DIR.
        context: Dictionary containing context variables for rendering.

    Returns:
        The rendered output as a string. If an error occurs, returns an empty string.
    """
    try:
        template = env.get_template(template_name)
        rendered_output = template.render(**context)
        log_event("TEMPLATE_RENDER_SUCCESS", _SOURCE_ID, {"template": template_name})
        return rendered_output
    except TemplateNotFound as e:
        log_event("TEMPLATE_NOT_FOUND", _SOURCE_ID, {"template": template_name, "error": str(e)})
        return ""
    except Exception as e:
        log_event("TEMPLATE_RENDER_ERROR", _SOURCE_ID, {
            "template": template_name, 
            "error": str(e), 
            "traceback": traceback.format_exc()
        })
        return ""

if __name__ == "__main__":
    # Example usage: attempt to render a test template with sample context.
    # Try to load sample context from an analysis file if available; fall back to a default context.
    sample_data_path = os.path.join(PROJECT_ROOT, "analysis", "temp_governance_data.json")
    try:
        if os.path.exists(sample_data_path):
            with open(sample_data_path, "r", encoding="utf-8") as f:
                context = json.load(f)
        else:
            context = {"example_key": "example_value"}
    except Exception as e:
        context = {"example_key": "example_value"}
    
    test_template = "test_template.j2"  # Make sure this template exists in TEMPLATE_DIR
    print("Rendering template:", test_template)
    output = render(test_template, context)
    print("Rendered Output:\n", output)
