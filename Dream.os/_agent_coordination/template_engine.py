import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Assuming templates are in a 'templates' directory relative to this file or project root
# Adjust TEMPLATE_DIRS if your structure is different
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # Or adjust as needed
TEMPLATE_DIRS = [os.path.join(PROJECT_ROOT, 'templates'), os.path.join(PROJECT_ROOT, '..', 'templates')]
# Filter out non-existent dirs
EXISTING_TEMPLATE_DIRS = [d for d in TEMPLATE_DIRS if os.path.isdir(d)]

if not EXISTING_TEMPLATE_DIRS:
    print("Warning: No template directories found in", TEMPLATE_DIRS)
    # Fallback or raise error depending on requirements
    env = None
else:
    env = Environment(
        loader=FileSystemLoader(EXISTING_TEMPLATE_DIRS),
        autoescape=select_autoescape([]) # Disable autoescaping for plain text social posts
    )

def render_template(template_name, context):
    """Renders a Jinja template with the given context."""
    if not env:
        print("Error: Jinja environment not initialized.")
        return f"Error rendering {template_name}: Jinja environment missing."
    try:
        template = env.get_template(template_name)
        # Get the template source from the environment loader
        template_source = env.loader.get_source(env, template_name)[0]
        # Get the AST for the template
        ast = env.parse(template_source)
        # Find all variables used in the template
        from jinja2.visitor import NodeVisitor
        class VariableFinder(NodeVisitor):
            def __init__(self):
                self.variables = set()
            def visit_Name(self, node):
                if node.ctx == 'load':
                    self.variables.add(node.name)
            def visit_Filter(self, node):
                self.visit(node.node)
            def visit_Getattr(self, node):
                # Handle nested attributes (e.g., user.name)
                if hasattr(node, 'node') and hasattr(node.node, 'name'):
                    self.variables.add(node.node.name)
        finder = VariableFinder()
        finder.visit(ast)
        # Check for missing variables
        missing_vars = [var for var in finder.variables if var not in context]
        if missing_vars:
            error_msg = f"Error rendering {template_name}: Missing variables {missing_vars}"
            print(f"Error: Missing required variables: {missing_vars}")
            return error_msg
        return template.render(context)
    except Exception as e:
        print(f"Error rendering template {template_name}: {e}")
        raise  # Re-raise the exception for proper error handling

# --- New Function --- #
def generate_post_from_template(platform: str, context: dict) -> str:
    """Generates social media post content using a platform-specific template."""
    template_file = f"social/{platform}_post.j2"
    print(f"[template] Generating post for {platform} using {template_file}")
    try:
        rendered_post = render_template(template_file, context)
        # Clean up whitespace: remove multiple consecutive newlines
        cleaned_post = '\n'.join(line for line in rendered_post.splitlines() if line.strip())
        return cleaned_post
    except Exception as e:
        print(f"Error generating post for {platform}: {e}")
        return f"Error rendering {template_file}."

# --- Example Usage (Optional) --- #
if __name__ == '__main__':
    # Example for rendering a general template
    example_context = {'title': 'Test Title', 'body': 'This is a test body.'}
    rendered = render_template('base.j2', example_context) # Assuming base.j2 exists
    print("--- Rendered base.j2 ---")
    print(rendered)
    print("------------------------\n")

    # Example for rendering a social post
    twitter_context = {
        "title": "Governance Alert!",
        "proposal_summary": "Proposal #PROP-123 requires review.",
        "gpt_decision": "Suggest REJECT due to conflict with Rule #R-042.",
        "status_update": "Requires Review",
        "governance_update": True
    }
    twitter_post = generate_post_from_template('twitter', twitter_context)
    print("--- Rendered twitter_post.j2 ---")
    print(twitter_post)
    print("-----------------------------") 