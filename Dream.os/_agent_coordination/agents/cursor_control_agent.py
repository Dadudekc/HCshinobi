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
            "generate_code": self._handle_generate_code, # Added handler
            # Add other command handlers here
            # e.g., "run_terminal_command": self._handle_run_terminal_command
        }
        logger.info(f"{self.AGENT_NAME} initialized. Monitoring inbox: {self.inbox_dir}. Using: {type(self.cursor_controller).__name__}. Task List: {self.task_list_path}")

    # --- Command Handlers (Updated for Real Controller & Strict Compliance) ---
    def _handle_resume_operation(self, message_payload: dict) -> bool:
        """Attempt to resume by running a *real* status check or default command."""
        params = message_payload.get("params", {})
        logger.info(f"Handling 'resume_operation'. Params: {params}")
        # Requires a REAL resume command/script. Using 'pwd' is a simulation.
        # command = params.get("resume_command", "path/to/real/resume_script.py") 
        # success = self.cursor_controller.run_command(command, wait_for_completion=True)
        logger.error(f"Cannot execute 'resume_operation': No real resume command/script defined. Task failed as per Rule ONB-001.")
        return False # Fail because 'pwd' is not a real resume action

    def _handle_generate_task(self, message_payload: dict) -> bool:
        # This handler *creates* a real task in task_list.json.
        # It doesn't simulate or use placeholders internally, so it's compliant.
        # (Existing implementation is okay)
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
        """Runs a command to retrieve logs, but cannot act on them without real analysis/prompting."""
        params = message_payload.get("params", {})
        logger.info(f"Handling 'diagnose_loop'. Params: {params}")
        log_file_path = params.get("log_file", "logs/agent_main.log") 
        num_lines = params.get("lines", 50)
        command = f"tail -n {num_lines} {log_file_path}" 
        
        success = self.cursor_controller.run_command(command, wait_for_completion=True)
        output_lines = self.cursor_controller.get_output(max_lines=num_lines + 5)
        logger.info(f"Log retrieval command '{command}' success: {success}")
        if success:
             logger.info(f"Retrieved Logs for Loop Diagnosis:\n---\n" + "\n".join(output_lines) + "\n---")
             # PROBLEM: Cannot analyze or send prompt for resolution. Task incomplete.
             logger.error("Successfully retrieved logs, but cannot analyze or act on them. Task failed as per Rule ONB-001 (incomplete action).")
             return False # Fail because we cannot complete the *purpose* of diagnosis
        else:
             logger.error(f"Failed to retrieve logs using command: {command}")
             return False

    def _handle_confirmation_check(self, message_payload: dict) -> bool:
        params = message_payload.get('params', {})
        logger.info(f"Handling 'confirmation_check'. Params: {params}")
        # Cannot run placeholder script tools/check_confirmation_state.py
        logger.error(f"Cannot execute 'confirmation_check': Relies on unimplemented tool 'tools/check_confirmation_state.py'. Task failed as per Rule ONB-001.")
        # command = "python tools/check_confirmation_state.py" 
        # success = self.cursor_controller.run_command(command, wait_for_completion=True)
        # output = self.cursor_controller.get_output(max_lines=10) 
        # logger.info(f"Confirmation check command '{command}' success (script exited 0?): {success}. Output: {output}")
        # return success 
        return False # Fail due to reliance on placeholder
        
    def _handle_context_reload(self, message_payload: dict) -> bool:
        params = message_payload.get('params', {})
        logger.info(f"Handling 'context_reload'. Params: {params}")
        # Cannot run placeholder script tools/reload_agent_context.py
        logger.error(f"Cannot execute 'context_reload': Relies on unimplemented tool 'tools/reload_agent_context.py'. Task failed as per Rule ONB-001.")
        # target = params.get("target_agent", self.AGENT_NAME) 
        # command = f"python tools/reload_agent_context.py --target {target}" 
        # success = self.cursor_controller.run_command(command, wait_for_completion=True)
        # output = self.cursor_controller.get_output(max_lines=10)
        # logger.info(f"Context reload command '{command}' success: {success}. Output: {output}")
        # return success
        return False # Fail due to reliance on placeholder
        
    def _handle_clarify_objective(self, message_payload: dict) -> bool:
        """Attempts to send prompt, fails if UI automation fails or is disabled."""
        params = message_payload.get("params", {})
        original_task_id = message_payload.get("original_task_id", "unknown_task")
        logger.info(f"Handling 'clarify_objective' for task {original_task_id}. Params: {params}")
        hint = params.get("instruction_hint", "Objective unclear.")
        relevant_files = params.get("relevant_files", [])
        context_str = f"Relevant files: {relevant_files}. " if relevant_files else ""
        prompt = f"Agent stalled due to unclear objective (Task: {original_task_id}). {context_str}Instruction hint: {hint}. Please provide a clearer next step or goal."
        
        logger.info(f"Attempting to send clarification prompt via UI controller...")
        success = self.prompt_controller.send_prompt_to_chat(prompt)
        
        if success:
            logger.info("Clarification prompt sent successfully via UI controller. Task considered complete (prompt sent).")
            # Note: We consider sending the prompt as completing *this* specific task.
            # Whether the clarification *succeeds* is a separate feedback loop.
            return True 
        else:
            logger.error("Failed to send clarification prompt via UI controller. Task failed.")
            return False 
        
    def _handle_generic_recovery(self, message_payload: dict) -> bool:
        """Attempts to run a REAL diagnostics script."""
        params = message_payload.get("params", {})
        action_keyword = message_payload.get("action_keyword", "Perform general diagnostics.")
        logger.warning(f"Handling 'generic_recovery'. Action: {action_keyword}. Params: {params}")
        
        # Cannot run placeholder script tools/diagnostics.py
        logger.error(f"Cannot execute 'generic_recovery': Relies on unimplemented tool 'tools/diagnostics.py'. Task failed as per Rule ONB-001.")
        # command = "python tools/diagnostics.py --auto"
        # success = self.cursor_controller.run_command(command, wait_for_completion=True)
        # output = self.cursor_controller.get_output(max_lines=20)
        # logger.info(f"Generic recovery command '{command}' success: {success}. Output: {output}")
        # return success
        return False # Fail due to reliance on placeholder

    def _handle_generate_code(self, message_payload: dict) -> bool:
        """Attempts to send prompt for code gen, fails if UI automation fails or is disabled."""
        params = message_payload.get("params", {})
        original_task_id = message_payload.get("original_task_id", "unknown_task")
        logger.info(f"Handling 'generate_code' for task {original_task_id}. Params: {params}")
        target_file = params.get("target_file")
        description = params.get("description")
        requirements = params.get("requirements", [])
        if not target_file or not description:
            logger.error("'generate_code' task missing required params: target_file or description.")
            return False
        prompt = f"Please generate the code for the following file:\n\n"
        prompt += f"Target File Path: {target_file}\n\n"
        prompt += f"Description:\n{description}\n\n"
        if requirements:
            prompt += f"Requirements:\n"
            for req in requirements:
                prompt += f"- {req}\n"
        prompt += f"\nPlease provide only the complete code for the file '{target_file}'."
        logger.info(f"--- CODE GENERATION PROMPT (Task: {original_task_id}) ---")
        logger.info(prompt)
        logger.info(f"--- END PROMPT ---")
        logger.info("Attempting to send code generation prompt via UI controller...")
        success = self.prompt_controller.send_prompt_to_chat(prompt)
        if success:
            logger.info("Code generation prompt sent successfully via UI controller.")
            # NOTE: This only sends the prompt. It doesn't guarantee generation or application.
            # Under strict ONB-001, sending the prompt is not *full* completion.
            logger.error("Prompt sent, but code application is not implemented. Task failed as per Rule ONB-001 (incomplete action).")
            return False # Fail because the full task (generate AND apply) is not complete
        else:
             logger.error("Failed to send code generation prompt via UI controller. Task failed.")
             return False 

    # --- Mailbox Processing Logic --- 
    def _process_mailbox_message(self, message_path: Path) -> bool:
        """Processes a single message file from the inbox and updates task status."""
        logger.debug(f"Processing message file: {message_path.name}")
        message_payload = None
        original_task_id = None
        execution_success = False
        error_msg = None
        result_summary = None 

        try:
            with message_path.open("r", encoding="utf-8") as f:
                message_payload = json.load(f)
            command = message_payload.get("command")
            original_task_id = message_payload.get("original_task_id")
            if not command or not original_task_id:
                 error_msg = "Message missing 'command' or 'original_task_id' field"
                 logger.error(f"Message {message_path.name}: {error_msg}")
                 execution_success = False
            else:
                handler = self.command_handlers.get(command)
                if handler:
                    logger.info(f"Executing handler for command '{command}' from task {original_task_id}...")
                    # Execute the handler - it now returns True ONLY if fully completed
                    execution_success = handler(message_payload)
                    if execution_success:
                        logger.info(f"Handler for command '{command}' from task {original_task_id} COMPLETED successfully.")
                        result_summary = f"Handler '{command}' executed successfully."
                    else:
                        # Error/block reason should be logged within the handler itself
                        logger.error(f"Handler for command '{command}' from task {original_task_id} FAILED or BLOCKED.")
                        error_msg = f"Handler for command '{command}' failed, blocked, or was incomplete (See logs for details)."
                else:
                    error_msg = f"No handler found for command '{command}'"
                    logger.warning(f"{error_msg} (from task {original_task_id}) in message {message_path.name}. Moving to error.")
                    execution_success = False 
        except Exception as e:
            logger.error(f"Unexpected error processing message {message_path.name}: {e}", exc_info=True)
            error_msg = f"Unexpected error during message processing: {e}"
            execution_success = False
        
        # --- Update Task Status --- 
        if original_task_id:
            # Use FAILED status for any non-completion according to ONB-001
            final_status = "COMPLETED" if execution_success else "FAILED" 
            logger.info(f"Updating status for original task '{original_task_id}' to '{final_status}'")
            # Use a more specific error message if the handler failed
            final_error_message = error_msg if error_msg else "Task handler reported failure or incomplete execution."
            update_task_status(
                self.task_list_path, 
                original_task_id, 
                final_status, 
                result_summary=result_summary if execution_success else None, 
                error_message=final_error_message if not execution_success else None
            )
        else:
             logger.error("Cannot update task status because original_task_id was not found in the message.")
             # If we couldn't get task ID, processing essentially failed
             execution_success = False 

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