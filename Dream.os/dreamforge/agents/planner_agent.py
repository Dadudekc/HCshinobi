import json
import re
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

# Add project root for imports
script_dir = os.path.dirname(__file__) # dreamforge/agents
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up two levels
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core Service Imports
try:
    from dreamforge.core.template_engine import render_template # UPDATED IMPORT
    from dreamforge.core.prompt_staging_service import stage_and_execute_prompt # UPDATED IMPORT
    from dreamforge.core.governance_memory_engine import log_event # UPDATED IMPORT
except ImportError as e:
    print(f"[PlannerAgent] Critical import failed: {e}. Functionality may be limited.")
    # Define fallbacks if necessary
    def render_template(template_name, context): return None
    def stage_and_execute_prompt(agent_id, prompt_subject, prompt_context, llm_config=None): return "Error: Prompt staging service unavailable."
    def log_event(event_type, agent_source, details): pass

AGENT_ID = "PlannerAgent"

class PlannerAgent:
    """
    Responsible for creating and refining task plans based on user goals or requests.
    Communicates with the LLM via the Prompt Staging Service.
    """
    def __init__(self, llm_config=None):
        self.agent_id = AGENT_ID
        self.llm_config = llm_config or {} # Use default LLM config if none provided
        log_event("AGENT_INIT", self.agent_id, {"status": "initialized", "llm_config_keys": list(self.llm_config.keys())})

    def _parse_llm_plan_response(self, llm_response: str) -> list | None:
        """Attempts to parse the LLM's JSON response into a list of tasks."""
        log_event("AGENT_DEBUG", self.agent_id, {"message": "Attempting to parse LLM plan response", "response_snippet": llm_response[:100]})
        try:
            # Attempt to extract JSON block (tolerant to surrounding text)
            json_match = re.search(r'```json\n(.*?)```', llm_response, re.DOTALL | re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1).strip()
            else:
                # Fallback: Assume the entire response might be JSON
                json_str = llm_response.strip()
                # Basic check if it looks like JSON
                if not (json_str.startswith('[') and json_str.endswith(']')) and not (json_str.startswith('{') and json_str.endswith('}')):
                     raise ValueError("Response does not appear to be valid JSON or wrapped in ```json")

            parsed_data = json.loads(json_str)

            # Check if the top-level structure is a list (as per the prompt)
            if isinstance(parsed_data, list):
                # Basic validation of task structure can be added here if needed
                log_event("AGENT_INFO", self.agent_id, {"message": "Successfully parsed LLM plan response", "task_count": len(parsed_data)})
                return parsed_data
            # Handle case where LLM might wrap the list in a dict (e.g., {"tasks": [...]})
            elif isinstance(parsed_data, dict) and "tasks" in parsed_data and isinstance(parsed_data["tasks"], list):
                 log_event("AGENT_WARNING", self.agent_id, {"warning": "Parsed plan response was a dict, extracting 'tasks' list", "keys": list(parsed_data.keys())})
                 return parsed_data["tasks"]
            else:
                log_event("AGENT_ERROR", self.agent_id, {"error": "Parsed JSON is not a list or expected dictionary structure", "parsed_type": type(parsed_data).__name__})
                return None

        except json.JSONDecodeError as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to decode LLM response JSON", "details": str(e), "response_snippet": llm_response[:200]})
            return None
        except ValueError as e:
             log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to parse LLM response", "details": str(e), "response_snippet": llm_response[:200]})
             return None
        except Exception as e:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Unexpected error parsing LLM response", "details": str(e), "response_snippet": llm_response[:200]})
            return None

    def plan_from_goal(self, user_goal: str) -> list | None:
        """
        Generates an initial task plan based on a high-level user goal.

        Args:
            user_goal: The goal provided by the user.

        Returns:
            A list of task dictionaries, or None if planning fails.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "plan_from_goal", "goal": user_goal})
        template_name = "planner/generate_plan.j2"
        context = {
            "user_goal": user_goal,
            "timestamp": datetime.now().isoformat()
        }

        # 1. Render the prompt
        prompt_text = render_template(template_name, context)
        if not prompt_text:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to render planning prompt template", "template": template_name})
            return None
        log_event("AGENT_DEBUG", self.agent_id, {"message": "Planning prompt rendered", "template": template_name})

        # 2. Stage and Execute the prompt via the service
        llm_response = stage_and_execute_prompt(
            agent_id=self.agent_id,
            prompt_subject=f"Generate task plan for goal: {user_goal[:50]}...",
            prompt_context=prompt_text,
            llm_config=self.llm_config
        )

        if not llm_response or llm_response.startswith("Error:"):
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to get valid response from prompt staging service", "response": llm_response})
            return None

        # 3. Parse the response
        task_list = self._parse_llm_plan_response(llm_response)

        if task_list is None:
            log_event("AGENT_ACTION_FAIL", self.agent_id, {"action": "plan_from_goal", "reason": "Failed to parse LLM response"})
        else:
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "plan_from_goal", "task_count": len(task_list)})

        return task_list

    def refine_plan(self, existing_plan: list, feedback: str) -> list | None:
        """
        Refines an existing task plan based on feedback.

        Args:
            existing_plan: The current list of task dictionaries.
            feedback: Feedback provided for refining the plan.

        Returns:
            A list of refined task dictionaries, or None if refinement fails.
        """
        log_event("AGENT_ACTION_START", self.agent_id, {"action": "refine_plan", "task_count": len(existing_plan), "feedback": feedback})
        
        # --- Implementation --- 
        template_name = "planner/refine_plan.j2"
        context = {
            "existing_plan": existing_plan,
            "feedback": feedback,
            "timestamp": datetime.now().isoformat()
        }

        # 1. Render the prompt
        prompt_text = render_template(template_name, context)
        if not prompt_text:
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to render refinement prompt template", "template": template_name})
            return None
        log_event("AGENT_DEBUG", self.agent_id, {"message": "Refinement prompt rendered", "template": template_name})
        
        # 2. Stage and Execute the prompt
        llm_response = stage_and_execute_prompt(
            agent_id=self.agent_id,
            prompt_subject=f"Refine task plan based on feedback: {feedback[:50]}...",
            prompt_context=prompt_text,
            llm_config=self.llm_config
        )

        if not llm_response or llm_response.startswith("Error:"):
            log_event("AGENT_ERROR", self.agent_id, {"error": "Failed to get valid response from prompt staging service for refinement", "response": llm_response})
            return None

        # 3. Parse the response (reuse the same parser as plan_from_goal)
        refined_task_list = self._parse_llm_plan_response(llm_response)

        if refined_task_list is None:
            log_event("AGENT_ACTION_FAIL", self.agent_id, {"action": "refine_plan", "reason": "Failed to parse LLM response for refined plan"})
        else:
            log_event("AGENT_ACTION_SUCCESS", self.agent_id, {"action": "refine_plan", "refined_task_count": len(refined_task_list)})
        
        return refined_task_list
        # --- End Implementation ---

    def _parse_llm_response(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """
        Parse LLM response into task list.
        
        Args:
            response (str): LLM response text
            
        Returns:
            list: List of task dictionaries or None if error
        """
        try:
            # Extract JSON from markdown code block if present
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if not json_match:
                print("Error: No JSON found in response", file=sys.stderr)
                return None
                
            json_str = json_match.group(1).strip()
            if not json_str:
                print("Error: Empty JSON in response", file=sys.stderr)
                return None
                
            # Parse JSON
            tasks = json.loads(json_str)
            if not isinstance(tasks, list):
                print("Error: JSON is not a list", file=sys.stderr)
                return None
                
            # Validate task structure
            for task in tasks:
                if not isinstance(task, dict):
                    print("Error: Task is not a dictionary", file=sys.stderr)
                    return None
                if "id" not in task or "description" not in task:
                    print("Error: Task missing required fields", file=sys.stderr)
                    return None
                    
            return tasks
            
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error in _parse_llm_response: {e}", file=sys.stderr)
            return None

    def _log_task_info(self, task_id: str, prompt_context: str):
        """Log task information for debugging."""
        # Extract subject from prompt context if available
        subject_pattern = r'Subject: (.*?)\n'
        subject_match = re.search(subject_pattern, prompt_context, re.IGNORECASE)
        print(f"Task ID: {task_id}, Subject: {subject_match.group(1) if subject_match else 'Unknown Subject'}")
        
    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """
        Validate task structure.
        
        Args:
            task (dict): Task dictionary
            
        Returns:
            bool: True if valid
        """
        required_fields = ["id", "description", "status"]
        return all(field in task for field in required_fields)

# Example Usage
if __name__ == '__main__':
    print("[PlannerAgent] Running example...")
    planner = PlannerAgent()
    goal = "Develop a simple web application for task management."
    
    # Use a dummy stage_and_execute_prompt for local testing if service not running
    def dummy_stage_prompt(agent_id, prompt_subject, prompt_context, llm_config=None):
        print("\n--- Dummy Prompt Staging Service Call ---")
        print(f"Agent: {agent_id}")
        subject_pattern = r'Subject: (.*?)\n'
        subject_match = re.search(subject_pattern, prompt_context, re.IGNORECASE)
        print(f"Subject: {subject_match.group(1) if subject_match else 'Unknown Subject'}")
        print(f"LLM Config: {llm_config}")
        print("Returning dummy JSON response...")
        
        # Simulate different responses based on prompt subject
        if "Generate task plan" in prompt_subject:
            dummy_json_response = '''
```json
[
  {
    "task_id": "DEV-001",
    "description": "Set up project structure (folders, basic files)",
    "status": "pending",
    "dependencies": [],
    "estimated_time": "2 hours",
    "assigned_to": "developer"
  },
  {
    "task_id": "DEV-002",
    "description": "Implement backend API for creating tasks",
    "status": "pending",
    "dependencies": ["DEV-001"],
    "estimated_time": "6 hours",
    "assigned_to": "developer"
  },
  {
    "task_id": "UI-001",
    "description": "Design basic UI mockups for task list and creation",
    "status": "pending",
    "dependencies": [],
    "estimated_time": "4 hours",
    "assigned_to": "designer"
  }
]
```
'''
        elif "Refine task plan" in prompt_subject:
             # Simulate adding the auth task based on feedback
             dummy_json_response = '''
```json
[
  {
    "task_id": "DEV-001",
    "description": "Set up project structure (folders, basic files)",
    "status": "pending",
    "dependencies": [],
    "estimated_time": "2 hours",
    "assigned_to": "developer"
  },
   {
    "task_id": "DEV-AUTH-001",
    "description": "Implement user authentication (backend)",
    "status": "pending",
    "dependencies": ["DEV-001"],
    "estimated_time": "5 hours",
    "assigned_to": "developer"
  },
  {
    "task_id": "DEV-002",
    "description": "Implement backend API for creating tasks",
    "status": "pending",
    "dependencies": ["DEV-001", "DEV-AUTH-001"],
    "estimated_time": "6 hours",
    "assigned_to": "developer"
  },
  {
    "task_id": "UI-001",
    "description": "Design basic UI mockups for task list and creation",
    "status": "pending",
    "dependencies": [],
    "estimated_time": "4 hours",
    "assigned_to": "designer"
  },
  {
    "task_id": "UI-AUTH-001",
    "description": "Design UI mockups for login/registration pages",
    "status": "pending",
    "dependencies": ["UI-001"],
    "estimated_time": "3 hours",
    "assigned_to": "designer"
  }
]
```
'''
        else:
            dummy_json_response = '{"error": "Unknown prompt subject for dummy response"}'
            
        return dummy_json_response
        
    # Temporarily replace the real function with the dummy one for this test
    original_stage_prompt = stage_and_execute_prompt
    stage_and_execute_prompt = dummy_stage_prompt
    
    initial_plan = planner.plan_from_goal(goal)

    if initial_plan:
        print("\nInitial Plan Generated:")
        print(json.dumps(initial_plan, indent=2))

        feedback = "Add tasks for user authentication (backend and UI design). Make sure task creation depends on auth."
        refined_plan = planner.refine_plan(initial_plan, feedback)

        if refined_plan:
            print("\nRefined Plan (Simulated):")
            print(json.dumps(refined_plan, indent=2))
        else:
            print("\nFailed to refine plan.")
            
    else:
        print("\nFailed to generate initial plan.")
        
    # Restore original function if needed elsewhere
    stage_and_execute_prompt = original_stage_prompt
    print("\n[PlannerAgent] Example finished.") 