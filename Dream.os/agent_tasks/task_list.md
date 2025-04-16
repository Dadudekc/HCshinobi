# Task List: agent_tasks Module (`/d:/Dream.os/agent_tasks/`)

Tasks related to defining, structuring, and managing agent task types and schemas.

## I. Task Schema Definition

-   [ ] **Standardize Task Structure:** Formally define the common JSON schema for all tasks stored in `/d:/Dream.os/runtime/task_list.json` (e.g., `task_id`, `task_type`, `status`, `params`, `target_agent`, timestamps, `priority`, `dependencies`).
-   [ ] **Define Specific Task Payloads:** For each `task_type` used by the system (e.g., `resume_operation`, `diagnose_loop`, `generate_task`, social tasks), define the expected structure and fields within the `params` object.
-   [ ] **Schema Validation:** Implement or integrate schema validation when tasks are created or potentially when read by the dispatcher (`/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py`).

## II. Task Type Management

-   [ ] **Catalog Task Types:** Maintain a clear list or enumeration of all valid `task_type` values used across the system.
-   [ ] **Update Inference Map:** Ensure the `_infer_target_agent` routing map in `/d:/Dream.os/_agent_coordination/dispatchers/task_dispatcher.py` is kept consistent with the defined task types and their intended agents.

## III. Task Lifecycle & Status

-   [ ] **Define Status Transitions:** Clearly document the valid state transitions for task `status` (e.g., `PENDING` -> `PROCESSING` -> (`DISPATCHED` | `FAILED`), `DISPATCHED` -> (`COMPLETED` | `FAILED` via agent update)).
-   [ ] **Error/Result Payloads:** Define standard structures for `error` and `result` fields within completed/failed tasks in `/d:/Dream.os/runtime/task_list.json`.

## IV. Documentation

-   [ ] **Document Task Schema:** Add comprehensive documentation (e.g., in `/d:/Dream.os/docs/task_list.md`) detailing the task JSON structure and fields.
-   [ ] **Document Task Types:** For each `task_type`, document its purpose, expected `params`, and the agent(s) responsible for handling it.

## V. Finalization

-   [ ] Commit any changes to task definitions or schemas.
-   [ ] Ensure task structures are consistent and well-documented. 