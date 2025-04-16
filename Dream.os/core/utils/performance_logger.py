import json
import os
import logging
from datetime import datetime, timezone # Use timezone
from contextlib import contextmanager
from typing import Optional, Dict, Any # Added for type hints

# Define log path relative to potential runtime directory, avoid hardcoding 'memory' top-level
# TODO: Centralize log/runtime path configuration
LOG_DIR = os.path.join("runtime", "logs")
LOG_PATH = os.path.join(LOG_DIR, "performance.jsonl")

# Ensure log directory exists
try:
    os.makedirs(LOG_DIR, exist_ok=True)
except OSError as e:
    # Log error but allow continuation if possible
    logging.basicConfig() # Ensure basicConfig is called if logger not set up
    logging.error(f"Failed to create performance log directory {LOG_DIR}: {e}")

# Logger specific to performance logging
perf_logger_instance = logging.getLogger("core.utils.performance")

class PerformanceLogger:
    """Logs performance metrics for agent operations and tasks."""
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.log_path = LOG_PATH # Instance might customize later?

    @contextmanager
    def track_operation(self, operation_name: str):
        """Context manager to track the duration of an operation."""
        start_time = datetime.now(timezone.utc)
        perf_logger_instance.debug(f"Starting operation '{operation_name}' for agent {self.agent_id}...")
        try:
            yield
        finally:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            perf_logger_instance.debug(f"Finished operation '{operation_name}' for agent {self.agent_id}. Duration: {duration:.3f}s")
            # Optionally log operation summary here if needed, beyond just task outcomes
            self._log_entry({
                 "event_type": "OPERATION_COMPLETED",
                 "agent_id": self.agent_id,
                 "operation_name": operation_name,
                 "start_time": start_time.isoformat(),
                 "end_time": end_time.isoformat(),
                 "duration_sec": duration
            })

    def log_outcome(
        self,
        task_id: str,
        # agent_id: str, # Already stored in self.agent_id
        task_type: str,
        status: str, # Expecting string (e.g., TaskStatus.name)
        start_time: Optional[str], # Expecting ISO format string
        end_time: Optional[str], # Expecting ISO format string
        error_message: Optional[str] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None
    ):
        """Logs the outcome of a specific task."""
        duration_ms = None
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
            except ValueError:
                 perf_logger_instance.warning(f"Could not parse timestamps to calculate duration for task {task_id}")

        entry = {
            "event_type": "TASK_OUTCOME",
            "task_id": task_id,
            "agent_id": self.agent_id,
            "task_type": task_type,
            "status": status.upper(),
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "error_message": error_message,
            "input_summary": input_summary,
            "output_summary": output_summary
        }
        self._log_entry(entry)

    def _log_entry(self, entry_dict: Dict[str, Any]):
         """Writes a structured entry to the performance log file."""
         entry_dict["log_timestamp"] = datetime.now(timezone.utc).isoformat()
         try:
             # Use 'a' mode for appending
             with open(self.log_path, "a", encoding="utf-8") as f:
                 f.write(json.dumps(entry_dict) + "\n")
             perf_logger_instance.debug(f"Logged performance entry: {entry_dict.get('event_type', 'N/A')} - {entry_dict.get('task_id') or entry_dict.get('operation_name')}")
         except Exception as e:
             perf_logger_instance.error(f"Failed to write to performance log ({self.log_path}): {e}", exc_info=True) 