# Project Finalization Task List (Current Version)

## I. Task Dispatching & Routing (`TaskDispatcherAgent`)

-   [ ] **Verify `TaskDispatcherAgent` Refactor:** Confirm the `_dispatch_task` and `_infer_target_agent` methods in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` are functioning correctly within the `async` environment.
-   [ ] **Confirm AgentBus Integration:** Ensure tasks are successfully dispatched as events using `agent_bus.dispatch_event`. Monitor logs for confirmation. (Relevant code primarily in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`)
-   [ ] **Test Agent Inference:** Inject a task with a known `task_type` but *without* a `target_agent`. Verify the dispatcher correctly infers the agent and dispatches the task. Check logs and `/d:/Dream.os/runtime/task_list.json` for `target_agent` field update.
-   [ ] **Test Dispatch Failure (Unknown Type):** Inject a task with an unknown `task_type`. Verify the dispatcher logs a warning and marks the task as `FAILED` with an appropriate error message in `/d:/Dream.os/runtime/task_list.json`.
-   [ ] **Test Dispatch Failure (AgentBus Issue):** Simulate `AGENT_BUS_AVAILABLE = False` (if possible) or an error during `agent_bus.dispatch_event` in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`. Verify the task is marked as `FAILED`.
-   [ ] **Review Status Updates:** Ensure `_update_task_status` in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` correctly reflects `PENDING`, `PROCESSING`, `DISPATCHED`, and `FAILED` states in `/d:/Dream.os/runtime/task_list.json`. Check `timestamp_updated` and `error`/`result` fields.

## II. Task Monitoring (`TaskListVisualizer`)

-   [ ] **Launch & Connect Visualizer:** Run `python /d:/Dream.os/tools/task_list_visualizer.py`. Confirm it opens and attempts to load `/d:/Dream.os/runtime/task_list.json`.
-   [ ] **Verify Real-time Refresh:** Observe if the visualizer automatically updates when `/d:/Dream.os/runtime/task_list.json` changes.
-   [ ] **Test Status Filtering:** Use the dropdown filter (`All`, `PENDING`, `PROCESSING`, etc.) and confirm the displayed tasks are filtered correctly.
-   [ ] **Confirm Data Display:** Check if `task_id`, `status`, `task_type`, `target_agent`, and `timestamp` are displayed correctly in the visualizer table.

## III. End-to-End Testing & Validation

-   [ ] **Full Lifecycle Test (Inferred Agent):**
    -   Inject a `PENDING` task (e.g., `task_type: "resume_operation"`) with no `target_agent` into `/d:/Dream.os/runtime/task_list.json`.
    -   Observe `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` logs for inference and dispatch.
    -   Observe `/d:/Dream.os/tools/task_list_visualizer.py` showing status change: `PENDING` -> `PROCESSING` -> `DISPATCHED`.
    -   *(Optional: Verify target agent receives the task event via AgentBus logs, potentially originating from `/d:/Dream.os/_agent_coordination/core/agent_bus.py` or similar).*
-   [ ] **Full Lifecycle Test (Explicit Agent):**
    -   Inject a `PENDING` task with an explicit `target_agent` into `/d:/Dream.os/runtime/task_list.json`.
    -   Repeat observation steps above.
-   [ ] **Concurrency Test (Basic):** Inject multiple `PENDING` tasks quickly into `/d:/Dream.os/runtime/task_list.json`. Observe if the dispatcher (`/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`) processes them without file locking errors or race conditions in status updates.

## IV. Code Quality & Documentation

-   [ ] **Review Logging:** Ensure logs from `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` are clear, informative, and capture key events.
-   [ ] **Review Error Handling:** Check robustness of file I/O and AgentBus interactions within `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`.
-   [ ] **Add/Update Docstrings:** Ensure `TaskDispatcherAgent` methods (`_dispatch_task`, `_infer_target_agent`, `_update_task_status`) in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` have clear docstrings. Add a module-level docstring.
-   [ ] **Update `TaskListVisualizer` Docstrings:** Add necessary documentation for `/d:/Dream.os/tools/task_list_visualizer.py`.
-   [ ] **Update Project README/Docs:** Add a section explaining the task dispatch mechanism (referencing `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`) and how to use `/d:/Dream.os/tools/task_list_visualizer.py`.

## V. Finalization & Versioning

-   [ ] **Commit Final Code:** Ensure all changes (e.g., `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`, `/d:/Dream.os/tools/task_list_visualizer.py`) are committed.
-   [ ] **(Optional) Tag Version:** Create a Git tag.
-   [ ] **(Optional) Push Changes:** Push commits and tags. 