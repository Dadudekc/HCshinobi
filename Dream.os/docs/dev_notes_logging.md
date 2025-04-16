# Dream.OS Logging - Developer Notes

## 1. Overview

The Dream.OS logging system, managed by `LogManager` (in `_agent_coordination/core/utils/logging.py`), provides a centralized and structured way to record events across the application. It aims for:

*   **Consistency:** Standardized format and retrieval.
*   **Observability:** Dual output to console (human-readable) and file (structured JSON Lines).
*   **Maintainability:** Log rotation and component tagging.

## 2. Configuration

Logging is configured during application startup by the `setup_environment` function in `main.py`, which calls `setup_logging`. This, in turn, is expected to call `LogManager().configure()`.

Key configuration aspects:

*   **Log Directory:** Set to `logs/` relative to the workspace root.
*   **Console Handler:**
    *   Level: `INFO` by default.
    *   Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
*   **File Handler (`logs/agent.log`):**
    *   Level: `DEBUG` by default.
    *   Format: JSON Lines (see below).
    *   Rotation: 10MB file size limit, 5 backup files kept (`agent.log.1`, `agent.log.2`, etc.).

## 3. Retrieving a Logger

Use the `get_logger` function from `core.utils.logger` (adjust import path if necessary, e.g., `from _agent_coordination.core.utils.logging import get_logger`):

```python
from core.utils.logger import get_logger

# Best practice: Use __name__ for the logger name
# Add a 'component' tag for structured file logs
logger = get_logger(__name__, component="MyComponent")

# Example usage
logger.info("Initialization complete.")
logger.debug("Detailed state: %s", complex_object)
logger.error("Failed to process task %s", task_id, exc_info=True) # Include exception traceback
```

*   **`name`:** Typically `__name__` of the module using the logger. This appears in the console log.
*   **`component`:** A string identifier for the logical part of the application (e.g., "MainWindow", "TaskMonitorTab", "FeedbackEngine"). This is added to the structured JSON logs for easier filtering and analysis.

## 4. Structured Log Format (`agent.log`)

Log entries in `logs/agent.log` are JSON objects, one per line (JSON Lines format). This facilitates automated parsing and analysis.

**Example JSON Entry:**

```json
{
  "timestamp": "2023-10-27T10:30:15.123456",
  "level": "INFO",
  "component": "TaskMonitorTab",
  "message": "Task state restored successfully",
  "logger": "core.gui.tabs.task_monitor_tab",
  "extra": { "success": true } 
}
```

**Example Error Entry:**

```json
{
  "timestamp": "2023-10-27T10:35:02.987654",
  "level": "ERROR",
  "component": "MainWindow",
  "message": "Error restoring tab state: 'cycle_execution'",
  "logger": "core.gui.main_window",
  "file": "core/gui/main_window.py",
  "line": 295,
  "function": "_load_state",
  "exception": {
    "type": "KeyError",
    "message": "'cycle_execution'",
    "traceback": "Traceback (most recent call last):\n... (standard Python traceback string) ..."
  }
}
```

**Fields:**

*   `timestamp`: ISO 8601 format timestamp.
*   `level`: Log level name (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").
*   `component`: The component name passed to `get_logger` (defaults to "unknown").
*   `message`: The formatted log message.
*   `logger`: The name of the logger (usually the module path).
*   `file`, `line`, `function`: Included for `ERROR` level and above.
*   `exception`: Included if `exc_info=True` was passed to the logging call. Contains `type`, `message`, and `traceback` string.
*   `extra`: Contains any additional dictionary passed via the `extra={...}` argument to logging calls (though this is not commonly used directly in the current GUI code).

## 5. Log Rotation & Management

*   Log rotation is handled automatically by `logging.handlers.RotatingFileHandler`.
*   When `agent.log` reaches the `max_size` (10MB), it's renamed to `agent.log.1`, `agent.log.1` becomes `agent.log.2`, and so on, up to `backup_count` (5).
*   Settings (`max_size`, `backup_count`, levels) can be adjusted by modifying the arguments passed to `LogManager().configure()` within the `setup_logging` function.

---
*Ensure logging is configured early in the application lifecycle to capture startup issues.* 