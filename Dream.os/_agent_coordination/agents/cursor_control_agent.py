import json
import logging
import time
import threading
import shutil
import sys # Added for path manipulation
from pathlib import Path
from typing import Dict, Callable

# --- Import Mailbox Utils --- 
# (Existing try/except block for mailbox_utils)
try:
    from .._agent_coordination.mailbox_utils import process_directory_loop 
except ImportError:
    try:
        sys.path.append(str(Path(__file__).parent.parent))
        from _agent_coordination.mailbox_utils import process_directory_loop
    except ImportError as e:
        print(f"Error: Could not import process_directory_loop. Please ensure mailbox_utils.py is accessible. {e}")
        def process_directory_loop(*args, **kwargs):
            print("WARNING: process_directory_loop failed to import. Mailbox listener inactive.")
            while True: time.sleep(60)

# --- Import Task Utils --- 
try:
    # Adjust relative import based on structure (agents -> _agent_coordination)
    from .._agent_coordination.task_utils import update_task_status
except ImportError:
     try:
        # Fallback if running directly
        sys.path.append(str(Path(__file__).parent.parent))
        from _agent_coordination.task_utils import update_task_status
     except ImportError as e:
        print(f"Error: Could not import update_task_status from task_utils. Status updates disabled. {e}")
        # Define a dummy function if import fails
        def update_task_status(*args, **kwargs):
            print(f"WARNING: update_task_status failed to import. Task status not updated. Args: {args}")
            return False

# --- Import Real Cursor Terminal Controller --- 
try:
    # Determine project root relative to this agent file (agents/agent.py -> project_root/)
    project_root = Path(__file__).parent.parent 
    # Add the 'social' directory to the path to allow imports from there
    social_core_path = project_root / "social" / "core"
    if str(social_core_path.parent) not in sys.path:
         sys.path.insert(0, str(social_core_path.parent)) # Add 'social' dir
    
    # Now import assuming 'social' is in the path
    from core.coordination.cursor.cursor_terminal_controller import CursorTerminalController
    logger.info("Successfully imported real CursorTerminalController.")
except ImportError as e:
    logger.error(f"Failed to import real CursorTerminalController: {e}. Falling back to placeholder.", exc_info=True)
    # Define a placeholder class if the real one fails to import
    class CursorTerminalController:
        def run_command(self, command, wait_for_completion=True):
            logger.warning(f"[PlaceholderController] Running command: {command}")
            return True # Simulate success
        def get_output(self, max_lines=None):
             return ["[PlaceholderController] Output..."]
        def get_current_directory(self):
             return "/placeholder/cwd"
        def send_input(self, text_input):
             logger.warning("[PlaceholderController] Sending input - not implemented.")
             return False
        def is_busy(self):
             return False

# --- Import Cursor Prompt Controller --- 
try:
    # Adjust relative import (agents -> _agent_coordination/ui_controllers)
    from .._agent_coordination.ui_controllers.cursor_prompt_controller import CursorPromptController
except ImportError:
     try:
        # Fallback if running directly
        sys.path.append(str(Path(__file__).parent.parent))
        from _agent_coordination.ui_controllers.cursor_prompt_controller import CursorPromptController
     except ImportError as e:
        print(f"Error: Could not import CursorPromptController. Prompt sending disabled. {e}")
        # Define a dummy class if import fails
        class CursorPromptController:
            def send_prompt_to_chat(self, prompt: str) -> bool:
                logger = logging.getLogger("CursorControlAgent") # Get logger
                logger.warning(f"[DummyPromptController] Would send prompt: {prompt[:100]}...")
                return False # Indicate failure as it's a dummy

# --- Configure Logging --- 
# (Existing logging setup)
if not logging.getLogger("CursorControlAgent").hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CursorControlAgent")


class CursorControlAgent:
    AGENT_NAME = "CursorControlAgent"

    def __init__(self, mailbox_root_dir="mailboxes", task_list_path="task_list.json"):
        self.mailbox_root = Path(mailbox_root_dir).resolve()
        self.task_list_path = Path(task_list_path).resolve()
        self.inbox_dir = self.mailbox_root / self.AGENT_NAME / "inbox"
        self.processed_dir = self.mailbox_root / self.AGENT_NAME / "processed"
        self.error_dir = self.mailbox_root / self.AGENT_NAME / "error"
        
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
        self.cursor_controller = CursorTerminalController() # Instantiate the REAL controller
        self.prompt_controller = CursorPromptController() # Instantiate prompt controller
        self.stop_event = threading.Event()
        self.listener_thread = None

        self.command_handlers: Dict[str, Callable[[dict], bool]] = {
            "resume_operation": self._handle_resume_operation,
            "generate_task": self._handle_generate_task, 
            "diagnose_loop": self._handle_diagnose_loop, 
            "confirmation_check": self._handle_confirmation_check, # NOW REAL
            "context_reload": self._handle_context_reload, # NOW REAL
            "clarify_objective": self._handle_clarify_objective, 
            "generic_recovery": self._handle_generic_recovery, # NOW REAL
            # Add other command handlers here
            # e.g., "run_terminal_command": self._handle_run_terminal_command
        }
        logger.info(f"{self.AGENT_NAME} initialized. Monitoring inbox: {self.inbox_dir}. Using: {type(self.cursor_controller).__name__}. Task List: {self.task_list_path}")

    # --- Command Handlers (Updated for Real Controller & Tools) ---
    def _handle_resume_operation(self, message_payload: dict) -> bool:
        """Attempt to resume by running a status check or default command."""
        params = message_payload.get("params", {})
        logger.info(f"Handling 'resume_operation'. Params: {params}")
        # Example: Run a simple command like 'pwd' or a specific status script
        command = params.get("resume_command", "pwd") # Allow command override via params
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output = self.cursor_controller.get_output(max_lines=10)
        logger.info(f"Resume command '{command}' success: {success}. Output: {output}")
        return success

    def _handle_generate_task(self, message_payload: dict) -> bool:
        """Generates a placeholder task and appends it to task_list.json."""
        # (Logic remains the same as it doesn't use the terminal controller directly)
        params = message_payload.get("params", {})
        logger.info(f"Handling 'generate_task'. Hint: {params.get('instruction_hint')}")
        new_task_id = f"generated_{int(time.time())}"
        new_task = {
            "task_id": new_task_id,
            "status": "PENDING",
            "task_type": "review_project_state", 
            "action": "Review current project state and suggest next logical step.",
            "params": {"triggering_stall": params.get("stall_category", "unknown")},
            "target_agent": "PlanningAgent", 
            "timestamp_created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        try:
            if not self.task_list_path.exists():
                 self.task_list_path.write_text("[]", encoding="utf-8")
            with self.task_list_path.open("r+", encoding="utf-8") as f:
                try:
                    content = f.read()
                    tasks = json.loads(content) if content else []
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode task_list.json, cannot append generated task.")
                    tasks = [] 
                    return False
                tasks.append(new_task)
                f.seek(0)
                json.dump(tasks, f, indent=2)
                f.truncate()
            logger.info(f"Appended generated task {new_task_id} to {self.task_list_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to append generated task to {self.task_list_path}: {e}")
            return False
        
    def _handle_diagnose_loop(self, message_payload: dict) -> bool:
        """Runs a command to retrieve logs for loop diagnosis."""
        params = message_payload.get("params", {})
        logger.info(f"Handling 'diagnose_loop'. Params: {params}")
        # Example: Tail the main agent log file
        log_file_path = params.get("log_file", "logs/agent_main.log") # Parameterize log file
        num_lines = params.get("lines", 50)
        command = f"tail -n {num_lines} {log_file_path}" # Adjust command for OS if needed
        
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output_lines = self.cursor_controller.get_output(max_lines=num_lines + 5) # Get command + output
        logger.info(f"Log retrieval command '{command}' success: {success}")
        # Instead of sending prompt (not supported by controller), log the findings
        if success:
             logger.info(f"Retrieved Logs for Loop Diagnosis:\n---\n" + "\n".join(output_lines) + "\n---")
             # Could potentially write output_lines to a diagnostic file
        else:
             logger.error(f"Failed to retrieve logs using command: {command}")

        return success # Return success of the command execution

    def _handle_confirmation_check(self, message_payload: dict) -> bool:
        params = message_payload.get('params', {})
        logger.info(f"Handling 'confirmation_check'. Params: {params}")
        # Execute the dedicated tool script
        command = "python tools/check_confirmation_state.py" 
        # Add params from message if needed by script, e.g.:
        # context_file = params.get('context_file')
        # if context_file: command += f" --context-file {context_file}" 
        
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output = self.cursor_controller.get_output(max_lines=10) # Get output/result from script
        logger.info(f"Confirmation check command '{command}' success (script exited 0?): {success}. Output: {output}")
        # Script uses exit code 0 for safe, 1 for needs confirmation (which run_command treats as success=False)
        return success # True if safe, False if confirmation needed
        
    def _handle_context_reload(self, message_payload: dict) -> bool:
        params = message_payload.get('params', {})
        logger.info(f"Handling 'context_reload'. Params: {params}")
        # Execute the dedicated tool script, passing target agent name
        target = params.get("target_agent", self.AGENT_NAME) # Default to self if not specified?
        command = f"python tools/reload_agent_context.py --target {target}" 
        
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output = self.cursor_controller.get_output(max_lines=10)
        logger.info(f"Context reload command '{command}' success: {success}. Output: {output}")
        return success
        
    def _handle_clarify_objective(self, message_payload: dict) -> bool:
        """Generates and attempts to send a clarification prompt via UI automation."""
        params = message_payload.get("params", {})
        logger.info(f"Handling 'clarify_objective'. Params: {params}")
        hint = params.get("instruction_hint", "Objective unclear.")
        relevant_files = params.get("relevant_files", [])
        context_str = f"Relevant files: {relevant_files}. " if relevant_files else ""
        prompt = f"Agent stalled due to unclear objective. {context_str}Instruction hint: {hint}. Please provide a clearer next step or goal."
        
        logger.info(f"Attempting to send clarification prompt via UI controller...")
        # Use the prompt controller to send the prompt
        success = self.prompt_controller.send_prompt_to_chat(prompt)
        
        if success:
            logger.info("Clarification prompt sent successfully via UI controller.")
        else:
            logger.error("Failed to send clarification prompt via UI controller.")
            # Consider fallback? Log to file? For now, just report failure.

        # Return success/failure of the UI automation attempt
        return success 
        
    def _handle_generic_recovery(self, message_payload: dict) -> bool:
        """Runs the diagnostics script as the generic recovery action."""
        params = message_payload.get("params", {})
        action_keyword = message_payload.get("action_keyword", "Perform general diagnostics.")
        logger.warning(f"Handling 'generic_recovery'. Action: {action_keyword}. Params: {params}")
        
        # Run the diagnostics script in auto mode
        command = "python tools/diagnostics.py --auto"
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output = self.cursor_controller.get_output(max_lines=20)
        logger.info(f"Generic recovery command '{command}' success: {success}. Output: {output}")
        # Success here means the script ran without error, not necessarily that it found no issues.
        # The script's output should be logged/analyzed if further action is needed.
        return success

    # --- Mailbox Processing Logic --- (No changes needed here)
    def _process_mailbox_message(self, message_path: Path) -> bool:
        """Processes a single message file from the inbox and updates task status."""
        logger.debug(f"Processing message file: {message_path.name}")
        message_payload = None
        original_task_id = None
        execution_success = False
        error_msg = None
        result_summary = None # Optional summary for successful tasks

        try:
            with message_path.open("r", encoding="utf-8") as f:
                message_payload = json.load(f)
            
            command = message_payload.get("command")
            # Get the ID of the task that generated this message
            original_task_id = message_payload.get("original_task_id")

            if not command:
                logger.error(f"Message {message_path.name} missing 'command'. Moving to error.")
                error_msg = "Message missing 'command' field"
                execution_success = False
            elif not original_task_id:
                 logger.error(f"Message {message_path.name} missing 'original_task_id'. Cannot update status. Moving to error.")
                 error_msg = "Message missing 'original_task_id' field"
                 execution_success = False # Cannot update status, treat as failure
            else:
                handler = self.command_handlers.get(command)
                if handler:
                    logger.info(f"Found handler for command '{command}' from task {original_task_id}. Executing...")
                    # Execute the handler
                    execution_success = handler(message_payload)
                    if execution_success:
                        logger.info(f"Handler for command '{command}' from task {original_task_id} completed successfully.")
                        result_summary = f"Handler '{command}' executed successfully."
                        # Optionally capture more specific results from handlers if they return it
                    else:
                        logger.error(f"Handler for command '{command}' from task {original_task_id} failed.")
                        error_msg = f"Handler for command '{command}' reported failure."
                else:
                    logger.warning(f"No handler found for command '{command}' (from task {original_task_id}) in message {message_path.name}. Moving to error.")
                    error_msg = f"No handler found for command '{command}'"
                    execution_success = False 

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {message_path.name}: {e}. Moving to error.")
            error_msg = f"JSONDecodeError: {e}"
            execution_success = False
        except Exception as e:
            logger.error(f"Unexpected error processing message {message_path.name}: {e}", exc_info=True)
            error_msg = f"Unexpected error: {e}"
            execution_success = False
        
        # --- Update Task Status --- 
        if original_task_id:
            final_status = "COMPLETED" if execution_success else "FAILED"
            logger.info(f"Updating status for original task '{original_task_id}' to '{final_status}'")
            update_task_status(
                self.task_list_path, 
                original_task_id, 
                final_status, 
                result_summary=result_summary, 
                error_message=error_msg
            )
        else:
             logger.error("Cannot update task status because original_task_id was not found in the message.")

        # Return execution_success to determine if file moves to processed/error
        return execution_success

    def start_listening(self):
        """Starts the mailbox listener loop in a separate thread."""
        if self.listener_thread and self.listener_thread.is_alive():
            logger.warning("Listener thread already running.")
            return

        logger.info("Starting mailbox listener thread...")
        self.stop_event.clear()
        self.listener_thread = threading.Thread(
            target=process_directory_loop,
            args=(
                self.inbox_dir,
                self._process_mailbox_message,
                self.processed_dir,
                self.error_dir
            ),
            kwargs={
                "poll_interval": 5, # Check more frequently
                "log_prefix": f"{self.AGENT_NAME}-Listener",
                "stop_event": self.stop_event
            },
            daemon=True
        )
        self.listener_thread.start()
        logger.info("Mailbox listener thread started.")

    def stop(self):
        """Signals the listener thread to stop and waits for it to join."""
        if not self.listener_thread or not self.listener_thread.is_alive():
            logger.info("Listener thread not running.")
            return
            
        logger.info("Stopping listener thread...")
        self.stop_event.set()
        self.listener_thread.join(timeout=10) # Wait for thread to finish
        if self.listener_thread.is_alive():
             logger.warning("Listener thread did not stop gracefully.")
        else:
             logger.info("Listener thread stopped.")
        self.listener_thread = None

# Example instantiation and execution
if __name__ == "__main__":
    # Assumes mailboxes/ is in the project root (adjust if needed)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent # Assumes agents/ is directly under project root
    mailbox_root = project_root / "mailboxes"
    
    print(f"Project Root detected as: {project_root}")
    print(f"Mailbox Root Dir: {mailbox_root}")

    # Define task list path for the agent
    task_list_file = project_root / "task_list.json"
    
    print(f"Task List Path: {task_list_file}")

    agent = CursorControlAgent(mailbox_root_dir=str(mailbox_root), task_list_path=str(task_list_file))
    agent.start_listening()

    try:
        # Keep the main thread alive while the listener runs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down agent...")
        agent.stop()
        print("Agent stopped.") 