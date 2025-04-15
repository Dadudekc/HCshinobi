#!/usr/bin/env python3
"""
TODO Finder - Locates TODO, FIXME, PLACEHOLDER, etc., in Python files.
Also flags large files (400+ lines) for modularization and identifies
exact-duplicate files for cleanup.

Usage:
  python todo_finder.py [directory_to_scan] [output_report.md]

By default, scans the current directory "." and writes "todo_report.md".
Generates a main report plus a subdirectory "todo_report_categories/" with
individual category reports.
"""

import os
import re
import glob
import sys
import hashlib
from collections import defaultdict, Counter
from datetime import datetime
import argparse

# ------------------------------------------------------------------------------------
# DEFAULT EXCLUSIONS & CONSTANTS
# ------------------------------------------------------------------------------------
DEFAULT_EXCLUDE_DIRS = [
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    "build", "dist", "*.egg-info", "runtime" # Added runtime
]
LINE_THRESHOLD_DEFAULT = 400

# ------------------------------------------------------------------------------------
# PATTERN DEFINITIONS
# ------------------------------------------------------------------------------------

COMMENT_PATTERNS = {
    "CRITICAL": [
        r"#\s*CRITICAL.*?:.*?([^\n]*)",
        r"#\s*FIXME.*?:.*?([^\n]*)"
    ],
    "IMPORTANT": [
        r"#\s*TODO.*?:.*?([^\n]*)",
        r"#\s*IMPORTANT.*?:.*?([^\n]*)"
    ],
    "SECURITY_CONCERN": [
        r"#.*?security.*?risk.*?([^\n]*)",
        r"#.*?vulnerable.*?([^\n]*)",
        r"#.*?insecure.*?([^\n]*)",
        r"#.*?needs security review.*?([^\n]*)"
    ],
    "MISSING_IMPLEMENTATION": [
        r"def\s+\w+\s*\([^)]*\)\s*:.*?pass\s*$",
        r"class\s+\w+\s*\([^)]*\)\s*:.*?pass\s*$",
        r"^\s*\.\.\.\s*$"
    ],
    "INCOMPLETE": [
        r"#.*?incomplete.*?([^\n]*)",
        r"#.*?not.*?complete.*?([^\n]*)",
        r"#.*?unfinished.*?([^\n]*)",
        r"#.*?partial.*?implementation.*?([^\n]*)"
    ],
    "TEST_NEEDED": [
        r"#.*?needs tests.*?([^\n]*)",
        r"#.*?add test.*?([^\n]*)",
        r"#.*?test.*?missing.*?([^\n]*)",
        r"#.*?implement test.*?([^\n]*)"
    ],
    "PERFORMANCE_ISSUE": [
        r"#.*?optimization.*?needed.*?([^\n]*)",
        r"#.*?slow.*?([^\n]*)",
        r"#.*?performance.*?issue.*?([^\n]*)",
        r"#.*?can be faster.*?([^\n]*)"
    ],
    "YOU_MAY_WANT_TO_CHECK": [
        r"#.*?a full implementation would include.*?([^\n]*)",
        r"#.*?future expansion.*?([^\n]*)",
        r"#.*?would be better to.*?([^\n]*)",
        r"#.*?could be improved by.*?([^\n]*)",
        r"#.*?in the future.*?([^\n]*)",
        r"#.*?eventually.*?([^\n]*)"
    ],
    "PLACEHOLDER": [
        r"#\s*PLACEHOLDER.*?([^\n]*)",
        r"#.*?placeholder.*?([^\n]*)"
    ],
    "ENHANCEMENT": [
        r"#\s*ENHANCEMENT.*?:.*?([^\n]*)",
        r"#\s*IDEA.*?:.*?([^\n]*)"
    ],
    "GENERAL": [
        r"#\s*TODO[^:]?([^\n]*)",
        r"#\s*FIXME[^:]?([^\n]*)",
        r"#.*?HACK.*?([^\n]*)"
    ]
}

CODE_ANALYSIS_PATTERNS = {
    "EMPTY_METHOD_BODY": {
        "pattern": r"(^\s*)def\s+(\w+)\s*\([^)]*\)\s*:\s*\n\1\s+pass(?:\s*#.*)?\s*$",
        "description": "Method with empty body (pass statement)",
        "category": "MISSING_IMPLEMENTATION",
        "check_previous_line_for": "@abstractmethod"
    },
    "STUBBED_IMPLEMENTATION": {
        "pattern": r"def\s+(\w+)\s*\([^)]*\)\s*:.*?return\s+None\s*\n",
        "description": "Method with stubbed implementation (just returns None)",
        "category": "MISSING_IMPLEMENTATION"
    },
    "BARE_EXCEPT": {
        "pattern": r"except\s*:",
        "description": "Bare except clause (should catch specific exceptions)",
        "category": "SECURITY_CONCERN"
    },
    "MAGIC_NUMBER": {
        "pattern": r"[^a-zA-Z_\"'][-+]?[0-9]+(?:\.[0-9]+)?[^a-zA-Z0-9_\"']",
        "description": "Magic number (should be defined as a constant)",
        "category": "ENHANCEMENT"
    },
    "HARDCODED_PATH": {
        "pattern": r"[\"'](?:/|\\\\|\w:\\\\)[a-zA-Z0-9_./\\\\-]+[\"']",
        "description": "Hardcoded file path (consider using configuration)",
        "category": "ENHANCEMENT"
    },
    "PRINT_DEBUG": {
        "pattern": r"print\s*\(",
        "description": "Print statement (possibly debug code left in)",
        "category": "ENHANCEMENT"
    }
}

# ------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------------------------

def _is_test_or_sandbox_file(rel_path):
    """
    Returns True if the file path suggests it is a test/sandbox/mock file.
    """
    filename = os.path.basename(rel_path)
    dir_components = os.path.dirname(rel_path).split(os.sep)

    # Common test-file indicators
    if (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or "tests" in dir_components
        or "test" in dir_components
        or "_sandbox" in dir_components
        or "mocks" in dir_components
    ):
        return True
    return False


def _extract_line_context(lines, match, context_size=3):
    """
    Given file lines and a regex match, return (line_no, context_lines).
    - line_no is 1-based
    - context_lines is a slice of lines around the match (±3 lines by default)
    """
    pos = match.start()
    # We'll reconstruct the file as a single string, but if we
    # already have content, we can just do:
    joined_content = "\n".join(lines)
    partial_text = joined_content[:pos]
    line_no = partial_text.count('\n') + 1

    start_line_idx = max(0, line_no - context_size - 1)  # zero-based
    end_line_idx = min(len(lines), line_no + context_size - 1)
    context_slice = lines[start_line_idx:end_line_idx]
    return line_no, context_slice


# ------------------------------------------------------------------------------------
# CORE SCAN FUNCTION
# ------------------------------------------------------------------------------------

def find_todos(directory=".", exclude_dirs=None, exclude_files=None, line_threshold=400):
    """
    Scans Python files under 'directory' for:
    - Placeholder comments (TODO, FIXME, etc.)
    - Suspicious code patterns (bare except, magic numbers, etc.)
    - Large files (>= line_threshold)
    - Duplicate files (exact text matches)

    Returns:
        (results, stats) where:
            results: {rel_path: {category: [list_of_findings]}}
            stats: {
                "total_files": int,
                "files_with_todos": int,
                "todos_by_category": Counter,
                "largest_offenders": Counter,
                "categories_by_file": defaultdict(Counter),
                "line_counts": {rel_path: int},
                "large_files": [rel_path_with_400+],
                "duplicates": [[fileA, fileB, ...], [fileC, fileD, ...], ...]
            }
    """
    print(f"[+] Starting scan in directory: {os.path.abspath(directory)}")
    results = defaultdict(lambda: defaultdict(list))
    stats = {
        "total_files": 0,
        "files_with_todos": 0,
        "todos_by_category": Counter(),
        "largest_offenders": Counter(),
        "categories_by_file": defaultdict(Counter),
        "line_counts": {},
        "large_files": [],
        "duplicates": []  # Will be formed later
    }

    # Combine provided exclusions with defaults
    if exclude_dirs is None:
        combined_exclude_dirs = DEFAULT_EXCLUDE_DIRS
    else:
        # Ensure provided dirs are relative to scan directory for path joining
        provided_abs_dirs = [os.path.abspath(os.path.join(directory, d)) for d in exclude_dirs]
        combined_exclude_dirs = DEFAULT_EXCLUDE_DIRS + provided_abs_dirs
        
    if exclude_files is None:
        exclude_files = [] # Keep as provided if given

    # Convert final excludes list to absolute paths
    exclude_dirs_abs = [os.path.abspath(d) for d in combined_exclude_dirs] # Use combined list
    exclude_files_abs = [os.path.abspath(os.path.join(directory, f)) for f in exclude_files]
    
    # --- Add Self Exclusion ---
    script_abs_path = os.path.abspath(__file__)
    if script_abs_path not in exclude_files_abs:
        exclude_files_abs.append(script_abs_path)
        print(f"[+] Auto-excluding self: {script_abs_path}")
    # --- End Self Exclusion ---
        
    print(f"[+] Exclude Dirs (Final Abs): {exclude_dirs_abs}") # Updated print
    print(f"[+] Exclude Files (Final Abs): {exclude_files_abs}") # Updated print

    python_files = glob.glob(os.path.join(directory, "**", "*.py"), recursive=True)
    print(f"[+] Found {len(python_files)} total Python files.")

    # Filter out excluded items
    filtered_files = []
    for file_path in python_files:
        abs_path = os.path.abspath(file_path)
        is_excluded = False
        # Use the final absolute exclude lists
        if any(abs_path.startswith(d) for d in exclude_dirs_abs):
            is_excluded = True
            continue
        if abs_path in exclude_files_abs:
            is_excluded = True
            continue
        
        # Skip test/sandbox files early
        rel_path_for_test_check = os.path.relpath(file_path, directory)
        if _is_test_or_sandbox_file(rel_path_for_test_check):
            is_excluded = True
            continue

        if not is_excluded:
            filtered_files.append(file_path)

    stats["total_files"] = len(filtered_files)
    print(f"[+] Processing {stats['total_files']} filtered Python files.")

    # Dictionary for duplicates detection: {sha256_hash: [rel_paths]}
    file_hash_map = defaultdict(list)

    for idx, file_path in enumerate(filtered_files):
        rel_path = os.path.relpath(file_path, directory)
        print(f"\n[>] Processing ({idx+1}/{stats['total_files']}): {rel_path}")

        try:
            print(f"  [.] Reading file content...")
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            lines = content.split('\n')
            line_count = len(lines)
            stats["line_counts"][rel_path] = line_count
            print(f"  [.] File lines: {line_count}")

            # Check for large file
            if line_count >= line_threshold:
                stats["large_files"].append(rel_path)
                results[rel_path]["LARGE_FILE"] = [{
                    "line": 1,
                    "text": f"File exceeds {line_threshold} lines ({line_count})",
                    "context": [f"File: {rel_path}", f"Lines: {line_count}"]
                }]
                stats["todos_by_category"]["LARGE_FILE"] += 1
                stats["categories_by_file"][rel_path]["LARGE_FILE"] += 1
                print(f"  [!] Found LARGE_FILE issue.")

            # File hashing for duplicates
            print(f"  [.] Calculating hash...")
            file_hash = hashlib.sha256(content.encode('utf-8', 'replace')).hexdigest()
            file_hash_map[file_hash].append(rel_path)

            file_has_todos = False
            print(f"  [.] Scanning for comment patterns...")
            # Scan for COMMENT_PATTERNS
            for category, patterns in COMMENT_PATTERNS.items():
                for pattern in patterns:
                    try:
                        for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                            line_no, context_lines = _extract_line_context(lines, match)
                            finding = {
                                "line": line_no,
                                "text": match.group(1).strip() if len(match.groups()) > 0 else match.group(0).strip(), # Handle patterns with/without capture group
                                "context": context_lines
                            }
                            results[rel_path][category].append(finding)
                            stats["todos_by_category"][category] += 1
                            stats["categories_by_file"][rel_path][category] += 1
                            stats["largest_offenders"].update([rel_path])
                            file_has_todos = True
                    except re.error as re_err:
                         print(f"  [ERROR ❌] Regex error for pattern '{pattern}' in {rel_path}: {re_err}")

            print(f"  [.] Scanning for code analysis patterns...")
            # Scan for CODE_ANALYSIS_PATTERNS
            for analysis_key, data in CODE_ANALYSIS_PATTERNS.items():
                pattern = data["pattern"]
                description = data["description"]
                category = data["category"]
                check_prev = data.get("check_previous_line_for")
                try:
                    for match in re.finditer(pattern, content, re.MULTILINE): # Note: IGNORECASE might be needed for some?
                        line_no, context_lines = _extract_line_context(lines, match)
                        
                        # Skip if previous line indicates it's intentional (e.g., @abstractmethod for pass)
                        if check_prev and line_no > 1 and check_prev in lines[line_no - 2]: # line_no is 1-based, lines list is 0-based
                             continue
                             
                        finding = {
                            "line": line_no,
                            "text": description,
                            "match": match.group(0).strip(),
                            "context": context_lines
                        }
                        results[rel_path][category].append(finding)
                        stats["todos_by_category"][category] += 1
                        stats["categories_by_file"][rel_path][category] += 1
                        stats["largest_offenders"].update([rel_path])
                        file_has_todos = True
                except re.error as re_err:
                    print(f"  [ERROR ❌] Regex error for pattern '{analysis_key}' in {rel_path}: {re_err}")

            if file_has_todos:
                stats["files_with_todos"] += 1
                print(f"  [+] Found issues in this file.")
            else:
                 print(f"  [.] No issues found in this file.")

        except Exception as e:
            print(f"[ERROR ❌] Failed to process file {rel_path}: {e}")
            # Optionally add to results/stats?
            results[rel_path]["PROCESSING_ERROR"] = [{
                "line": 0,
                "text": f"Error processing file: {e}",
                "context": []
            }]
            stats["todos_by_category"]["PROCESSING_ERROR"] += 1
            stats["categories_by_file"][rel_path]["PROCESSING_ERROR"] += 1
            stats["largest_offenders"].update([rel_path])
            stats["files_with_todos"] += 1

    # Process duplicates
    print("\n[+] Processing duplicates...")
    for file_hash, paths in file_hash_map.items():
        if len(paths) > 1:
            stats["duplicates"].append(sorted(paths))
    print(f"[+] Found {len(stats['duplicates'])} sets of duplicate files.")

    print("[+] Scan complete.")
    return results, stats


# ------------------------------------------------------------------------------------
# REPORT GENERATION
# ------------------------------------------------------------------------------------

def generate_report(results, stats, output_file=None):
    """
    Creates a main Markdown report plus separate category-based files.

    Args:
        results (dict): Nested {rel_path: {category: [...issues...]}}
        stats (dict): Summary statistics (including duplicates, large_files, etc.)
        output_file (str, optional): If provided, main report is written here.

    Returns:
        str: The main report's full text.
    """
    output_dir = os.path.dirname(output_file) if output_file else "."
    report_base_name = os.path.splitext(os.path.basename(output_file))[0] if output_file else "todo_report"
    category_dir = os.path.join(output_dir, f"{report_base_name}_categories")
    os.makedirs(category_dir, exist_ok=True)

    # Category order
    category_order = [
        "CRITICAL",
        "IMPORTANT",
        "SECURITY_CONCERN",
        "MISSING_IMPLEMENTATION",
        "INCOMPLETE",
        "TEST_NEEDED",
        "PERFORMANCE_ISSUE",
        "YOU_MAY_WANT_TO_CHECK",
        "PLACEHOLDER",
        "ENHANCEMENT",
        "GENERAL"
    ]

    # User-friendly display names
    category_display_names = {
        "CRITICAL": "Critical Issues",
        "IMPORTANT": "Important TODOs",
        "SECURITY_CONCERN": "Security Concerns",
        "MISSING_IMPLEMENTATION": "Missing Implementations",
        "INCOMPLETE": "Incomplete Implementations",
        "TEST_NEEDED": "Tests Needed",
        "PERFORMANCE_ISSUE": "Performance Issues",
        "YOU_MAY_WANT_TO_CHECK": "You May Want to Check",
        "PLACEHOLDER": "Placeholders",
        "ENHANCEMENT": "Enhancement Ideas",
        "GENERAL": "General TODOs"
    }

    # Build main report
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    main_report = []
    main_report.append(f"# TODO Finder Report - {now_str}")
    main_report.append("\n## Overview")
    main_report.append("This report helps track and organize development tasks found in code comments or patterns.")
    main_report.append(f"- **Generated**: {now_str}")

    # Summary stats
    main_report.append("\n## Summary")
    main_report.append(f"- **Scanned Files**: {stats['total_files']}")
    main_report.append(f"- **Files with TODOs**: {stats['files_with_todos']}")

    # Categories (table in main report)
    main_report.append("\n## Categories")
    main_report.append("| Category | Count | Link |")
    main_report.append("| --- | --- | --- |")

    for cat in category_order:
        count = stats["todos_by_category"][cat]
        if count > 0:
            cat_name = category_display_names.get(cat, cat)
            cat_file = f"{cat.lower()}.md"
            link_path = os.path.join(f"{report_base_name}_categories", cat_file)
            main_report.append(f"| {cat_name} | {count} | [View]({link_path}) |")

            # Build that category's sub-report
            cat_report = []
            cat_report.append(f"# {cat_name}")
            cat_report.append(f"\n[← Back to Main Report](../{report_base_name}.md)\n")
            cat_report.append("## Summary")
            cat_report.append(f"- **Total Issues**: {count}")
            cat_report.append(f"- **Report Date**: {now_str}")

            # Which files have entries in this category?
            cat_file_counts = {}
            for file_path, cat_dict in results.items():
                if cat in cat_dict and cat_dict[cat]:
                    cat_file_counts[file_path] = len(cat_dict[cat])

            # Sort files by count
            cat_report.append("\n## Files")
            cat_report.append("| File | Issue Count |")
            cat_report.append("| --- | --- |")
            sorted_files = sorted(cat_file_counts.items(), key=lambda x: x[1], reverse=True)
            for fpath, ccount in sorted_files:
                safe_anchor = fpath.replace('\\', '/').replace(' ', '%20').lower().replace('/', '-').replace('.', '-')
                cat_report.append(f"| [{fpath}](#{safe_anchor}) | {ccount} |")

            # Detailed breakdown
            cat_report.append("\n## Details")
            for fpath, cat_dict in results.items():
                if cat in cat_dict and cat_dict[cat]:
                    safe_anchor = fpath.replace('\\', '/').replace(' ', '%20').lower().replace('/', '-').replace('.', '-')
                    cat_report.append(f"\n### <a id='{safe_anchor}'></a>{fpath}")

                    for issue in cat_dict[cat]:
                        cat_report.append(f"\n#### Line {issue['line']}: `{issue['text']}`")
                        cat_report.append("```python")
                        cat_report.extend(issue['context'])
                        cat_report.append("```")

            # Write the category file
            with open(os.path.join(category_dir, cat_file), 'w', encoding='utf-8') as cf:
                cf.write("\n".join(cat_report))

    # Top offenders
    main_report.append("\n## Top Files with Most TODOs")
    main_report.append("| File | Count | Categories |")
    main_report.append("| --- | --- | --- |")
    for file_path, total_count in stats["largest_offenders"].most_common(15):
        cat_counts = stats["categories_by_file"][file_path]
        # Show top 3 categories as a summary
        cat_summary = ", ".join(
            f"{category_display_names.get(c, c)}: {n}"
            for c, n in cat_counts.most_common(3)
        )
        main_report.append(f"| {file_path} | {total_count} | {cat_summary} |")

    # Large files section
    large_files = stats["large_files"]
    if large_files:
        main_report.append("\n## Large Files (≥ 400 lines)")
        main_report.append("These files might be candidates for splitting into smaller modules.\n")
        main_report.append("| File | Line Count |")
        main_report.append("| --- | --- |")
        for lf in sorted(large_files, key=lambda x: stats["line_counts"][x], reverse=True):
            main_report.append(f"| {lf} | {stats['line_counts'][lf]} |")

    # Potential duplicates section
    duplicates = stats["duplicates"]
    if duplicates:
        main_report.append("\n## Potential Duplicates")
        main_report.append("The following files have identical content (exact match). Consider removing or refactoring.\n")
        group_idx = 1
        for group in duplicates:
            # group is a list of file paths that match exactly
            main_report.append(f"- **Duplicate Group {group_idx}**:")
            for fp in group:
                main_report.append(f"  - {fp}")
            group_idx += 1

    # Combine everything
    main_report_text = "\n".join(main_report)

    # Optionally write to file
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as mf:
            mf.write(main_report_text)
        print(f"Main report written to '{output_file}'")
        print(f"Category reports in '{category_dir}/'")

    return main_report_text


# ------------------------------------------------------------------------------------
# ENTRY POINT
# ------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Find TODOs and potential issues in Python code.")
    parser.add_argument('scan_directory', nargs='?', default='.', 
                        help="Directory to scan recursively (default: current directory)")
    parser.add_argument('output_report', nargs='?', default='todo_report.md', 
                        help="Main output report file (default: todo_report.md)")
    parser.add_argument('-e', '--exclude-dir', action='append', default=[],
                        help="Directory to exclude (relative to scan_directory). Can be used multiple times.")
    parser.add_argument('-f', '--exclude-file', action='append', default=[],
                        help="File to exclude (relative to scan_directory). Can be used multiple times.")
    parser.add_argument('--line-threshold', type=int, default=400,
                        help="Line count threshold to flag files as large (default: 400)")

    args = parser.parse_args()

    print(f"Scanning directory: {args.scan_directory}")
    print(f"Output report: {args.output_report}")
    print(f"Excluding Dirs: {args.exclude_dir}") # Use provided relative dirs here
    print(f"Excluding Files: {args.exclude_file}")

    try:
        # Pass provided exclusions directly; function handles combining with defaults
        results, stats = find_todos(
            directory=args.scan_directory, 
            exclude_dirs=args.exclude_dir, 
            exclude_files=args.exclude_file, 
            line_threshold=args.line_threshold
        )
        generate_report(results, stats, args.output_report)
        print("\nReport generation complete.")
    except Exception as e:
        print(f"\n[ERROR ❌] An unexpected error occurred during scan/report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) # Exit with error code

if __name__ == "__main__":
    main()
