"""
Defines and manages the state machine for agent task execution.
Handles transitions between states (e.g., PENDING, RUNNING, COMPLETED, FAILED).
"""
import logging
import time
import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from enum import Enum, auto

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

class TaskState(Enum):
    """Enumeration of possible task states."""
    PENDING = auto()
    RECEIVED = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    ERROR = auto()
    CANCELLED = auto()

class TaskExecutionStateMachine:
    """Manages the state transitions for a single agent task."""

    def __init__(self, task_id: str, initial_state: TaskState = TaskState.PENDING):
        self.task_id = task_id
        self._state = initial_state
        self.history: List[Dict[str, Any]] = []
        self.callbacks: Dict[TaskState, List[Callable]] = {state: [] for state in TaskState}
        self._log_transition(TaskState.PENDING, initial_state, "Initialization")
        logger.info(f"State machine initialized for task '{self.task_id}' in state {self._state.name}")

    @property
    def state(self) -> TaskState:
        """Current state of the task."""
        return self._state

    def _log_transition(self, from_state: TaskState, to_state: TaskState, reason: str):
        """Logs a state transition."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from_state": from_state.name,
            "to_state": to_state.name,
            "reason": reason
        }
        self.history.append(log_entry)
        logger.info(f"Task '{self.task_id}' state transition: {from_state.name} -> {to_state.name} (Reason: {reason})")
        # Placeholder: Could also emit an event via AgentBus or similar

    def _trigger_callbacks(self, new_state: TaskState):
        """Triggers registered callbacks for the new state."""
        if new_state in self.callbacks:
            for callback in self.callbacks[new_state]:
                try:
                    # Pass task_id and new_state to callback
                    callback(self.task_id, new_state)
                except Exception as e:
                    logger.error(f"Error executing callback {callback.__name__} for state {new_state.name} on task {self.task_id}: {e}", exc_info=True)

    def register_callback(self, state: TaskState, callback: Callable):
        """Registers a function to be called when entering a specific state."""
        if state in self.callbacks:
            self.callbacks[state].append(callback)
            logger.info(f"Registered callback {callback.__name__} for state {state.name} on task {self.task_id}")
        else:
            logger.error(f"Cannot register callback for invalid state: {state}")

    def transition_to(self, new_state: TaskState, reason: str) -> bool:
        """Attempts to transition to a new state."""
        # Basic validation (can add more complex rules, e.g., allowed transitions)
        if not isinstance(new_state, TaskState):
            logger.error(f"Invalid target state type: {type(new_state)}")
            return False
        
        if self._state == new_state:
             logger.warning(f"Task '{self.task_id}' already in state {new_state.name}. Transition skipped.")
             return False # Or True, depending on desired behavior

        # Prevent transitioning out of terminal states
        if self._state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.ERROR, TaskState.CANCELLED]:
            logger.warning(f"Task '{self.task_id}' is in terminal state {self._state.name}. Cannot transition to {new_state.name}.")
            return False

        old_state = self._state
        self._state = new_state
        self._log_transition(old_state, new_state, reason)
        self._trigger_callbacks(new_state)
        return True

    # --- Convenience transition methods ---
    def set_received(self, reason: str = "Task received by agent") -> bool:
        return self.transition_to(TaskState.RECEIVED, reason)

    def set_running(self, reason: str = "Execution started") -> bool:
        return self.transition_to(TaskState.RUNNING, reason)

    def set_paused(self, reason: str = "Execution paused") -> bool:
        return self.transition_to(TaskState.PAUSED, reason)

    def set_completed(self, reason: str = "Execution finished successfully") -> bool:
        return self.transition_to(TaskState.COMPLETED, reason)

    def set_failed(self, reason: str = "Execution failed due to known error") -> bool:
        return self.transition_to(TaskState.FAILED, reason)

    def set_error(self, reason: str = "Execution failed due to unexpected error") -> bool:
        return self.transition_to(TaskState.ERROR, reason)

    def set_cancelled(self, reason: str = "Task cancelled by user or system") -> bool:
        return self.transition_to(TaskState.CANCELLED, reason)

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

    # --- Example Callback Function ---
    def example_completion_callback(task_id, new_state):
        print(f"*** CALLBACK TRIGGERED for Task {task_id}: Entered state {new_state.name} ***")
        output_summary.append(f"Callback triggered for state: {new_state.name}")
    # -------------------------------

    try:
        # Instantiate
        task_id = "DemoTask-StateMachine-789"
        print(f"\n>>> Instantiating TaskExecutionStateMachine for task '{task_id}'...")
        sm = TaskExecutionStateMachine(task_id=task_id)
        output_summary.append(f"StateMachine instantiated for {task_id}. Initial state: {sm.state.name}")
        print(f">>> StateMachine instantiated. Initial state: {sm.state.name}")

        # Register a callback
        print("\n>>> Registering completion callback...")
        sm.register_callback(TaskState.COMPLETED, example_completion_callback)
        sm.register_callback(TaskState.FAILED, example_completion_callback) # Also call on failure
        output_summary.append("Callback registered for COMPLETED and FAILED.")
        print(">>> Callback registered.")

        # Test Transitions
        print("\n>>> Testing transitions...")
        transitions = [
            (sm.set_received, "Agent picked up task"),
            (sm.set_running, "Executor started process"),
            (sm.set_paused, "Waiting for user input"),
            (sm.set_running, "User input received, resuming"),
            (sm.set_failed, "Known error: API rate limit hit"),
            (sm.set_running, "Attempting retry after backoff (should fail - terminal state)"), # This should fail
        ]
        for transition_func, reason in transitions:
            print(f"  Attempting: {transition_func.__name__} ('{reason}')")
            success = transition_func(reason=reason)
            print(f"    Transition {'OK' if success else 'Rejected'}. Current state: {sm.state.name}")
            output_summary.append(f"{transition_func.__name__}: {'OK' if success else 'Rejected'} -> {sm.state.name}")

        # Test another sequence leading to completion
        print("\n>>> Testing completion sequence...")
        sm_complete = TaskExecutionStateMachine(task_id="DemoTask-Complete-123")
        sm_complete.register_callback(TaskState.COMPLETED, example_completion_callback)
        sm_complete.set_received()
        sm_complete.set_running()
        sm_complete.set_completed()
        output_summary.append(f"Completion sequence tested. Final state: {sm_complete.state.name}")
        print(f"  Completion sequence finished. Final state: {sm_complete.state.name}")

        execution_status = "executed"
        print(f"\n>>> Usage block executed successfully.")

    except Exception as e:
        logger.exception("Error during usage block execution.")
        errors = f"{type(e).__name__}: {str(e)}"
        execution_status = "error"
        print(f">>> ERROR during execution: {errors}")

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