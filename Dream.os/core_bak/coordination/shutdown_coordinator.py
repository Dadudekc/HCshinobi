"""Handles the multi-phase shutdown sequence for the Agent Bus system."""

import asyncio
import json
import logging
import sys
import uuid # Added for directive ID generation
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Callable, Optional # Added Optional

from .agent_registry import AgentRegistry
from .system_diagnostics import SystemDiagnostics
from core.coordination.dispatcher import EventDispatcher, Event, EventType
from core.utils.system import SystemUtils

logger = logging.getLogger(__name__)

class ShutdownCoordinator:
    """Orchestrates the agent and system shutdown process."""

    def __init__(self,
                 agent_registry: AgentRegistry,
                 diagnostics: SystemDiagnostics,
                 event_dispatcher: EventDispatcher,
                 sys_utils: SystemUtils,
                 dispatch_event_callback: Callable):
        self.agent_registry = agent_registry
        self.diagnostics = diagnostics
        self.event_dispatcher = event_dispatcher
        self.sys_utils = sys_utils
        self._dispatch_event = dispatch_event_callback
        self.shutdown_directive_template: Optional[str] = None
        self.shutdown_directive_path = Path("user_prompts/shutdown_directive.prompt.txt")
        self._load_shutdown_directive()

    def _load_shutdown_directive(self):
        """Load shutdown directive template."""
        try:
            if self.shutdown_directive_path.exists():
                self.shutdown_directive_template = self.shutdown_directive_path.read_text()
                logger.info(f"Loaded shutdown directive from {self.shutdown_directive_path}")
            else:
                logger.warning(f"Shutdown directive file not found at {self.shutdown_directive_path}. Using default structure.")
                # Provide a fallback minimal structure if file is missing
                self.shutdown_directive_template = json.dumps({
                    "directive_id": "DEFAULT_SHUTDOWN",
                    "description": "Default shutdown sequence.",
                    "execution_sequence": {
                        "prep": {"description": "Prepare for shutdown", "actions": []},
                        "persist": {"description": "Persist state", "actions": []},
                        "cleanup": {"description": "Clean up resources", "actions": []},
                        "broadcast": {"description": "Final broadcast", "actions": []}
                    }
                })
        except Exception as e:
            logger.error(f"Failed to load shutdown directive: {e}", exc_info=True)
            # Ensure template is set to avoid errors later
            if self.shutdown_directive_template is None:
                 # Use an empty JSON object as a safe fallback
                 self.shutdown_directive_template = json.dumps({})

    async def broadcast_shutdown(self, shutdown_in_progress_flag: bool) -> bool:
        """Initiate system-wide shutdown sequence.

        Args:
            shutdown_in_progress_flag: A boolean indicating if shutdown is already running.

        Returns:
            True if shutdown proceeds successfully, False otherwise.
        """
        if shutdown_in_progress_flag:
            logger.warning("Shutdown requested, but already in progress.")
            return False

        logger.info("Initiating shutdown sequence...")

        # Run pre-shutdown diagnostics first
        diagnostics_result = await self.diagnostics.run_pre_shutdown_diagnostics()

        # Check for critical failures from diagnostics
        if diagnostics_result["total_failed"] > 0:
            logger.warning("Pre-shutdown diagnostics reported failures.")
            if diagnostics_result["critical_warnings"]:
                 logger.error("Critical pre-shutdown warnings detected:")
                 for warning in diagnostics_result["critical_warnings"]:
                     logger.critical(f"  - {warning}")
                 # Decide if critical errors should halt shutdown (configurable later?)
                 # For now, let's assume critical means halt.
                 logger.error("Halting shutdown due to critical diagnostic failures.")
                 # Optionally dispatch an event indicating halted shutdown
                 await self._dispatch_event(
                    "shutdown_halted",
                    {"reason": "Critical diagnostic failures", "details": diagnostics_result},
                    priority=0
                 )
                 return False # Indicate shutdown did not proceed
            else:
                logger.warning("Proceeding with shutdown despite non-critical diagnostic failures.")

        start_time = datetime.now()
        active_agents_count = len(await self.agent_registry.get_active_agents_set())

        await self._dispatch_event(
            "shutdown_initiated",
            {
                "active_agents": active_agents_count,
                "timestamp": start_time.isoformat()
            },
            priority=0
        )

        # --- Shutdown Execution --- #
        shutdown_outcome_successful = False
        try:
            # Define shutdown phases and timeouts (consider making configurable)
            phases = {
                "prep": 5,
                "persist": 10,
                "cleanup": 10,
                "broadcast": 5
            }

            all_phases_reported_success = True
            for phase, timeout in phases.items():
                 phase_reported_success = await self._execute_shutdown_phase(phase, timeout)
                 if not phase_reported_success:
                     all_phases_reported_success = False
                     logger.warning(f"Shutdown phase '{phase}' reported failure. Continuing sequence cautiously.")
                     # Potentially trigger emergency shutdown here if a phase failure is critical

            # Verify final shutdown state only if all phases seemed ok
            if all_phases_reported_success:
                shutdown_verification_passed = await self._verify_shutdown()
                shutdown_outcome_successful = shutdown_verification_passed
            else:
                logger.error("Skipping final shutdown verification due to failures in previous phases.")
                shutdown_outcome_successful = False # If any phase failed, outcome is fail

            duration = (datetime.now() - start_time).total_seconds()
            shutdown_ready_count = len(await self.agent_registry.get_shutdown_ready_set())

            if shutdown_outcome_successful:
                logger.info(f"Shutdown completed successfully in {duration:.2f} seconds.")
                await self._dispatch_event(
                    "shutdown_completed",
                    {
                        "duration": duration,
                        "compliant_agents": shutdown_ready_count
                    },
                    priority=0
                )
            else:
                logger.error(f"Shutdown sequence finished but did not complete successfully (Duration: {duration:.2f}s). Verification failed or phase errors occurred.")
                active_agents = await self.agent_registry.get_active_agents_set()
                ready_agents = await self.agent_registry.get_shutdown_ready_set()
                missing_agents = list(active_agents - ready_agents)
                await self._dispatch_event(
                    "shutdown_incomplete",
                    {
                        "duration": duration,
                        "missing_agents": missing_agents,
                        "reason": "Verification failed or phase errors occurred"
                    },
                    priority=0
                )

        except Exception as e:
            logger.error(f"Shutdown sequence failed unexpectedly during execution: {e}", exc_info=True)
            # Trigger emergency shutdown immediately on unexpected error
            await self._emergency_shutdown(f"Exception during shutdown sequence: {e}")
            return False # Indicate failure

        return shutdown_outcome_successful

    async def _execute_shutdown_phase(self, phase: str, timeout: int) -> bool:
        """Execute a specific shutdown phase by broadcasting directives.
        Returns True if the phase completes without timeout or major errors, False otherwise.
        """
        phase_start_time = datetime.now()
        logger.info(f"Starting shutdown phase: '{phase}' (timeout: {timeout}s)")

        await self._dispatch_event(
            "shutdown_phase_started",
            {
                "phase": phase,
                "timeout": timeout,
                "timestamp": phase_start_time.isoformat()
            },
            priority=1 # Higher priority for phase events
        )

        phase_success = True
        try:
            # Create phase-specific directive from template
            directive = self._create_phase_directive(phase)
            if not directive:
                 logger.error(f"Could not create directive for phase '{phase}'. Skipping phase execution.")
                 return False # Cannot proceed without directive

            # Broadcast to all active agents
            active_agents = await self.agent_registry.get_active_agents_set()
            tasks = []
            logger.debug(f"Dispatching phase '{phase}' directive to {len(active_agents)} agents.")
            for agent_id in active_agents:
                 event = Event(
                     type=EventType.SYSTEM,
                     source_id="agent_bus", # Source is the bus orchestrator
                     priority=0 # High priority for shutdown commands
                 )
                 # Ensure data payload is structured correctly
                 event.data = {
                     "type": "shutdown_directive", # Standardized type for directives
                     "agent_id": agent_id,      # Target agent
                     "directive_id": directive.get("directive_id", f"SHUTDOWN_{phase.upper()}"),
                     "phase": phase,
                     "config": directive.get("config", {}), # Config specific to the phase
                     "timestamp": directive.get("timestamp", datetime.now().isoformat())
                 }
                 # Use the event dispatcher associated with the bus
                 task = asyncio.create_task(
                     self.event_dispatcher.dispatch_event(event)
                 )
                 tasks.append(task)

            if not tasks:
                logger.info(f"No active agents to notify for phase '{phase}'. Phase complete.")
                # No failure if no agents need notification
            else:
                # Wait for dispatches to complete or timeout
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=timeout,
                    return_when=asyncio.ALL_COMPLETED
                )

                # Handle timeouts/cancellations
                if pending:
                    logger.warning(f"Phase '{phase}' timed out waiting for directive dispatch/ack. {len(pending)} tasks pending.")
                    phase_success = False # Timeout is considered a failure for the phase
                    for task in pending:
                        task.cancel()
                        try:
                            await task # Wait for cancellation to complete
                        except asyncio.CancelledError:
                            pass # Expected
                        except Exception as task_e:
                            logger.error(f"Error cancelling pending task for phase '{phase}': {task_e}")

                # Check results of completed tasks (if they return status)
                for task in done:
                     try:
                         result = task.result()
                         # Assuming dispatch_event returns True on success or raises error
                         if result is False: # Or check specific error conditions if applicable
                             phase_success = False
                             logger.warning(f"Directive dispatch reported failure for an agent during phase '{phase}'.")
                     except asyncio.CancelledError: # Task was cancelled due to timeout
                          logger.warning(f"A directive dispatch task was cancelled for phase '{phase}'.")
                          phase_success = False # If any task was cancelled, phase failed
                     except Exception as task_e:
                         logger.error(f"Error occurred retrieving result from dispatch task during phase '{phase}': {task_e}")
                         phase_success = False

        except Exception as e:
            logger.error(f"Critical error executing shutdown phase '{phase}': {e}", exc_info=True)
            phase_success = False
            # Consider emergency shutdown here? Depending on policy.
            # await self._emergency_shutdown(f"Exception during phase {phase}: {e}")

        duration = (datetime.now() - phase_start_time).total_seconds()
        logger.info(f"Completed shutdown phase: '{phase}' in {duration:.2f}s (Reported Success: {phase_success}).")

        await self._dispatch_event(
            "shutdown_phase_completed",
            {
                "phase": phase,
                "success": phase_success,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            },
            priority=1
        )

        return phase_success

    def _create_phase_directive(self, phase: str) -> Optional[Dict]:
        """Create phase-specific shutdown directive from the loaded template."""
        if not self.shutdown_directive_template:
             logger.error("Shutdown directive template is not loaded.")
             return None
        try:
            # Ensure template is valid JSON before proceeding
            base_directive = json.loads(self.shutdown_directive_template)
            sequence = base_directive.get("execution_sequence", {})
            phase_config = sequence.get(phase)

            if phase_config is None:
                logger.warning(f"Phase '{phase}' not found in shutdown directive sequence. Creating default.")
                # Provide a default minimal structure if phase is missing
                phase_config = {"description": f"Default action for phase {phase}", "actions": []}

            # Generate a unique ID for this specific directive instance
            directive_id = f"SHUTDOWN_{phase.upper()}_{uuid.uuid4().hex[:6]}"

            return {
                "directive_id": directive_id,
                "phase": phase,
                "config": phase_config, # Contains description, actions, etc.
                "timestamp": datetime.now().isoformat()
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse shutdown directive template JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error creating phase '{phase}' directive: {e}", exc_info=True)
            return None

    async def _verify_shutdown(self) -> bool:
        """Verify shutdown completion and system state.
        Returns True if all checks pass, False otherwise.
        """
        logger.info("Verifying final shutdown state...")
        all_checks_passed = True
        try:
            # Check 1: All agents reported ready
            active_agents = await self.agent_registry.get_active_agents_set()
            ready_agents = await self.agent_registry.get_shutdown_ready_set()
            missing_agents = active_agents - ready_agents
            if missing_agents:
                logger.error(f"Shutdown Verification Failed: Agents not ready: {missing_agents}")
                all_checks_passed = False
            else:
                 logger.debug("Verification Check 1 Passed: All active agents reported shutdown ready.")

            # Check 2: Critical state files (re-run relevant diagnostic check)
            state_check_result = await self.diagnostics._check_state_files()
            if not state_check_result["passed"]:
                 # Log specific errors found by the check
                 error_details = state_check_result.get('errors', ['No specific errors listed'])
                 logger.error(f"Shutdown Verification Failed: State file check failed. Errors: {error_details}")
                 all_checks_passed = False
            else:
                 logger.debug("Verification Check 2 Passed: State file check passed.")

            # Check 3: Resource cleanup (re-run relevant diagnostic check)
            resource_check_result = await self.diagnostics._check_resources()
            if not resource_check_result["passed"]:
                # Log specific errors, but only fail verification if critical issues remain
                error_details = resource_check_result.get('errors', ['No specific errors listed'])
                logger.warning(f"Shutdown Verification Warning: Resource check failed. Errors: {error_details}")
                if resource_check_result.get("critical"):
                    logger.error("Critical resource check failure during final verification.")
                    all_checks_passed = False
                else:
                    logger.debug("Non-critical resource check failure noted during verification.")
            else:
                 logger.debug("Verification Check 3 Passed: Resource check passed.")

            # Check 4: Event queue is empty (re-run relevant diagnostic check)
            event_check_result = await self.diagnostics._check_event_system()
            queue_size = event_check_result["details"].get("queue_size", -1)
            if queue_size != 0:
                logger.warning(f"Shutdown Verification Warning: Event queue size is {queue_size}. Events might have been missed.")
                # Depending on policy, a non-empty queue might be an error or just a warning.
                # For now, treat as a warning, not a hard failure.
                # all_checks_passed = False
            else:
                 logger.debug("Verification Check 4 Passed: Event queue is empty.")

            logger.info(f"Final Shutdown Verification Result: {'Success' if all_checks_passed else 'Failed'}")
            return all_checks_passed

        except Exception as e:
            logger.error(f"Shutdown verification process encountered an unexpected error: {e}", exc_info=True)
            return False

    async def _emergency_shutdown(self, reason: str = "Unknown reason"):
        """Execute emergency shutdown procedure."""
        logger.critical(f"Initiating emergency shutdown due to: {reason}")

        try:
            # Attempt to get agent state before shutting down
            try:
                active_agents_list = list(await self.agent_registry.get_active_agents_set())
                ready_agents_list = list(await self.agent_registry.get_shutdown_ready_set())
            except Exception as state_e:
                 logger.error(f"Could not retrieve agent state during emergency shutdown: {state_e}")
                 active_agents_list = ["unknown"]
                 ready_agents_list = ["unknown"]

            # Save emergency state snapshot
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "reason": reason,
                "active_agents": active_agents_list,
                "shutdown_ready": ready_agents_list,
                "error_state": True
            }

            emergency_file = Path("memory/emergency_snapshot.json")
            try:
                 emergency_file.parent.mkdir(parents=True, exist_ok=True)
                 emergency_file.write_text(
                     json.dumps(snapshot, indent=2)
                 )
                 logger.info(f"Emergency state snapshot saved to {emergency_file}")
            except Exception as file_e:
                 logger.error(f"Failed to save emergency snapshot: {file_e}")

            # Force cleanup critical resources via SystemUtils
            try:
                await self.sys_utils.force_cleanup()
                logger.info("Attempted forceful resource cleanup.")
            except Exception as cleanup_e:
                logger.error(f"Error during forceful resource cleanup: {cleanup_e}")

            # Log emergency shutdown event (best effort)
            try:
                await self._dispatch_event(
                    "emergency_shutdown",
                    snapshot,
                    priority=-1 # Highest priority
                )
                logger.critical("Emergency shutdown event dispatched.")
            except Exception as dispatch_e:
                logger.error(f"Failed to dispatch emergency shutdown event: {dispatch_e}")

        except Exception as e:
            # Log critical failure even during emergency shutdown
            logger.critical(f"Emergency shutdown procedure itself failed critically: {e}", exc_info=True)
        finally:
            # Ensure event dispatcher stops
            try:
                logger.info("Stopping event dispatcher during emergency shutdown...")
                await self.event_dispatcher.stop()
                logger.info("Event dispatcher stopped during emergency shutdown.")
            except Exception as dispatch_stop_e:
                 logger.critical(f"Failed to stop event dispatcher during emergency shutdown: {dispatch_stop_e}")

            # Force exit the application
            logger.critical("Forcing system exit now.")
            sys.exit(1) 