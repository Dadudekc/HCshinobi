"""
Tool to perform a basic refactoring action: moving a block of code 
(identified by line numbers) from a source file to a target file.

Handles basic extraction and insertion. Includes a dry-run mode.
Does NOT automatically handle import updates - this is complex and left as TODO.
"""

import argparse
import sys
from pathlib import Path
import difflib # For showing diff in dry run

def extract_block(lines: List[str], start_line: int, end_line: int) -> List[str]:
    """Extracts lines (inclusive) based on 1-based line numbers."""
    # Adjust to 0-based index
    start_idx = start_line - 1
    end_idx = end_line 
    if start_idx < 0 or start_idx >= len(lines) or end_idx > len(lines):
        raise ValueError(f"Invalid line numbers: {start_line}-{end_line} for file with {len(lines)} lines.")
    return lines[start_idx:end_idx]

def remove_block(lines: List[str], start_line: int, end_line: int) -> List[str]:
    """Removes lines (inclusive) based on 1-based line numbers."""
    start_idx = start_line - 1
    end_idx = end_line
    if start_idx < 0 or start_idx >= len(lines) or end_idx > len(lines):
        raise ValueError(f"Invalid line numbers: {start_line}-{end_line} for file with {len(lines)} lines.")
    
    # Combine lines before and after the block
    new_lines = lines[:start_idx] + lines[end_idx:]
    
    # Clean up potential extra blank lines left after removal
    # This is basic, might need more sophisticated cleanup
    cleaned_lines = []
    for i, line in enumerate(new_lines):
         # Skip blank line if it was immediately before the removed block 
         # and the line after it is also blank or EOF
         is_potentially_extra_blank = (i == start_idx - 1 and not line.strip())
         next_line_is_blank_or_eof = (i + 1 >= len(new_lines) or not new_lines[i+1].strip())
         
         if is_potentially_extra_blank and next_line_is_blank_or_eof:
             continue
         cleaned_lines.append(line)
         
    # Ensure file doesn't end with too many blank lines
    while cleaned_lines and not cleaned_lines[-1].strip():
         cleaned_lines.pop()
    # Ensure at least one trailing newline if file is not empty
    if cleaned_lines:
        cleaned_lines.append("\n")
        
    return cleaned_lines

def add_block_to_target(target_lines: List[str], block: List[str], symbol_name: str, symbol_type: str) -> List[str]:
    """Adds the extracted block to the target file content.
    
    Currently appends to the end, ensuring necessary imports are mentioned.
    Future improvements could insert at a specific location or organize imports.
    """
    new_target_lines = target_lines[:]
    
    # --- TODO: Implement more sophisticated import handling --- 
    # 1. Analyze `block` for required imports.
    # 2. Check if those imports already exist in `target_lines`.
    # 3. Add missing imports near the top of the file.
    import_placeholder = f"# TODO: Add necessary imports for symbol '{symbol_name}' here\n"
    if import_placeholder not in "".join(new_target_lines): # Avoid adding multiple times
         # Basic: add placeholder at the beginning or after initial comments/docstring
         insert_pos = 0
         for i, line in enumerate(new_target_lines):
             if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('""'):
                 insert_pos = i
                 break
         new_target_lines.insert(insert_pos, import_placeholder)
         new_target_lines.insert(insert_pos + 1, "\n") # Add blank line after
    # --- End Import Handling Placeholder ---
    
    # Ensure separation from existing content
    if new_target_lines and not new_target_lines[-1].strip():
        new_target_lines.append("\n") # Add extra blank line if needed
    elif new_target_lines:
         new_target_lines.append("\n\n") # Add two blank lines

    # Add the code block
    new_target_lines.extend(block)
    
    # Ensure trailing newline
    if not new_target_lines[-1].endswith('\n'):
         new_target_lines[-1] += '\n'
         
    return new_target_lines

def refactor_move_symbol(
    source_file: Path, 
    target_file: Path, 
    symbol_name: str, 
    symbol_type: str, 
    start_line: int, 
    end_line: int, 
    dry_run: bool = True
) -> bool:
    """Performs the move operation (or simulates if dry_run)."""
    
    print(f"--- Refactor: Move Symbol --- ")
    print(f" Symbol: {symbol_name} ({symbol_type})")
    print(f" Source: {source_file} (Lines: {start_line}-{end_line})")
    print(f" Target: {target_file}")
    print(f" Dry Run: {dry_run}")
    print("-----------------------------")

    # --- Read Source File ---
    try:
        print(f"Reading source file: {source_file}")
        source_lines = source_file.read_text(encoding='utf-8').splitlines(keepends=True)
    except Exception as e:
        print(f"Error reading source file {source_file}: {e}", file=sys.stderr)
        return False

    # --- Extract Block --- 
    try:
        print("Extracting code block...")
        extracted_block = extract_block(source_lines, start_line, end_line)
        print(f" -> Extracted {len(extracted_block)} lines.")
        # print("--- Extracted Block ---")
        # print("".join(extracted_block[:15]) + ("..." if len(extracted_block) > 15 else "")) # Preview
        # print("-----------------------")
    except ValueError as e:
        print(f"Error extracting block: {e}", file=sys.stderr)
        return False

    # --- Generate Modified Source --- 
    try:
        print("Generating modified source content...")
        modified_source_lines = remove_block(source_lines, start_line, end_line)
    except ValueError as e:
        print(f"Error removing block from source: {e}", file=sys.stderr)
        return False
        
    # --- Read Target File (or create empty list if new) ---
    target_lines = []
    if target_file.exists():
        try:
            print(f"Reading existing target file: {target_file}")
            target_lines = target_file.read_text(encoding='utf-8').splitlines(keepends=True)
        except Exception as e:
            print(f"Error reading target file {target_file}: {e}. Will proceed assuming new file.", file=sys.stderr)
            # Allow proceeding, maybe the write will work
    else:
        print(f"Target file {target_file} does not exist. Will be created.")
        
    # --- Generate Modified Target --- 
    try:
        print("Generating modified target content...")
        modified_target_lines = add_block_to_target(target_lines, extracted_block, symbol_name, symbol_type)
    except Exception as e:
        print(f"Error adding block to target content: {e}", file=sys.stderr)
        return False

    # --- Perform Actions (Dry Run or Write) --- 
    if dry_run:
        print("\n--- DRY RUN: Proposed Changes ---")
        
        print(f"\n--- Source File: {source_file} ---")
        source_diff = difflib.unified_diff(source_lines, modified_source_lines, fromfile='a/'+source_file.name, tofile='b/'+source_file.name, lineterm='')
        print('\n'.join(source_diff))
        
        print(f"\n--- Target File: {target_file} ---")
        target_diff = difflib.unified_diff(target_lines, modified_target_lines, fromfile='a/'+target_file.name, tofile='b/'+target_file.name, lineterm='')
        print('\n'.join(target_diff))
        
        print("\n--- End Dry Run ---")
        print("No files were modified.")
    else:
        print("\n--- APPLYING CHANGES --- ")
        try:
            print(f"Writing modified source file: {source_file}")
            source_file.write_text("".join(modified_source_lines), encoding='utf-8')
            print(f"Writing modified target file: {target_file}")
            target_file.parent.mkdir(parents=True, exist_ok=True) # Ensure target dir exists
            target_file.write_text("".join(modified_target_lines), encoding='utf-8')
            print("✅ Files successfully modified.")
            # --- TODO: Run code formatter (black/ruff) on modified files --- 
            
            # --- TODO: Advanced - Scan workspace for imports of the moved symbol --- 
            # Use tools like `rg` or Python AST analysis across project files
            # Identify files importing `symbol_name` from `source_file`
            # Attempt to rewrite imports to point to `target_file`
            print("NOTE: Import statements in other files may need manual updates.")
            
        except Exception as e:
            print(f"Error writing modified files: {e}", file=sys.stderr)
            # TODO: Consider rollback mechanism? For now, just report error.
            return False
            
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Move a symbol (class/function) from a source file to a target file.",
        epilog="WARNING: This tool modifies files. Use --dry-run first. Import statements are NOT automatically updated."
    )
    parser.add_argument("--source", required=True, help="Path to the source Python file.")
    parser.add_argument("--target", required=True, help="Path to the target Python file (will be created if needed).")
    parser.add_argument("--symbol", required=True, help="Name of the class or function to move.")
    parser.add_argument("--type", required=True, choices=['class', 'function'], help="Type of the symbol.")
    parser.add_argument("--start-line", required=True, type=int, help="Start line number of the symbol block (1-based, inclusive).")
    parser.add_argument("--end-line", required=True, type=int, help="End line number of the symbol block (1-based, inclusive).")
    parser.add_argument("--dry-run", action="store_true", help="Show proposed changes without modifying files.")

    args = parser.parse_args()

    source_path = Path(args.source).resolve()
    target_path = Path(args.target).resolve()

    if not source_path.is_file():
        print(f"Error: Source file not found: {source_path}", file=sys.stderr)
        sys.exit(1)
        
    if target_path.is_dir():
         print(f"Error: Target path is a directory, please specify a file name: {target_path}", file=sys.stderr)
         sys.exit(1)
         
    if source_path == target_path:
         print("Error: Source and target files cannot be the same.", file=sys.stderr)
         sys.exit(1)

    success = refactor_move_symbol(
        source_file=source_path,
        target_file=target_path,
        symbol_name=args.symbol,
        symbol_type=args.type,
        start_line=args.start_line,
        end_line=args.end_line,
        dry_run=args.dry_run
    )

    if success:
        print("\nRefactor operation completed" + (" (Dry Run)" if args.dry_run else "") + ".")
    else:
        print("\nRefactor operation failed.")
        sys.exit(1) 