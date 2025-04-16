# Agent Coordination Module Task List

This list focuses on tasks specific to the `_agent_coordination` module, particularly the `TaskDispatcherAgent` and its interactions.

## I. `TaskDispatcherAgent` Functionality (`/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`)

-   [ ] **Verify Async `_dispatch_task`:** Confirm the refactored `_dispatch_task` method runs correctly within the `async` loop (`_process_pending_tasks`).
-   [ ] **Verify `_infer_target_agent` Logic:** Ensure the routing map is correct and the inference mechanism functions as expected when `target_agent` is missing.
-   [ ] **Confirm AgentBus Event Dispatch:** Verify that `agent_bus.dispatch_event` is called correctly with the appropriate `Event` structure (type `EventType.TASK`, correct `source_id`, and `data` payload).
-   [ ] **Test `_update_task_status` Integration:** 
    -   Check successful update to `PROCESSING` before dispatch attempt.
    -   Check successful update to `DISPATCHED` after event dispatch.
    -   Check successful update to `FAILED` if agent inference fails.
    -   Check successful update to `FAILED` if `agent_bus.dispatch_event` fails or `AGENT_BUS_AVAILABLE` is false.
    -   Confirm details (`error` message) are correctly added on failure.
-   [ ] **Verify File Locking (`portalocker`):** Review `_read_task_list`, `_write_task_list`, and `_update_task_status` (which likely uses write) to ensure `portalocker` is used correctly to prevent race conditions when accessing `/d:/Dream.os/runtime/task_list.json`.

## II. AgentBus Interaction (Core & Dispatcher)

-   [ ] **Verify AgentBus Availability Check:** Confirm the `if not AGENT_BUS_AVAILABLE:` check in `_dispatch_task` works correctly.
-   [ ] **(Optional) Trace Event Handling:** If possible, trace the `EventType.TASK` event dispatched by `TaskDispatcherAgent` through the `AgentBus` (potentially `/d:/Dream.os/_agent_coordination/core/agent_bus.py`) to the intended recipient agent.

## III. Testing within `_agent_coordination`

-   [ ] **Unit/Integration Tests (Dispatcher):** 
    -   *(Consider)* Add tests specifically for `_infer_target_agent`.
    -   *(Consider)* Add tests for `_dispatch_task`, mocking `agent_bus` and file system interactions to verify status updates and event creation under different scenarios (inference success/fail, dispatch success/fail).

## IV. Code Quality & Documentation (`_agent_coordination`)

-   [ ] **Review Logging:** Ensure logs within `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` and potentially core AgentBus components are sufficient for debugging coordination issues.
-   [ ] **Review Error Handling:** Focus on error handling surrounding `agent_bus.dispatch_event` calls and file I/O within the dispatcher.
-   [ ] **Add/Update Docstrings:** Ensure all public methods and classes within the dispatcher (`/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`) and relevant core components (like `AgentBus` if modified) have comprehensive docstrings.
-   [ ] **Module README:** Consider adding or updating a `README.md` within `/d:/Dream.os/_agent_coordination/` explaining the purpose of this module, especially the role of the dispatcher and the AgentBus.

## V. Finalization

-   [ ] **Commit Module Code:** Ensure all changes within `/d:/Dream.os/_agent_coordination/` are committed. 