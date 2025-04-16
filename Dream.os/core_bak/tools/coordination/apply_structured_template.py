"""
Tool: apply_structured_template
Objective: Apply context data to a predefined template file and output the result,
           optionally writing it to a target file.

Limitations (Simulated Tool):
- Templating Engine: Uses basic Python f-string formatting or .format() instead
                   of a dedicated engine like Jinja2. Complex logic (loops, conditionals)
                   within the template is not supported by this simple placeholder.
- Template Loading: Assumes templates are simple text files read directly.
"""
import argparse
import os
import sys
import logging
import json
from datetime import datetime

# --- Placeholder Agent Coordination Functions ---
def _log_tool_action(tool_name, status, message, details=None):
    print(f"[TOOL LOG - {tool_name}] Status: {status}, Msg: {message}, Details: {details or 'N/A'}")

def _update_status_file(file_path, status_data):
    abs_path = os.path.abspath(file_path)
    print(f"[STATUS UPDATE] Writing to {abs_path}: {json.dumps(status_data)}")
    # In reality, write status_data to file_path
# --- End Placeholders ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TOOL_NAME = "apply_structured_template"

# --- Placeholder Template Loading ---
# In a real tool, load from a central template directory
PLACEHOLDER_TEMPLATES = {
    "agentic_main_block.py.tpl": """
if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for {purpose}
    print(f">>> Running module: {{__file__}})"

    # Instantiate or call core functionality
    # example = {main_class_or_function}()
    # result = example.{demo_method}()
    print(">>> Placeholder Output for {main_class_or_function}")
""",
    "simple_report.txt.tpl": """
Report generated: {report_time}
Source: {source_module}
Status: {status}
Details: {details}
"""
}

def load_template(template_name: str) -> Optional[str]:
    """Placeholder for loading template content."""
    logging.info(f"Loading template: {template_name}")
    content = PLACEHOLDER_TEMPLATES.get(template_name)
    if not content:
        logging.error(f"Template '{template_name}' not found in placeholder store.")
    return content


def render_template(template_content: str, context: dict) -> str:
    """
    Placeholder: Renders the template using basic string formatting.
    Only supports simple key replacement.
    """
    logging.info(f"Rendering template with context keys: {list(context.keys())}")
    try:
        # Basic .format() replacement - will fail if keys are missing
        rendered_content = template_content.format(**context)
        return rendered_content
    except KeyError as e:
        logging.error(f"Missing key in context for template: {e}")
        raise ValueError(f"Missing key in context: {e}")
    except Exception as e:
        logging.exception("Failed to render template using basic formatting.")
        raise


def write_output_file(file_path: str, content: str) -> bool:
    """Writes the rendered content to the target file."""
    abs_path = os.path.abspath(file_path)
    logging.info(f"Writing rendered output to: {abs_path}")
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except IOError as e:
        logging.error(f"Failed to write output file '{abs_path}': {e}")
        return False

if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, and simulation
    print(f">>> Running module: {__file__}")

    parser = argparse.ArgumentParser(description=f"Tool: {TOOL_NAME} - Apply context to templates.")
    parser.add_argument("template_name", help="Name of the template to use (e.g., 'agentic_main_block.py.tpl').")
    parser.add_argument("context_json", help="JSON string containing the context data for the template.")
    parser.add_argument("--output_file", help="Optional: Path to write the rendered output (can be relative).")
    parser.add_argument("--status_file", help="Optional: Path to JSON file for status updates (can be relative).")

    # --- Example Simulation ---
    # Assume script is run from D:\Dream.os\_agent_coordination\tools
    example_context_str = json.dumps({
        "purpose": "Agentic Simulation",
        "main_class_or_function": "MyCoolService",
        "demo_method": "process_data"
    })
    example_args = [
        "agentic_main_block.py.tpl",
        example_context_str,
        "--output_file", "../output/rendered_main.py",
        "--status_file", "../status/apply_template_status.json"
    ]
    args = parser.parse_args(example_args) # Use example for demo
    # args = parser.parse_args(sys.argv[1:]) # Use this for actual command line execution
    print(f">>> Parsed Arguments (raw): {vars(args)}")

    if args.output_file:
        args.output_file = os.path.abspath(args.output_file)
    if args.status_file:
        args.status_file = os.path.abspath(args.status_file)
    print(f">>> Parsed Arguments (processed): template='{args.template_name}', output='{args.output_file}', context_keys={list(json.loads(args.context_json).keys())}")
    # -------------------------

    _log_tool_action(TOOL_NAME, "STARTED", f"Applying template '{args.template_name}'.")
    rendered_output = None
    tool_status = "FAILED"
    tool_message = ""

    try:
        # 1. Load Template
        template_content = load_template(args.template_name)
        if not template_content:
            raise ValueError(f"Template '{args.template_name}' not found.")

        # 2. Parse Context
        try:
            context_data = json.loads(args.context_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid context JSON provided: {e}")

        # 3. Render Template
        rendered_output = render_template(template_content, context_data)

        # 4. Output or Write File
        if args.output_file:
            if write_output_file(args.output_file, rendered_output):
                print(f">>> Rendered output written to: {args.output_file}")
                tool_status = "COMPLETED"
                tool_message = f"Template '{args.template_name}' rendered and saved to {args.output_file}."
            else:
                tool_message = f"Template '{args.template_name}' rendered, but failed to write to {args.output_file}."
                # Keep status as FAILED
                print(f">>> Tool Error: Failed to write output file.")
        else:
            # Print to stdout if no output file specified
            print(f">>> Rendered Output:\n---\n{rendered_output}\n---")
            tool_status = "COMPLETED"
            tool_message = f"Template '{args.template_name}' rendered successfully to stdout."

        _log_tool_action(TOOL_NAME, tool_status, tool_message)

        if args.status_file:
            status_data = {
                "tool": TOOL_NAME,
                "timestamp": datetime.now().isoformat(),
                "parameters": {
                     "template_name": args.template_name,
                     "context_keys": list(context_data.keys()), # Don't log potentially large context values
                     "output_file": args.output_file
                 },
                "result": {"status": tool_status, "message": tool_message}
            }
            _update_status_file(args.status_file, status_data)

    except Exception as e:
        logging.exception("An error occurred during template application.")
        error_result = {"status": "ERROR", "message": str(e)}
        print(f">>> Tool Error: {json.dumps(error_result, indent=2)}")
        _log_tool_action(TOOL_NAME, "ERROR", str(e))
        if args.status_file:
             status_data = {
                "tool": TOOL_NAME,
                "timestamp": datetime.now().isoformat(),
                "parameters": vars(args) if 'args' in locals() else {},
                "result": error_result
            }
             _update_status_file(args.status_file, status_data)
        sys.exit(1)

    sys.exit(0 if tool_status == "COMPLETED" else 1) 