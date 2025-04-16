# Task List: docs Module (`/d:/Dream.os/docs/`)

Tasks focused on updating and creating project documentation.

## I. Core System Documentation

-   [ ] **Task Dispatcher:** Document the refactored `TaskDispatcherAgent` (`/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`), including:
    -   Agent inference logic (`_infer_target_agent`).
    -   Usage of `AgentBus` for event dispatch (`_dispatch_task`).
    -   Task status updates (`PENDING`, `PROCESSING`, `DISPATCHED`, `FAILED`).
    -   File locking mechanism (`portalocker`) for `/d:/Dream.os/runtime/task_list.json`.
-   [ ] **AgentBus:** Document the `AgentBus` (`/d:/Dream.os/_agent_coordination/core/agent_bus.py` or similar):
    -   Core concepts (events, pub/sub, registration).
    -   Standard `Event` structure and common `EventType`s (e.g., `TASK`, `DIRECTIVE`, social events).
    -   How agents should register and subscribe.
-   [ ] **Task List (`task_list.json`):** Document the structure and fields of `/d:/Dream.os/runtime/task_list.json`.
    -   Explain the meaning of each status (`PENDING`, `PROCESSING`, `DISPATCHED`, `FAILED`, `COMPLETED`, `ERROR`).
    -   Provide examples of different task types.
-   [ ] **TaskListVisualizer:** Document the usage of the visualizer tool (`/d:/Dream.os/tools/task_list_visualizer.py`).
    -   How to launch it.
    -   Features (filtering, auto-refresh).
    -   Expected data source (`/d:/Dream.os/runtime/task_list.json`).

## II. Architecture & Guides

-   [ ] **Update Architecture Diagram:** Modify diagrams to accurately reflect the role of `TaskDispatcherAgent` and `AgentBus` in the task flow.
-   [ ] **Developer Guide:** Add/update sections on:
    -   Creating new agents and integrating them with `AgentBus`.
    -   Adding new task types and updating the inference map.
    -   Debugging task execution using logs and the visualizer.
-   [ ] **User Guide (If Applicable):** Document how to interact with the system or monitor its status, potentially referencing the visualizer.

## III. Review & Maintenance

-   [ ] **Review Existing Docs:** Check all existing documentation for accuracy following recent refactoring.
-   [ ] **Fix Broken Links:** Ensure all internal/external links are valid.
-   [ ] **Improve Readability:** Refine formatting and structure for clarity.

## IV. Finalization

-   [ ] Commit all documentation changes.
-   [ ] Ensure documentation accurately reflects the current state of the codebase. 