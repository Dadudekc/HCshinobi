"""
Provides a high-level interface to coordinate actions within the Cursor application.
Integrates various controllers (Instance, Window, Editor, Locator, Terminal).
"""
import logging
import time
import os
import sys
import json
from datetime import datetime
from typing import Optional, Any, List, Dict

# Import the individual controller classes
# Assuming they are in a 'cursor' subdirectory relative to this file
try:
    from .cursor.cursor_instance_controller import CursorInstanceController
    from .cursor.cursor_window_controller import CursorWindowController
    from .cursor.cursor_editor_controller import CursorEditorController, CursorPosition
    from .cursor.cursor_element_locator import CursorElementLocator, ElementInfo
    from .cursor.cursor_terminal_controller import CursorTerminalController
except ImportError:
    # Fallback for running the script directly if modules aren't found relatively
    logger.warning("Relative imports failed, attempting direct imports (might fail if not in PYTHONPATH).")
    from cursor.cursor_instance_controller import CursorInstanceController
    from cursor.cursor_window_controller import CursorWindowController
    from cursor.cursor_editor_controller import CursorEditorController, CursorPosition
    from cursor.cursor_element_locator import CursorElementLocator, ElementInfo
    from cursor.cursor_terminal_controller import CursorTerminalController


# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Placeholder Agent Coordination Functions ---
# (Keep existing placeholders)
def _log_tool_action(tool_name, status, message, details=None): print(f"[TOOL LOG - {tool_name}] Status: {status}, Msg: {message}, Details: {details or 'N/A'}")
def _update_status_file(file_path, status_data): abs_path = os.path.abspath(file_path); print(f"[STATUS UPDATE] Writing to {abs_path}: {json.dumps(status_data)}")
def _append_to_task_list(file_path, task_data): abs_path = os.path.abspath(file_path); print(f"[TASK LIST APPEND] Appending to {abs_path}: {json.dumps(task_data)}")
def _update_project_board(file_path, board_data): abs_path = os.path.abspath(file_path); print(f"[PROJECT BOARD UPDATE] Updating {abs_path}: {json.dumps(board_data)}")
# --- End Placeholders ---

class CursorCoordinator:
    """Coordinates actions across different Cursor controllers (Placeholders)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, launch_new_instance: bool = False):
        """
        Initializes the coordinator, sets up controllers for a Cursor instance.

        Args:
            config: Optional configuration dictionary (e.g., {"executable_path": "..."}).
            launch_new_instance: If True, always launches a new instance instead of finding existing.
        """
        self.config = config or {}
        logger.info(f"Initializing CursorCoordinator with config: {self.config}")

        # 1. Initialize Instance Controller
        self.instances = CursorInstanceController(executable_path=self.config.get("executable_path"))

        # 2. Find or Launch a Cursor Instance
        self.target_instance_id: Optional[Any] = None
        launched_by_us = False # Track if we launched this instance for cleanup

        if not launch_new_instance:
            existing_pids = self.instances.find_existing_instances()
            if existing_pids:
                self.target_instance_id = existing_pids[0] # Use the first found instance
                logger.info(f"Found existing Cursor instance, targeting PID: {self.target_instance_id}")

        if self.target_instance_id is None:
            logger.info("No existing Cursor instance found or launch_new_instance=True, launching...")
            launched_pid = self.instances.launch_instance()
            if launched_pid:
                self.target_instance_id = launched_pid
                launched_by_us = True
                logger.info(f"Launched new Cursor instance, targeting PID: {self.target_instance_id}")
            else:
                logger.error("Failed to launch or find a Cursor instance. Coordinator cannot target controllers.")
                # Set controllers to None or raise an error
                self.window = None
                self.editor = None
                self.locator = None
                self.terminal = None
                self._was_launched = False
                return # Stop initialization

        self._was_launched = launched_by_us # Store for potential cleanup in __main__

        # 3. Initialize other controllers, targeting the instance
        window_identifier = self.target_instance_id
        locator_handle = self.target_instance_id
        editor_id = "main_editor"
        terminal_id = "main_terminal"

        try:
            self.window = CursorWindowController(window_identifier=window_identifier)
            self.editor = CursorEditorController(editor_identifier=editor_id)
            self.locator = CursorElementLocator(cursor_window_handle=locator_handle)
            self.terminal = CursorTerminalController(terminal_identifier=terminal_id)
        except Exception as e:
             logger.error(f"Error initializing controllers for instance {self.target_instance_id}: {e}", exc_info=True)
             # Clean up if we launched the instance but couldn't init controllers
             if self._was_launched:
                 self.instances.close_instance(pid=self.target_instance_id, force=True)
             self.window = self.editor = self.locator = self.terminal = None
             self.target_instance_id = None
             self._was_launched = False
             raise RuntimeError("Failed to initialize coordinator controllers.") from e


        logger.info("CursorCoordinator initialized successfully with all controllers.")

    # --- High-Level Action Methods (Examples) ---

    def ensure_cursor_focused(self) -> bool:
        """Ensures the target Cursor window is focused."""
        if not self.window or self.target_instance_id is None:
            logger.error("Cannot focus: Window controller or target instance not available.")
            return False
        logger.info("Ensuring Cursor window is focused...")
        return self.window.focus()

    def open_file_in_editor(self, file_path: str) -> bool:
        """Placeholder: Opens a specified file in the Cursor editor."""
        if not self.editor:
             logger.error("Cannot open file: Editor controller not available.")
             return False
        # Ensure focus before interaction
        if not self.ensure_cursor_focused():
             logger.warning("Could not focus Cursor window before attempting file open.")
             # Decide whether to proceed or fail

        logger.info(f"Attempting to open file: {file_path}")
        # Placeholder Logic: Simulate UI interaction or command-line opening
        time.sleep(0.5)
        abs_path = os.path.abspath(file_path)
        self.editor._current_file = abs_path
        # Simulate reading file content if it exists locally for a better demo
        simulated_content = f"# Content of {os.path.basename(abs_path)}
print('Simulated file open!')"
        if os.path.exists(abs_path):
             try:
                 with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                     simulated_content = f.read()
                 logger.debug(f"Read content from actual file {abs_path} for simulation.")
             except Exception as e:
                 logger.warning(f"Could not read actual file {abs_path} for simulation: {e}")

        self.editor._editor_content = simulated_content
        self.editor._lines = self.editor._editor_content.split('\n')
        self.editor._cursor_pos = (0, 0)
        self.editor._selection = None
        logger.info(f"Placeholder: Simulated opening file '{abs_path}'. Updated editor state.")
        return True

    def get_editor_content(self) -> Optional[str]:
        """Gets the current content from the editor."""
        if not self.editor:
            logger.error("Cannot get editor content: Editor controller not available.")
            return None
        return self.editor.get_text()

    def set_editor_content(self, content: str) -> bool:
        """Sets the content of the editor."""
        if not self.editor:
             logger.error("Cannot set editor content: Editor controller not available.")
             return False
        if not self.ensure_cursor_focused():
             logger.warning("Could not focus Cursor window before setting editor content.")
        return self.editor.set_text(content)

    def insert_editor_text(self, text: str, position: Optional[CursorPosition] = None) -> bool:
        """Inserts text into the editor."""
        if not self.editor:
             logger.error("Cannot insert editor text: Editor controller not available.")
             return False
        if not self.ensure_cursor_focused():
             logger.warning("Could not focus Cursor window before inserting editor text.")
        return self.editor.insert_text(text, position=position)

    def run_terminal_command(self, command: str, wait: bool = True) -> bool:
        """Runs a command in the integrated terminal."""
        if not self.terminal:
             logger.error("Cannot run command: Terminal controller not available.")
             return False
        if not self.ensure_cursor_focused(): # May not be strictly necessary but good practice
             logger.warning("Could not focus Cursor window before running terminal command.")
        return self.terminal.run_command(command, wait_for_completion=wait)

    def get_terminal_output(self, max_lines: Optional[int] = None) -> Optional[List[str]]:
        """Gets output from the integrated terminal."""
        if not self.terminal:
             logger.error("Cannot get terminal output: Terminal controller not available.")
             # Return None on failure to align with agent checks
             # return [] 
             return None
        try:
            # Assume the underlying controller might return None or raise Exception on error
            output = self.terminal.get_output(max_lines=max_lines)
            return output
        except Exception as e:
             logger.error(f"Error getting terminal output: {e}", exc_info=True)
             return None

    def find_element(self, by: str, query: str, timeout: int = 10) -> Optional[ElementInfo]:
        """Finds a UI element using the specified method."""
        if not self.locator:
             logger.error("Cannot find element: Element locator not available.")
             return None
        if not self.ensure_cursor_focused():
             logger.warning("Could not focus Cursor window before finding element.")

        by = by.lower()
        if by == "text":
            return self.locator.find_element_by_text(query, timeout=timeout)
        elif by == "id":
            return self.locator.find_element_by_id(query, timeout=timeout)
        elif by == "image":
            return self.locator.find_element_by_image(query, timeout=timeout)
        else:
            logger.error(f"Unsupported find method: '{by}'. Use 'text', 'id', or 'image'.")
            return None

    def close_cursor(self, force: bool = False) -> bool:
        """Closes the controlled Cursor instance."""
        if not self.instances or self.target_instance_id is None:
             logger.warning("Cannot close Cursor: Instance controller or target instance not available or already closed.")
             return False # Or True if already closed?
        logger.warning(f"Attempting to close Cursor instance PID: {self.target_instance_id}")
        success = self.instances.close_instance(pid=self.target_instance_id, force=force)
        if success:
             logger.info(f"Successfully requested closure for PID {self.target_instance_id}.")
             # Clear controllers as the instance is gone
             self.window = None
             self.editor = None
             self.locator = None
             self.terminal = None
             self.target_instance_id = None
             self._was_launched = False # It's closed now
        else:
             logger.error(f"Failed to close Cursor instance PID {self.target_instance_id}.")
        return success

# ========= USAGE BLOCK START ==========
if __name__ == "__main__":
    # 🚀 Example usage — Standalone run for debugging, onboarding, and simulation
    # (Imports os, sys, json, datetime, time)
    print(f">>> Running module: {__file__}")
    abs_file_path = os.path.abspath(__file__)
    filename = os.path.basename(abs_file_path)
    agent_id = "UsageBlockAgent"
    # (Coordination file paths defined)
    # Adjust base dir if structure changes
    coord_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) # Assumes core/coordination
    status_file = os.path.join(coord_base_dir, "status", "usage_block_status.json")
    task_list_file = os.path.join(coord_base_dir, "task_list.json")
    project_board_file = os.path.join(coord_base_dir, "project_board.json")

    # --- Coordination: Log Start ---
    _log_tool_action(f"UsageBlock_{filename}", "STARTED", f"Executing usage block for {filename}")
    # -----------------------------

    output_summary = []
    errors = None
    execution_status = "failed"
    coordinator: Optional[CursorCoordinator] = None # Define for finally block
    instance_launched_for_demo = False

    try:
        # Instantiate the Coordinator
        print("\n>>> Instantiating CursorCoordinator...")
        # Set launch_new_instance=True for a clean demo that requires cleanup
        coordinator = CursorCoordinator(launch_new_instance=True)
        if coordinator and coordinator.target_instance_id:
            instance_launched_for_demo = coordinator._was_launched
            output_summary.append(f"Coordinator instantiated. Target PID: {coordinator.target_instance_id}")
            print(f">>> Coordinator instantiated. Target PID: {coordinator.target_instance_id}")
        else:
            raise RuntimeError("Failed to initialize CursorCoordinator or target an instance.")

        # Use high-level methods
        print("\n>>> Testing ensure_cursor_focused()...")
        focus_ok = coordinator.ensure_cursor_focused()
        print(f">>> Output: Focus OK = {focus_ok} (Placeholder)")
        output_summary.append(f"ensure_cursor_focused: OK={focus_ok}")

        print("\n>>> Testing get_editor_content()...")
        content = coordinator.get_editor_content()
        print(f">>> Output (First 5 lines):")
        if content:
            for i, line in enumerate(content.split('\n')):
                 if i >= 5: break
                 print(f"  {line}")
        else:
            print("  <No Content or Error>")
        output_summary.append(f"get_editor_content: Retrieved content (length={len(content) if content else 0}).")

        # Create a dummy file to "open"
        dummy_file_path = "./temp_coordinator_demo_file.txt"
        with open(dummy_file_path, "w") as f:
            f.write("Hello from the dummy file!")
        print(f"\n>>> Testing open_file_in_editor('{dummy_file_path}')...")
        open_ok = coordinator.open_file_in_editor(dummy_file_path)
        print(f">>> Output: Open File OK = {open_ok}")
        output_summary.append(f"open_file_in_editor: OK={open_ok}")
        os.remove(dummy_file_path) # Clean up dummy file

        print("\n>>> Testing get_editor_content() after open...")
        content_after_open = coordinator.get_editor_content()
        print(f">>> Output: '{content_after_open}'")
        output_summary.append(f"get_editor_content (after open): Retrieved content (length={len(content_after_open) if content_after_open else 0}).")

        print("\n>>> Testing run_terminal_command('echo Coordinator Test')...")
        term_ok = coordinator.run_terminal_command("echo Coordinator Test")
        print(f">>> Output: Run Command OK = {term_ok}")
        output_summary.append(f"run_terminal_command: OK={term_ok}")

        print("\n>>> Testing get_terminal_output(max_lines=5)...")
        term_output = coordinator.get_terminal_output(max_lines=5)
        print(f">>> Output (Last 5 lines):")
        for line in term_output: print(f"  {line}")
        output_summary.append(f"get_terminal_output: Retrieved {len(term_output)} lines.")

        print("\n>>> Testing find_element(by='text', query='Terminal')...")
        element = coordinator.find_element(by="text", query="Terminal")
        result_find = f"Result: {element}" if element else "Result: Not Found"
        print(f">>> Output: {result_find}")
        output_summary.append(f"find_element: {result_find}")

        execution_status = "executed"
        print(f"\n>>> Usage block executed successfully.")

    except Exception as e:
        logger.exception("Error during usage block execution.")
        errors = f"{type(e).__name__}: {str(e)}"
        execution_status = "error"
        print(f">>> ERROR during execution: {errors}")

    finally:
        # Close the Cursor instance ONLY if this demo launched it
        if coordinator and instance_launched_for_demo and coordinator.target_instance_id:
            print(f"\n>>> Cleaning up: Closing Cursor instance PID {coordinator.target_instance_id} launched by demo...")
            closed = coordinator.close_cursor(force=True) # Force close in cleanup
            print(f">>> Cleanup: Close {'OK' if closed else 'Failed'}")
            output_summary.append(f"close_cursor (cleanup): {'OK' if closed else 'Failed'}")
        elif coordinator and coordinator.target_instance_id:
            print(f"\n>>> Instance PID {coordinator.target_instance_id} was pre-existing, not closing.")

    # --- Coordination: Log End & Update Status ---
    # (Keep existing coordination logging placeholders)
    timestamp = datetime.now().isoformat()
    final_message = f"Usage block execution {execution_status}."
    _log_tool_action(f"UsageBlock_{filename}", execution_status.upper(), final_message, details={"errors": errors})
    # Ensure coord paths exist for status writing
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    os.makedirs(os.path.dirname(project_board_file), exist_ok=True)
    # Touch task list file if it doesn't exist
    if not os.path.exists(task_list_file): open(task_list_file, 'a').close()

    status_data = { "file": abs_file_path, "status": execution_status, "output_summary": "\n".join(output_summary), "errors": errors, "timestamp": timestamp, "agent": agent_id }
    _update_status_file(status_file, status_data)
    task_data = { "task_id": f"USAGE_BLOCK_EXECUTION_{filename}", "description": f"Usage block injected and run in {filename}", "status": "complete" if execution_status == "executed" else "failed", "priority": "low", "timestamp_completed": timestamp }
    _append_to_task_list(task_list_file, task_data)
    board_data = { "component": filename, "usage_block": f"{execution_status}_and_validated" if execution_status == "executed" else execution_status, "last_run": timestamp, "agent": agent_id }
    _update_project_board(project_board_file, board_data)
    # -----------------------------------------

    print(f">>> Module {filename} demonstration complete.")
    sys.exit(0 if execution_status == "executed" else 1)
# ========= USAGE BLOCK END ========== 