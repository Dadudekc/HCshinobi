#!/usr/bin/env python
import argparse
import sys
import logging
import shutil
from pathlib import Path
import os # For path normalization, backup check

# --- Constants ---
MARKER_START = "# CODE_APPLICATOR_START"
MARKER_END = "# CODE_APPLICATOR_END"

# --- Logging Setup ---
logger = logging.getLogger("CodeApplicatorTool")
# Basic config if no handlers set (e.g., when run directly)
if not logger.hasHandlers():
    log_level = logging.INFO
    # Check for verbose flag early (before full parsing if needed, but okay here)
    if '--verbose' in sys.argv or '-v' in sys.argv:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Core Logic Function ---
def apply_code(target_file_path: Path, code_content: str, mode: str, 
               create_dirs: bool, backup: bool, 
               start_marker: str = MARKER_START, end_marker: str = MARKER_END):
    """Applies the provided code content to the target file based on the specified mode."""
    
    logger.debug(f"Applying code to '{target_file_path}' using mode '{mode}'. Create Dirs: {create_dirs}, Backup: {backup}")

    # --- Directory Handling ---
    parent_dir = target_file_path.parent
    if not parent_dir.exists():
        if create_dirs:
            try:
                logger.info(f"Creating parent directories: {parent_dir}")
                parent_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create parent directories for '{target_file_path}': {e}", exc_info=True)
                return False # Cannot proceed
        else:
            logger.error(f"Parent directory '{parent_dir}' does not exist and --create-dirs flag not set.")
            return False
    elif not parent_dir.is_dir():
         logger.error(f"Parent path '{parent_dir}' exists but is not a directory.")
         return False

    # --- Backup Handling ---
    backup_path = None
    if backup and target_file_path.exists() and target_file_path.is_file():
        try:
            backup_path = target_file_path.with_suffix(target_file_path.suffix + ".bak")
            # Avoid overwriting existing backups? For simplicity, we overwrite.
            logger.info(f"Creating backup: '{target_file_path}' -> '{backup_path}'")
            shutil.copy2(target_file_path, backup_path) # copy2 preserves metadata
        except Exception as e:
            logger.error(f"Failed to create backup file '{backup_path}': {e}", exc_info=True)
            # Proceed without backup? Or fail? Let's fail to be safe.
            return False

    # --- Apply Code based on Mode ---
    try:
        if mode == 'overwrite':
            logger.debug(f"Mode: Overwrite. Writing {len(code_content)} chars to {target_file_path}")
            with target_file_path.open("w", encoding='utf-8') as f:
                f.write(code_content)
            logger.info(f"Successfully overwrote '{target_file_path}'.")

        elif mode == 'append':
            logger.debug(f"Mode: Append. Appending {len(code_content)} chars to {target_file_path}")
            # Add newline before appending if file not empty and doesn't end with one?
            prefix = ""
            if target_file_path.exists() and target_file_path.stat().st_size > 0:
                 with target_file_path.open("r", encoding='utf-8') as f_read:
                      last_char = f_read.read()[-1:]
                      if last_char != '\n':
                           prefix = "\n"
            
            with target_file_path.open("a", encoding='utf-8') as f:
                f.write(prefix + code_content)
            logger.info(f"Successfully appended to '{target_file_path}'.")

        elif mode == 'replace_markers':
            logger.debug(f"Mode: Replace Markers. Start='{start_marker}', End='{end_marker}'")
            if not target_file_path.exists() or not target_file_path.is_file():
                logger.error(f"Target file '{target_file_path}' does not exist for mode 'replace_markers'.")
                # Optionally: could treat as overwrite if file doesn't exist?
                # For now, require file existence for replace_markers.
                return False
            
            with target_file_path.open("r", encoding='utf-8') as f:
                original_content = f.read()

            start_index = original_content.find(start_marker)
            end_index = original_content.find(end_marker)

            if start_index == -1:
                logger.error(f"Start marker '{start_marker}' not found in '{target_file_path}'.")
                return False
            if end_index == -1:
                logger.error(f"End marker '{end_marker}' not found in '{target_file_path}'.")
                return False
            if end_index <= start_index:
                 logger.error(f"End marker '{end_marker}' found before start marker '{start_marker}' in '{target_file_path}'.")
                 return False

            # Extract parts and construct new content
            part_before = original_content[:start_index + len(start_marker)]
            part_after = original_content[end_index:]
            # Ensure newline handling is reasonable between sections
            new_content = part_before.rstrip('\r\n') + "\n" + code_content.strip('\r\n') + "\n" + part_after.lstrip('\r\n')
            
            logger.debug(f"Replacing content between markers. Writing {len(new_content)} chars.")
            with target_file_path.open("w", encoding='utf-8') as f:
                f.write(new_content)
            logger.info(f"Successfully replaced content between markers in '{target_file_path}'.")

        else:
             # Should not happen if argparse choices are set correctly
             logger.error(f"Internal error: Unknown mode '{mode}'.")
             return False

        return True # Success

    except Exception as e:
        logger.error(f"Failed to apply code to '{target_file_path}' using mode '{mode}': {e}", exc_info=True)
        # Optional: Attempt to restore backup if it exists?
        if backup_path and backup_path.exists():
             try:
                  logger.warning(f"Attempting to restore backup from '{backup_path}'")
                  shutil.move(backup_path, target_file_path)
                  logger.info(f"Backup restored to '{target_file_path}'")
             except Exception as restore_e:
                  logger.error(f"Failed to restore backup: {restore_e}")
        return False

# --- Main Execution --- 
def main():
    parser = argparse.ArgumentParser(description="Apply generated code to a target file.")
    parser.add_argument("--target-file", required=True, help="Path to the target file.")
    
    # Input source group - mutually exclusive
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--code-input", help="Code content as a string.")
    input_group.add_argument("--code-file", help="Path to a file containing the code.")
    input_group.add_argument("--code-stdin", action="store_true", help="Read code from standard input.")
    
    parser.add_argument("--mode", choices=['overwrite', 'replace_markers', 'append'], default='overwrite', 
                        help="How to apply the code (default: overwrite). replace_markers requires start/end markers.")
    parser.add_argument("--create-dirs", action="store_true", help="Create parent directories for target file if they don't exist.")
    parser.add_argument("--backup", action="store_true", help="Create a backup (.bak) of the original file before changes.")
    parser.add_argument("--start-marker", default=MARKER_START, help="Start marker for replace_markers mode.")
    parser.add_argument("--end-marker", default=MARKER_END, help="End marker for replace_markers mode.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose (DEBUG) logging.")

    args = parser.parse_args()

    # Reconfigure logger level if verbose flag is set
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    # --- Get Code Content ---
    code_content = None
    try:
        if args.code_input is not None:
            logger.debug("Reading code from --code-input argument.")
            code_content = args.code_input
        elif args.code_file:
            logger.debug(f"Reading code from file: {args.code_file}")
            code_file_path = Path(args.code_file).resolve()
            if not code_file_path.is_file():
                 raise FileNotFoundError(f"Code input file not found: {code_file_path}")
            with code_file_path.open("r", encoding='utf-8') as f:
                code_content = f.read()
        elif args.code_stdin:
            logger.debug("Reading code from standard input...")
            code_content = sys.stdin.read()
            logger.debug("Finished reading from stdin.")
            
        if code_content is None:
             # Should be caught by mutually exclusive group, but belt-and-suspenders
             raise ValueError("No code content provided.")
             
    except Exception as e:
         logger.error(f"Error reading code input: {e}", exc_info=True)
         sys.exit(1)
         
    # --- Resolve Target Path ---
    target_file_path = Path(args.target_file).resolve()
    logger.info(f"Target file resolved to: {target_file_path}")

    # --- Apply Code ---
    success = apply_code(target_file_path, code_content, args.mode, 
                         args.create_dirs, args.backup, 
                         args.start_marker, args.end_marker)

    # --- Exit ---
    if success:
        logger.info("Code application completed successfully.")
        sys.exit(0)
    else:
        logger.error("Code application failed.")
        sys.exit(1)

if __name__ == "__main__":
    main() 