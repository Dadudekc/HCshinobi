import json
import logging
import time
import shutil
# import sys # Removed
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Callable, List, Any # Added Any

# --- Configure Logging --- 
# Ensure logger is configured BEFORE any module-level logging calls
# Use __name__ for logger
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    # Check root logger
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Core Component Imports (Absolute, assuming project root in PYTHONPATH) ---
try:
    from core.coordination.agent_bus import AgentBus # Canonical AgentBus
    # process_directory_loop is removed as mailbox listening is replaced by AgentBus
    # from core.utils.mailbox_utils import process_directory_loop
    # update_task_status is removed, task status updates via AgentBus/service
    # from core.utils.task_utils import update_task_status
    # Assuming controllers are moved under services/
    from services.cursor.cursor_terminal_controller import CursorTerminalController
    from services.ui_controllers.cursor_prompt_controller import CursorPromptController
    # Import log_event for consistency?
    from core.memory.governance_memory_engine import log_event
    _core_imports_ok = True
except ImportError as e:
    logger.critical(f"Failed to import core components: {e}. Agent cannot function.", exc_info=True)
    _core_imports_ok = False
    # Define critical dummies only if necessary for basic file structure, 
    # but agent should ideally fail completely if core components are missing.
    class CursorTerminalController:
        def __init__(self, *args, **kwargs): logger.warning("Using dummy CursorTerminalController")
        def run_command(self, *args, **kwargs): return False
        def get_output(self, *args, **kwargs): return ["[DummyController: Error importing real controller]"]
        # Add other methods as needed, returning dummy/error values
    class CursorPromptController:
        def __init__(self, *args, **kwargs): logger.warning("Using dummy CursorPromptController")
        def send_prompt_to_chat(self, *args, **kwargs): return False
    # Remove dummy process_directory_loop
    # Remove dummy update_task_status
    # AgentBus dummy might not be needed if init requires it
    # Add dummy log_event if needed
    if "governance_memory_engine" in str(e):
         def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")

# Define default agent ID
AGENT_ID_DEFAULT = "CursorControlAgent"

# --- Agent Definition ---
# TODO: Inherit from BaseAgent (Phase 3)
class CursorControlAgent:
    AGENT_NAME = AGENT_ID_DEFAULT
    CAPABILITIES = ["cursor_control", "terminal_execution", "prompt_sending", "task_generation"] # Example

    # Modify __init__ to accept agent_bus and INJECTED dependencies
    def __init__(self,
                 agent_id: str = AGENT_ID_DEFAULT,
                 agent_bus: AgentBus = None,
                 terminal_controller: CursorTerminalController = None,
                 prompt_controller: CursorPromptController = None):
        if not _core_imports_ok:
            msg = "CursorControlAgent cannot initialize due to missing core component imports."
            try: logger.critical(msg)
            except NameError: print(f"CRITICAL: {msg}")
            raise RuntimeError(msg)
        if agent_bus is None:
             raise ValueError("AgentBus instance is required for CursorControlAgent initialization.")
        if terminal_controller is None or prompt_controller is None:
            raise ValueError("TerminalController and PromptController instances are required.")

        self.agent_id = agent_id # Store agent_id
        self.agent_bus = agent_bus # Store agent_bus instance

        # Inject dependencies
        self.cursor_controller = terminal_controller
        self.prompt_controller = prompt_controller

        # Agent-specific state dir
        self.state_dir = Path("./state") / self.agent_id # TODO: Re-evaluate state management location
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.confirmation_flag_path = self.state_dir / "user_confirmation.flag"

        # Remove command handlers dictionary - methods are now public dispatch targets
        # self.command_handlers: Dict[str, Callable[[dict], bool]] = { ... }

        # Remove handler registration call
        # self._register_handlers()

        # Register Agent with Agent Bus (Synchronous)
        try:
            registration_success = self.agent_bus.register_agent(self)
            if registration_success:
                 log_event("AGENT_REGISTERED", self.agent_id, {"message": "Successfully registered with AgentBus."})
                 logger.info(f"Agent {self.agent_id} registered successfully.")
            else:
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to register with AgentBus (register_agent returned False)."})
                 logger.error("Agent registration failed.")
                 # raise RuntimeError(f"Failed to register {self.agent_id} with AgentBus")
        except Exception as reg_e:
             log_event("AGENT_ERROR", self.agent_id, {"error": f"Exception during AgentBus registration: {reg_e}", "traceback": traceback.format_exc()})
             logger.exception("Exception during AgentBus registration.")
             # raise RuntimeError(f"Failed to register {self.agent_id} with AgentBus: {reg_e}") from reg_e

    # Removed handler registration method
    # def _register_handlers(self):

    # --- Public Methods (Dispatch Targets) ---

    # Renamed from _handle_generate_task
    def generate_task(self, task_description: str, priority: str = 'MEDIUM', target_module: str = None, calling_agent_id: str = "Unknown", **kwargs) -> Any:
        """Generates a new task by dispatching to a TaskManagementService (or similar)."""
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "generate_task", "caller": calling_agent_id, "desc_snippet": task_description[:50]})
        logger.info(f"Received generate_task request from {calling_agent_id}: '{task_description[:50]}...' ({priority}) Module: {target_module}")

        if not task_description:
            logger.error(f"'generate_task' failed: Missing 'task_description'.")
            return None # Indicate failure

        # TODO: Define standard task creation schema and target agent/method
        task_service_agent_id = "TaskServiceAgent" # Example target
        task_creation_method = "create_new_task" # Example target method
        new_task_params = {
            "description": task_description,
            "priority": priority,
            "source_agent": self.agent_id,
            "target_module": target_module,
            # Add other necessary fields: task_id (generated by service?), status, etc.
            **kwargs # Pass through any extra params
        }

        try:
            # Dispatch to the task service
            logger.info(f"Dispatching task creation request to {task_service_agent_id}.{task_creation_method}")
            result = self.agent_bus.dispatch(
                target_agent_id=task_service_agent_id,
                method_name=task_creation_method,
                **new_task_params
            )
            # Log based on result (e.g., was task ID returned?)
            if result:
                 logger.info(f"Task generation dispatch successful. Result: {result}")
                 log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "generate_task", "result": result})
            else:
                 logger.warning(f"Task generation dispatch to {task_service_agent_id} returned None or failed.")
                 log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "generate_task", "reason": "Dispatch returned None/failed"})
            return result # Return result from task service
        except Exception as e:
            logger.exception(f"Failed to dispatch task generation request to {task_service_agent_id}")
            log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "generate_task", "error": str(e)})
            return None # Indicate failure

    # Renamed from _handle_context_reload
    def context_reload(self, target_agent: str, original_task_id: str = "unknown_task", calling_agent_id: str = "Unknown") -> Any:
        """Dispatches a request for another agent to reload its context."""
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "context_reload", "caller": calling_agent_id, "target": target_agent})
        logger.info(f"Received context_reload request from {calling_agent_id} targeting {target_agent} (orig_task: {original_task_id}).")

        if not target_agent:
            logger.error(f"'context_reload' failed: Missing 'target_agent'.")
            return None

        # Define the target method name on the recipient agent
        target_method = "internal_reload_context" # Example convention
        dispatch_params = {
             "triggering_agent": self.agent_id,
             "triggering_task_id": original_task_id
        }

        try:
            logger.info(f"Dispatching {target_method} to {target_agent}")
            result = self.agent_bus.dispatch(
                target_agent_id=target_agent,
                method_name=target_method,
                **dispatch_params
            )
            logger.info(f"Context reload dispatch to {target_agent} returned: {result}")
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "context_reload", "target": target_agent, "result_type": type(result).__name__})
            return result
        except Exception as e:
            logger.exception(f"Failed to dispatch context reload request to {target_agent}.{target_method}")
            log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "context_reload", "target": target_agent, "error": str(e)})
            return None

    # This was internal, make it public if needed via dispatch?
    # Or keep internal if only called by other public methods of this agent.
    # For now, assume it's a potential dispatch target.
    def internal_reload_context(self, triggering_agent: str, triggering_task_id: str) -> bool:
         """Handles a request to reload context (called via dispatch)."""
         log_event("AGENT_ACTION_RECEIVED", self.agent_id, {"action": "internal_reload_context", "triggering_agent": triggering_agent, "triggering_task_id": triggering_task_id})
         logger.info(f"Received internal request to reload context. Triggered by {triggering_agent} (Task: {triggering_task_id}). Reloading logic TBD.")
         # TODO: Implement actual context reloading logic here
         # Example: self.cursor_controller.reload_context() ?
         # Return True on success, False on failure
         return True # Placeholder

    # --- Other Methods (Make public if they are dispatch targets) ---
    # TODO: Review these methods, rename (remove _), update signatures if they become public dispatch targets.

    def _handle_resume_operation(self, **kwargs): # Keep internal for now? Or public resume_operation(**kwargs)?
        logger.info("Handling resume_operation... Logic TBD.")
        # Example: Check state, maybe run a command via self.cursor_controller
        return True # Placeholder success

    def _handle_diagnose_loop(self, **kwargs):
        logger.info("Handling diagnose_loop... Logic TBD.")
        # Example: Analyze logs, use self.cursor_controller to inspect state
        return True

    def _handle_confirmation_check(self, **kwargs):
        logger.info("Handling confirmation_check... Logic TBD.")
        # Example: Check self.confirmation_flag_path
        return not self.confirmation_flag_path.exists() # Example: True if confirmation NOT needed

    def _handle_clarify_objective(self, **kwargs):
        logger.info("Handling clarify_objective... Logic TBD.")
        # Example: Use self.prompt_controller to ask user for clarification
        return True

    def _handle_generic_recovery(self, **kwargs):
        logger.info("Handling generic_recovery... Logic TBD.")
        # Example: Run basic diagnostic commands via self.cursor_controller
        return True

    def _handle_generate_code(self, **kwargs):
        logger.info("Handling generate_code... Logic TBD.")
        # Example: Use self.prompt_controller to generate code based on params
        return True

    # --- Removed Agent Main Loop --- (Agent methods are called via dispatch)
    # async def run(self):

    # --- Removed Old Mailbox Listener Logic ---
    # def start_listening(self): ...
    # def stop(self): ...
    # def _process_mailbox_message(self, message_path: Path) -> bool: ...

# --- Removed Main Execution Block ---
# if __name__ == "__main__": ... 