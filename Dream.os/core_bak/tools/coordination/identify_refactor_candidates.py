"""Standalone script to identify code symbols (classes, functions) for potential refactoring/moving."""

import ast
import json
import argparse
import os
import sys # Added
from pathlib import Path # Added

class SymbolFinder(ast.NodeVisitor):
    """AST Visitor to find top-level class and function definitions."""
    def __init__(self, target_symbols: list[str]):
        self.target_symbols = set(target_symbols)
        self.found_symbols = {}

    def visit_ClassDef(self, node):
        if node.name in self.target_symbols:
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
            # AST end_lineno might not cover everything perfectly (e.g., trailing comments)
            # A source-code based approach might be needed for exact slicing
            self.found_symbols[node.name] = {
                "type": "class",
                "start_line": start_line,
                "end_line": end_line # AST calculated end line
            }
        # Don't call generic_visit unless we want nested items

    def visit_FunctionDef(self, node):
        # We assume this visitor is only called on top-level module nodes
        # (see find_symbols_for_refactor implementation) so no need to check parent
        if node.name in self.target_symbols:
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
            self.found_symbols[node.name] = {
                "type": "function",
                "start_line": start_line,
                "end_line": end_line # AST calculated end line
            }
        # Don't call generic_visit

    def visit_AsyncFunctionDef(self, node):
        # Treat async functions similarly to regular functions
        self.visit_FunctionDef(node)

def find_symbols_for_refactor(filepath: str, symbols: list[str]) -> dict:
    """Finds the location (line numbers) of specified symbols in a Python file."""
    target_path = Path(filepath).resolve() # Use Path object
    if not target_path.is_file():
        print(f"Error: File not found or is not a file: {filepath}", file=sys.stderr)
        # Raise specific error instead of returning empty dict?
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"Analyzing file: {target_path}")
    try:
        source = target_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        finder = SymbolFinder(symbols)
        # Only visit top-level nodes directly to avoid finding methods
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                finder.visit(node)
        return finder.found_symbols
    except SyntaxError as e:
        print(f"Error: Failed to parse {filepath} - SyntaxError on line {e.lineno}: {e.msg}", file=sys.stderr)
        raise ValueError(f"Failed to parse {filepath}: {e}") from e # Re-raise for main block
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}", file=sys.stderr)
        raise # Re-raise other errors


if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, and simulation
    print(">>> Running module:", __file__)

    parser = argparse.ArgumentParser(description='Identify code symbols for refactoring.')
    parser.add_argument('filepath', help='Path to the Python file to analyze.')
    parser.add_argument('-s', '--symbols', required=True, nargs='+', 
                        help='List of class or function names to find.')
    parser.add_argument('--output', help='Optional path to save the JSON output.')
    
    args = parser.parse_args()

    print(f">>> Analyzing file: {args.filepath}")
    print(f">>> Searching for symbols: {', '.join(args.symbols)}")

    try:
        found_data = find_symbols_for_refactor(args.filepath, args.symbols)
        output_json = json.dumps(found_data, indent=2)
        
        print("\n>>> Found Symbols Result:")
        if not found_data:
            print("(No specified symbols found at the top level)")
        else:
            print(output_json)
        
        if args.output:
            try:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists
                output_path.write_text(output_json, encoding='utf-8')
                print(f"\n>>> Output saved to: {output_path.resolve()}")
            except IOError as e:
                print(f"\n>>> Error saving output file: {e}", file=sys.stderr)
                
    except (FileNotFoundError, ValueError, Exception) as e:
        print(f"\n>>> Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("\n>>> Analysis complete.") 