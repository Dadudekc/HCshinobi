# Task Schema Definition (`master_task_list.json` / `runtime/task_list.json`)

This document defines the standardized JSON schema for tasks within the Dream.OS system.

## Task Object Structure

```typescript
interface Task {
  task_id: string; // UUID, Mandatory
  description: string; // Mandatory
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "FAILED" | "BLOCKED"; // Mandatory
  priority: "CRITICAL" | "HIGH" | "NORMAL" | "LOW"; // Recommended Mandatory, Default: NORMAL
  task_type: string; // Mandatory (Defines the action/handler)
  params?: Record<string, any>; // Optional, structure depends on task_type

  // Optional Fields:
  assigned_to?: string; // Agent ID, added when claimed/completed
  target_agent?: string; // Explicit agent target, overrides inference
  depends_on?: string[]; // List of prerequisite task_ids
  result_summary?: string; // Text summary of result/error
  result?: ResultPayload | ErrorPayload; // Detailed structured result/error data (See below)
  source_file?: string; // Originating file path (e.g., task_list.md)
  module?: string; // Logical module association
  original_line?: number; // Line number in source_file
  timestamp_created_utc?: string; // ISO 8601 timestamp (When task was first defined)
  timestamp_updated_utc?: string; // ISO 8601 timestamp (Last status change)
  timestamp_aggregated_utc?: string; // ISO 8601 timestamp (When task was added from source)
}
```

**Notes:**

*   **Mandatory Fields:** `task_id`, `description`, `status`, `task_type`. `priority` is strongly recommended, defaulting to `NORMAL`.
*   **`task_type`:** This is crucial for routing the task to the correct agent handler.
*   **`params`:** The structure of this object is defined per `task_type`. (See Task `dffb8c48-633f-4fea-8054-d63cd0cc4e98` for defining these).
*   **Timestamps:** `timestamp_created_utc` (when the task goal was defined) and `timestamp_updated_utc` (last status change) are recommended for tracking.

## Status Transitions

The following are the standard valid transitions for the `status` field:

*   `PENDING` -> `IN_PROGRESS` / `CLAIMED` / `RUNNING` (Task claimed/started)
*   `PENDING` -> `FAILED` (Immediate failure, e.g., invalid task)
*   `IN_PROGRESS` / `CLAIMED` / `RUNNING` -> `COMPLETED` (Successful execution)
*   `IN_PROGRESS` / `CLAIMED` / `RUNNING` -> `FAILED` (Execution error)
*   `IN_PROGRESS` / `CLAIMED` / `RUNNING` -> `CANCELLED` (External cancellation signal)
*   `IN_PROGRESS` / `CLAIMED` / `RUNNING` -> `BLOCKED` (Execution stalled, resource unavailable, dependency issue)
*   `FAILED` -> `PENDING` (For retry mechanisms)
*   `BLOCKED` -> `PENDING` (When the blocking condition is resolved)

*(Note: The specific statuses like `IN_PROGRESS`, `CLAIMED`, `RUNNING` used during active execution may depend on agent/dispatcher implementation details.)*

## Result/Error Payload Structure (`result` field)

When a task reaches a terminal state (`COMPLETED`, `FAILED`, `BLOCKED`), the optional `result` field should contain structured information.

### Success Payload (`status: COMPLETED`)

```typescript
interface ResultPayload {
  status: "success";
  message?: string; // Optional human-readable success message (supplements result_summary)
  data?: Record<string, any>; // Task-specific structured output data
}
```

### Error Payload (`status: FAILED` / `status: BLOCKED`)

```typescript
interface ErrorPayload {
  status: "error"; 
  error_code: string; // Standardized error category (e.g., AGENT_ERROR, FILE_NOT_FOUND, API_ERROR, VALIDATION_ERROR, TIMEOUT)
  message: string; // Mandatory human-readable error message (can align with result_summary)
  details?: Record<string, any>; // Optional object containing structured error details (e.g., traceback, failed_step)
}
```

**Key Points:**

*   A top-level `status` ("success" or "error") within the `result` object is recommended for easy programmatic checks.
*   `error_code` allows for categorized error handling.
*   `message` provides human-readable context.
*   `data` (for success) and `details` (for error) offer flexibility for task-specific structured information. 