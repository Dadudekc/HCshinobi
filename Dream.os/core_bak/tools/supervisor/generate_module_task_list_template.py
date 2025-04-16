#!/usr/bin/env python3
from pathlib import Path
import argparse
import datetime

# Using textwrap to dedent the template for cleaner source code
import textwrap 

TEMPLATE = textwrap.dedent("""\\ 
# Task List: {module_name} Module (`{absolute_path}`)

Generated: {timestamp_utc} UTC

## I. Code Review & Cleanup

- [ ] Review class/function docstrings for completeness and accuracy.
- [ ] Remove unused variables, imports, functions, or classes.
- [ ] Resolve TODO comments or convert them into actionable tasks.
- [ ] Remove temporary logging or print statements.
- [ ] Ensure adherence to project coding style conventions (e.g., PEP 8).

## II. AgentBus Integration (If Applicable)

- [ ] Verify agent registration with `AgentBus` (if this module contains agents).
- [ ] Review event subscriptions: Ensure the module subscribes to all necessary events.
- [ ] Review event dispatching: Ensure events are dispatched correctly with proper payloads.
- [ ] Ensure task handlers (if processing `EventType.TASK`) are robust, parse payloads correctly, and handle errors gracefully.
- [ ] Confirm status reporting mechanism (for tasks) aligns with project standards (e.g., updating `/d:/Dream.os/runtime/task_list.json`, sending status events).

## III. Testing

- [ ] Review existing unit tests for coverage of core functionality.
- [ ] Add unit tests for any new or untested public methods/functions.
- [ ] Review existing integration tests (especially those involving `AgentBus` or inter-module communication).
- [ ] Add integration tests for key workflows involving this module.
- [ ] Add tests for expected failure modes (e.g., invalid inputs, missing dependencies, API errors).

## IV. Documentation

- [ ] Ensure the module has a clear module-level docstring explaining its purpose.
- [ ] Verify or add documentation for public classes and functions (parameters, return values, exceptions).
- [ ] Update project documentation (`/d:/Dream.os/docs/` or `/d:/Dream.os/_agent_coordination/README.md`) if this module introduces significant changes or new concepts.
- [ ] Consider adding usage examples if applicable.

## V. Specific Module Goals

- [ ] *Add tasks specific to the primary function of the `{module_name}` module here.*
- [ ]
- [ ]

## VI. Finalization

- [ ] Ensure all tasks in this list are addressed or intentionally deferred.
- [ ] Commit all related code changes, tests, and documentation.
- [ ] Notify Supervisor or relevant team members upon completion.
""")

def generate_task_list(module_path: Path):
    # Resolve to an absolute path for display and checking
    absolute_module_path = module_path.resolve()
    
    if not absolute_module_path.exists() or not absolute_module_path.is_dir():
        print(f"❌ Error: Invalid or non-existent directory path provided: {absolute_module_path}")
        return

    target_file = absolute_module_path / "task_list.md"
    if target_file.exists():
        print(f"⚠️ Warning: task_list.md already exists at {target_file}. No action taken.")
        return

    try:
        content = TEMPLATE.format(
            module_name=absolute_module_path.name, # Use resolved path name
            absolute_path=str(absolute_module_path).replace('\\', '/'), # Use resolved path, convert backslashes
            timestamp_utc=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        )
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Successfully generated task list template: {target_file}")

    except Exception as e:
        print(f"❌ Error: Failed to generate task list at {target_file}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a boilerplate task_list.md for a module.")
    parser.add_argument("module_path", help="Path to the target module directory (e.g., ../core, ./agents).")
    args = parser.parse_args()

    # Allow relative paths from CWD
    generate_task_list(Path(args.module_path)) 