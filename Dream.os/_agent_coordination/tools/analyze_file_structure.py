"""
Tool to analyze the structure of a Python file using Abstract Syntax Trees (AST).
Provides an overview of classes, functions, and imports.
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Union, Optional

class StructureAnalyzer(ast.NodeVisitor):
    """NodeVisitor to extract structural information from Python code."""

    def __init__(self):
        self.structure: Dict[str, List[Dict[str, Any]]] = {
            "imports": [],
            "functions": [],
            "classes": [],
            # Could add top-level assignments, etc.
        }
        self.current_class_name: Optional[str] = None

    def _format_args(self, args_node: ast.arguments) -> List[str]:
        """Format function/method arguments into a list of strings."""
        args_list = []
        # Positional/Keyword args
        posonlyargs_count = len(args_node.posonlyargs)
        args_count = len(args_node.args)
        
        # Positional-only args
        for i, arg in enumerate(args_node.posonlyargs):
            args_list.append(arg.arg)
            if i == posonlyargs_count - 1:
                args_list.append('/') # Marker for pos-only end

        # Regular args (positional or keyword)
        for i, arg in enumerate(args_node.args):
             args_list.append(arg.arg)

        # Vararg (*args)
        if args_node.vararg:
            args_list.append(f"*{args_node.vararg.arg}")
        # Keyword-only args
        if args_node.kwonlyargs:
             if not args_node.vararg: # Add * marker if no *args
                  args_list.append('*')
             for arg in args_node.kwonlyargs:
                 args_list.append(arg.arg)
        # Kwarg (**kwargs)
        if args_node.kwarg:
            args_list.append(f"**{args_node.kwarg.arg}")
        return args_list

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.structure["imports"].append({
                "type": "import",
                "module": alias.name,
                "alias": alias.asname,
                "lineno": node.lineno
            })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module_name = node.module if node.module else "." * node.level
        for alias in node.names:
            self.structure["imports"].append({
                "type": "from_import",
                "module": module_name,
                "name": alias.name,
                "alias": alias.asname,
                "lineno": node.lineno
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]):
        func_info = {
            "name": node.name,
            "args": self._format_args(node.args),
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "docstring": ast.get_docstring(node, clean=False)
        }
        if self.current_class_name:
            # Find the current class dict and append the method
            for class_dict in self.structure["classes"]:
                if class_dict["name"] == self.current_class_name:
                    class_dict.setdefault("methods", []).append(func_info)
                    break
        else:
            self.structure["functions"].append(func_info)
        # Do not visit children further for functions within functions (unless needed)
        # self.generic_visit(node) 

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Reuse the FunctionDef logic
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        # Get base class names if they are simple names (won't resolve complex bases)
        base_names = [b.id for b in node.bases if isinstance(b, ast.Name)]
        class_info = {
            "name": node.name,
            "bases": base_names,
            "lineno": node.lineno,
            "end_lineno": node.end_lineno,
            "docstring": ast.get_docstring(node, clean=False),
            "methods": [] # Methods will be added when visited
        }
        self.structure["classes"].append(class_info)
        
        # Track current class context for methods
        previous_class_name = self.current_class_name
        self.current_class_name = node.name
        self.generic_visit(node) # Visit methods etc. inside the class
        self.current_class_name = previous_class_name # Restore context

def analyze_structure(target_file: Path) -> Optional[Dict[str, Any]]:
    """Parses the file and returns the extracted structure."""
    if not target_file.exists() or not target_file.is_file():
        print(f"Error: Target file '{target_file}' does not exist or is not a file.", file=sys.stderr)
        return None
        
    print(f"Analyzing file: {target_file}")
    try:
        content = target_file.read_text()
        tree = ast.parse(content)
        analyzer = StructureAnalyzer()
        analyzer.visit(tree)
        return analyzer.structure
    except SyntaxError as e:
        print(f"Error: Invalid Python syntax in '{target_file}' at line {e.lineno}, offset {e.offset}: {e.msg}", file=sys.stderr)
        return None
    except IOError as e:
        print(f"Error reading file '{target_file}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred during analysis: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Python File Structure using AST")
    parser.add_argument("target_file", help="Path to the Python file to analyze.")
    parser.add_argument("--output-json", action="store_true", help="Output the structure as JSON.")

    args = parser.parse_args()

    target_path = Path(args.target_file).resolve()
    
    structure = analyze_structure(target_path)

    if structure:
        print("--- Analysis Complete ---")
        if args.output_json:
            print(json.dumps(structure, indent=2))
        else:
            # Simple text output
            print("\nImports:")
            if structure['imports']:
                for imp in structure['imports']:
                    if imp['type'] == 'import':
                        print(f"  - import {imp['module']}" + (f" as {imp['alias']}" if imp['alias'] else ""))
                    else: # from_import
                        print(f"  - from {imp['module']} import {imp['name']}" + (f" as {imp['alias']}" if imp['alias'] else ""))
            else:
                print("  (None)")

            print("\nTop-Level Functions:")
            if structure['functions']:
                for func in structure['functions']:
                    async_prefix = "async " if func['is_async'] else ""
                    print(f"  - {async_prefix}{func['name']}({', '.join(func['args'])}) (Line: {func['lineno']})")
            else:
                print("  (None)")
                
            print("\nClasses:")
            if structure['classes']:
                for cls in structure['classes']:
                    bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                    print(f"\n  Class: {cls['name']}{bases} (Line: {cls['lineno']})")
                    if cls['methods']:
                        print("    Methods:")
                        for meth in cls['methods']:
                            async_prefix = "async " if meth['is_async'] else ""
                            print(f"      - {async_prefix}{meth['name']}({', '.join(meth['args'])}) (Line: {meth['lineno']})")
                    else:
                        print("    Methods: (None)")
            else:
                print("  (None)")
            
        print("\n--- End of Report ---")
    else:
        print("Analysis failed.")
        sys.exit(1) 