# Agent Coordination Documentation

This directory contains essential documents for coordinating agent behavior and understanding system-wide protocols within the Dream.OS project.

Consult these documents to understand how agents should operate, communicate, and integrate within the broader system.

## Key Coordination Documents

*   **Rulebook:** [`rulebook.md`](/d:/Dream.os/_agent_coordination/rulebook.md)
    *   Defines core operational principles, constraints, and mandatory behaviors for all agents.
*   **Agent Stop Protocol:** [`agent_stop_protocol.md`](/d:/Dream.os/_agent_coordination/agent_stop_protocol.md)
    *   Specifies how agents should log pauses related to meta-rules or awaiting review.
*   **Main Task List:** [`/d:/Dream.os/tasks/task_list.md`](/d:/Dream.os/tasks/task_list.md)
    *   The primary high-level task list for the entire Dream.OS project.

## Guidelines & Logs

*   **Onboarding Guidelines:**
    *   `./logs/onboarding/supervisor_guidelines.md`
    *   `./logs/onboarding/social_agent_guidelines.md`
    *   *(Add other agent-specific guidelines here)*
*   **Governance Logs:**
    *   Stored in `/d:/Dream.os/core/memory/governance_memory.jsonl` (via `governance_memory_engine.py`)

## Notes

*   Maintain consistency across all related documentation.
*   Use absolute paths when referencing core documents from agent-specific task lists or onboarding materials.

## Key Areas:

- **/protocols**: Defines standard communication formats, message structures, and interaction patterns (e.g., file-based message bus).
- **/onboarding**: Provides agent-specific guidelines, role definitions, and initial setup instructions.
- **/rulebook** (Potential Future): A central location for overarching system rules and constraints.

## 🛠️ Available Tool Scripts (`tools/`)

These scripts provide helpful automation for common development and operational tasks within the Dream.OS framework. They can be executed directly or invoked by agents via the `run_terminal_cmd` capability.

### 1. `generate_agent_worker.py`

*   **Purpose:** Generates boilerplate agent worker files (`worker.py`) and their associated directory structures (`agents/agent_<id>/`, `memory/`, `mailbox/inbox/`, `mailbox/outbox/`).
*   **Usage:**
    ```bash
    python tools/generate_agent_worker.py --id <agent_id> --domain <AGENT_DOMAIN_ENUM> --caps <capability1> <capability2> ... [--force]
    ```
*   **Example:**
    ```bash
    python tools/generate_agent_worker.py --id 5 --domain UTILITY_AGENT --caps file_management script_execution --force
    ```

### 2. `inject_or_update_usage_block.py`

*   **Purpose:** Injects or updates the standard `if __name__ == "__main__":` example usage block into a target Python file. Aids in testing, onboarding, and demonstrating module capabilities.
*   **Usage:**
    ```bash
    python tools/inject_or_update_usage_block.py --target <path/to/python_file.py> [--force]
    ```
*   **Example:**
    ```bash
    python tools/inject_or_update_usage_block.py --target core/utils/file_manager.py --force
    ```

### 3. `run_agent_swarm.py`

*   **Purpose:** Launches and manages the AgentBus and specified agent worker processes using Python's `subprocess`. Provides a cross-platform way to start the swarm and handles graceful shutdown via Ctrl+C.
*   **Usage:**
    ```bash
    python tools/run_agent_swarm.py [--agents <id1> <id2> ... bus] [--debug-bus] [--debug-agents] [--skip-bus]
    ```
*   **Example (Run bus, agents 1 & 2 with debug):**
    ```bash
    python tools/run_agent_swarm.py --agents bus 1 2 --debug-bus --debug-agents
    ```

### 4. `check_component_integration.py`

*   **Purpose:** Performs basic static checks (using regex, with placeholders for AST analysis) to verify integration points between components, such as checking if an agent worker imports and uses a specific bridge class.
*   **Usage:**
    ```bash
    python tools/check_component_integration.py --worker-file <path/to/worker.py> [--check-import <module.path>] [--check-instantiation <ClassName>] [--instance-var <var_name>] [--check-call <var.method_name>]
    ```
*   **Example (Check Agent 2 uses bridge):**
    ```bash
    python tools/check_component_integration.py --worker-file agents/agent_2/worker.py --check-import core.execution.cursor_executor_bridge.CursorExecutorBridge --check-instantiation CursorExecutorBridge --instance-var bridge --check-call bridge.refactor_file
    ``` 