import os
import sys
import json
import re # Needed for parsing
from datetime import datetime

# Add project root for imports
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core Service Imports
try:
    from dreamforge.core.template_engine import render_template
    from dreamforge.core.prompt_staging_service import stage_and_execute_prompt
    from dreamforge.core.governance_memory_engine import log_event # Assuming central logger
except ImportError as e:
    print(f"[CalendarAgent] Critical import failed: {e}. Functionality may be limited.")
    # Define fallbacks if necessary
    def render_template(template_name, context): return None
    def stage_and_execute_prompt(agent_id, prompt_subject, prompt_context, llm_config=None): return "Error: Prompt staging service unavailable."
    def log_event(event_type, agent_source, details): pass

AGENT_ID = "CalendarAgent"

class CalendarAgent:
    """
    Responsible for scheduling tasks onto a calendar, considering dependencies,
    durations, and existing commitments.
    Communicates with the LLM via the Prompt Staging Service for complex scheduling logic.
    """
    def __init__(self, llm_config=None):
        self.agent_id = AGENT_ID
        self.llm_config = llm_config or {}
        log_event("AGENT_INIT", self.agent_id, {"status": "initialized", "llm_config_keys": list(self.llm_config.keys())})

    def _parse_llm_schedule_response(self, llm_response: str, original_tasks: list) -> list | None:
        """Parses the LLM response JSON for scheduled tasks and merges with original data."""
        log_event("AGENT_DEBUG", self.agent_id, {"message": "Attempting to parse LLM schedule response", "response_snippet": llm_response[:100]})
        try:
            # Extract JSON list from ```json block or direct list
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', llm_response, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            elif llm_response.strip().startswith('[') and llm_response.strip().endswith(']'):
                 json_str = llm_response.strip()
            else:
                 raise ValueError("Response does not appear to be a valid JSON list or wrapped in ```json")

            parsed_schedule_list = json.loads(json_str)

            if not isinstance(parsed_schedule_list, list):
                log_event("AGENT_ERROR", self.agent_id, {"error": "Parsed JSON schedule is not a list", "parsed_type": type(parsed_schedule_list).__name__})
                return None

            # Create a dictionary of original tasks for easy lookup
            original_tasks_dict = {task['task_id']: task for task in original_tasks if 'task_id' in task}
            updated_tasks = []
            returned_ids = set()

            for item in parsed_schedule_list:
                if not isinstance(item, dict) or 'task_id' not in item:
                    log_event("AGENT_WARNING", self.agent_id, {"warning": "Ignoring invalid item in parsed schedule (missing task_id or not dict)", "item": item})
                    continue
                
                task_id = item['task_id']
                returned_ids.add(task_id)

                if task_id in original_tasks_dict:
                    # Merge LLM results into the original task data
                    merged_task = original_tasks_dict[task_id].copy()
                    merged_task.update({
                        'start_time': item.get('start_time'),
                        'end_time': item.get('end_time'),
                        'scheduling_status': item.get('scheduling_status', 'Unknown') # Default if missing
                    })
                    updated_tasks.append(merged_task)
                else:
                    log_event("AGENT_WARNING", self.agent_id, {"warning": "LLM returned schedule for unknown/unexpected task_id", "unknown_task_id": task_id})
                    # Option: Include the unexpected task anyway?
                    # updated_tasks.append(item) 

            # Check for tasks that were sent but not returned by the LLM
            missing_ids = set(original_tasks_dict.keys()) - returned_ids
            if missing_ids:
                 log_event("AGENT_WARNING", self.agent_id, {"warning": "LLM schedule response missing tasks", "missing_task_ids": list(missing_ids)})
                 for task_id in missing_ids:
                     missing_task = original_tasks_dict[task_id].copy()
                     missing_task['scheduling_status'] = 'Failed: Missing in LLM response'
                     missing_task['start_time'] = None
                     missing_task['end_time'] = None
                     updated_tasks.append(missing_task)
                     
            log_event("AGENT_INFO", self.agent_id, {"message": "Successfully parsed and merged LLM schedule response", "final_task_count": len(updated_tasks)})
            return updated_tasks

        except json.JSONDecodeError as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to decode LLM schedule response JSON", "details": str(e), "response_snippet": llm_response[:200]})
            return None
        except ValueError as e:
             log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to parse LLM schedule response", "details": str(e), "response_snippet": llm_response[:200]})
             return None
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Unexpected error parsing LLM schedule response", "details": str(e), "response_snippet": llm_response[:200]})
            return None

    def schedule_tasks(self, tasks_to_schedule: list, existing_events: list) -> list | None:
        """
        Schedules a list of tasks, considering dependencies and existing events.

        Args:
            tasks_to_schedule: A list of task dictionaries (from PlannerAgent).
            existing_events: A list of existing calendar event dictionaries.

        Returns:
            A list of task dictionaries updated with scheduling information
            (start_time, end_time, scheduling_status), or None on failure.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "schedule_tasks", "task_count": len(tasks_to_schedule), "existing_event_count": len(existing_events)})

        # --- Implementation --- 
        if not tasks_to_schedule:
            log_event("AGENT_INFO", self.agent_id, {"message": "No tasks provided to schedule.", "action": "schedule_tasks"})
            return [] # Return empty list if no tasks given

        template_name = "calendar/schedule_tasks.j2"
        context = {
            "tasks_to_schedule": tasks_to_schedule,
            "existing_events": existing_events,
            "timestamp": datetime.now().isoformat()
        }

        # 1. Render the prompt
        prompt_text = render_template(template_name, context)
        if not prompt_text:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to render scheduling prompt template", "template": template_name})
            return None
        log_event("AGENT_DEBUG", self.agent_id, {"message": "Scheduling prompt rendered", "template": template_name})

        # 2. Stage and Execute the prompt
        llm_response = stage_and_execute_prompt(
            agent_id=self.agent_id,
            prompt_subject=f"Schedule {len(tasks_to_schedule)} tasks considering {len(existing_events)} existing events",
            prompt_context=prompt_text,
            llm_config=self.llm_config
        )

        if not llm_response or llm_response.startswith("Error:"):
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to get valid response from prompt staging service for scheduling", "response": llm_response})
            return None
            
        # 3. Parse the response using the dedicated parser
        updated_task_list = self._parse_llm_schedule_response(llm_response, tasks_to_schedule)

        if updated_task_list is None:
            log_event("AGENT_ACTION_FAIL", self.agent_id, {"action": "schedule_tasks", "reason": "Failed to parse LLM response for scheduled tasks"})
        else:
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "schedule_tasks", "final_task_count": len(updated_task_list)})

        return updated_task_list
        # --- End Implementation ---

    def add_event(self, event_details: dict) -> bool:
        """
        Adds a single event directly to the calendar (e.g., a meeting).

        Args:
            event_details: Dictionary describing the event.

        Returns:
            True if successful, False otherwise.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "add_event", "event_summary": event_details.get('summary', 'N/A')})
        # TODO: Implement actual calendar integration (e.g., Google Calendar API, local file)
        print(f"[{self.agent_id}] Placeholder: Adding event: {event_details.get('summary', '?')}")
        log_event("AGENT_WARNING", self.agent_id, {"warning": "add_event not implemented", "action": "add_event"})
        return True # Placeholder success

    def get_availability(self, start_time: str, end_time: str) -> list:
        """
        Checks for free time slots within a given period.

        Args:
            start_time: ISO format start time.
            end_time: ISO format end time.

        Returns:
            A list of available time slot dictionaries.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "get_availability", "start": start_time, "end": end_time})
        # TODO: Implement actual calendar integration
        print(f"[{self.agent_id}] Placeholder: Getting availability between {start_time} and {end_time}")
        log_event("AGENT_WARNING", self.agent_id, {"warning": "get_availability not implemented", "action": "get_availability"})
        return [] # Placeholder empty list

# Example Usage
if __name__ == '__main__':
    print("[CalendarAgent] Running example...")
    calendar = CalendarAgent()

    # Use a dummy stage_and_execute_prompt for local testing
    # (Note: This will use the dummy response defined in llm_bridge.py now)
    try:
        from dreamforge.core.prompt_staging_service import stage_and_execute_prompt
    except ImportError:
        print("Cannot run example without prompt staging service")
        sys.exit(1)

    tasks = [
        {"task_id": "DEV-001", "description": "Setup", "dependencies": [], "estimated_time": "1 hour", "assigned_to": "dev"},
        {"task_id": "DEV-002", "description": "Backend", "dependencies": ["DEV-001"], "estimated_time": "4 hours", "assigned_to": "dev"},
        {"task_id": "DOC-001", "description": "Write Docs", "dependencies": ["DEV-002"], "estimated_time": "2 hours", "assigned_to": "writer"}
    ]
    events = [
        {"summary": "Team Meeting", "start": "2025-01-01T10:00:00Z", "end": "2025-01-01T11:00:00Z"}
    ]

    print("\n--- Scheduling Tasks (using dummy LLM bridge response) ---")
    scheduled_tasks = calendar.schedule_tasks(tasks, events)
    
    if scheduled_tasks is not None:
        print("\nScheduled Tasks Result:")
        print(json.dumps(scheduled_tasks, indent=2))
    else:
        print("\nFailed to schedule tasks.")

    print("\n--- Testing Other Methods (Placeholders) ---")
    added = calendar.add_event({"summary": "Client Call", "start": "2025-01-02T14:00:00Z", "end": "2025-01-02T14:30:00Z"})
    print(f"\nEvent Added (Placeholder): {added}")

    avail = calendar.get_availability("2025-01-03T09:00:00Z", "2025-01-03T17:00:00Z")
    print(f"\nAvailability (Placeholder): {avail}")
    print("\n[CalendarAgent] Example finished.") 