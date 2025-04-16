#!/usr/bin/env python3
"""
QA Checklist Runner for Dream.OS

This script provides a simple CLI to interact with the QA checklist
stored in ../docs/qa_checklist.json.

Usage:
  python scripts/run_qa.py list [--status <status>]
  python scripts/run_qa.py update <test_id> <new_status>
  python scripts/run_qa.py summary

Arguments:
  list              List checklist items.
  update            Update the status of a specific test item.
  summary           Show a summary of test statuses.
  <test_id>         The ID of the test item (e.g., T3.1).
  <new_status>      The new status (e.g., pass, fail, wip, pending, skipped).

Options:
  --status <status>  Filter list by status (e.g., pending, pass, fail).
  --checklist <path> Path to the checklist JSON file (default: ../docs/qa_checklist.json).
"""

import json
import argparse
from pathlib import Path
from collections import Counter
from datetime import datetime

DEFAULT_CHECKLIST_PATH = Path(__file__).parent.parent / "docs" / "qa_checklist.json"
DEFAULT_REPORT_PATH = Path(__file__).parent.parent / "docs" / "qa_report.md"
VALID_STATUSES = ["pass", "fail", "wip", "pending", "skipped"]

# Status Emojis
STATUS_EMOJI = {
    "pass": "✅",
    "fail": "❌",
    "wip": "⏳",
    "pending": "❓",
    "skipped": "⏩",
    "unknown": "❔"
}

def load_checklist(checklist_path: Path) -> dict:
    """Loads the checklist JSON file."""
    if not checklist_path.exists():
        print(f"Error: Checklist file not found at {checklist_path}")
        exit(1)
    try:
        with open(checklist_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in checklist file {checklist_path}: {e}")
        exit(1)
    except Exception as e:
        print(f"Error loading checklist file {checklist_path}: {e}")
        exit(1)

def save_checklist(checklist_path: Path, data: dict) -> None:
    """Saves the checklist data back to the JSON file."""
    try:
        with open(checklist_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Checklist updated: {checklist_path}")
    except Exception as e:
        print(f"Error saving checklist file {checklist_path}: {e}")
        exit(1)

def find_item(data: dict, test_id: str) -> (str, int):
    """Finds a test item by its ID within the checklist data."""
    for category, content in data.get('categories', {}).items():
        for index, item in enumerate(content.get('items', [])):
            if item.get('id') == test_id:
                return category, index
    return None, -1

def list_items(data: dict, filter_status: str = None):
    """Prints the checklist items, optionally filtered by status."""
    print(f"--- {data.get('phase', 'QA Checklist')} ---")
    total_items = 0
    shown_items = 0
    for category, content in data.get('categories', {}).items():
        print(f"\n[{category.replace('_', ' ').title()}] - {content.get('description', '')}")
        items_in_category = content.get('items', [])
        if not items_in_category:
            print("  (No items)")
            continue

        category_shown_count = 0
        for item in items_in_category:
            total_items += 1
            item_id = item.get('id', 'N/A')
            label = item.get('label', '(No label)')
            status = item.get('status', 'unknown')
            file_info = f" ({item['file']})" if 'file' in item else ""

            if filter_status is None or status.lower() == filter_status.lower():
                print(f"  [{item_id}] {label}{file_info} - Status: {status.upper()}")
                shown_items += 1
                category_shown_count += 1

        if filter_status and category_shown_count == 0:
             print(f"  (No items match status '{filter_status}')")

    print(f"\nTotal items: {total_items}. Items shown: {shown_items}.")


def update_item_status(data: dict, test_id: str, new_status: str) -> bool:
    """Updates the status of a specific test item."""
    if new_status.lower() not in VALID_STATUSES:
        print(f"Error: Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}")
        return False

    category, index = find_item(data, test_id)
    if category is None:
        print(f"Error: Test ID '{test_id}' not found in the checklist.")
        return False

    old_status = data['categories'][category]['items'][index].get('status')
    data['categories'][category]['items'][index]['status'] = new_status.lower()
    print(f"Updated item [{test_id}] status from '{old_status}' to '{new_status.lower()}'")
    return True

def show_summary(data: dict):
    """Prints a summary of test statuses by category."""
    print(f"--- {data.get('phase', 'QA Checklist')} Summary ---")
    overall_status_counts = Counter()
    total_items = 0

    for category, content in data.get('categories', {}).items():
        category_name = category.replace('_', ' ').title()
        print(f"\n[{category_name}]")
        category_status_counts = Counter()
        items = content.get('items', [])
        category_total = len(items)
        total_items += category_total

        if category_total == 0:
            print("  (No items)")
            continue

        for item in items:
            status = item.get('status', 'unknown').lower()
            category_status_counts[status] += 1
            overall_status_counts[status] += 1

        for status, count in sorted(category_status_counts.items()):
            print(f"  {status.upper()}: {count}")
        print(f"  Total: {category_total}")

    print("\n--- Overall Summary ---")
    if total_items == 0:
        print("(No items found)")
    else:
        for status, count in sorted(overall_status_counts.items()):
             percentage = (count / total_items) * 100
             print(f"  {status.upper()}: {count}/{total_items} ({percentage:.1f}%)")
    print("="*25)

def generate_markdown_report(data: dict) -> str:
    """Generates a Markdown report from the checklist data."""
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    phase = data.get('phase', 'QA Checklist')

    lines.append(f"# {phase} - QA Report")
    lines.append(f"_Last generated: {now}_")
    lines.append("\n---")

    overall_status_counts = Counter()
    total_items = 0

    for category, content in data.get('categories', {}).items():
        category_name = category.replace('_', ' ').title()
        lines.append(f"\n## {category_name}")
        lines.append(f"> {content.get('description', '')}")
        lines.append("")

        items = content.get('items', [])
        if not items:
            lines.append("_(No items in this category)_\n")
            continue

        # Header for the table
        lines.append("| Status | ID   | Label                     | File/Notes |")
        lines.append("| :----: | :--- | :------------------------ | :--------- |")

        category_status_counts = Counter()
        category_total = len(items)
        total_items += category_total

        for item in items:
            status = item.get('status', 'unknown').lower()
            emoji = STATUS_EMOJI.get(status, STATUS_EMOJI["unknown"])
            item_id = item.get('id', 'N/A')
            label = item.get('label', '(No label)')
            file_info = f"`{item['file']}`" if 'file' in item else ""

            lines.append(f"| {emoji}  | {item_id} | {label} | {file_info} |")

            category_status_counts[status] += 1
            overall_status_counts[status] += 1

        lines.append("") # Add blank line after table

    # Overall Summary Section
    lines.append("\n---")
    lines.append("\n## Overall Summary")
    if total_items == 0:
        lines.append("_(No items found in checklist)_\n")
    else:
        lines.append("| Status    | Count | Percentage |")
        lines.append("| :-------- | ----: | ---------: |")
        for status, count in sorted(overall_status_counts.items()):
            percentage = (count / total_items) * 100
            emoji = STATUS_EMOJI.get(status, STATUS_EMOJI["unknown"])
            lines.append(f"| {emoji} {status.upper()} | {count} | {percentage:.1f}% |")
        lines.append(f"| **Total** | **{total_items}** | **100.0%** |")

    return "\n".join(lines)

def save_report(report_content: str, output_path: Path):
    """Saves the generated report content to the specified file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True) # Ensure dir exists
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"QA Report saved to: {output_path}")
    except Exception as e:
        print(f"Error saving report file {output_path}: {e}")
        exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="QA Checklist Runner for Dream.OS.",
        epilog="Example: python scripts/run_qa.py update T3.1 pass"
    )

    parser.add_argument(
        "--checklist",
        type=Path,
        default=DEFAULT_CHECKLIST_PATH,
        help="Path to the QA checklist JSON file."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    parser_list = subparsers.add_parser("list", help="List checklist items.")
    parser_list.add_argument(
        "--status",
        choices=VALID_STATUSES + [s.upper() for s in VALID_STATUSES], # Allow upper/lower case
        help="Filter list by status."
    )

    # Update command
    parser_update = subparsers.add_parser("update", help="Update status of a test item.")
    parser_update.add_argument("test_id", help="The ID of the test item (e.g., T3.1).")
    parser_update.add_argument(
        "new_status",
        choices=VALID_STATUSES + [s.upper() for s in VALID_STATUSES], # Allow upper/lower case
        help=f"The new status (e.g., {VALID_STATUSES})."
    )

    # Summary command
    parser_summary = subparsers.add_parser("summary", help="Show a summary of test statuses.")

    # NEW: Report command
    parser_report = subparsers.add_parser("report", help="Generate a Markdown report of the checklist.")
    parser_report.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to save the Markdown report file."
    )

    args = parser.parse_args()

    # Load data
    checklist_data = load_checklist(args.checklist)

    # Execute command
    if args.command == "list":
        list_items(checklist_data, filter_status=args.status)
    elif args.command == "update":
        if update_item_status(checklist_data, args.test_id, args.new_status):
            save_checklist(args.checklist, checklist_data)
    elif args.command == "summary":
        show_summary(checklist_data)
    elif args.command == "report":
        report_content = generate_markdown_report(checklist_data)
        save_report(report_content, args.output)

if __name__ == "__main__":
    main() 