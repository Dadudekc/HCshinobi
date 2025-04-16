import os
import sys

# Add project root for imports if necessary
script_dir = os.path.dirname(__file__) # dreamforge/core
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Up TWO levels from core
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components
try:
    from dreamforge.core.governance_memory_engine import log_event # UPDATED IMPORT PATH
    from dreamforge.core.llm_bridge import call_llm # UPDATED IMPORT PATH
except ImportError as e:
    print(f"[PromptStagingService] Warning: Failed to import dependencies: {e}. Using fallbacks.")
    # --- Fallbacks --- 
    def log_event(event_type, agent_source, details): 
        print(f"[DummyLogger-PSS] {event_type} | {agent_source} | {details}")
    def call_llm(prompt: str, llm_config: dict = None): 
        print(f"[DummyLLMBridge] Called with prompt: {prompt[:50]}...")
        return f"Error: LLM Bridge not available."
    # --- End Fallbacks --- 

_SOURCE_ID = "PromptStagingService"

def stage_and_execute_prompt(agent_id: str, prompt_subject: str, prompt_context: str, llm_config: dict = None) -> str | None:
    """
    Stages, logs, executes (via LLM bridge), and logs the response for a prompt.

    Args:
        agent_id: The ID of the agent submitting the prompt.
        prompt_subject: A short description/subject for the prompt.
        prompt_context: The full text/content of the prompt.
        llm_config: Optional dictionary with specific configurations for the LLM call.

    Returns:
        The raw response string from the LLM, or None on failure.
    """
    log_event("PROMPT_STAGED", _SOURCE_ID, {
        "agent_source": agent_id,
        "prompt_subject": prompt_subject,
        "prompt_context_snippet": prompt_context[:150] + ("..." if len(prompt_context) > 150 else ""),
        "llm_config_keys": list(llm_config.keys()) if llm_config else []
    })

    # --- Call the LLM Bridge --- 
    llm_response = call_llm(prompt_context, llm_config or {})
    # --- End LLM Call ---

    if llm_response is not None:
        log_event("PROMPT_COMPLETED", _SOURCE_ID, {
            "agent_source": agent_id,
            "prompt_subject": prompt_subject,
            "response_snippet": llm_response[:150] + ("..." if len(llm_response) > 150 else "")
        })
    else:
        log_event("PROMPT_FAILED", _SOURCE_ID, {
            "agent_source": agent_id,
            "prompt_subject": prompt_subject,
            "error": "LLM call failed or returned None (check LLMBridge logs)."
        })

    return llm_response

# Example Usage
if __name__ == '__main__':
    print(f"[{_SOURCE_ID}] Running example...")
    # Ensure the bridge can be imported for the example
    try:
        from dreamforge.core.llm_bridge import call_llm
    except ImportError:
        print("Error: Cannot run example without llm_bridge.py existing in core/")
        sys.exit(1)
        
    test_agent = "TestAgent_Planner"
    test_subject = "Generate Plan Example"
    test_prompt = "User Goal: Create a test plan.\nInstructions: Output JSON list.\nFormat: [...]"
    test_config = {"model": "test-model-v1", "temperature": 0.6}

    response = stage_and_execute_prompt(test_agent, test_subject, test_prompt, test_config)

    print(f"\n[{_SOURCE_ID}] Response Received:")
    if response:
        print(response)
    else:
        print("Execution failed.")
    print(f"\n[{_SOURCE_ID}] Example finished.") 