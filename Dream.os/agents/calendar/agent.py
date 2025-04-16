import os
# import sys # Removed sys.path manipulation
import traceback
import logging # Added
from datetime import datetime, timedelta
import json
import re
from typing import List # Added

# Remove sys.path manipulation - rely on PYTHONPATH or editable install
# script_dir = os.path.dirname(__file__)
# project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)
# del sys # Remove after use

# Core Component Imports (Absolute)
try:
    # Assuming prompt staging is under core/services?
    from core.services.prompt_staging import stage_and_execute_prompt # Assuming moved
    from core.templates.template_engine import default_template_engine as template_engine # Assuming moved
    from core.coordination.agent_bus import AgentBus # Canonical bus
    from core.memory.governance_memory_engine import log_event # Assuming correct path
    from core.utils.llm_parser import extract_json_from_response # Assuming moved to core/utils
    _core_imports_ok = True
except ImportError as e:
    # Cannot use logger here as it might not be configured
    print(f"FATAL: Failed to import core components for CalendarAgent: {e}. Agent cannot function.", file=sys.stderr)
    _core_imports_ok = False
    # Define dummy log_event only if needed for basic structure check, but fail ideally
    if "governance_memory_engine" in str(e):
         def log_event(etype, src, dtls): print(f"[DummyLOG] {etype}|{src}|{dtls}")

# Configure Logging # Added
logger = logging.getLogger(__name__)

AGENT_ID_DEFAULT = "CalendarAgent"

# TODO: Inherit from BaseAgent (Phase 3)
class CalendarAgent:
    """Agent responsible for scheduling tasks and managing time blocks via AgentBus dispatch.""" # Updated docstring
    AGENT_NAME = AGENT_ID_DEFAULT # Consistency
    CAPABILITIES = ["scheduling", "time_blocking"] # Example

    # Modify __init__ for AgentBus integration
    def __init__(self, agent_id: str = AGENT_ID_DEFAULT, agent_bus: AgentBus = None):
        """Initializes the CalendarAgent and registers with the bus.""" # Updated docstring
        if not _core_imports_ok:
            # Logger might not be available if basicConfig hasn't run
            try: logger.critical("CalendarAgent cannot initialize due to missing core component imports.")
            except NameError: print("CRITICAL: CalendarAgent cannot initialize due to missing core component imports.")
            raise RuntimeError("CalendarAgent cannot initialize due to missing core component imports.")
        if agent_bus is None:
             # Agent requires the bus to be registered and receive dispatches
             raise ValueError("AgentBus instance is required for CalendarAgent initialization.")

        self.agent_id = agent_id
        self.agent_bus = agent_bus

        # Remove handler registration - methods are called directly via dispatch
        # self._register_handlers()

        # Register with Agent Bus (Synchronous)
        try:
            registration_success = self.agent_bus.register_agent(self)
            if registration_success:
                 log_event("AGENT_REGISTERED", self.agent_id, {"message": "Successfully registered with AgentBus."}) # Use log_event for now
                 logger.info(f"Agent {self.agent_id} registered successfully.")
            else:
                 # Log failure if register_agent returns False (e.g., duplicate ID handling failed)
                 log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to register with AgentBus (register_agent returned False)."})
                 logger.error("Agent registration failed.")
                 # Optionally raise error if registration is critical
                 # raise RuntimeError("Failed to register CalendarAgent with AgentBus")
        except Exception as reg_e:
             # Log exception during registration call
             log_event("AGENT_ERROR", self.agent_id, {"error": f"Exception during AgentBus registration: {reg_e}", "traceback": traceback.format_exc()})
             logger.exception("Exception during AgentBus registration.")
             # Optionally raise error
             # raise RuntimeError(f"Failed to register CalendarAgent with AgentBus: {reg_e}") from reg_e

    # Removed handler registration method
    # def _register_handlers(self):

    # --- Core Logic Methods (Now intended to be called via AgentBus.dispatch) ---

    # Renamed from _perform_scheduling to be the public dispatch target
    def schedule_tasks(self, tasks: list[dict], calling_agent_id: str = "Unknown") -> list[dict]:
        """Schedules tasks based on input, called via AgentBus.dispatch."""
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "schedule_tasks", "task_count": len(tasks), "caller": calling_agent_id})
        logger.info(f"Received schedule_tasks request from {calling_agent_id} for {len(tasks)} tasks.")
        # ... (rest of the original schedule_tasks logic goes here) ...
        tasks_to_schedule = {task['task_id']: task.copy() for task in tasks if 'task_id' in task}
        original_task_ids = set(tasks_to_schedule.keys())
        try:
            existing_events = self._load_existing_schedule()
            prompt_context = {"tasks": list(tasks_to_schedule.values()), "existing_events": existing_events}
            template_path = "core/templates/calendar/schedule_tasks.j2" # Corrected path assumption
            prompt_text = template_engine.render(template_path, prompt_context)
            # ... (rest of try block) ...
            if not prompt_text: raise ValueError(f"Failed to render template: {template_path}")
            llm_response = stage_and_execute_prompt(prompt_text, agent_id=self.agent_id, purpose="schedule_tasks")
            if not llm_response: raise ValueError("No response from LLM")
            parsed_schedule = self._parse_llm_schedule(llm_response)
            if parsed_schedule:
                # ... (merging logic) ...
                scheduled_count = 0
                parsed_ids = set()
                for parsed_task in parsed_schedule:
                    task_id = parsed_task.get('task_id')
                    if task_id in tasks_to_schedule:
                        parsed_ids.add(task_id)
                        tasks_to_schedule[task_id].update(parsed_task)
                        if tasks_to_schedule[task_id].get('scheduling_status') == 'Scheduled': scheduled_count += 1
                    else: 
                        log_event("AGENT_WARNING", self.agent_id, {"warning": "LLM returned schedule for unknown task_id", "unknown_task_id": task_id})
                        logger.warning(f"LLM returned schedule for unknown task_id: {task_id}")
                missing_ids = original_task_ids - parsed_ids
                if missing_ids:
                    log_event("AGENT_WARNING", self.agent_id, {"warning": "LLM schedule response missing tasks", "missing_task_ids": list(missing_ids)})
                    logger.warning(f"LLM schedule response missing tasks: {list(missing_ids)}")
                    for task_id in missing_ids: tasks_to_schedule[task_id].setdefault('scheduling_status', 'Failed: Missing in LLM response')
                log_event("AGENT_TASKS_SCHEDULED", self.agent_id, {"method": "schedule_tasks", "scheduled_count": scheduled_count, "total_processed": len(original_task_ids)})
                logger.info(f"Scheduling complete. Scheduled: {scheduled_count}/{len(original_task_ids)}.")
            else:
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Schedule parsing failed", "llm_response_snippet": llm_response[:200]})
                logger.warning(f"Schedule parsing failed. LLM Response Snippet: {llm_response[:200]}")
                for task_id in tasks_to_schedule: tasks_to_schedule[task_id]['scheduling_status'] = 'Failed: Parsing Error'
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"method": "schedule_tasks", "error": str(e), "traceback": traceback.format_exc()})
            logger.exception("Error during schedule_tasks execution.")
            for task_id in tasks_to_schedule: tasks_to_schedule[task_id]['scheduling_status'] = 'Failed: Agent Error'
        return list(tasks_to_schedule.values()) # Return results directly

    # Renamed from _perform_slot_finding
    def find_available_slots(self, duration_minutes: int, constraints: dict = None, calling_agent_id: str = "Unknown") -> list[dict]:
        """Finds available time slots based on duration and constraints, called via AgentBus.dispatch."""
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "find_available_slots", "duration": duration_minutes, "constraints": constraints, "caller": calling_agent_id})
        logger.info(f"Received find_available_slots request from {calling_agent_id} for duration {duration_minutes} mins.")
        # ... (rest of the original find_available_slots logic goes here) ...
        available_slots = []
        try:
            existing_events = self._load_existing_schedule()
            prompt_context = {"duration_minutes": duration_minutes, "constraints": constraints or {}, "existing_events": existing_events}
            template_path = "core/templates/calendar/find_available_slots.j2" # Corrected path assumption
            prompt_text = template_engine.render(template_path, prompt_context)
            if not prompt_text: raise ValueError(f"Failed to render template: {template_path}")
            llm_response = stage_and_execute_prompt(prompt_text, agent_id=self.agent_id, purpose="find_available_slots")
            if not llm_response: raise ValueError("No response from LLM")
            parsed_slots = self._parse_llm_slots(llm_response)
            if parsed_slots is None: # Parsing failed
                available_slots = []
                log_event("AGENT_WARNING", self.agent_id, {"warning": "Slot parsing failed", "llm_response_snippet": llm_response[:200]})
                logger.warning(f"Slot parsing failed. LLM Response Snippet: {llm_response[:200]}")
            else:
                available_slots = parsed_slots
                log_event("AGENT_SLOTS_FOUND", self.agent_id, {"method": "find_available_slots", "slot_count": len(available_slots)})
                logger.info(f"Slot finding complete. Found {len(available_slots)} slots.")
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"method": "find_available_slots", "error": str(e), "traceback": traceback.format_exc()})
            logger.exception("Error during find_available_slots execution.")
            available_slots = [] # Ensure empty list on error
        return available_slots # Return results directly

    # --- Helper Methods --- (Keep _load_existing_schedule, _parse_llm_schedule, _parse_llm_slots)
    # ... (These likely remain internal helpers) ...
    def _load_existing_schedule(self) -> list[dict]:
        # Placeholder: Load from file, DB, or external API
        log_event("AGENT_INFO", self.agent_id, {"message": "Loading existing schedule (placeholder)"})
        logger.debug("Loading existing schedule (placeholder)." )
        # Example placeholder data
        return [
            {"summary": "Team Meeting", "start_time": "2023-10-28T09:00:00Z", "end_time": "2023-10-28T10:00:00Z"},
            {"summary": "Focus Work", "start_time": "2023-10-28T10:30:00Z", "end_time": "2023-10-28T12:00:00Z"}
        ]

    def _parse_llm_schedule(self, llm_response: str) -> list[dict] | None:
        log_event("AGENT_ACTION_PROGRESS", self.agent_id, {"action": "_parse_llm_schedule"})
        logger.debug("Parsing LLM schedule response...")
        extracted_json = extract_json_from_response(llm_response)
        if extracted_json and isinstance(extracted_json, list):
            # TODO: Add validation for required fields (task_id, status, start/end times?)
            logger.debug(f"Successfully parsed {len(extracted_json)} schedule items.")
            return extracted_json
        else:
            logger.warning(f"Could not parse schedule list from LLM response. Extracted: {type(extracted_json)}")
            return None

    def _parse_llm_slots(self, llm_response: str) -> list[dict] | None:
        log_event("AGENT_ACTION_PROGRESS", self.agent_id, {"action": "_parse_llm_slots"})
        logger.debug("Parsing LLM slots response...")
        extracted_json = extract_json_from_response(llm_response)
        if extracted_json and isinstance(extracted_json, list):
             # TODO: Add validation for required fields (start_time, end_time)
             logger.debug(f"Successfully parsed {len(extracted_json)} available slots.")
             return extracted_json
        else:
            logger.warning(f"Could not parse slot list from LLM response. Extracted: {type(extracted_json)}")
            return None

# Example Usage
if __name__ == '__main__':
    # Dummy log_event
    def log_event(etype, src, dtls): print(f"[LOG] {etype} | {src} | {dtls}")
    import json
    
    calendar = CalendarAgent()
    
    # Test find_available_slots
    print("\n--- Finding Available Slots --- ")
    slots = calendar.find_available_slots(duration_minutes=45, constraints={'buffer_minutes': 10})
    print("\n--- Available Slots Result --- ")
    print(json.dumps(slots, indent=2))
    
    # Test schedule_tasks
    dummy_tasks = [
        {'task_id': 'T1', 'description': 'Task A', 'estimated_time': '2h', 'dependencies': []},
        {'task_id': 'T2', 'description': 'Task B', 'estimated_time': '30m', 'dependencies': ['T1']}
    ]
    scheduled = calendar.schedule_tasks(dummy_tasks)
    print("\n--- Scheduled Tasks --- ")
    print(json.dumps(scheduled, indent=2)) 