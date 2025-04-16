"""
Handles rendering of Jinja2 templates.
"""
import os
import sys
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound, TemplateSyntaxError

# --- Add project root to sys.path for potential relative imports in templates ---
# This assumes this file is in core/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Setup Jinja2 Environment ---
# Load templates relative to the project root
template_loader = None
template_env = None

try:
    template_loader = FileSystemLoader(project_root, followlinks=True)
    template_env = Environment(
        loader=template_loader,
        autoescape=select_autoescape(['html', 'xml']), # Adjust autoescape as needed
        trim_blocks=True,
        lstrip_blocks=True,
        enable_async=False # Set to True if using async functions in templates
    )
    # Add custom filters or globals if needed
    # template_env.globals['now'] = datetime.utcnow
    # template_env.filters['my_filter'] = my_custom_filter
    print("[TemplateEngine] Jinja2 Environment initialized.") # Use logging later if needed
except Exception as e:
    print(f"[TemplateEngine] CRITICAL: Failed to initialize Jinja2 Environment: {e}")
    # template_env remains None

# ------------------------------

def render_template(template_name: str, context: dict) -> str | None:
    """
    Renders a Jinja2 template with the given context.

    Args:
        template_name: The path to the template file (relative to project root).
        context: A dictionary containing variables for the template.

    Returns:
        The rendered string, or None if rendering fails or engine is unavailable.
    """
    if not template_env:
        print(f"[TemplateEngine] Error rendering '{template_name}': Environment not available.")
        return None

    try:
        template = template_env.get_template(template_name)
        rendered_content = template.render(context)
        print(f"[TemplateEngine] Successfully rendered template '{template_name}'") # Use logging later
        return rendered_content
    except TemplateNotFound:
        print(f"[TemplateEngine] Error rendering template: Template '{template_name}' not found.")
        return None
    except TemplateSyntaxError as syntax_e:
        print(f"[TemplateEngine] Error rendering template '{template_name}': Syntax error at line {syntax_e.lineno}: {syntax_e.message}")
        return None
    except Exception as e:
        print(f"[TemplateEngine] Error rendering template '{template_name}': {type(e).__name__}: {e}")
        # Optionally log full traceback here
        return None

# Example usage (optional)
if __name__ == '__main__':
    print("\nTesting TemplateEngine...")
    # Create a dummy template file relative to project root for testing
    dummy_template_path = os.path.join(project_root, 'dummy_test_template.j2')
    try:
        with open(dummy_template_path, 'w') as f:
            f.write("Hello {{ name }}! Your value is {{ data.value }}.")
        
        print(f"Created dummy template: {dummy_template_path}")
        test_context = {"name": "World", "data": {"value": 123}}
        rendered = render_template('dummy_test_template.j2', test_context)
        
        if rendered:
            print("\nRendered Output:")
            print(rendered)
        else:
            print("\nRendering failed.")
            
        # Test template not found
        print("\nTesting non-existent template...")
        render_template('nonexistent.j2', {})
        
    finally:
        # Clean up dummy template
        if os.path.exists(dummy_template_path):
            os.remove(dummy_template_path)
            print(f"Cleaned up dummy template: {dummy_template_path}") 