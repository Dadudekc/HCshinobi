"""Standalone script demonstrating workspace-aware path resolution logic."""

import os
import argparse
from pathlib import Path
import sys # Added

def resolve_path_relative_to_workspace(input_path: str, workspace_root: str) -> str:
    """Resolves an input path relative to a given workspace root.

    Handles:
    - Absolute paths (returned as is if outside workspace, relative if inside).
    - Relative paths (resolved based on the workspace root).
    - Paths starting with '..' relative to the workspace root.
    """
    try:
        workspace_path = Path(workspace_root).resolve(strict=True) # Ensure workspace exists
        input_path_obj = Path(input_path)

        # If the input is already absolute
        if input_path_obj.is_absolute():
            resolved_input = input_path_obj.resolve()
            # Check if it exists (optional, depends on use case)
            # if not resolved_input.exists():
            #     print(f"Warning: Absolute input path does not exist: {resolved_input}", file=sys.stderr)
            
            # Check if it's within the workspace
            try:
                relative_to_workspace = resolved_input.relative_to(workspace_path)
                # Return the relative path from workspace root if inside
                return str(relative_to_workspace).replace('\', '/') # Normalize to forward slashes
            except ValueError:
                # Path is absolute but outside workspace, return the absolute path
                return str(resolved_input).replace('\', '/') # Normalize
        else:
            # If input is relative, resolve it based on the workspace root
            resolved_relative = (workspace_path / input_path).resolve()
            # Check if it exists (optional)
            # if not resolved_relative.exists():
            #      print(f"Warning: Resolved relative path does not exist: {resolved_relative}", file=sys.stderr)
            
            # Return the path relative to the workspace root
            try:
                return str(resolved_relative.relative_to(workspace_path)).replace('\', '/') # Normalize
            except ValueError:
                 # Should not happen if logic is correct, but as fallback:
                 # If somehow resolved outside workspace (e.g., ../../..), return absolute
                 print(f"Warning: Path resolved outside workspace: {resolved_relative}. Returning absolute path.", file=sys.stderr)
                 return str(resolved_relative).replace('\', '/') # Normalize
                 
    except FileNotFoundError:
         print(f"Error: Workspace root directory not found: {workspace_root}", file=sys.stderr)
         raise # Re-raise the error for the main block to handle
    except Exception as e:
         print(f"Error during path resolution: {e}", file=sys.stderr)
         raise


if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, and simulation
    print(">>> Running module:", __file__)

    parser = argparse.ArgumentParser(description='Resolve paths relative to a workspace.')
    parser.add_argument('input_path', help='The path to resolve (can be relative or absolute). Use forward slashes.')
    parser.add_argument('-w', '--workspace', default=os.getcwd(),
                        help='The workspace root directory (defaults to current working directory). Use forward slashes.')

    args = parser.parse_args()

    # Normalize input paths from args just in case
    input_path_norm = args.input_path.replace('\', '/')
    workspace_norm = args.workspace.replace('\', '/')

    print(f"\n>>> Input Path:    {input_path_norm}")
    print(f">>> Workspace Root: {workspace_norm}")

    try:
        resolved_path = resolve_path_relative_to_workspace(input_path_norm, workspace_norm)
        print(f"\n>>> Resolved Path (relative to workspace): {resolved_path}")

        # Optional: Show the absolute path as well for clarity
        abs_workspace = Path(workspace_norm).resolve()
        
        # Check if the function returned an absolute path (meaning outside workspace)
        is_absolute_result = Path(resolved_path).is_absolute()
        if is_absolute_result:
             print(f">>> Absolute Path: {resolved_path}")
        else:
             # Reconstruct absolute path from workspace + relative result
             reconstructed_abs = (abs_workspace / resolved_path).resolve()
             print(f">>> Absolute Path: {str(reconstructed_abs).replace('\', '/')}")
             
    except Exception as e:
        print(f"\n>>> Error resolving path in main block: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n>>> Resolution complete.") 