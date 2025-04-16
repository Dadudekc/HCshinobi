#!/usr/bin/env python
import subprocess
import os
import argparse
import sys

# Potential enhancement: Add option to configure Vulture confidence level

def sniff_dead_code(target_dir, dry_run=True):
    print(f"🎯 DeadCodeSniffer: Scanning target directory: {target_dir}", file=sys.stderr) # Log to stderr
    
    # Basic check if target directory exists
    if not os.path.isdir(target_dir):
        print(f"❌ DeadCodeSniffer: Error - Target directory not found: {target_dir}", file=sys.stderr)
        return None # Indicate error
        
    # Ensure vulture is installed or accessible
    # Simple check - could be more robust (e.g., shutil.which)
    try:
        subprocess.run(["vulture", "--version"], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"❌ DeadCodeSniffer: Error - 'vulture' command not found or failed. Is it installed and in PATH? Error: {e}", file=sys.stderr)
        return None
        
    command = ["vulture", target_dir, "--min-confidence", "80"] # Set a reasonable confidence

    print("🐍 DeadCodeSniffer: Running Vulture...", file=sys.stderr)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False) # Don't check=True, parse output
    except Exception as e:
        print(f"❌ DeadCodeSniffer: Error running Vulture subprocess: {e}", file=sys.stderr)
        return None

    lines = result.stdout.splitlines()
    # Filter based on Vulture's typical output format
    unused_items = [line for line in lines if "% confidence" in line]

    if not unused_items:
        print("✅ DeadCodeSniffer: No unused code found with >= 80% confidence.", file=sys.stderr)
        return [] # Return empty list for success

    print(f"💀 DeadCodeSniffer: Found {len(unused_items)} potential dead code items:", file=sys.stderr)
    # Return the raw lines found
    return unused_items 

if __name__ == "__main__":
    # Basic argument parsing when run directly
    parser = argparse.ArgumentParser(description="💀 Dead Code Sniffa – Find potentially unused Python code using Vulture.")
    parser.add_argument("target", help="Path to the Python project directory or file to scan.")
    # Removed dry_run as deletion wasn't implemented anyway
    
    args = parser.parse_args()
    
    findings = sniff_dead_code(args.target)
    
    if findings is None:
        print("\nScript encountered an error.", file=sys.stderr)
        sys.exit(1)
    elif not findings:
        print("\nScan complete. No issues found.")
    else:
        print("\nScan complete. Potential dead code found:")
        for i, line in enumerate(findings, 1):
            print(f"{i:2d}. {line}") 