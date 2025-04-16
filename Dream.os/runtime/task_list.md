# Task List: runtime Module (`/d:/Dream.os/runtime/`)

Tasks related to runtime data, state management, and persistent files.

## I. Task List (`task_list.json`)

-   [ ] **Verify Path:** Confirm `/d:/Dream.os/runtime/task_list.json` is the definitive path used by all components (Dispatcher, Visualizer, potentially Agents for updates).
-   [ ] **Schema Definition/Validation:**
    -   [ ] Formally define the expected JSON schema for a task entry.
    -   [ ] Implement validation checks when reading/writing tasks (e.g., required fields, data types) either in `_read/write_task_list` or upon task creation.
-   [ ] **Archiving/Rotation:**
    -   [ ] Design a strategy for managing the size of `task_list.json` (e.g., moving completed/failed tasks older than X days to an archive file).
    -   [ ] Implement the archiving/rotation logic (potentially as a separate utility script or agent task).
-   [ ] **Status Update Mechanism:**
    -   [ ] Clarify and document how agents update task status to `COMPLETED` or `FAILED` (e.g., Do they write directly? Send an `AgentBus` event? Use a shared utility?).
    -   [ ] Ensure the update mechanism uses file locking (`portalocker`) if direct writes occur.

## II. Other Runtime Data

-   [ ] **Identify Other Files:** Review other files stored in `/d:/Dream.os/runtime/` (e.g., agent state, logs if stored here).
-   [ ] **Review Formats:** Ensure data formats are efficient and well-defined.
-   [ ] **Consistency Checks:** Verify naming conventions and usage patterns for runtime files.

## III. Robustness

-   [ ] **Error Handling:** Ensure robust error handling for file I/O operations within this directory (e.g., permissions, disk full, corrupt files).
-   [ ] **Backup Strategy (Optional):** Consider if a backup mechanism for critical runtime data (like `task_list.json`) is needed.

## IV. Finalization

-   [ ] Commit any changes to runtime data handling logic.
-   [ ] Ensure runtime data structures are stable and documented. 