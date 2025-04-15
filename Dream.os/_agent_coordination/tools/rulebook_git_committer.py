import subprocess
import sys
from pathlib import Path
import argparse

# --- Helper Function (copied/adapted from auto_recovery_runner) --- #
def run_git_command(command: list[str], cwd: Path, check_output: bool = True) -> tuple[bool, str, str]:
    """Runs a git command using subprocess, returns success, stdout, stderr."""
    print(f"---> Running Git Command: {' '.join(command)} in {cwd}")
    try:
        process = subprocess.run(command, check=check_output, capture_output=True, text=True, cwd=cwd)
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        print("<--- Git command finished successfully.")
        return True, stdout, stderr
    except subprocess.CalledProcessError as e:
        stdout = e.stdout.strip()
        stderr = e.stderr.strip()
        print(f"Error running git command: {' '.join(command)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        if stdout:
             print(f"Stdout: {stdout}", file=sys.stderr)
        if stderr:
             print(f"Stderr: {stderr}", file=sys.stderr)
        print("<--- Git command failed.")
        return False, stdout, stderr
    except FileNotFoundError:
         print(f"Error: 'git' command not found. Is Git installed and in PATH?", file=sys.stderr)
         print("<--- Git command failed.")
         return False, "", "'git' command not found"
    except Exception as e:
        print(f"Unexpected error running git command {' '.join(command)}: {e}", file=sys.stderr)
        print("<--- Git command failed.")
        return False, "", str(e)

# --- Main Commit Function --- #
def commit_rulebook(rulebook_path: Path, commit_message: str, workspace_root: Path) -> bool:
    """Stages and commits the specified rulebook file."""
    
    if not workspace_root.is_dir():
        print(f"Error: Workspace root directory not found: {workspace_root}", file=sys.stderr)
        return False
        
    if not rulebook_path.is_file():
        print(f"Error: Rulebook file not found: {rulebook_path}", file=sys.stderr)
        return False

    # 1. Check if inside a git repository
    print("Checking Git repository status...")
    is_repo_cmd = ["git", "rev-parse", "--is-inside-work-tree"]
    is_repo_success, _, _ = run_git_command(is_repo_cmd, cwd=workspace_root, check_output=False)
    if not is_repo_success:
        print("Warning: Not inside a Git repository or 'git rev-parse' failed. Skipping commit.", file=sys.stderr)
        return False # Not an error for the caller, just can't commit

    # 2. Stage the file
    print(f"Staging {rulebook_path.relative_to(workspace_root)}...")
    # Ensure we use relative path for git add
    relative_rulebook_path = rulebook_path.relative_to(workspace_root)
    add_cmd = ["git", "add", str(relative_rulebook_path)]
    add_success, _, add_stderr = run_git_command(add_cmd, cwd=workspace_root)
    if not add_success:
        print(f"Error: Failed to stage rulebook file ({add_stderr}). Skipping commit.", file=sys.stderr)
        return False
        
    # 3. Commit the file
    print(f"Committing with message: \"{commit_message}\"...")
    commit_cmd = ["git", "commit", "-m", commit_message]
    commit_success, _, commit_stderr = run_git_command(commit_cmd, cwd=workspace_root)
    if not commit_success:
        # Check if commit failed because nothing was staged (e.g., file unchanged)
        if "nothing to commit" in commit_stderr.lower() or "no changes added to commit" in commit_stderr.lower():
             print("Info: Git commit skipped - no changes detected in rulebook.")
             return True # Treat as success if no changes
        else:
             print(f"Error: Failed to commit rulebook ({commit_stderr}).", file=sys.stderr)
             return False

    print("✅ Rulebook committed successfully.")
    return True

# --- CLI Interface (for direct testing/use) --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Git Committer for Rulebook Files.")
    parser.add_argument("rulebook_file", help="Path to the rulebook.md file to commit.")
    parser.add_argument("-m", "--message", required=True, help="Commit message.")
    parser.add_argument("--workspace-root", default=".", help="Path to the Git workspace root directory (defaults to cwd).")

    args = parser.parse_args()

    workspace_path = Path(args.workspace_root).resolve()
    rulebook_file_path = Path(args.rulebook_file).resolve()

    if not rulebook_file_path.is_relative_to(workspace_path):
         print(f"Error: Rulebook file {rulebook_file_path} must be inside the workspace root {workspace_path}", file=sys.stderr)
         sys.exit(1)

    success = commit_rulebook(
        rulebook_path=rulebook_file_path,
        commit_message=args.message,
        workspace_root=workspace_path
    )

    if not success:
        print("Rulebook commit process failed.", file=sys.stderr)
        sys.exit(1)
    else:
         print("Rulebook commit process finished.") 