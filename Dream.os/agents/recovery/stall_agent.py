import time
import json
import traceback # Added
from pathlib import Path
import logging
from typing import List, Any # Added Any

# Assuming task_utils is importable from parent dir
try:
    # from .._agent_coordination.task_utils import read_tasks # Old import
    from core.utils.task_utils import read_tasks # New absolute import
    from core.tools.context import produce_project_context # New absolute import
    from core.coordination.agent_bus import AgentBus # Import canonical bus
    from core.memory.governance_memory_engine import log_event # Added
    _core_imports_ok = True
except ImportError as e:
    # Use logger once defined
    # print(f"Error: Could not import core utilities/AgentBus: {e}")
    _core_imports_ok = False
    # Define dummy functions if needed for basic structure, but agent should fail
    def read_tasks(*args, **kwargs): return None
    def produce_project_context(*args, **kwargs): return {}
    # Add dummy log_event if needed
    if "governance_memory_engine" in str(e):
         def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")
    # AgentBus dummy might not be needed if init requires it

# Configure logging
logger = logging.getLogger(__name__) # Use __name__ for logger
if not logger.hasHandlers():
    # Check root logger instead of checking self and then root
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Define AGENT_ID_DEFAULT earlier
AGENT_ID_DEFAULT = "StallRecoveryAgent"

# TODO: Inherit from BaseAgent (Phase 3)
class StallRecoveryAgent:
    """Detects system stalls by monitoring logs and dispatches recovery tasks via AgentBus.""" # Updated docstring
    AGENT_NAME = AGENT_ID_DEFAULT
    CAPABILITIES = ["stall_detection", "recovery_task_dispatch"] # Example

    # Modify __init__ for AgentBus integration
    def __init__(self,
                 agent_id: str = AGENT_ID_DEFAULT,
                 agent_bus: AgentBus = None, # Now required
                 project_root=".",
                 log_file_path="logs/agent_ChatCommander.log", # TODO: Make log path configurable via agent config
                 task_list_path="master_task_list.json" # Default to master list - TODO: Remove dependency
                 ):
        if not _core_imports_ok:
             # Use logger if available, otherwise print critical error before raising
             msg = "StallRecoveryAgent cannot initialize due to missing core component imports."
             try: logger.critical(msg)
             except NameError: print(f"CRITICAL: {msg}")
             raise RuntimeError(msg)
        if agent_bus is None:
            raise ValueError("AgentBus instance is required for StallRecoveryAgent initialization.")

        self.agent_id = agent_id
        self.agent_bus = agent_bus # Required
        self.project_root = Path(project_root).resolve()
        self.log_file_path = self.project_root / log_file_path
        self.task_list_path = self.project_root / task_list_path # TODO: Remove direct task list dependency
        self.last_log_size = 0
        try:
            if self.log_file_path.exists():
                self.last_log_size = self.log_file_path.stat().st_size
                logger.info(f"Monitoring log file: {self.log_file_path} (Initial size: {self.last_log_size})")
            else:
                 logger.warning(f"Monitored log file does not exist initially: {self.log_file_path}")
        except Exception as e:
            logger.warning(f"Could not get initial log file size for {self.log_file_path}: {e}")

        # Register with Agent Bus (Synchronous)
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

    # --- Public Dispatch Target Method ---
    def perform_stall_check(self, calling_agent_id: str = "Unknown") -> bool:
        """Checks for system stall and attempts recovery if detected.
        
        Called via AgentBus.dispatch(). Returns True if recovery was attempted, False otherwise.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "perform_stall_check", "caller": calling_agent_id})
        logger.info(f"Received perform_stall_check request from {calling_agent_id}.")
        
        recovery_attempted = False
        try:
            log_snippet = self.check_for_stall() # Internal check
            if log_snippet:
                logger.info("Stall detected, attempting recovery...")
                dispatched_task_id = self.attempt_recovery(log_snippet) # Internal recovery attempt
                if dispatched_task_id:
                    recovery_attempted = True
                    log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "perform_stall_check", "result": "Recovery Attempted", "recovery_task_id": dispatched_task_id})
                else:
                    log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "perform_stall_check", "reason": "Recovery dispatch failed"})
                    logger.error("Stall detected, but failed to dispatch recovery task.")
            else:
                 log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "perform_stall_check", "result": "No Stall Detected"})
                 logger.info("No stall detected.")
                 
        except Exception as e:
            log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "perform_stall_check", "error": str(e), "traceback": traceback.format_exc()})
            logger.exception("Error during perform_stall_check execution.")
            
        return recovery_attempted # Return status

    # --- Internal Helper Methods ---
    def _is_system_busy(self) -> bool:
        """Checks if there are active tasks in the task list."""
        # TODO: Replace direct file read with AgentBus query for system status/active tasks (Phase 2/3)
        logger.warning("_is_system_busy currently reads task list file directly. Needs refactoring for AgentBus.")
        if not self.agent_bus:
             logger.error("Cannot check system busy status: AgentBus not available.") # Should not happen if init requires bus
             return False # Assume not busy if bus missing (error state)
        
        # Conceptual: Query bus
        # try:
        #     status_result = self.agent_bus.dispatch(target_agent_id="SystemMonitorAgent", method_name="get_system_status")
        #     return status_result.get("is_busy", False) if status_result else False
        # except Exception as query_e:
        #     logger.error(f"Failed to query system status via AgentBus: {query_e}")
        #     # Fallback or assume busy/not busy?
        #     return False # Assuming not busy on query failure

        logger.info("AgentBus query for system busy status not yet implemented. Falling back to file read.")
        tasks = read_tasks(self.task_list_path)

        if tasks is None: # Handle read failure
            logger.warning("Could not read task list to check busy status. Assuming not busy.")
            return False
        
        for task in tasks:
            status = task.get("status", "").upper()
            # TODO: Define busy statuses more robustly (e.g., IN_PROGRESS, CLAIMED?)
            if status in ["PENDING", "PROCESSING", "IN_PROGRESS"]:
                logger.debug(f"System busy: Task {task.get('task_id')} is {status}.")
                return True
        logger.debug("System not busy: No active tasks found.")
        return False

    def check_for_stall(self) -> str | None:
        """
        Checks the monitored log file for signs of a stall, but only if the system
        doesn't appear busy based on the task list.
        Returns the log tail snippet if a stall is detected, otherwise None.
        """
        try:
            current_log_size = self.log_file_path.stat().st_size
            log_unchanged = (current_log_size == self.last_log_size and current_log_size > 0)
            
            if log_unchanged:
                logger.debug(f"Log file size unchanged ({self.log_file_path}). Checking system busy status...")
                if not self._is_system_busy():
                    logger.warning(f"Potential stall detected: Log file size hasn't changed AND no active tasks found.")
                    # Read last N lines/chars for context analysis
                    try:
                        with self.log_file_path.open('r', encoding='utf-8') as f:
                            # Efficiently get last ~10k chars (adjust as needed)
                            f.seek(max(0, current_log_size - 10000)) 
                            log_tail = f.read() 
                        return log_tail # Return the tail for context production
                    except Exception as read_e:
                         logger.error(f"Error reading log tail for stall analysis: {read_e}")
                         return None # Cannot analyze if read fails
                else:
                     logger.info("Log file size unchanged, but system is busy with tasks. No stall declared.")
                     # Update last_log_size even if busy, so next check uses current size
                     self.last_log_size = current_log_size 
                     return None
            else:
                # Log changed size (optional, can be verbose)
                # logger.debug(f"Log file size changed: {self.last_log_size} -> {current_log_size}")
                pass
                
            # Always update size if it changed or if we didn't declare stall despite no change
            self.last_log_size = current_log_size
            return None 
        except FileNotFoundError:
            # Don't treat missing log file as a stall unless persistent
            logger.warning(f"Monitored log file not found: {self.log_file_path}")
            self.last_log_size = 0
            return None
        except Exception as e:
            logger.error(f"Error checking log file for stall: {e}", exc_info=True)
            return None

    def log_stall_event(self, context: dict, recovery_dispatched: bool):
        """Logs the details of a detected stall event to a JSON file."""
        log_path = self.project_root / "logs" / "stall_events.log" # Using .log extension for consistency
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "stall_category": context.get("stall_category", "UNKNOWN"),
            "relevant_files": context.get("relevant_files", []),
            "suggested_action_keyword": context.get("suggested_action_keyword", "N/A"),
            "recovery_dispatched": recovery_dispatched,
            "recovery_task_id": context.get("recovery_task_id", None) # Add task_id if available
        }
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True) # Ensure logs directory exists
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to log stall event to {log_path}: {e}") # Use logger

    def dispatch_recovery_task(self, context: dict) -> Any:
        """Generates and dispatches a recovery task via AgentBus.dispatch().""" # Updated docstring
        if not self.agent_bus:
            logger.error("Cannot dispatch recovery task: AgentBus not available.")
            return None

        stall_category = context.get("stall_category", "UNCATEGORIZED")
        recovery_task_id = f"recovery_{stall_category.lower()}_{int(time.time())}"

        # Determine target method name (assuming it matches task_type convention)
        # and assemble parameters for the target agent's method
        target_method_name = "generic_recovery" # Default method
        params = {
            "stall_category": stall_category,
            "relevant_files": context.get("relevant_files", [])[:3],
            "recovery_intent": context.get("suggested_action_keyword", "Perform general diagnostics.")
            # Add task_id? The target method might need it.
            # "task_id": recovery_task_id 
        }
        target_agent = "CursorControlAgent" # Default target agent ID

        if stall_category == "NO_INPUT": target_method_name = "resume_operation"
        elif stall_category == "NEEDS_TASKS": target_method_name = "generate_task"
        elif stall_category == "LOOP_BREAK": target_method_name = "diagnose_loop"
        elif stall_category == "AWAIT_CONFIRM": target_method_name = "confirmation_check"
        elif stall_category == "MISSING_CONTEXT": target_method_name = "context_reload"
        elif stall_category == "UNCLEAR_OBJECTIVE": target_method_name = "clarify_objective"
        # TODO: Ensure target_agent (CursorControlAgent) has these methods defined as dispatch targets

        # Adjust params if needed for specific target methods
        if target_method_name == "generate_task":
             params["task_description"] = context.get("suggested_action_keyword", "Generate next logical task based on stall context.")
             params["priority"] = "HIGH"
        elif target_method_name == "context_reload":
             # Context reload needs a target_agent param for *its* dispatch
             params["target_agent"] = context.get("target_agent_for_reload", None) # Example: context needs to provide this
             params["original_task_id"] = recovery_task_id # Pass recovery task ID
             if not params["target_agent"]:
                 logger.error(f"Cannot dispatch context_reload for {recovery_task_id}: Missing target_agent_for_reload in context.")
                 return None

        # Remove params not needed by the target method?
        # Might be safer to keep them or define schemas

        logger.info(f"Dispatching recovery method {target_agent}.{target_method_name} for task {recovery_task_id}")
        try:
            # Use AgentBus.dispatch()
            dispatch_result = self.agent_bus.dispatch(
                target_agent_id=target_agent,
                method_name=target_method_name,
                calling_agent_id=self.agent_id, # Pass caller context
                **params
            )
            logger.info(f"Recovery dispatch successful. Result: {dispatch_result}")
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "dispatch_recovery_task", "recovery_task_id": recovery_task_id, "target_agent": target_agent, "target_method": target_method_name})
            # Return the dispatch result AND the task ID for logging
            return {"task_id": recovery_task_id, "dispatch_result": dispatch_result} 
        except Exception as e:
            logger.exception(f"Failed to dispatch recovery task {recovery_task_id} via AgentBus")
            log_event("AGENT_ACTION_FAILED", self.agent_id, {"action": "dispatch_recovery_task", "recovery_task_id": recovery_task_id, "error": str(e)})
            return None

    def attempt_recovery(self, log_snippet) -> str | None:
        """
        Uses the context bridge utility to analyze the situation, log the event,
        and dispatch a recovery task. Returns the recovery task ID if dispatched, else None.
        """ # Updated docstring
        logger.info("Attempting stall recovery...")
        context = produce_project_context(log_snippet, str(self.project_root), return_dict=True)
        recovery_dispatched = False
        dispatched_task_id = None

        if context:
            logger.info("--- Stall Context ---")
            logger.info(f"Category: {context['stall_category']}")
            logger.info(f"Suggested Keyword: {context['suggested_action_keyword']}")
            logger.info(f"Relevant Files: {context['relevant_files']}")
            logger.info("---------------------")

            # Dispatch recovery task
            dispatch_info = self.dispatch_recovery_task(context)
            if dispatch_info and isinstance(dispatch_info, dict):
                dispatched_task_id = dispatch_info.get("task_id")
                if dispatched_task_id:
                     recovery_dispatched = True
                     context["recovery_task_id"] = dispatched_task_id # Add for logging

            # Log the event regardless of dispatch success, but note if dispatched
            self.log_stall_event(context, recovery_dispatched)
            # ... (logging action desc remains same) ...
            action_desc = "Perform general diagnostics or escalate."
            if context['stall_category'] == "AWAIT_CONFIRM":
                action_desc = "Analyze context and potentially send confirmation request."
            elif context['stall_category'] == "NO_INPUT":
                 action_desc = "Check task queue or generate next task."
            logger.info(f"Recovery Action: {action_desc}")
        else:
            logger.error("Failed to generate stall context.")
            # Log minimal failure event
            self.log_stall_event({"stall_category": "CONTEXT_FAILURE"}, False)
            
        return dispatched_task_id # Return the task ID if dispatched

    # Removed the run() method - triggering should be external via dispatch

# --- Removed Direct Execution Block ---
# if __name__ == "__main__":
#     ...

# Example instantiation and run (if executed directly)
if __name__ == "__main__":
    # Assumes running from the workspace root where logs/ and tools/ exist
    recovery_agent = StallRecoveryAgent(agent_id="StallRecoveryAgent", agent_bus=None, project_root=".") 
    recovery_agent.run() 