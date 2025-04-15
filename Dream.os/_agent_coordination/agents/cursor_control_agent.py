import json
import logging
import time
import threading
import shutil
from pathlib import Path
from typing import Dict, Callable

# Assuming mailbox_utils is importable (adjust path if needed)
# Potential: from _agent_coordination.mailbox_utils import process_directory_loop
try:
    # Adjust this relative import based on actual project structure
    from .._agent_coordination.mailbox_utils import process_directory_loop 
except ImportError:
    # Fallback if running script directly or structure differs
    try:
        # Attempt import assuming it's in the parent directory's _agent_coordination
        import sys
        sys.path.append(str(Path(__file__).parent.parent))
        from _agent_coordination.mailbox_utils import process_directory_loop
    except ImportError as e:
        print(f"Error: Could not import process_directory_loop. Please ensure mailbox_utils.py is accessible. {e}")
        # Define a dummy function if import fails, to allow basic structure creation
        def process_directory_loop(*args, **kwargs):
            print("WARNING: process_directory_loop failed to import. Mailbox listener inactive.")
            while True: time.sleep(60)

# Placeholder for actual Cursor interaction logic
class CursorTerminalController:
    def run_command(self, command, params):
        logger.info(f"[Placeholder] Running command: {command} with params {params}")
        # Simulate success
        return {"status": "success", "output": f"Executed {command}"}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CursorControlAgent")

class CursorControlAgent:
    AGENT_NAME = "CursorControlAgent"

    def __init__(self, mailbox_root_dir="mailboxes"):
        self.mailbox_root = Path(mailbox_root_dir).resolve()
        self.inbox_dir = self.mailbox_root / self.AGENT_NAME / "inbox"
        self.processed_dir = self.mailbox_root / self.AGENT_NAME / "processed"
        self.error_dir = self.mailbox_root / self.AGENT_NAME / "error"
        
        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
        self.cursor_controller = CursorTerminalController() # Placeholder
        self.stop_event = threading.Event()
        self.listener_thread = None

        # Map command strings (from task_type) to handler methods
        self.command_handlers: Dict[str, Callable[[dict], bool]] = {
            "resume_operation": self._handle_resume_operation,
            "generate_task": self._handle_generate_task, # Placeholder
            "diagnose_loop": self._handle_diagnose_loop, # Placeholder
            "confirmation_check": self._handle_confirmation_check, # Placeholder
            "context_reload": self._handle_context_reload, # Placeholder
            "clarify_objective": self._handle_clarify_objective, # Placeholder
            "generic_recovery": self._handle_generic_recovery, # Placeholder
            # Add other commands CursorControlAgent should handle
            # e.g., "run_terminal_command": self._handle_run_terminal_command
        }
        logger.info(f"{self.AGENT_NAME} initialized. Monitoring inbox: {self.inbox_dir}")

    # --- Command Handlers ---
    def _handle_resume_operation(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'resume_operation'. Params: {message_payload.get('params')}")
        # Example: Send a no-op or status check command to Cursor
        result = self.cursor_controller.run_command("check_status", message_payload.get('params'))
        # Update task list based on result? Send feedback?
        return result.get("status") == "success"

    def _handle_generate_task(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'generate_task'. Params: {message_payload.get('params')}")
        # Placeholder: May involve complex interaction or invoking another agent
        return True # Simulate success for now
        
    def _handle_diagnose_loop(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'diagnose_loop'. Params: {message_payload.get('params')}")
        # Placeholder: Get recent logs/actions from Cursor, analyze, maybe suggest prompt
        result = self.cursor_controller.run_command("get_recent_activity", message_payload.get('params'))
        return result.get("status") == "success"

    def _handle_confirmation_check(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'confirmation_check'. Params: {message_payload.get('params')}")
        # Placeholder: Analyze state, maybe send a specific confirmation prompt via Cursor
        result = self.cursor_controller.run_command("analyze_confirmation_context", message_payload.get('params'))
        return result.get("status") == "success"
        
    def _handle_context_reload(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'context_reload'. Params: {message_payload.get('params')}")
        # Placeholder: Trigger internal context reload or send command to Cursor
        result = self.cursor_controller.run_command("reload_context", message_payload.get('params'))
        return result.get("status") == "success"
        
    def _handle_clarify_objective(self, message_payload: dict) -> bool:
        logger.info(f"Handling 'clarify_objective'. Params: {message_payload.get('params')}")
        # Placeholder: Generate and send a clarification prompt via Cursor
        prompt = f"Need clarification based on stall: {message_payload.get('params', {}).get('instruction_hint')}"
        result = self.cursor_controller.run_command("send_clarification_prompt", {"prompt": prompt})
        return result.get("status") == "success"
        
    def _handle_generic_recovery(self, message_payload: dict) -> bool:
        logger.warning(f"Handling 'generic_recovery'. Action: {message_payload.get('action_keyword')}. Params: {message_payload.get('params')}")
        # Placeholder: Attempt a basic diagnostic command
        result = self.cursor_controller.run_command("run_basic_diagnostics", message_payload.get('params'))
        return result.get("status") == "success"

    # --- Mailbox Processing Logic ---
    def _process_mailbox_message(self, message_path: Path) -> bool:
        """Processes a single message file from the inbox."""
        logger.debug(f"Processing message file: {message_path.name}")
        try:
            with message_path.open("r", encoding="utf-8") as f:
                message_payload = json.load(f)
            
            command = message_payload.get("command")
            if not command:
                logger.error(f"Message {message_path.name} missing 'command'. Moving to error.")
                return False # Move to error dir

            handler = self.command_handlers.get(command)
            if handler:
                logger.info(f"Found handler for command '{command}'. Executing...")
                # Execute the handler
                success = handler(message_payload)
                if success:
                    logger.info(f"Handler for command '{command}' completed successfully.")
                    # Optionally: Update original task in task_list.json here? Requires task_list access.
                    # Optionally: Write response to an outbox?
                    return True # Move to processed dir
                else:
                    logger.error(f"Handler for command '{command}' failed.")
                    return False # Move to error dir
            else:
                logger.warning(f"No handler found for command '{command}' in message {message_path.name}. Moving to error.")
                return False # Move to error dir

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from {message_path.name}: {e}. Moving to error.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error processing message {message_path.name}: {e}", exc_info=True)
            return False # Move to error dir

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

    agent = CursorControlAgent(mailbox_root_dir=str(mailbox_root))
    agent.start_listening()

    try:
        # Keep the main thread alive while the listener runs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down agent...")
        agent.stop()
        print("Agent stopped.") 