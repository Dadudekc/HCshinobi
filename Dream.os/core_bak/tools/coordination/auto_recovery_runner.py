import sys
import subprocess
import argparse
from pathlib import Path
import os
import json # Import json for loading context

# Import the rule adding function
from _agent_coordination.tools.rulebook_utils import add_rule
# Import the git commit function
from rulebook_git_committer import commit_rulebook

# --- Constants --- #
# Define output directory relative to the script's location
TOOLS_DIR = Path(__file__).parent.resolve()
WORKSPACE_ROOT = TOOLS_DIR.parent # Assumes tools/ is one level down from root
# Base output directory matching the generator
BASE_OUTPUT_DIR = WORKSPACE_ROOT / "outputs" / "recovery_contexts"
LATEST_CONTEXT_FILENAME_SUFFIX = "_latest.json"
# Default rulebook path (can be overridden if needed)
DEFAULT_RULEBOOK_PATH = WORKSPACE_ROOT / "rulebook.md"

# --- Helper Functions --- #
def run_command(command: list[str], cwd: Path | None = None, check_output: bool = True) -> bool:
    """Runs a command using subprocess and returns True on success.
       (Simplified for general commands, git commands handled by committer utility)
    """
    print(f"\n---> Running command: {' '.join(command)}")
    try:
        process = subprocess.run(command, check=check_output, capture_output=True, text=True, cwd=cwd)
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        if stdout:
            print("Output:\n" + stdout)
        if stderr:
            print("Stderr:\n" + stderr, file=sys.stderr)
        print("<--- Command finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(command)}", file=sys.stderr)
        print(f"Return code: {e.returncode}", file=sys.stderr)
        stdout = e.stdout.strip()
        stderr = e.stderr.strip()
        if stdout:
             print(f"Stdout: {stdout}", file=sys.stderr)
        if stderr:
             print(f"Stderr: {stderr}", file=sys.stderr)
        print("<--- Command failed.")
        return False
    except FileNotFoundError:
         print(f"Error: Command not found (is {' '.join(command).split()[0]} installed and in PATH?): {' '.join(command)}", file=sys.stderr)
         print("<--- Command failed.")
         return False
    except Exception as e:
        print(f"Unexpected error running command {' '.join(command)}: {e}", file=sys.stderr)
        print("<--- Command failed.")
        return False

# --- Main Execution --- #
def main():
    parser = argparse.ArgumentParser(description="Automated Runner: Generates recovery context, updates rulebook, optionally commits, and dispatches to Cursor.")
    parser.add_argument("--agent", required=True, help="Name of the stalled agent class (e.g., ArchitectsEdgeAgent)")
    parser.add_argument("--log", required=True, help="Path to the stalled log file or inline string")
    parser.add_argument("--inline", action="store_true", help="Use --log as inline text")
    parser.add_argument("--project-root", default=".", help="Path to project directory (defaults to cwd)")
    parser.add_argument("--context-file", default=None, help="Optional: Path to a specific context file to dispatch (skips generation and rule update)")
    parser.add_argument("--skip-rulebook", action="store_true", help="Optional: Skip updating the rulebook for this run.")
    parser.add_argument("--auto-commit-rulebook", action="store_true", help="Optional: Automatically git add and commit rulebook.md after update.")

    args = parser.parse_args()
    agent_name = args.agent
    should_update_rulebook = not args.skip_rulebook
    should_auto_commit = args.auto_commit_rulebook
    context_data = None # Initialize context_data

    # Determine the context file path
    if args.context_file:
        # User specified an exact file - skip generation and rule update
        context_file_to_dispatch = Path(args.context_file)
        should_update_rulebook = False
        should_auto_commit = False # Cannot commit if we didn't update
        print(f"🚚 Dispatching specific context file provided: {context_file_to_dispatch}")
        print("ℹ️ Skipping context generation and rulebook update.")
        if not context_file_to_dispatch.is_file():
             print(f"❌ Error: Specified context file not found: {context_file_to_dispatch}")
             sys.exit(1)
        # Try to load context data even if provided, needed for dispatch info potentially
        try:
             with open(context_file_to_dispatch, "r", encoding="utf-8") as f:
                context_data = json.load(f)
        except Exception as e:
             print(f"Warning: Could not load provided context file {context_file_to_dispatch} for reading: {e}", file=sys.stderr)
             # Continue without context_data if loading fails? Or exit?
             context_data = {} # Allow continuing but commit message might be generic

    else:
        # Default: Generate new context and use the latest file
        agent_output_dir = BASE_OUTPUT_DIR / agent_name
        latest_context_filename = f"{agent_name}{LATEST_CONTEXT_FILENAME_SUFFIX}"
        latest_context_path = agent_output_dir / latest_context_filename
        context_file_to_dispatch = latest_context_path

        print(f"🛠️ Starting Auto Recovery Runner for Agent: {agent_name}")
        print(f"📂 Project Root: {Path(args.project_root).resolve()}")
        print(f"💾 Target Latest Context File: {latest_context_path}")

        # --- Step 1: Generate Recovery Context --- #
        print(f"\n[Step 1/{3 + should_update_rulebook + (should_update_rulebook and should_auto_commit)}] Generating/Updating Recovery Context...")
        generator_script = TOOLS_DIR / "recovery_context_generator.py"
        generator_cmd = [
            sys.executable,
            str(generator_script),
            "--agent", agent_name,
            "--log", args.log,
            "--project-root", args.project_root,
        ]
        if args.inline:
            generator_cmd.append("--inline")

        if not run_command(generator_cmd, cwd=WORKSPACE_ROOT):
            print("\n❌ Failed to generate recovery context. Aborting.")
            sys.exit(1)

        print(f"✅ Recovery context generated/updated successfully ({latest_context_path}).")
        
        # Load the generated context data here
        try:
            with open(context_file_to_dispatch, "r", encoding="utf-8") as f:
                context_data = json.load(f)
        except Exception as e:
             print(f"❌ Error: Could not load generated context file {context_file_to_dispatch} for reading: {e}", file=sys.stderr)
             sys.exit(1)

    # --- Step 2: Update Rulebook (if not skipped) --- #
    rule_added_this_run = False
    if should_update_rulebook:
        current_step = 2
        print(f"\n[Step {current_step}/{3 + should_update_rulebook + (should_update_rulebook and should_auto_commit)}] Updating Rulebook...")
        if not context_data:
             print("❌ Error: Cannot update rulebook without loaded context data.", file=sys.stderr)
             sys.exit(1)
        try:
            rule_added_this_run = add_rule(
                agent_name=context_data.get("agent", "UnknownAgent"),
                stall_category=context_data.get("stall_category", "UNKNOWN"),
                detected_issue=context_data.get("detected_issue", "N/A"),
                proposed_fix=context_data.get("recommended_fix", "No specific fix recommended."),
                rulebook_path=DEFAULT_RULEBOOK_PATH
            )
            if rule_added_this_run:
                print("📘 Rulebook updated.")
            else:
                print("📘 Rulebook update skipped (e.g., duplicate detected).")
        except Exception as e:
            print(f"❌ Error updating rulebook: {e}", file=sys.stderr)
            sys.exit(1)
    elif not args.context_file:
        print(f"\n[Step 2/{3 + should_update_rulebook + (should_update_rulebook and should_auto_commit)}] Skipping Rulebook update as requested.")

    # --- Step 3: Auto-Commit Rulebook (if applicable) --- #
    if rule_added_this_run and should_auto_commit:
        current_step = 3
        print(f"\n[Step {current_step}/{3 + should_update_rulebook + should_auto_commit}] Auto-committing rulebook.md...")
        if not context_data:
             print("❌ Error: Cannot generate commit message without loaded context data.", file=sys.stderr)
             sys.exit(1)
        
        # Generate commit message from context
        agent_ctx = context_data.get("agent", "UnknownAgent")
        category_ctx = context_data.get("stall_category", "UNKNOWN")
        commit_msg = f"docs(rulebook): Auto-add rule for {agent_ctx} ({category_ctx})"
        
        # Call the committer function
        commit_success = commit_rulebook(
            rulebook_path=DEFAULT_RULEBOOK_PATH,
            commit_message=commit_msg,
            workspace_root=WORKSPACE_ROOT
        )
        
        if not commit_success:
             # commit_rulebook prints specific errors, just note the failure here
             print("⚠️ Rulebook auto-commit process reported an issue.", file=sys.stderr)
             # Decide if this should be fatal? Maybe not, allow dispatch anyway.

    elif should_auto_commit and not rule_added_this_run:
         print(f"\n[Step 3/{3 + should_update_rulebook + should_auto_commit}] Skipping auto-commit because no new rule was added.")

    # --- Step 4: Dispatch to Cursor --- # (Adjust step number)
    final_step_offset = (should_update_rulebook and should_auto_commit and rule_added_this_run) + should_update_rulebook
    current_step = 2 + final_step_offset
    total_steps = 1 + final_step_offset + 1 # 1 for generation, offset for optional steps, 1 for dispatch
    if args.context_file:
         total_steps = 1 # Only dispatch step if context file is provided
         current_step = 1
         
    print(f"\n[Step {current_step}/{total_steps}] Dispatching Context File {context_file_to_dispatch} to Cursor...")
    bridge_script = TOOLS_DIR / "agent_cursor_bridge.py"
    bridge_cmd = [
        sys.executable,
        str(bridge_script),
        "--context-file", str(context_file_to_dispatch)
    ]

    if not run_command(bridge_cmd, cwd=WORKSPACE_ROOT):
        print("\n❌ Failed to dispatch context to Cursor.")
        sys.exit(1)

    print("\n✅✅✅ Auto Recovery Runner finished successfully! ✅✅✅")

if __name__ == "__main__":
    main() 