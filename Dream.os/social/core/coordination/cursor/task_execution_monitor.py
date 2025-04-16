"""
Monitors the execution of agent tasks, tracking status, duration, and resource usage.
Integrates with task state machines and coordination components.
"""
import logging
import time
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import threading

# Placeholder for dependencies like psutil (for resource usage), system monitoring libraries

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Placeholder Agent Coordination Functions ---
def _log_tool_action(tool_name, status, message, details=None):
    print(f"[TOOL LOG - {tool_name}] Status: {status}, Msg: {message}, Details: {details or 'N/A'}")

def _update_status_file(file_path, status_data):
    abs_path = os.path.abspath(file_path)
    print(f"[STATUS UPDATE] Writing to {abs_path}: {json.dumps(status_data)}")
    # Placeholder: Write status_data to file_path

def _append_to_task_list(file_path, task_data):
     abs_path = os.path.abspath(file_path)
     print(f"[TASK LIST APPEND] Appending to {abs_path}: {json.dumps(task_data)}")
     # Placeholder: Load JSON, append task, save JSON

def _update_project_board(file_path, board_data):
    abs_path = os.path.abspath(file_path)
    print(f"[PROJECT BOARD UPDATE] Updating {abs_path}: {json.dumps(board_data)}")
    # Placeholder: Load JSON, update/add entry, save JSON
# --- End Placeholders ---

class TaskExecutionMonitor:
    """Placeholder class for monitoring agent task execution."""

    def __init__(self, state_machine: Optional[Any] = None, alert_thresholds: Optional[Dict[str, Any]] = None):
        self.state_machine = state_machine # Reference to the state machine being monitored
        self.monitored_tasks: Dict[str, Dict[str, Any]] = {} # task_id -> {start_time, status, thread, ...}
        self.alert_thresholds = alert_thresholds or {
            "max_duration_seconds": 3600, # 1 hour
            "max_cpu_percent": 90.0,
            "max_memory_mb": 1024
        }
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        logger.info(f"TaskExecutionMonitor initialized. Thresholds: {self.alert_thresholds}")

    def start_monitoring_task(self, task_id: str, task_thread: Optional[threading.Thread] = None):
        """Placeholder: Begins monitoring a specific task."""
        with self._lock:
            if task_id in self.monitored_tasks:
                logger.warning(f"Task {task_id} is already being monitored.")
                return
            start_time = datetime.now()
            self.monitored_tasks[task_id] = {
                "start_time": start_time,
                "status": "RUNNING", # Assume started if monitoring begins
                "last_heartbeat": start_time,
                "thread": task_thread, # Reference to the execution thread if available
                "alerts": []
            }
            logger.info(f"Started monitoring task: {task_id}")
            # Start the background monitor thread if not already running
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                self._start_monitor_thread()

    def update_task_status(self, task_id: str, status: str, message: Optional[str] = None):
        """Placeholder: Updates the status of a monitored task."""
        with self._lock:
            if task_id not in self.monitored_tasks:
                logger.warning(f"Cannot update status for unmonitored task: {task_id}")
                return
            self.monitored_tasks[task_id]["status"] = status
            self.monitored_tasks[task_id]["last_heartbeat"] = datetime.now()
            if status in ["COMPLETED", "FAILED", "ERROR"]:
                 duration = (datetime.now() - self.monitored_tasks[task_id]["start_time"]).total_seconds()
                 self.monitored_tasks[task_id]["duration_seconds"] = duration
                 logger.info(f"Task {task_id} reached terminal state: {status}. Duration: {duration:.2f}s")
                 # Optionally remove from active monitoring here or keep for history
                 # del self.monitored_tasks[task_id]
            else:
                 logger.info(f"Updated status for task {task_id}: {status}")

    def _check_tasks(self):
        """Placeholder: Internal method run periodically to check task health."""
        with self._lock:
            now = datetime.now()
            for task_id, data in list(self.monitored_tasks.items()): # Iterate over copy for potential deletion
                if data["status"] not in ["RUNNING", "STARTED"]:
                    continue # Skip completed/failed tasks for health checks

                duration = (now - data["start_time"]).total_seconds()
                # Check Duration
                if duration > self.alert_thresholds["max_duration_seconds"]:
                    alert_msg = f"Task {task_id} exceeded max duration ({duration:.0f}s > {self.alert_thresholds['max_duration_seconds']}s)"
                    if alert_msg not in data["alerts"]:
                        logger.warning(alert_msg)
                        data["alerts"].append(alert_msg)
                        # Placeholder: Trigger alert mechanism (e.g., notify operator)

                # Placeholder: Check Resource Usage (requires psutil or similar)
                # if data["thread"] and psutil:
                #     try:
                #         p = psutil.Process(data["thread"].native_id) # Get process by thread ID (might need PID)
                #         cpu = p.cpu_percent(interval=0.1)
                #         mem = p.memory_info().rss / (1024 * 1024) # MB
                #         if cpu > self.alert_thresholds["max_cpu_percent"]:
                #             # log alert
                #         if mem > self.alert_thresholds["max_memory_mb"]:
                #             # log alert
                #     except psutil.NoSuchProcess:
                #          logger.warning(f"Process/Thread for task {task_id} not found for resource check.")

    def _monitor_loop(self):
        """Background thread loop to periodically check tasks."""
        logger.info("Task monitor background thread started.")
        while not self._stop_event.is_set():
            try:
                self._check_tasks()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)
            time.sleep(30) # Check every 30 seconds
        logger.info("Task monitor background thread stopped.")

    def _start_monitor_thread(self):
        """Starts the background monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop_monitoring(self):
        """Stops the background monitoring thread gracefully."""
        logger.info("Stopping task monitor...")
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
        self._monitor_thread = None
        logger.info("Task monitor stopped.")

    def get_task_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
         """Gets the current monitoring summary for a task."""
         with self._lock:
             return self.monitored_tasks.get(task_id, {}).copy() # Return copy

# ========= USAGE BLOCK START ==========
if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, and simulation
    print(f">>> Running module: {__file__}")
    abs_file_path = os.path.abspath(__file__)
    filename = os.path.basename(abs_file_path)
    agent_id = "UsageBlockAgent"

    # Define relative paths for coordination files
    coord_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    status_file = os.path.join(coord_base_dir, "status", "usage_block_status.json")
    task_list_file = os.path.join(coord_base_dir, "task_list.json")
    project_board_file = os.path.join(coord_base_dir, "project_board.json")

    # --- Coordination: Log Start ---
    _log_tool_action(f"UsageBlock_{filename}", "STARTED", f"Executing usage block for {filename}")
    # -----------------------------

    output_summary = []
    errors = None
    execution_status = "failed"
    monitor = None # Define monitor in outer scope for finally block

    try:
        # Instantiate
        print("\n>>> Instantiating TaskExecutionMonitor...")
        # Example with custom thresholds
        custom_thresholds = {"max_duration_seconds": 5, "max_memory_mb": 512}
        monitor = TaskExecutionMonitor(alert_thresholds=custom_thresholds)
        output_summary.append(f"Monitor instantiated with thresholds: {monitor.alert_thresholds}")
        print(f">>> Monitor instantiated.")

        # Start monitoring a dummy task
        task_id_1 = "Task-Sim-001"
        print(f"\n>>> Testing start_monitoring_task('{task_id_1}')...")
        monitor.start_monitoring_task(task_id_1)
        result_start1 = f"Result: Task '{task_id_1}' added to monitored tasks."
        print(f">>> Output: {result_start1}")
        output_summary.append(f"start_monitoring_task: {result_start1}")

        # Simulate task progress
        print("\n>>> Simulating task '{task_id_1}' running...")
        time.sleep(2)
        monitor.update_task_status(task_id_1, "RUNNING", "Processing step A")
        output_summary.append(f"update_task_status('{task_id_1}', 'RUNNING'): Status updated.")
        time.sleep(2)
        monitor.update_task_status(task_id_1, "RUNNING", "Processing step B")
        output_summary.append(f"update_task_status('{task_id_1}', 'RUNNING'): Status updated again.")

        # Get task summary
        print(f"\n>>> Testing get_task_summary('{task_id_1}')...")
        summary1 = monitor.get_task_summary(task_id_1)
        result_summary1 = f"Result: {summary1}"
        print(f">>> Output: {result_summary1}")
        output_summary.append(f"get_task_summary: Retrieved summary for {task_id_1}.")

        # Simulate task exceeding duration (based on custom threshold)
        print(f"\n>>> Simulating task '{task_id_1}' exceeding max duration (threshold={custom_thresholds['max_duration_seconds']}s)...")
        time.sleep(2) # Total sleep is now 2+2+2 = 6s > 5s threshold
        # Monitor loop runs every 30s, so manually call check for demo
        print("  (Manually triggering _check_tasks() for immediate demo of alert)")
        monitor._check_tasks()
        summary1_after_alert = monitor.get_task_summary(task_id_1)
        alert_found = bool(summary1_after_alert.get('alerts'))
        print(f">>> Output: Alert generated = {alert_found}. Alerts: {summary1_after_alert.get('alerts')}")
        output_summary.append(f"_check_tasks (duration alert): Alert generated = {alert_found}")

        # Simulate task completion
        print(f"\n>>> Testing update_task_status('{task_id_1}', 'COMPLETED')...")
        monitor.update_task_status(task_id_1, "COMPLETED")
        summary1_final = monitor.get_task_summary(task_id_1)
        result_complete1 = f"Result: Final status '{summary1_final.get('status')}', Duration: {summary1_final.get('duration_seconds')}"
        print(f">>> Output: {result_complete1}")
        output_summary.append(f"update_task_status('{task_id_1}', 'COMPLETED'): {result_complete1}")

        execution_status = "executed"
        print(f"\n>>> Usage block executed successfully.")

    except Exception as e:
        logger.exception("Error during usage block execution.")
        errors = f"{type(e).__name__}: {str(e)}"
        execution_status = "error"
        print(f">>> ERROR during execution: {errors}")

    finally:
        if monitor:
            print("\n>>> Stopping monitor thread...")
            monitor.stop_monitoring()
            print(">>> Monitor stopped.")

    # --- Coordination: Log End & Update Status ---
    timestamp = datetime.now().isoformat()
    final_message = f"Usage block execution {execution_status}."
    _log_tool_action(f"UsageBlock_{filename}", execution_status.upper(), final_message, details={"errors": errors})

    # Post Status to Mailbox (Simulated)
    status_data = {
        "file": abs_file_path,
        "status": execution_status,
        "output_summary": "\n".join(output_summary),
        "errors": errors,
        "timestamp": timestamp,
        "agent": agent_id
     }
    _update_status_file(status_file, status_data)

    # Append Task to Task List (Simulated)
    task_data = {
        "task_id": f"USAGE_BLOCK_EXECUTION_{filename}",
        "description": f"Usage block injected and run in {filename}",
        "status": "complete" if execution_status == "executed" else "failed",
        "priority": "low",
        "timestamp_completed": timestamp
    }
    _append_to_task_list(task_list_file, task_data)

    # Update Project Board (Simulated)
    board_data = {
        "component": filename,
        "usage_block": f"{execution_status}_and_validated" if execution_status == "executed" else execution_status,
        "last_run": timestamp,
        "agent": agent_id
    }
    _update_project_board(project_board_file, board_data)
    # -----------------------------------------

    print(f">>> Module {filename} demonstration complete.")
    sys.exit(0 if execution_status == "executed" else 1)
# ========= USAGE BLOCK END ========== 