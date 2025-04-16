# Task List: tests Module (`/d:/Dream.os/tests/`)

Tasks focused on testing the core system components, especially recent changes.

## I. Task Dispatching & Coordination Tests

-   [ ] **`TaskDispatcherAgent` Integration Tests:**
    -   [ ] Test task injection (`PENDING` -> `PROCESSING` -> `DISPATCHED`) with explicit `target_agent`.
    -   [ ] Test task injection (`PENDING` -> `PROCESSING` -> `DISPATCHED`) with inferred `target_agent` (verify inference logic).
    -   [ ] Test task injection resulting in `FAILED` status (unknown `task_type`).
    -   [ ] Test task injection resulting in `FAILED` status (inference fails).
    -   [ ] Test task injection resulting in `FAILED` status (mocked `AgentBus` dispatch error).
    -   *Requires mocking `AgentBus` and file I/O (`_update_task_status`).*
-   [ ] **`_infer_target_agent` Unit Tests:** Add unit tests specifically for the inference map logic in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`.
-   [ ] **File Locking Tests:** Add tests to simulate concurrent access to `/d:/Dream.os/runtime/task_list.json` to ensure `portalocker` prevents race conditions during status updates.
-   [ ] **`AgentBus` Tests:**
    -   [ ] Test agent registration/unregistration.
    -   [ ] Test event dispatching and subscription (point-to-point and potentially broadcast if used).
    -   [ ] Test error handling within the `AgentBus`.

## II. Agent Task Handling Tests

-   [ ] **Agent Event Reception:** For key agents (`CursorControlAgent`, etc.), add tests to verify they correctly receive `EventType.TASK` events from a mocked `AgentBus`.
-   [ ] **Task Payload Parsing:** Test agents' ability to parse task details (`action`, `params`) from the event payload.
-   [ ] **Task Status Update Tests:** Test the mechanism agents use to report `COMPLETED`/`FAILED` status back to `/d:/Dream.os/runtime/task_list.json` (mocking the update mechanism).

## III. Visualizer Tests (Optional)

-   [ ] **Basic UI Tests:** *(Low Priority)* If feasible, add simple tests to check if `/d:/Dream.os/tools/task_list_visualizer.py` launches and displays the main elements.
-   [ ] **Data Loading Test:** Test the `load_tasks` function in the visualizer, mocking `/d:/Dream.os/runtime/task_list.json` with various valid/invalid contents.

## IV. Test Infrastructure & Maintenance

-   [ ] **Review Test Coverage:** Analyze test coverage for critical modules (`_agent_coordination`, `agents`) and add tests where needed.
-   [ ] **Refactor Existing Tests:** Update any existing tests affected by the `AgentBus` integration or dispatcher refactor.
-   [ ] **CI Integration:** Ensure all tests run correctly in the Continuous Integration environment (if applicable).

## V. Finalization

-   [ ] Commit all new or updated test code.
-   [ ] Ensure all tests are passing reliably. 