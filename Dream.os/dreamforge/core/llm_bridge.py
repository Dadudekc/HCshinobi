import os
import sys
import time
import json
from typing import Optional, Dict, Any

# Add project root for imports if necessary
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components
try:
    from governance_memory_engine import log_event
except ImportError as e:
    print(f"[LLMBridge] Warning: Failed to import log_event: {e}. Using fallback.")
    def log_event(event_type, agent_source, details): pass

_SOURCE_ID = "LLMBridge"

def call_llm(prompt: str, model: str = "gpt-3.5-turbo", temperature: float = 0.7) -> Optional[str]:
    """
    Call LLM service with prompt.
    
    Args:
        prompt (str): Prompt text
        model (str): Model to use
        temperature (float): Temperature parameter
        
    Returns:
        str: LLM response or None if error
    """
    try:
        # TODO: Replace with actual LLM call
        # For now return dummy response based on prompt
        if "task list" in prompt.lower():
            tasks = [
                {
                    "id": "TASK-001",
                    "title": "Example Task",
                    "description": "This is a dummy task",
                    "status": "pending"
                }
            ]
            dummy_response = f'```json\n{json.dumps(tasks, indent=2)}\n```'
            return dummy_response
            
        return "Dummy LLM response"
        
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        return None

# Example Usage
if __name__ == '__main__':
    import re # Import re here for the example usage
    print(f"[{_SOURCE_ID}] Running example...")
    
    test_prompt_success = "Subject: Test Success\nGenerate a plan for testing."
    test_prompt_fail = "Subject: Test Failure\nPlease fail this request."
    test_prompt_plan = "Subject: Generate Plan\nUser Goal: Test.\nGenerate task plan instructions..."
    test_prompt_schedule = '''Subject: Schedule Tasks
TASKS TO SCHEDULE:
```json
[
  {
    "task_id": "T1",
    "description": "Task 1",
    "dependencies": [],
    "estimated_time": "1h"
  }
]
```
EXISTING CALENDAR EVENTS: []
Instructions...'''

    print("\n--- Testing Success Case ---")
    response_ok = call_llm(test_prompt_success, {"model": "sim-v1"})
    print(f"Response: {response_ok}")

    print("\n--- Testing Failure Case ---")
    response_fail = call_llm(test_prompt_fail)
    print(f"Response: {response_fail}")
    
    print("\n--- Testing Plan Case ---")
    response_plan = call_llm(test_prompt_plan)
    print(f"Response:\n{response_plan}")
    
    print("\n--- Testing Schedule Case ---")
    response_schedule = call_llm(test_prompt_schedule)
    print(f"Response:\n{response_schedule}")

    print(f"\n[{_SOURCE_ID}] Example finished.") 