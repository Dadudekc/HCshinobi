# Onboarding Notes: Agent Analysis Philosophy & Recent Exploration

This document outlines the reasoning and methodology used during the analysis of the `_agent_coordination` project structure and the `agent_1/worker.py` implementation, serving as a guide for understanding the system's components and how we approach discovery.

## Context Switching & Initial Discovery

*   **Trigger:** Analysis shifted from the `social` sub-project when exploration of its components seemed complete or when higher-level interactions needed investigation. The focus moved to the sibling directory `_agent_coordination`, suspected to contain shared or orchestrating logic.
*   **Methodology:**
    *   The `list_dir` tool was used on the target directory (`_agent_coordination`) to get a high-level overview of its contents (`agents/`, `core/`, etc.). *(Note: This step initially faced path issues due to workspace context, highlighting the need to be mindful of the current working directory/scope).*
    *   Based on the structure (`agents/agent_1`, `agents/agent_2`, ...), we hypothesized that each numbered subdirectory contained a distinct agent implementation.
    *   `list_dir` was used again on `_agent_coordination/agents/agent_1` to identify specific files. The presence of `worker.py` strongly suggested it was the primary implementation file for `agent_1`.

## Deep Dive into `agent_1/worker.py`

*   **Objective:** Understand the functionality, communication patterns, and dependencies of `agent_1`.
*   **Tool Selection:**
    *   Initially, the standard file reading tool would be preferred.
    *   However, due to observed context limitations (tool potentially restricted to the `social` workspace), an alternative approach was necessary.
    *   The `run_terminal_cmd` tool with `Get-Content` (or `cat` on Linux/macOS) was employed as a robust fallback to read the file content directly via the shell, demonstrating flexibility when standard tools face constraints.
*   **Analysis Process:**
    1.  **Identify Core Components:** The code was broken down into logical sections: Initialization (`__init__`), Context Management, Task Management, Agent Bus Interaction, Mailbox Handling, Task Execution (`_execute_task`), Main Loop (`run`), and Shutdown.
    2.  **Communication Patterns:** We specifically looked for how the agent interacts with other parts of the system. Key findings included:
        *   **Hybrid Model:** Uses *both* the `AgentBus` (registration, status, events) *and* a file-based mailbox (`inbox`). This differs significantly from agents in the `social` project.
        *   **Bus Integration:** Leverages `core.agent_bus` and concepts from `dreamos.coordinator`.
        *   **Mailbox Usage:** Polled for specific directives (`shutdown_directive`, `task_assignment`).
    3.  **Task Handling:** Noted the agent maintains its own `task_list.json`, processing tasks retrieved from it, contrasting with agents that might only receive tasks via the bus.
    4.  **Specialized Logic:** The unique handling of the `inject_usage_block` task, relying on dispatching events via `dispatch_usage_block_update`, was highlighted as an important interaction pattern, likely involving a coordinating agent.
    5.  **Dependencies:** Imports revealed dependencies on `core.agent_bus`, `core.utils.*`, and the external `dreamos.coordinator` package/module.
*   **Key Takeaway:** `agent_1/worker.py` represents a more complex, potentially foundational agent pattern within the `_agent_coordination` system compared to the simpler, more specialized agents examined previously in the `social` project.

## "Outside the Box" Best Practices Demonstrated

*   **Adaptability:** Recognizing tool limitations (like file access constraints) and switching to alternative methods (`run_terminal_cmd`) to achieve the goal.
*   **Hypothesis-Driven Exploration:** Making educated guesses based on directory/file naming conventions (`worker.py` likely being the main file) to guide exploration efficiently.
*   **Structured Analysis:** Breaking down complex files into logical components to understand functionality systematically.
*   **Comparative Analysis:** Contrasting the observed patterns (`agent_1`) with previously analyzed components (`social` agents) to identify key architectural differences and potential roles.
*   **Focus on Interactions:** Prioritizing the understanding of how a component communicates and integrates with the wider system (AgentBus, mailbox, file I/O).

This iterative process of discovery, hypothesis, targeted analysis, and adaptation allows for effective exploration even in unfamiliar or complex codebases.

## Exploring `_agent_coordination/core`

*   **Objective:** Identify shared components, particularly the `AgentBus` implementation.
*   **Methodology:**
    *   Used `run_terminal_cmd` with `Get-ChildItem .\_agent_coordination\core` (adjusted from `ls` for PowerShell compatibility and to handle directories correctly) to list directory contents.
    *   Identified key files (`agent_bus.py`, `__init__.py`) and subdirectories (`coordination`, `execution`, `refactoring`, `utils`).
*   **Inference:** The structure suggests `agent_bus.py` is the main bus interface, delegating specific functionalities to modules within the subdirectories (`coordination`, etc.) and using shared functions from `utils`.
*   **Next Step:** Analyze `_agent_coordination/core/agent_bus.py`.

## Analysis of `_agent_coordination/core/agent_bus.py`

*   **Objective:** Understand the implementation and role of the central `AgentBus`.
*   **Methodology:** Used `run_terminal_cmd` with `Get-Content` to read the file.
*   **Key Findings:**
    *   Confirmed `AgentBus` acts as a central hub/façade.
    *   **Modular Design:** Imports and initializes components for specific responsibilities:
        *   `EventDispatcher` (`core.coordination.dispatcher`): Manages event queue and handler dispatch.
        *   `AgentRegistry` (`core.agent_registry`): Intended for agent registration/status/capability tracking (though some logic currently resides directly in `AgentBus`).
        *   `SystemDiagnostics` (`core.system_diagnostics`): Performs system health checks.
        *   `ShutdownCoordinator` (`core.shutdown_coordinator`): Manages graceful shutdown.
        *   `Utils` (`core.utils`): Provides file/system utilities.
    *   **Event-Driven:** Relies heavily on an event system (`EventType`, `Event`, `register_handler`). Dispatches system events for agent lifecycle changes (register, unregister, status update).
    *   **API:** Provides methods for agent management (`register_agent`, `update_agent_status`, `get_available_agents`) and event handling (`register_handler`).
    *   **Lifecycle Management:** Handles agent registration, status tracking (Idle, Busy, Error, ShutdownReady), and coordinated shutdown via signals and dedicated coordinator component.
    *   **Global Singleton:** Instantiated as `agent_bus` for global access within the project.
    *   **Debugging Support:** Includes a comprehensive `__main__` block demonstrating usage patterns, event flow, and error handling.
*   **Inference:** This is a sophisticated, event-driven bus designed for coordinating multiple agents with distinct capabilities, including robust lifecycle and shutdown management.
*   **Next Step Options:** Investigate modular components (`EventDispatcher`, `AgentRegistry`, `ShutdownCoordinator`), utilities (`utils`), or another agent.

## Analysis of `_agent_coordination/core/coordination/dispatcher.py`

*   **Objective:** Understand the event handling mechanism.
*   **Methodology:** Listed contents of `core/coordination/` directory and read `dispatcher.py` using terminal commands.
*   **Key Findings:**
    *   Defines `EventType` Enum (`CURSOR`, `CHAT`, `SYSTEM`) and base `Event` class (with `type`, `source_id`, `priority`, `timestamp`).
    *   `EventDispatcher` class manages event flow:
        *   Uses `asyncio.PriorityQueue` for event queuing, prioritizing lower numerical priority values and using timestamps as tie-breakers.
        *   `register_handler(event_type, handler)` allows subscription to specific event types.
        *   `dispatch_event(event)` adds an event to the queue.
        *   An asynchronous background task (`_process_events`) dequeues events and calls registered handlers sequentially based on priority.
        *   Includes error handling for individual handlers.
*   **Inference:** A standard async priority event queue implementation, decoupling event producers and consumers. Core to the bus's operation.
*   **Next Step Options:** Investigate other coordination components (`config_service.py`, `path_manager.py`), other core modules (`agent_registry`, `shutdown_coordinator`, `utils`), or another agent.

## Investigating Import Discrepancies & Pivoting to `core/utils`

*   **Observation:** Attempting to locate `core/shutdown_coordinator.py` based on the import `from .shutdown_coordinator import ...` in `agent_bus.py` failed. File not found.
*   **Verification:** Grep search for `class ShutdownCoordinator` within `core/` yielded no results. Testing for `core/agent_registry.py` (also imported via `from .agent_registry import ...`) confirmed it also doesn't exist at that location.
*   **Hypothesis:** The imports for modular components (`.agent_registry`, `.shutdown_coordinator`, `.system_diagnostics`, `.bus_types`) within `core/agent_bus.py` do not align with the observed file structure in `_agent_coordination/core`. This suggests `agent_bus.py` might be from a different version, incomplete, or part of a larger package structure (e.g., `dreamos`) where those files would be siblings.
*   **Strategy Change:** Since the modular components referenced by relative paths in `agent_bus.py` seem missing, focus shifts to exploring components with confirmed existence and usage, like the `core/utils` directory.
*   **Methodology:** Listed contents of `core/utils` using `Get-ChildItem`. Identified several potentially useful modules: `file_manager.py`, `system.py`, `agent_helpers.py`, `logging.py`, etc.
*   **Next Step:** Analyze `_agent_coordination/core/utils/file_manager.py` as file operations are common.

## The Case of the Missing `FileManager`

*   **Observation:** Despite `agent_1/worker.py` and `agent_bus.py` both importing `from core.utils.file_manager import FileManager`, attempts to locate this file within `_agent_coordination/core/utils/` failed:
    *   `Get-ChildItem` did not list `file_manager.py`.
    *   `Test-Path` reported `__init__.py` as non-existent in that directory.
    *   `grep` search for `class FileManager` within existing `.py` files (`agent_helpers.py`, `base.py`, etc.) in `core/utils` yielded no results.
*   **Hypothesis:** The `core.utils.file_manager` module likely exists *outside* the `_agent_coordination` directory structure but is accessible via Python's `sys.path`. This could be a shared `core` library located elsewhere (e.g., in a parent directory, or part of the `dreamos` package).
*   **Implication:** Analysis is currently limited by dependencies residing outside the visible project scope (`social/` and `_agent_coordination/`).
*   **Strategy:** Proceed by analyzing existing files within `core/utils`, such as `system.py`, while keeping in mind the external dependency on `FileManager`.
*   **Next Step:** Analyze `_agent_coordination/core/utils/system.py`.

## Analysis of `_agent_coordination/core/utils/system.py`

*   **Objective:** Understand available system-level utilities.
*   **Methodology:** Read file content using `Get-Content`.
*   **Key Findings:**
    *   **`FileManager` Found:** Defines the `FileManager` class, solving the earlier import mystery. The class was likely exposed via `core/utils/__init__.py`.
        *   Provides async methods (`safe_read`, `safe_write`, `safe_move`, `safe_copy`, `safe_delete`).
        *   Uses `RetryManager` (from `.base`) for robust, retrying file operations.
    *   **`CommandExecutor`:**
        *   Provides `async run_command` using `asyncio.create_subprocess_exec`.
        *   Captures stdout/stderr, returns structured `CommandResult`.
        *   Includes timeout and retry logic (via `RetryManager`).
    *   **`DirectoryMonitor`:**
        *   Async polling mechanism to watch a directory (`watch_dir`).
        *   Processes files found via an abstract `process_file` method.
        *   Moves processed files to `success_dir` or `error_dir` with timestamps.
    *   **Core Themes:** Emphasis on async operations and resilience through built-in retry mechanisms (`RetryManager`).
*   **Inference:** Provides robust, reusable, async building blocks for agents needing to interact with the file system, execute commands, or monitor directories.
*   **Next Step Options:** Analyze `core/utils/base.py` (for `RetryManager`), `core/utils/agent_helpers.py`, other core modules, or another agent.

## Analysis of `_agent_coordination/core/utils/base.py`

*   **Objective:** Understand base utilities, particularly the `RetryManager`.
*   **Methodology:** Read file content using `Get-Content`.
*   **Key Findings:**
    *   **`RetryManager` Class:**
        *   Implements the retry logic used by `FileManager` and `CommandExecutor`.
        *   Uses exponential backoff (`base_delay * (exponential_base ** attempt)`) capped by `max_delay` between retries.
        *   Configurable via `max_retries`, delays, and exponential base.
        *   `execute(func, ...)` method wraps an async function call with this retry logic.
    *   **Other Utilities:**
        *   `Singleton` metaclass.
        *   `AsyncLockManager`: Async context manager for `asyncio.Lock` with timeout.
        *   `Cache`: Generic async cache with optional TTL.
        *   `generate_id()`: UUID-based unique ID generator.
        *   Basic *synchronous* JSON load/save functions (`load_json_file`, `save_json_file`).
        *   `ValidationError` exception and basic validation helper functions (`validate_required_fields`, `validate_field_type`).
*   **Inference:** Provides common programming patterns and the core resilience mechanism (`RetryManager`) for other utilities.
*   **Next Step Options:** Analyze `core/utils/agent_helpers.py`, other `core/utils` files (`logging.py`, `metrics.py`), other core modules, or another agent (e.g., `agent_2`).

## Analysis of `_agent_coordination/core/utils/agent_helpers.py`

*   **Objective:** Understand helper functions used by agents.
*   **Methodology:** Read file content using `Get-Content`.
*   **Key Findings:**
    *   Defines `dispatch_usage_block_update(agent_id, target_file, status, ..., task_id)`:
        *   Used by `agent_1/worker.py` for the `inject_usage_block` task type.
        *   Abstracts away the dispatching of multiple related events after a usage block operation.
        *   Dispatches three distinct events using `agent_bus._dispatcher.dispatch_event`:
            1.  `SYSTEM` event (`type: usage_block_status`): Detailed log of the operation result.
            2.  `TASK` event (`type: task_update`): Updates the overall task status (`complete` or `error`). Confirms existence of `EventType.TASK`.
            3.  `SYSTEM` event (`type: project_board_update`): High-level status update for monitoring/UI (e.g., `present_and_validated`).
*   **Inference:** Provides standardized ways for agents to report complex operation results via multiple coordinated events, simplifying agent logic.
*   **Next Step Options:** Analyze other `core/utils` files (`logging.py`, `metrics.py`), other core modules, or another agent (e.g., `agent_2`).

## Analysis of `_agent_coordination/core/utils/logging.py`

*   **Objective:** Understand the logging setup.
*   **Methodology:** Read file content using `Get-Content`.
*   **Key Findings:**
    *   **`LogManager` (Singleton):** Manages global logging configuration.
        *   `configure()` sets up console (`StreamHandler`) and rotating file (`RotatingFileHandler`) handlers.
        *   Configurable levels, log directory, file size, backup count.
    *   **`LogFormatter`:** Custom formatter used for file handler.
        *   Outputs logs in **JSON format**.
        *   Includes standard fields plus component (via LoggerAdapter), error location, exception info, and arbitrary `extra` data.
    *   **`get_logger(name, component)`:** Convenience function to get a logger instance.
        *   Uses `sys._getframe` to default `name` to the calling module's name.
        *   Optionally wraps logger in `LoggerAdapter` to add `component` context to JSON logs.
*   **Inference:** Provides a robust, centralized, and configurable logging system emphasizing structured (JSON) logging for better machine readability and analysis.
*   **Next Step Options:** Analyze `core/utils/metrics.py`, other core modules, or another agent (e.g., `agent_2`). 