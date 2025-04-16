"""
Tool to check basic integration points between components (e.g., Agent Workers and Bridges).

NOTE: This is a basic placeholder. Real static analysis is complex and would likely 
require libraries like `ast` for parsing Python code and analyzing its structure.
"""

import argparse
import sys
import re
import ast # Python's Abstract Syntax Tree module
from pathlib import Path


def check_import_present(file_path: Path, module_to_import: str) -> bool:
    """Check if a specific module is imported in the file."""
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return False
        
    try:
        content = file_path.read_text()
        # Basic check (can be fooled by comments)
        # A more robust check would use AST
        import_pattern_1 = re.compile(f"^import\\s+{module_to_import.split('.')[0]}", re.MULTILINE)
        import_pattern_2 = re.compile(f"^from\\s+{module_to_import.rsplit('.', 1)[0]}\\s+import\\s+{module_to_import.rsplit('.', 1)[-1]}", re.MULTILINE)
        
        if import_pattern_1.search(content) or import_pattern_2.search(content):
             print(f"[Check] Found likely import of '{module_to_import}' in {file_path.name}")
             return True
             
        # --- AST Based Check (More Robust Example) ---
        # try:
        #     tree = ast.parse(content)
        #     for node in ast.walk(tree):
        #         if isinstance(node, ast.Import):
        #             for alias in node.names:
        #                 if alias.name == module_to_import.split('.')[0]:
        #                     print(f"[AST Check] Found 'import {alias.name}'...")
        #                     return True
        #         elif isinstance(node, ast.ImportFrom):
        #             if node.module == module_to_import.rsplit('.', 1)[0]:
        #                  for alias in node.names:
        #                      if alias.name == module_to_import.rsplit('.', 1)[-1]:
        #                          print(f"[AST Check] Found 'from {node.module} import {alias.name}'...")
        #                          return True
        # except SyntaxError as e:
        #     print(f"Warning: Could not parse {file_path.name} with AST: {e}")
        #     # Fallback to regex or fail?
            
    except IOError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return False
        
    print(f"[Check] Did not find likely import of '{module_to_import}' in {file_path.name}")
    return False

def check_instantiation(file_path: Path, class_to_instantiate: str, variable_name: Optional[str] = None) -> bool:
    """Check if a specific class appears to be instantiated.
    
    NOTE: Very basic check using regex. AST is needed for reliability.
    If variable_name is provided, checks for assignment like 'self.var = Class()'
    """
    if not file_path.exists(): return False
    try:
        content = file_path.read_text()
        if variable_name:
            # Look for self.variable = Class(...) or variable = Class(...)
            pattern = re.compile(f"(?:self\\.)?{variable_name}\\s*=\\s*{class_to_instantiate}\\(\\)")
        else:
            # Look for instantiation Class()
            pattern = re.compile(f"{class_to_instantiate}\\(\\)")
            
        if pattern.search(content):
             print(f"[Check] Found likely instantiation of '{class_to_instantiate}'" + (f" into '{variable_name}'" if variable_name else "") + f" in {file_path.name}")
             return True
             
        # TODO: Add AST check for Assign nodes
            
    except IOError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return False
        
    print(f"[Check] Did not find likely instantiation of '{class_to_instantiate}'" + (f" into '{variable_name}'" if variable_name else "") + f" in {file_path.name}")
    return False

def check_method_call(file_path: Path, variable_name: str, method_name: str) -> bool:
    """Check if a method is likely called on a variable (e.g., self.var.method()).
    
    NOTE: Very basic check using regex. AST is needed for reliability.
    """
    if not file_path.exists(): return False
    try:
        content = file_path.read_text()
        # Look for self.variable.method(...) or variable.method(...)
        pattern = re.compile(f"(?:self\\.)?{variable_name}\\.{method_name}\\(") # Matches start of call
        if pattern.search(content):
             print(f"[Check] Found likely call to '{method_name}' on '{variable_name}' in {file_path.name}")
             return True
             
        # TODO: Add AST check for Call nodes with Attribute access

    except IOError as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return False
        
    print(f"[Check] Did not find likely call to '{method_name}' on '{variable_name}' in {file_path.name}")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check Component Integration Points (Basic)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Example Usage:
 Check if Agent 2 worker imports and instantiates the Cursor bridge:
   python tools/check_component_integration.py --worker-file agents/agent_2/worker.py --check-import core.execution.cursor_executor_bridge.CursorExecutorBridge --check-instantiation CursorExecutorBridge --instance-var bridge

 Check if Agent 2 worker calls the 'refactor_file' method on its bridge instance:
   python tools/check_component_integration.py --worker-file agents/agent_2/worker.py --check-call bridge.refactor_file
'''
    )
    parser.add_argument("--worker-file", required=True, help="Path to the agent worker file to check.")
    parser.add_argument("--check-import", help="Python module path to check for import (e.g., core.execution.bridge.MyBridge)")
    parser.add_argument("--check-instantiation", help="Class name to check for instantiation (e.g., MyBridge)")
    parser.add_argument("--instance-var", help="Variable name the class is expected to be assigned to (e.g., self.bridge or bridge)")
    parser.add_argument("--check-call", help="Method call to check (e.g., bridge.method_name or self.bridge.method_name)")

    args = parser.parse_args()

    worker_path = Path(args.worker_file).resolve()
    results = []

    print(f"--- Checking Integrations for: {worker_path.name} ---")

    if args.check_import:
        module_path = args.check_import
        # Infer class name if checking instantiation/call later
        class_name_from_import = module_path.rsplit('.', 1)[-1]
        results.append(check_import_present(worker_path, module_path))

    if args.check_instantiation:
        class_name = args.check_instantiation
        instance_var = args.instance_var # Can be None
        results.append(check_instantiation(worker_path, class_name, instance_var))
        
    if args.check_call:
        call_parts = args.check_call.split('.')
        if len(call_parts) < 2:
            print("Error: --check-call format must be variable.method_name or self.variable.method_name", file=sys.stderr)
            sys.exit(1)
            
        method_name = call_parts[-1]
        variable_name = ".".join(call_parts[:-1]) # Handles self.var or just var
        # Clean variable name if it starts with self.
        if variable_name.startswith("self."):
             variable_name_cleaned = variable_name[5:]
        else:
             variable_name_cleaned = variable_name
             
        results.append(check_method_call(worker_path, variable_name_cleaned, method_name))

    print("--- Check Summary ---")
    if not results:
        print("No checks specified.")
    elif all(results):
        print("✅ All specified checks passed (based on basic analysis).")
    else:
        print("❌ Some specified checks failed (based on basic analysis).")
        sys.exit(1) # Exit with error code if checks fail 