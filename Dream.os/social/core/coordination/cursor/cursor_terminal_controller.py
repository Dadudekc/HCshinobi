"""
Controls the integrated terminal pane within the Cursor application.
Handles running commands, capturing output, sending input, etc.
NOTE: This version attempts real command execution using subprocess.
"""
import logging
import time
import os
import sys
import json
import threading
import subprocess # For real command execution
import queue # For thread-safe output capturing
from datetime import datetime
from typing import Optional, List, Any, Dict, Union

# Adjust path for sibling imports if necessary
script_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Placeholder Agent Coordination Functions - Keep for now
def _log_tool_action(tool_name, status, message, details=None): print(f"[TOOL LOG - {tool_name}] Status: {status}, Msg: {message}, Details: {details or 'N/A'}")
def _update_status_file(file_path, status_data): abs_path = os.path.abspath(file_path); print(f"[STATUS UPDATE] Writing to {abs_path}: {json.dumps(status_data)}")
def _append_to_task_list(file_path, task_data): abs_path = os.path.abspath(file_path); print(f"[TASK LIST APPEND] Appending to {abs_path}: {json.dumps(task_data)}")
def _update_project_board(file_path, board_data): abs_path = os.path.abspath(file_path); print(f"[PROJECT BOARD UPDATE] Updating {abs_path}: {json.dumps(board_data)}")
# --- End Placeholders ---

# Ensure logger setup if not done globally
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

class CursorTerminalController:
    """Manages interactions with the Cursor integrated terminal (using subprocess)."""

    def __init__(self, terminal_identifier: Any = "main_terminal"):
        self.identifier = terminal_identifier
        # --- Terminal State ---
        self._current_directory: str = os.path.expanduser("~") # Start in user's home dir
        self._output_buffer: List[str] = [f"Terminal {self.identifier} initialized."]
        self._output_queue = queue.Queue() # For background process output
        self._process: Optional[subprocess.Popen] = None
        self._process_thread: Optional[threading.Thread] = None # For async output reading
        self._input_stream = None
        self._lock = threading.Lock() # Lock for accessing shared state
        self._command_running: Optional[str] = None

        logger.info(f"CursorTerminalController initialized for identifier: {self.identifier}")
        logger.info(f"Initial CWD: {self._current_directory}")

    def _read_output(self, stream, stream_type):
        """Reads lines from a stream and puts them into the queue."""
        try:
            for line in iter(stream.readline, b''):
                decoded_line = line.decode(errors='replace').rstrip()
                self._output_queue.put((stream_type, decoded_line))
            stream.close()
        except ValueError:
             # Handle case where stream is closed prematurely
             logger.debug(f"Stream ({stream_type}) closed or became invalid during read.")
        except Exception as e:
            logger.error(f"Error reading {stream_type} stream: {e}", exc_info=True)
            self._output_queue.put((stream_type, f"[Error reading stream: {e}]"))
        finally:
             # Signal that reading from this stream is done
             self._output_queue.put((stream_type, None)) 

    def _update_output_buffer(self):
         """Processes lines from the output queue and adds them to the buffer."""
         while not self._output_queue.empty():
             try:
                 stream_type, line = self._output_queue.get_nowait()
                 if line is not None:
                     prefix = "" if stream_type == "stdout" else "[stderr] "
                     with self._lock:
                         self._output_buffer.append(prefix + line)
                     # Maybe log stderr immediately?
                     # if stream_type == "stderr": logger.warning(f"TERMINAL STDERR: {line}")
                 # We don't need the None sentinel in the buffer
             except queue.Empty:
                 break # No more messages for now
             except Exception as e:
                  logger.error(f"Error processing output queue: {e}")

    def _handle_cd(self, command: str) -> bool:
         """Handles the 'cd' command specifically, updating internal CWD."""
         try:
             target_dir_part = command.strip()[2:].strip()
             if not target_dir_part: # Just 'cd' often means go home
                  target_dir = os.path.expanduser("~")
             elif target_dir_part.startswith('~'):
                  target_dir = os.path.expanduser(target_dir_part)
             elif os.path.isabs(target_dir_part):
                  target_dir = target_dir_part
             else:
                 target_dir = os.path.join(self._current_directory, target_dir_part)
             
             # Validate if directory exists
             if os.path.isdir(target_dir):
                 with self._lock:
                     self._current_directory = os.path.normpath(target_dir)
                     self._output_buffer.append(f"$ {command}") # Echo cd command
                     self._output_buffer.append(f"Changed directory to: {self._current_directory}")
                 logger.info(f"Internal CWD changed to: {self._current_directory}")
                 return True
             else:
                 error_msg = f"cd: no such file or directory: {target_dir}"
                 with self._lock:
                     self._output_buffer.append(f"$ {command}")
                     self._output_buffer.append(error_msg)
                 logger.warning(error_msg)
                 return False
         except Exception as e:
             error_msg = f"Error processing cd command: {e}"
             with self._lock:
                 self._output_buffer.append(f"$ {command}")
                 self._output_buffer.append(error_msg)
             logger.error(error_msg, exc_info=True)
             return False

    def run_command(self, command: str, wait_for_completion: bool = True) -> bool:
        """Runs a command in the terminal using subprocess."""
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                logger.error(f"Terminal '{self.identifier}' is busy with command: '{self._command_running}'. Cannot run: '{command}'")
                return False
            self._command_running = command # Store current command
        
        logger.info(f"Running command in '{self._current_directory}': '{command}'")

        # --- Special handling for 'cd' --- 
        # Subprocess doesn't persistently change the CWD of the parent Python process.
        # We handle 'cd' manually to update our internal state.
        if command.strip().startswith("cd"):
            return self._handle_cd(command)
        # --- End special handling --- 

        try:
            # Clear previous process/thread if any
            self._process = None
            self._process_thread = None
            # Empty the output queue before starting new command
            while not self._output_queue.empty(): self._output_queue.get_nowait() 

            with self._lock:
                 self._output_buffer.append(f"$ {command}") # Echo command

            # Use shell=True cautiously, consider splitting command for safety if possible
            # For simplicity here, using shell=True to handle pipelines, env vars etc.
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, # Allow sending input
                shell=True,
                cwd=self._current_directory,
                text=False # Read bytes for reliable decoding
            )
            self._input_stream = self._process.stdin

            # Start threads to read stdout and stderr concurrently
            stdout_thread = threading.Thread(target=self._read_output, args=(self._process.stdout, "stdout"), daemon=True)
            stderr_thread = threading.Thread(target=self._read_output, args=(self._process.stderr, "stderr"), daemon=True)
            stdout_thread.start()
            stderr_thread.start()
            # Store the reader threads maybe?

            if wait_for_completion:
                logger.debug("Waiting for command completion...")
                # Wait for threads to finish reading (they signal with None)
                stdout_thread.join()
                stderr_thread.join()
                # Wait for the process itself
                self._process.wait()
                self._update_output_buffer() # Get remaining output
                exit_code = self._process.poll()
                logger.info(f"Command '{command}' finished with exit code: {exit_code}")
                with self._lock:
                    self._process = None
                    self._command_running = None
                    self._input_stream = None
                return exit_code == 0
            else:
                logger.info(f"Command '{command}' started asynchronously.")
                # Store process to check status later
                # Output will be collected in the background via the queue
                return True # Command started successfully

        except FileNotFoundError as e:
            # Often means command not found
            error_msg = f"Command not found or invalid path: {command} (in CWD: {self._current_directory}) - {e}"
            with self._lock:
                self._output_buffer.append(error_msg)
                self._process = None
                self._command_running = None
                self._input_stream = None
            logger.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"Failed to run command '{command}': {e}"
            with self._lock:
                self._output_buffer.append(error_msg)
                self._process = None
                self._command_running = None
                self._input_stream = None
            logger.error(error_msg, exc_info=True)
            return False

    def get_output(self, max_lines: Optional[int] = None) -> List[str]:
        """Retrieves the recent output from the terminal buffer, processing queue first."""
        self._update_output_buffer() # Process any pending output from queue
        logger.debug(f"Getting output from terminal '{self.identifier}' (Max Lines: {max_lines})")
        with self._lock:
            # Return a copy
            buffer = self._output_buffer[:]
        if max_lines is None or max_lines <= 0 or max_lines >= len(buffer):
            return buffer
        else:
            return buffer[-max_lines:]

    def get_current_directory(self) -> Optional[str]:
        """Returns the simulated current working directory of the terminal."""
        logger.debug(f"Getting CWD for terminal '{self.identifier}'")
        # No lock needed for read-only access to potentially changing CWD string?
        # Lock might be safer if assignments aren't atomic, though unlikely needed here.
        # with self._lock:
        return self._current_directory

    def send_input(self, text_input: str) -> bool:
        """Sends text input to the currently running process (if any)."""
        logger.info(f"Sending input to terminal '{self.identifier}': '{text_input[:50]}...'")
        # Update buffer before checking process state
        self._update_output_buffer()

        with self._lock:
            if self._process is None or self._process.poll() is not None or self._input_stream is None:
                logger.warning(f"Cannot send input: No command running or input stream unavailable in '{self.identifier}'.")
                return False
            try:
                 # Ensure input ends with newline for most shells/programs
                 input_bytes = (text_input + '\n').encode()
                 self._input_stream.write(input_bytes)
                 self._input_stream.flush()
                 # Simulate echoing input to buffer
                 self._output_buffer.append(f"[Input Sent]: {text_input}") 
                 logger.info(f"Sent input '{text_input}' to process.")
                 return True
            except Exception as e:
                 logger.error(f"Error sending input to process: {e}")
                 return False

    def is_busy(self) -> bool:
        """Checks if a command is currently running in the terminal."""
        # Update buffer first to potentially capture process termination output
        self._update_output_buffer()
        with self._lock:
            is_running = self._process is not None and self._process.poll() is None
            if not is_running and self._command_running:
                # Process finished but state wasn't fully cleared (e.g., async finish)
                logger.debug(f"Clearing finished command state for: '{self._command_running}'")
                self._process = None
                self._command_running = None
                self._input_stream = None
            logger.debug(f"Checking busy status for terminal '{self.identifier}': {is_running}")
            return is_running

# ========= USAGE BLOCK START ==========
if __name__ == "__main__":
    # 💻 Example usage — Standalone run for debugging, onboarding, and simulation
    # (Imports os, sys, json, datetime, time, threading, subprocess, queue)
    print(f">>> Running module: {__file__} (Real Subprocess Test)")
    # ... (Keep setup for coordination logging, status files etc.) ...
    # Assume coordination placeholders are defined above
    abs_file_path = os.path.abspath(__file__)
    filename = os.path.basename(abs_file_path)
    agent_id = "UsageBlockAgent_TermReal"
    coord_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    status_file = os.path.join(coord_base_dir, "status", f"usage_block_status_{filename}.json")
    task_list_file = os.path.join(coord_base_dir, "task_list.json")
    project_board_file = os.path.join(coord_base_dir, "project_board.json")

    # --- Coordination: Log Start ---
    _log_tool_action(f"UsageBlock_{filename}", "STARTED", f"Executing usage block for {filename}")
    # -----------------------------

    output_summary = []
    errors = None
    execution_status = "failed"
    terminal: Optional[CursorTerminalController] = None

    try:
        print("\n>>> Instantiating CursorTerminalController...")
        terminal = CursorTerminalController()
        initial_cwd = terminal.get_current_directory()
        output_summary.append(f"Terminal controller instantiated. Initial CWD: {initial_cwd}")
        print(f">>> Controller instantiated. CWD: {initial_cwd}")

        # Test Basic Command (Sync)
        test_cmd_echo = "echo Hello Terminal!"
        print(f"\n>>> Running sync command: '{test_cmd_echo}'")
        sync_ok = terminal.run_command(test_cmd_echo, wait_for_completion=True)
        print(f">>> Sync Command OK = {sync_ok}")
        output_summary.append(f"run_command sync ('{test_cmd_echo}'): OK={sync_ok}")
        time.sleep(0.1) # Give buffer time
        output_after_sync = terminal.get_output(max_lines=5)
        print(">>> Output (last 5 lines):")
        for line in output_after_sync: print(f"  {line}")
        output_summary.append(f"Output after sync echo: {output_after_sync[-2:]}") # Get last couple lines

        # Test 'cd' command
        test_cmd_cd = "cd .."
        print(f"\n>>> Running command: '{test_cmd_cd}'")
        cd_ok = terminal.run_command(test_cmd_cd)
        new_cwd = terminal.get_current_directory()
        print(f">>> CD Command OK = {cd_ok}, New CWD = {new_cwd}")
        output_summary.append(f"run_command ('{test_cmd_cd}'): OK={cd_ok}, New CWD={new_cwd}")
        assert new_cwd != initial_cwd # Check if CWD actually changed

        # Test Async Command (e.g., ping)
        # Use platform-specific ping command that runs for a bit
        ping_cmd = "ping -n 3 127.0.0.1" if sys.platform == "win32" else "ping -c 3 127.0.0.1"
        print(f"\n>>> Running async command: '{ping_cmd}'")
        async_ok = terminal.run_command(ping_cmd, wait_for_completion=False)
        print(f">>> Async Command Started OK = {async_ok}")
        output_summary.append(f"run_command async ('{ping_cmd}'): Started OK={async_ok}")
        time.sleep(0.5) # Give it time to start

        print("\n>>> Checking is_busy() while async command runs...")
        busy_status_1 = terminal.is_busy()
        print(f">>> Is Busy = {busy_status_1}")
        output_summary.append(f"is_busy (during async): {busy_status_1}")
        assert busy_status_1 is True

        print("\n>>> Attempting to send input (will likely be ignored by ping)...")
        input_ok = terminal.send_input("Some test input")
        print(f">>> Send Input OK = {input_ok}")
        output_summary.append(f"send_input (during async): OK={input_ok}")

        print("\n>>> Waiting for async command to finish (polling is_busy)...")
        wait_start = time.time()
        while terminal.is_busy():
            print(".", end="", flush=True)
            time.sleep(0.5)
            if time.time() - wait_start > 15: # Safety timeout
                 print("\nTimeout waiting for busy flag!")
                 output_summary.append("Timeout waiting for async command.")
                 errors = "Timeout waiting for async command"
                 break
        if not errors:
             print("\nAsync command finished.")
             output_summary.append("Async command completed normally.")

        print("\n>>> Checking is_busy() after waiting...")
        busy_status_2 = terminal.is_busy()
        print(f">>> Is Busy = {busy_status_2}")
        output_summary.append(f"is_busy (after async): {busy_status_2}")
        assert busy_status_2 is False

        print("\n>>> Getting final output...")
        final_output = terminal.get_output()
        print(f">>> Output (Full Buffer - {len(final_output)} lines):")
        for line in final_output[-10:]: print(f"  {line}") # Print last 10 lines
        output_summary.append(f"Final output retrieved ({len(final_output)} lines). Last: {final_output[-1:]}")

        # Test command not found
        print("\n>>> Testing invalid command: 'invalid_command_xyz'")
        invalid_ok = terminal.run_command("invalid_command_xyz")
        print(f">>> Invalid Command OK = {invalid_ok} (Expected False)")
        output_summary.append(f"run_command invalid: OK={invalid_ok}")
        assert invalid_ok is False
        invalid_output = terminal.get_output(max_lines=3)
        print(">>> Output after invalid command:")
        for line in invalid_output: print(f"  {line}")
        output_summary.append(f"Output after invalid: {invalid_output[-1:]}") # Check for error message

        execution_status = "executed" if not errors else "error"
        print(f"\n>>> Usage block finished. Status: {execution_status}")

    except Exception as e:
        logger.exception("Error during usage block execution.")
        errors = f"{type(e).__name__}: {str(e)}"
        execution_status = "error"
        print(f">>> ERROR during execution: {errors}")

    # --- Coordination: Log End & Update Status ---
    # (Keep existing coordination logging placeholders)
    timestamp = datetime.now().isoformat()
    final_message = f"Usage block execution {execution_status}."
    _log_tool_action(f"UsageBlock_{filename}", execution_status.upper(), final_message, details={"errors": errors})
    # Ensure status dir exists
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    status_data = { "file": abs_file_path, "status": execution_status, "output_summary": "\n".join(output_summary), "errors": errors, "timestamp": timestamp, "agent": agent_id }
    _update_status_file(status_file, status_data)
    # Update task list/project board if needed (omitted for brevity)
    # ... 

    print(f">>> Module {filename} demonstration complete.")
    sys.exit(0 if execution_status == "executed" else 1)
# ========= USAGE BLOCK END ========== 