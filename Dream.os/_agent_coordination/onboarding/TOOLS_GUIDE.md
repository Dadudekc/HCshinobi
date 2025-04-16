# Dream.OS Tools Guide

This document provides guidance on the available tools within the `tools/` directory, intended for use by autonomous agents or developers.

## Usage Principles

- **Targeted Execution:** Use the most specific tool for the job.
- **Parameterization:** Utilize command-line arguments to control tool behavior where available.
- **Idempotency:** Tools should ideally be safe to run multiple times where applicable.
- **Logging:** Tools should provide clear console output indicating their actions and results.
- **Exit Codes:** Tools should use standard exit codes (0 for success, non-zero for failure or specific conditions).

---

## Agent Communication Tools

### 1. `tools/send_mailbox_message.py`

*   **Purpose:** Sends a structured JSON message to a specified agent's mailbox directory.
*   **Arguments:**
    *   `--recipient <agent_name>`: (Required) The name of the agent receiving the message.
    *   `--payload-json "<json_string>"`: (Required) A valid JSON string representing the message payload (the content the recipient agent will process). Example: `--payload-json "{\"command\": \"status_request\", \"details\": \"Provide current task ID.\"}"` (Note the escaped quotes required when passing JSON via CLI).
    *   `--sender <agent_name>`: (Optional) The name of the agent sending the message. Defaults to `UnknownSender`.
    *   `--mailbox-root <path>`: (Optional) Path to the root `mailboxes/` directory. Defaults to the `mailboxes` directory located as a sibling to the `tools` directory.
*   **Output:** Logs success or failure messages to stdout/stderr.
*   **File Output:** Creates a `msg_<uuid>.json` file in the `<mailbox_root>/<recipient>/inbox/` directory. The file contains the specified payload along with standard envelope fields (`message_id`, `sender_agent`, `timestamp_dispatched`).
*   **Exit Codes:**
    *   `0`: Message sent successfully.
    *   `1`: Failure (e.g., invalid JSON payload, directory creation error, file write error).
*   **Agent Usage:** Useful for direct agent-to-agent communication or for sending specific notifications/requests not tied to a standard task list item. Can be invoked via `CursorTerminalController.run_command`.
*   **Example Call:** `python tools/send_mailbox_message.py --recipient SupervisorAgent --sender CursorControlAgent --payload-json "{\"event\": \"task_failed\", \"task_id\": \"dev_xyz\", \"reason\": \"Missing dependency\"}"`

---

## Code Generation & Manipulation Tools

### 2. `tools/code_applicator.py`

*   **Purpose:** Applies provided code content to a target file using various modes.
*   **Arguments:**
    *   `--target-file <path>`: (Required) Path to the target file.
    *   Input Source (Exactly ONE Required):
        *   `--code-input <string>`: Code content as a direct string.
        *   `--code-file <path>`: Path to a file containing the code.
        *   `--code-stdin`: Read code content from standard input.
    *   `--mode {overwrite|replace_markers|append}`: (Optional) Application mode. Default: `overwrite`.
    *   `--create-dirs`: (Optional Flag) Create parent directories for `--target-file` if missing.
    *   `--backup`: (Optional Flag) Create a `.bak` backup of the original file before modifying.
    *   `--start-marker <string>`: (Optional) Custom start marker for `replace_markers` mode. Default: `# CODE_APPLICATOR_START`.
    *   `--end-marker <string>`: (Optional) Custom end marker for `replace_markers` mode. Default: `# CODE_APPLICATOR_END`.
    *   `-v`, `--verbose`: (Optional Flag) Enable DEBUG level logging.
*   **Output:** Logs actions and results to stdout/stderr.
*   **File Output:** Modifies or creates the `--target-file`.
*   **Exit Codes:**
    *   `0`: Code applied successfully.
    *   `1`: Failure (e.g., invalid arguments, file errors, marker errors, write errors).
*   **Agent Usage:** Essential for agents performing code generation. After obtaining generated code (e.g., from Cursor output, potentially saved to a temp file or clipboard), an agent can use this tool via `run_command` to apply it. Adheres to ONB-001 by performing a real action.
*   **Example Calls:**
    *   `python tools/code_applicator.py --target-file path/to/new_file.py --code-file /tmp/generated.py --create-dirs --backup`
    *   `python tools/code_applicator.py --target-file path/to/existing.py --code-input "print('Appended')" --mode append`
    *   `echo "New content" | python tools/code_applicator.py --target-file path/to/replace.py --code-stdin --mode replace_markers`

---

## Recovery & Diagnostics Tools

These tools are primarily invoked by agents like `CursorControlAgent` in response to recovery tasks dispatched by the `TaskDispatcher`.

### 3. `tools/check_confirmation_state.py`

*   **Purpose:** Simulates checking the system state to determine if explicit user confirmation is required before proceeding with a potentially sensitive or ambiguous action.
*   **Arguments:**
    *   None currently implemented (can be extended, e.g., `--context-file <path>`)
*   **Output:** Prints status messages to stdout.
*   **Exit Codes:**
    *   `0`: Confirmation NOT required; safe to proceed.
    *   `1`: Confirmation REQUIRED.
*   **Agent Usage:** Used by `CursorControlAgent`'s `_handle_confirmation_check` method. The agent should treat exit code `1` as a failure for the handler, indicating the need for escalation or clarification.
*   **Example Call:** `python tools/check_confirmation_state.py`

### 4. `tools/reload_agent_context.py`

*   **Purpose:** Simulates reloading the operational context or memory for a specified agent.
*   **Arguments:**
    *   `--target <agent_name>`: (Required) The name of the agent whose context should be reloaded.
*   **Output:** Prints status messages to stdout.
*   **Exit Codes:**
    *   `0`: Simulated context reload successful.
    *   `1`: Simulated context reload failed.
*   **Agent Usage:** Used by `CursorControlAgent`'s `_handle_context_reload` method. The target agent name is typically passed from the task parameters.
*   **Example Call:** `python tools/reload_agent_context.py --target CursorControlAgent`

### 5. `tools/diagnostics.py`

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

### 6. `tools/project_context_producer.py`

*   **Purpose:** Analyzes conversation logs and project files to generate a context summary (`agent_bridge_context.json`), often used by `StallRecoveryAgent` to categorize stalls and identify relevant files.
*   **Arguments (as a module):** The `produce_project_context` function takes:
    *   `conversation_log (str)`: The log content to analyze.
    *   `project_dir_str (str)`: Path to the project root.
    *   `return_dict (bool)`: If True, returns context as dict instead of writing to file (default: False).
*   **Output:** Writes `agent_bridge_context.json` to the project root or returns a dictionary.
*   **Agent Usage:** Imported and used by `StallRecoveryAgent` during stall analysis.
*   **Example Call (as script, if __main__ enabled):** `python tools/project_context_producer.py "...log snippet..." .` (Requires adapting the script to take CLI args if run directly).

---

*(TODO: Document other tools found in the tools/ directory, such as project_scanner.py, cursor_dispatcher.py, etc.)* 