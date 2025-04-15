import argparse
import os
from pathlib import Path
import sys

# --- Constants ---
TEMPLATE_FILE_NAME = "agent_worker_template.py.tmpl"


def load_template() -> str:
    """Loads the worker template from the file."""
    template_path = Path(__file__).parent / TEMPLATE_FILE_NAME
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Template file not found at {template_path}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading template file {template_path}: {e}", file=sys.stderr)
        sys.exit(1)


def generate_worker(agent_id: str, domain_name: str, capabilities: list[str], output_dir: str = 'agent_workers') -> None:
    """Generates the agent worker file from the template."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    worker_file_path = output_path / f"agent_{agent_id}_{domain_name.lower()}_worker.py"

    # Load the template content
    worker_template = load_template()

    # Convert capabilities list to string representation for the template
    capabilities_list_str = str(capabilities)
    # Get the enum name from the domain string (e.g., "REFACTOR_COORDINATOR")
    domain_enum_name = domain_name.upper()

    # Format the template with provided values
    # Use .format() for the template string placeholders
    try:
        formatted_template = worker_template.format(
            agent_id=agent_id,
            domain_name=domain_name,
            domain_enum_name=domain_enum_name,
            capabilities_list_str=capabilities_list_str
        )
    except KeyError as e:
        print(f"Error: Missing placeholder in template: {e}", file=sys.stderr)
        print("Ensure the template file has all required placeholders: {agent_id}, {domain_name}, {domain_enum_name}, {capabilities_list_str}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during template formatting: {e}", file=sys.stderr)
        sys.exit(1)


    # Ensure all f-string literals within the template were correctly escaped with {{ }}
    # (This check is best done manually by reviewing the template file)

    try:
        with open(worker_file_path, 'w') as f:
            f.write(formatted_template)
        print(f"Successfully generated worker file: {worker_file_path}")
        # Make the script executable (optional, depends on OS/use case)
        # try:
        #     os.chmod(worker_file_path, 0o755)
        # except OSError as e:
        #     print(f"Warning: Could not make script executable: {e}", file=sys.stderr)

    except IOError as e:
        print(f"Error writing worker file {worker_file_path}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred during file writing: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an Agent Worker script from a template.")
    parser.add_argument("--id", required=True, help="Unique ID for the agent.")
    parser.add_argument("--domain", required=True, help="Domain name for the agent (e.g., REFACTOR_COORDINATOR). Must match an AgentDomain enum member name.")
    parser.add_argument("--caps", required=True, nargs='+', help="List of capabilities for the agent.")
    parser.add_argument("--output-dir", default="agent_workers", help="Directory to save the generated worker file (default: agent_workers).")

    args = parser.parse_args()

    # Basic validation (more robust validation could be added)
    if not args.id.strip():
        print("Error: Agent ID cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if not args.domain.strip():
        print("Error: Agent domain cannot be empty.", file=sys.stderr)
        sys.exit(1)
    # Consider adding validation for capabilities if needed

    generate_worker(args.id, args.domain, args.caps, args.output_dir)
