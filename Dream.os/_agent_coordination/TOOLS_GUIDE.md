# Dream.OS Tools Guide

This document provides guidance on the available tools within the `tools/` directory, intended for use by autonomous agents or developers.

## Usage Principles

- **Targeted Execution:** Use the most specific tool for the job.
- **Parameterization:** Utilize command-line arguments to control tool behavior where available.
- **Idempotency:** Tools should ideally be safe to run multiple times where applicable.
- **Logging:** Tools should provide clear console output indicating their actions and results.
- **Exit Codes:** Tools should use standard exit codes (0 for success, non-zero for failure or specific conditions).

---

## Recovery & Diagnostics Tools

These tools are primarily invoked by agents like `CursorControlAgent` in response to recovery tasks dispatched by the `TaskDispatcher`.

### 1. `tools/check_confirmation_state.py`

*   **Purpose:** Simulates checking the system state to determine if explicit user confirmation is required before proceeding with a potentially sensitive or ambiguous action.
*   **Arguments:**
    *   None currently implemented (can be extended, e.g., `--context-file <path>`)
*   **Output:** Prints status messages to stdout.
*   **Exit Codes:**
    *   `0`: Confirmation NOT required; safe to proceed.
    *   `1`: Confirmation REQUIRED.
*   **Agent Usage:** Used by `CursorControlAgent`'s `_handle_confirmation_check` method. The agent should treat exit code `1` as a failure for the handler, indicating the need for escalation or clarification.
*   **Example Call:** `python tools/check_confirmation_state.py`

### 2. `tools/reload_agent_context.py`

*   **Purpose:** Simulates reloading the operational context or memory for a specified agent.
*   **Arguments:**
    *   `--target <agent_name>`: (Required) The name of the agent whose context should be reloaded.
*   **Output:** Prints status messages to stdout.
*   **Exit Codes:**
    *   `0`: Simulated context reload successful.
    *   `1`: Simulated context reload failed.
*   **Agent Usage:** Used by `CursorControlAgent`'s `_handle_context_reload` method. The target agent name is typically passed from the task parameters.
*   **Example Call:** `python tools/reload_agent_context.py --target CursorControlAgent`

### 3. `tools/diagnostics.py`

*   **Purpose:** Runs a set of diagnostic checks on the system state (simulated).
*   **Arguments:**
    *   `--level {basic|full}`: (Optional) Specifies the diagnostic level (default: `basic`).
    *   `--auto`: (Optional) Flag to indicate automated execution (currently only affects logging).
*   **Output:** Prints diagnostic steps and findings to stdout.
*   **Exit Codes:**
    *   `0`: Basic checks passed without warnings.
    *   `1`: Warnings encountered (e.g., old failed tasks found).
*   **Agent Usage:** Used by `CursorControlAgent`'s `_handle_generic_recovery` method. The agent should check the exit code to determine if potential issues were flagged.
*   **Example Call:** `python tools/diagnostics.py --auto`

---

## Project & Context Tools

### 4. `tools/project_context_producer.py`

*   **Purpose:** Analyzes conversation logs and project files to generate a context summary (`agent_bridge_context.json`), often used by `StallRecoveryAgent` to categorize stalls and identify relevant files.
*   **Arguments (as a module):** The `produce_project_context` function takes:
    *   `conversation_log (str)`: The log content to analyze.
    *   `project_dir_str (str)`: Path to the project root.
    *   `return_dict (bool)`: If True, returns context as dict instead of writing to file (default: False).
*   **Output:** Writes `agent_bridge_context.json` to the project root or returns a dictionary.
*   **Agent Usage:** Imported and used by `StallRecoveryAgent` during stall analysis.
*   **Example Call (as script, if __main__ enabled):** `python tools/project_context_producer.py "...log snippet..." .` (Requires adapting the script to take CLI args if run directly).

---

## General Utilities

These tools provide general functionality for interacting with the agent system components.

### `tools/send_mailbox_message.py`

*   **Location:** `_agent_coordination/tools/send_mailbox_message.py`
*   **Purpose:** Sends a message JSON file directly to a target agent's mailbox directory. Useful for manual agent activation, testing, or system bootstrapping (as mentioned in `SUPERVISOR_ONBOARDING.md`, Capability 6).
*   **Arguments:**
    *   `--recipient <AGENT_NAME>`: (Required) Target agent's name.
    *   `--sender <SENDER_NAME>`: (Required) Name of the entity sending the message (e.g., `SupervisorTool`, `SystemOrchestrator`).
    *   `--payload-json "{...}"`: (Required) The message payload as a JSON string.
    *   `--mailbox-root <PATH>`: (Optional) Path to the root mailboxes directory (defaults to `runtime/mailboxes/` relative to `_agent_coordination`).
*   **Output:** Prints confirmation or error messages to stdout.
*   **Example Call:** `python _agent_coordination/tools/send_mailbox_message.py --recipient CursorControlAgent --sender SupervisorTool --payload-json "{\"command\": \"resume_operation\", \"reason\": \"Manual reactivation via tool.\"}"`

---

## Supervisor Utilities

These tools are specifically designed to assist with the advanced capabilities expected of the Supervisor role, focusing on project analysis, planning, monitoring, and validation. They are located in `_agent_coordination/supervisor_tools/`.

### 1. `supervisor_tools/check_project_structure.py`

*   **Purpose:** Audits the project structure against predefined expectations. Checks for the presence of key directories, critical system files, and `task_list.md` files within modules. Helps identify missing components or deviations from standard layout (Supports Supervisor Capability 1 & 5).
*   **Arguments:**
    *   `--root <PATH>`: (Optional) Project root directory to check (defaults to the parent of `_agent_coordination`).
*   **Output:** Prints a report to stdout listing found and missing components, highlighting issues with warnings.
*   **Example Call:** `python _agent_coordination/supervisor_tools/check_project_structure.py --root /d:/Dream.os`

### 2. `supervisor_tools/generate_module_task_list_template.py`

*   **Purpose:** Creates a standardized boilerplate `task_list.md` file within a specified module directory. Pre-fills the file with standard sections (Code Review, Testing, Documentation, etc.) to ensure consistency and provide a starting point for module-specific planning (Supports Supervisor Capability 2).
*   **Arguments:**
    *   `module_path`: (Required) Path to the target module directory (e.g., `../core`, `../agents/specific_agent`).
*   **Output:** Creates the `task_list.md` file in the target directory or prints a warning if it already exists. Prints confirmation or error messages to stdout.
*   **Example Call:** `python _agent_coordination/supervisor_tools/generate_module_task_list_template.py ../agents`

### 3. `supervisor_tools/summarize_agent_status.py`

*   **Purpose:** Provides a snapshot summary of agent status by scanning mailbox directories (`inbox`, `processed`, `error` counts) and optionally correlating with the last known task from `task_list.json`. Useful for quickly identifying potentially stalled, overloaded, or inactive agents.
*   **Arguments:**
    *   `--mailbox-root <PATH>`: (Optional) Path to the root mailboxes directory.
    *   `--task-list <PATH>`: (Optional) Path to the `task_list.json` file.
    *   `--format <cli|md>`: (Optional) Output format (default: `cli`).
*   **Output:** Prints a formatted report (CLI table or Markdown) summarizing message counts and last task details for each agent found.
*   **Example Call:** `python _agent_coordination/supervisor_tools/summarize_agent_status.py --format md`

### 4. `supervisor_tools/generate_task_list_from_code.py`

*   **Purpose:** Analyzes a Python source file and automatically generates a `task_list.md` containing actionable items based on found `# TODO` comments, `pass` statements, `NotImplementedError` exceptions, and empty function/method bodies. Helps bootstrap planning for existing or legacy code.
*   **Arguments:**
    *   `python_file`: (Required) Path to the Python source file to analyze.
    *   `--output <OUTPUT_MD_PATH>`: (Optional) Path to save the generated Markdown report. If omitted, prints to stdout.
*   **Output:** Prints the generated Markdown task list to stdout or saves it to the specified file.
*   **Example Call:** `python _agent_coordination/supervisor_tools/generate_task_list_from_code.py ../agents/some_agent.py --output ../agents/some_agent_task_list.md`

### 5. `supervisor_tools/task_list_status_report.py`

*   **Purpose:** Generates a comprehensive Markdown report summarizing the contents of `task_list.json`. Groups tasks by status, highlights tasks with missing required fields, calculates task age, and lists dependencies. Provides a high-level overview of the task backlog health.
*   **Arguments:**
    *   `--task-list <PATH>`: (Optional) Path to the `task_list.json` file.
    *   `--output <OUTPUT_MD_PATH>`: (Optional) Path to save the Markdown report. If omitted, prints to stdout.
    *   `--max-age-days <DAYS>`: (Optional) Only include tasks created within the last N days.
*   **Output:** Prints the generated Markdown report to stdout or saves it to the specified file.
*   **Example Call:** `python _agent_coordination/supervisor_tools/task_list_status_report.py --output weekly_report.md --max-age-days 7`

### 6. `supervisor_tools/validate_agent_onboarding.py`

*   **Purpose:** Checks for consistency between discovered agents (from mailboxes and `task_list.json`) and the onboarding documentation (`AGENT_ONBOARDING.md`). Verifies that agents have mailbox directories and are mentioned in the documentation. Helps prevent undocumented or orphaned agents (Supports Supervisor Capability 5).
*   **Arguments:**
    *   `--mailbox-root <PATH>`: (Optional) Path to the root mailboxes directory.
    *   `--task-list <PATH>`: (Optional) Path to the `task_list.json` file.
    *   `--onboarding-doc <PATH>`: (Optional) Path to the `AGENT_ONBOARDING.md` file (defaults to parent directory).
*   **Output:** Prints validation results to stdout, highlighting any inconsistencies found.
*   **Example Call:** `python _agent_coordination/supervisor_tools/validate_agent_onboarding.py`

### 7. `supervisor_tools/aggregate_task_lists.py`

*   **Purpose:** Scans the project directory recursively for all `task_list.md` files, parses Markdown checklist items (`- [ ]` or `- [x]`), and aggregates them into a single master JSON output file. Provides a unified view of all checklist tasks across the project.
*   **Arguments:**
    *   `--root <PROJECT_ROOT>`: (Optional) Project root directory to scan (defaults to the parent of `_agent_coordination`).
    *   `--output <OUTPUT_JSON_PATH>`: (Optional) Path to save the aggregated JSON file (defaults to `./master_task_list.json` in the current working directory).
*   **Output:** Creates a JSON file containing a list of task objects, each with a unique `task_id`, `description`, `status` (PENDING/COMPLETED), `source_file`, `module`, and aggregation timestamp. Prints progress and confirmation to stdout.
*   **Example Call:** `python _agent_coordination/supervisor_tools/aggregate_task_lists.py --output ../runtime/master_task_list.json`

---

*(TODO: Document other tools found in the tools/ directory, such as project_scanner.py, cursor_dispatcher.py, etc.)* 