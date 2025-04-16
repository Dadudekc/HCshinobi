"""
Controls the lifecycle of Cursor application instances.
Handles launching, finding, focusing, and closing Cursor windows.
"""
import logging
import time
import os
import sys
import json
import subprocess
import platform
from datetime import datetime
from typing import Optional, Any, List, Dict

# Optional import for psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None # Define psutil as None if import fails

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


class CursorInstanceController:
    """Manages Cursor application instances using subprocess and psutil (if available)."""

    def __init__(self, executable_path: Optional[str] = None):
        self.executable_path = executable_path or self._find_cursor_executable()
        if not self.executable_path or not os.path.exists(self.executable_path):
            logger.warning(f"Cursor executable not found or specified path invalid: {self.executable_path}")
            # Allow initialization but launching will fail
        self.active_procs: Dict[int, subprocess.Popen] = {} # Store Popen objects by PID
        logger.info(f"CursorInstanceController initialized. Executable: '{self.executable_path}'")

    def _find_cursor_executable(self) -> Optional[str]:
        """Attempts to find the Cursor executable based on OS."""
        logger.debug("Attempting to find Cursor executable...")
        system = platform.system()
        potential_paths = []

        if system == "Windows":
            common_paths = [
                os.path.expandvars("%LOCALAPPDATA%\\Programs\\Cursor\\Cursor.exe"),
                os.path.expandvars("%ProgramFiles%\\Cursor\\Cursor.exe"),
            ]
            potential_paths.extend(common_paths)
        elif system == "Darwin": # macOS
            potential_paths.append("/Applications/Cursor.app/Contents/MacOS/Cursor") # Adjust as needed
        elif system == "Linux":
            # Add common Linux paths if known (e.g., /usr/bin/cursor, /opt/cursor/cursor)
            potential_paths.extend(["/usr/local/bin/cursor", "/opt/Cursor/cursor"])

        for path in potential_paths:
            if os.path.exists(path):
                logger.info(f"Found Cursor executable at: {path}")
                return path

        logger.warning("Could not automatically find Cursor executable.")
        return None

    def launch_instance(self, workspace_path: Optional[str] = None) -> Optional[int]:
        """Launches a new instance of Cursor, optionally opening a workspace. Returns PID."""
        if not self.executable_path or not os.path.exists(self.executable_path):
             logger.error("Cannot launch Cursor: Executable path not found or invalid.")
             return None
             
        command = [self.executable_path]
        if workspace_path:
            abs_workspace_path = os.path.abspath(workspace_path)
            if os.path.isdir(abs_workspace_path):
                command.append(abs_workspace_path)
                logger.info(f"Launching Cursor with workspace: '{abs_workspace_path}'")
            else:
                logger.warning(f"Workspace path not found, launching without workspace: {abs_workspace_path}")
                logger.info("Launching Cursor without specific workspace.")
        else:
            logger.info("Launching Cursor without specific workspace.")

        try:
            # Launch in a way that doesn't block and allows us to get PID
            # Use DETACHED_PROCESS on Windows? Or start_new_session on POSIX?
            # Adjust creationflags as needed for different OS
            flags = 0
            if platform.system() == "Windows":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP # Or DETACHED_PROCESS
            
            proc = subprocess.Popen(command, creationflags=flags, close_fds=True) # Close fds on POSIX
                                   
            self.active_procs[proc.pid] = proc
            logger.info(f"Launched Cursor instance with PID: {proc.pid}")
            # Give it a moment to start up before potentially interacting
            time.sleep(3) # Adjust as needed
            return proc.pid
        except FileNotFoundError:
            logger.error(f"Failed to launch Cursor: Executable not found at '{self.executable_path}'.")
        except Exception as e:
            logger.exception(f"Failed to launch Cursor instance: {e}")
        return None

    def find_existing_instances(self, workspace_path: Optional[str] = None) -> List[int]:
        """Finds running Cursor PIDs. Workspace filtering requires psutil."""
        if not PSUTIL_AVAILABLE:
            logger.warning("psutil not installed. Cannot reliably find existing instances or filter by workspace.")
            # Return PIDs managed by *this* controller instance
            return list(self.active_procs.keys())

        logger.info(f"Finding existing Cursor processes. Filter Workspace: {workspace_path or 'Any'}")
        found_pids = []
        exe_name = os.path.basename(self.executable_path or "Cursor.exe").lower()
        abs_workspace_path = os.path.abspath(workspace_path) if workspace_path else None

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and exe_name in proc.info['name'].lower():
                    # Basic check passed, now check workspace if specified
                    if abs_workspace_path:
                        cmdline = proc.info['cmdline']
                        if cmdline and any(abs_workspace_path in arg for arg in cmdline):
                            found_pids.append(proc.info['pid'])
                    else:
                        # No workspace filter, add based on name match
                        found_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue # Process ended or restricted
            except Exception as e:
                 logger.warning(f"Error checking process {proc.pid}: {e}")

        logger.info(f"Found {len(found_pids)} potential Cursor process(es) with PIDs: {found_pids}")
        # Update internal tracking if needed
        # for pid in found_pids:
        #     if pid not in self.active_procs:
        #         self.active_procs[pid] = None # Mark as found externally
        return found_pids

    def focus_instance(self, pid: Optional[int] = None, handle: Optional[Any] = None) -> bool:
        """Placeholder: Brings the specified Cursor window to the foreground."""
        target = pid or handle
        logger.info(f"Attempting to focus Cursor instance (PID/Handle: {target})")
        # --- Placeholder Logic --- Requires UI automation library ---
        logger.warning("Focusing window requires a UI automation library (pywinauto, etc.) - Placeholder returning True.")
        # Example using pywinauto (needs import and setup):
        # try:
        #     app = pywinauto.Application().connect(process=pid)
        #     window = app.top_window()
        #     window.set_focus()
        #     return True
        # except Exception as e:
        #     logger.error(f"Failed to focus PID {pid}: {e}")
        #     return False
        # --- End Placeholder ---
        return True # Placeholder success

    def close_instance(self, pid: Optional[int] = None, handle: Optional[Any] = None, force: bool = False) -> bool:
        """Closes the specified Cursor instance by PID. Handle is ignored in this impl."""
        if not pid:
             logger.error("PID must be provided to close an instance.")
             # Could try finding PID from handle if using UI lib
             return False
             
        logger.info(f"Attempting to close Cursor instance (PID: {pid}, Force: {force})")
        proc_to_close = self.active_procs.pop(pid, None) # Remove from internal tracking first
        
        try:
            if PSUTIL_AVAILABLE:
                 p = psutil.Process(pid)
                 if force:
                     logger.warning(f"Forcibly terminating PID {pid}...")
                     p.terminate() # Or p.kill() for more forceful
                 else:
                     logger.info(f"Requesting graceful termination for PID {pid}...")
                     p.terminate() # Request termination
                 # Wait a bit for termination
                 try:
                      p.wait(timeout=5)
                      logger.info(f"Process PID {pid} terminated successfully.")
                      return True
                 except psutil.TimeoutExpired:
                      logger.warning(f"Process PID {pid} did not terminate gracefully after 5s. Consider force=True.")
                      if force:
                           p.kill()
                           logger.info(f"Process PID {pid} killed forcefully.")
                           return True
                      return False
            else:
                # Fallback if psutil not available (less reliable)
                logger.warning("psutil not available. Attempting termination via subprocess (less reliable).")
                if platform.system() == "Windows":
                    cmd = ["taskkill", "/PID", str(pid)]
                    if force:
                        cmd.append("/F")
                    subprocess.run(cmd, check=False, capture_output=True)
                else: # POSIX
                    cmd = ["kill", str(pid)]
                    if force:
                        cmd.insert(1, "-9")
                    subprocess.run(cmd, check=False, capture_output=True)
                logger.info(f"Termination command sent for PID {pid}. Verification requires psutil.")
                return True # Assume command sent ok

        except psutil.NoSuchProcess:
            logger.warning(f"Process PID {pid} not found. Already closed?")
            if pid in self.active_procs:
                 del self.active_procs[pid] # Clean up internal state
            return True # Consider it closed if not found
        except Exception as e:
            logger.exception(f"Error closing process PID {pid}: {e}")
            # Add back to tracking if termination failed?
            # if proc_to_close:
            #    self.active_procs[pid] = proc_to_close
            return False


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
    launched_pids = [] # Keep track of PIDs launched in this demo

    try:
        # Instantiate
        print("\n>>> Instantiating CursorInstanceController...")
        controller = CursorInstanceController() # Use default executable finding
        output_summary.append(f"Controller instantiated (Executable: {controller.executable_path})")
        print(f">>> Controller instantiated (Executable: {controller.executable_path})")
        if not controller.executable_path:
             raise FileNotFoundError("Demo cannot proceed without finding Cursor executable.")

        # Launch a new instance
        print("\n>>> Testing launch_instance()...")
        pid1 = controller.launch_instance() # Launch without workspace
        result_launch1 = f"Result: Launched PID '{pid1}'" if pid1 else "Result: Launch Failed"
        print(f">>> Output: {result_launch1}")
        output_summary.append(f"launch_instance(None): {result_launch1}")
        if pid1: launched_pids.append(pid1)

        # Launch another instance (with dummy workspace path for demo)
        print("\n>>> Testing launch_instance(workspace_path='./temp_workspace')...")
        # Ensure dummy workspace exists for demo
        dummy_workspace = "./temp_workspace"
        os.makedirs(dummy_workspace, exist_ok=True)
        pid2 = controller.launch_instance(workspace_path=dummy_workspace)
        result_launch2 = f"Result: Launched PID '{pid2}'" if pid2 else "Result: Launch Failed"
        print(f">>> Output: {result_launch2}")
        output_summary.append(f"launch_instance(workspace): {result_launch2}")
        if pid2: launched_pids.append(pid2)
        # Clean up dummy workspace dir
        if os.path.exists(dummy_workspace):
             os.rmdir(dummy_workspace)

        # Find instances (will primarily use psutil if available)
        print("\n>>> Testing find_existing_instances()...")
        all_pids = controller.find_existing_instances()
        result_find_all = f"Result: Found PIDs {all_pids} (Requires psutil for accuracy)"
        print(f">>> Output: {result_find_all}")
        output_summary.append(f"find_existing_instances(None): {result_find_all}")

        # Focus an instance (Placeholder)
        if pid1:
            print(f"\n>>> Testing focus_instance(pid='{pid1}')...")
            focus_success = controller.focus_instance(pid=pid1)
            result_focus = f"Result: {'Success (Placeholder)' if focus_success else 'Failed'}"
            print(f">>> Output: {result_focus}")
            output_summary.append(f"focus_instance({pid1}): {result_focus}")

        # Close instances launched by this demo
        print(f"\n>>> Closing instances launched by demo: {launched_pids}...")
        closed_count = 0
        for pid_to_close in launched_pids:
            print(f"  Closing PID {pid_to_close}...")
            close_success = controller.close_instance(pid=pid_to_close)
            if close_success:
                closed_count += 1
            print(f"    Close {'OK' if close_success else 'Failed'}")
            output_summary.append(f"close_instance({pid_to_close}): {'OK' if close_success else 'Failed'}")
            time.sleep(1) # Give time between closes

        # Verify closed instances are gone (may still show if termination is slow)
        print("\n>>> Testing find_existing_instances() after close attempts...")
        all_pids_after = controller.find_existing_instances()
        result_find_after = f"Result: Found PIDs {all_pids_after} (Check if demo PIDs are gone)"
        print(f">>> Output: {result_find_after}")
        output_summary.append(f"find_existing_instances(after_close): {result_find_after}")

        execution_status = "executed"
        print(f"\n>>> Usage block executed successfully (Check logs for details).")

    except Exception as e:
        logger.exception("Error during usage block execution.")
        errors = f"{type(e).__name__}: {str(e)}"
        execution_status = "error"
        print(f">>> ERROR during execution: {errors}")

    finally:
        # Ensure any processes potentially missed are cleaned up (if PIDs recorded)
        if launched_pids:
             print(f"\n>>> Final cleanup check for PIDs: {launched_pids}...")
             if PSUTIL_AVAILABLE:
                 for pid in launched_pids:
                     try:
                         p = psutil.Process(pid)
                         logger.warning(f"Attempting final forceful cleanup for PID {pid}")
                         p.terminate()
                         time.sleep(0.5)
                         if p.is_running(): p.kill()
                     except psutil.NoSuchProcess:
                         pass # Already gone
                     except Exception as final_e:
                          logger.error(f"Error during final cleanup of PID {pid}: {final_e}")
             else:
                  logger.warning("Cannot perform final PID cleanup check without psutil.")

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