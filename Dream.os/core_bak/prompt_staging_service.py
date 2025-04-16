import os
import sys
import json
from datetime import datetime
import time # Add time import
# from jinja2 import Environment, FileSystemLoader, select_autoescape # No longer needed directly

# --- Add project root to sys.path ---
# This assumes the script is in core/
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ------------------------------------

# --- Core Service Imports ---
try:
    from tools.chat_cursor_bridge import write_to_cursor_input, read_from_cursor_output
    # Import the actual dependencies
    from core.template_engine import default_template_engine as template_engine # Use singleton instance
    from core.memory.governance_memory_engine import log_event
    # Import supervisor state loader
    from core.memory.supervisor_memory import load_state 
    dependencies_loaded = True
except ImportError as e:
    # print(f"[PromptStagingService Error ❌] Failed to import dependencies: {e}") # Keep print in fallback
    # Fallback if core deps are missing, retain bridge funcs if possible
    dependencies_loaded = False
    template_engine = None
    # Define log_event within this scope if import fails
    def log_event(event_type, source, details): print(f"[Dummy Log] Event: {event_type}, Source: {source}, Details: {details}")
    # Ensure bridge functions are defined even on partial import failure
    try:
        from tools.chat_cursor_bridge import write_to_cursor_input, read_from_cursor_output
    except ImportError:
        # print("[PromptStagingService Error ❌] Critical: chat_cursor_bridge not found.") # Keep print in fallback
        def write_to_cursor_input(text): print("Dummy write_to_cursor_input"); return False
        def read_from_cursor_output(): print("Dummy read_from_cursor_output"); return None
    # Define dummy load_state if import fails
    load_state = lambda: {"error": "Supervisor memory unavailable", "current_focus": {}, "active_goals": [], "agent_states": {}, "task_assignments": {}, "system_notes": []}

# --- Import Config ---
from core import config

# --- Constants ---
# Paths are now imported from config
_SOURCE = "PromptStagingService" # Define logging source

# --- Helper: Load Project Analysis ---
def _load_project_analysis() -> dict:
    """Loads the project analysis file, returning default on error."""
    default_analysis = {"error": "Analysis unavailable", "files": {}, "summary": {}}
    # Use config path
    log_context = {"path": config.PROJECT_ANALYSIS_FILE}
    if not os.path.exists(config.PROJECT_ANALYSIS_FILE):
        # print(f"[PromptStagingService Info] Project analysis file not found: {config.PROJECT_ANALYSIS_FILE}")
        log_event("PROMPT_STAGE_INFO", _SOURCE, {**log_context, "message": "Project analysis file not found"})
        return default_analysis
    try:
        with open(config.PROJECT_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        log_event("PROMPT_STAGE_DEBUG", _SOURCE, {**log_context, "message": "Project analysis loaded successfully"})
        return analysis_data
    except json.JSONDecodeError as e:
        # print(f"[PromptStagingService Error ❌] Failed to parse project analysis {config.PROJECT_ANALYSIS_FILE}: {e}")
        log_event("PROMPT_STAGE_ERROR", _SOURCE, {**log_context, "error": "Failed to parse project analysis", "details": str(e)})
        return default_analysis
    except Exception as e:
        # print(f"[PromptStagingService Error ❌] Failed to load project analysis {config.PROJECT_ANALYSIS_FILE}: {e}")
        log_event("PROMPT_STAGE_ERROR", _SOURCE, {**log_context, "error": "Failed to load project analysis", "details": str(e)})
        return default_analysis

# --- Jinja Environment Setup --- (Now handled by TemplateEngine)
# try:
#     # ... Jinja setup code removed ...
# except Exception as e:
#     # ... Jinja error handling removed ...

# --- Service Functions ---

def render_prompt(template_name: str, context: dict) -> str | None:
    """
    Renders a Jinja template, automatically injecting supervisor state 
    and project analysis into the context.
    
    Args:
        template_name: The filename of the template (e.g., 'my_prompt.j2').
        context: Additional variables. State added under 'supervisor_state', 
                 analysis added under 'project_scan'.

    Returns:
        The rendered prompt string, or None if rendering fails.
    """
    log_context = {"template": template_name}
    if not template_engine or not template_engine.jinja_env:
        # print("[PromptStagingService Error ❌] Template Engine not available.")
        # Log event without state as state loading wasn't attempted
        log_event("PROMPT_RENDER_FAILED", _SOURCE, {**log_context, "error": "Template Engine unavailable"})
        return None

    # Load current supervisor state
    supervisor_state = load_state()
    if not supervisor_state:
        # load_state prints errors, but log it too and provide a default
        # print("[PromptStagingService Warn ⚠️] Failed to load supervisor state. Using default empty state for template.")
        supervisor_state = {"error": "Failed to load", "current_focus": {}, "active_goals": [], "agent_states": {}, "task_assignments": {}, "system_notes": []} # Provide default structure
        log_event("SUPERVISOR_STATE_LOAD_FAILED", _SOURCE, {**log_context}) # Already logged by load_state? Adding context here.

    # Load project analysis data
    project_scan_data = _load_project_analysis()

    # Combine provided context with supervisor state and project scan
    full_context = context.copy()
    full_context['supervisor_state'] = supervisor_state
    full_context['project_scan'] = project_scan_data # Add scan data

    # Render using the template engine
    rendered_text = template_engine.render(template_name, full_context)
    
    scan_included_flag = project_scan_data.get("error") is None # Simplify flag
    state_included_flag = supervisor_state.get("error") != "Failed to load" # Check if default was used

    if rendered_text is not None:
        log_event("PROMPT_RENDERED", _SOURCE, {
            **log_context,
            "context_keys": list(context.keys()),
            "state_included": state_included_flag,
            "scan_included": scan_included_flag
            })
        # print(f"[PromptStagingService ✅] Rendered template '{template_name}' (with state & scan data)")
    else:
        # Error is printed by TemplateEngine.render
        log_event("PROMPT_RENDER_FAILED", _SOURCE, {
            **log_context,
            "error": "Rendering failed in TemplateEngine",
            "state_included": state_included_flag,
            "scan_included": scan_included_flag
            })
        # print(f"[PromptStagingService Error ❌] Failed to render template '{template_name}'")
    return rendered_text

def stage_prompt_for_cursor(template_name: str, context: dict) -> bool:
    """
    Renders a Jinja template (injecting supervisor state and project scan) and writes the output.
    
    Args:
        template_name: The filename of the template (e.g., 'my_prompt.j2').
        context: Additional variables to pass to the template.

    Returns:
        True if the prompt was rendered and written successfully, False otherwise.
    """
    # Use config path
    log_context = {"template": template_name, "target": config.CURSOR_INPUT_FILE}
    rendered_prompt = render_prompt(template_name, context)
    if rendered_prompt is None:
        # print(f"[PromptStagingService Error ❌] Aborting staging due to render failure for '{template_name}'.")
        # Render failure already logged by render_prompt
        return False

    success = write_to_cursor_input(rendered_prompt, target_path=config.CURSOR_INPUT_FILE) # Assuming write_to_cursor_input takes path
    # Include state/scan included flags in log
    scan_included_flag = True # Assume true if rendering succeeded (scan loaded earlier)
    state_included_flag = True # Assume true if rendering succeeded (state loaded earlier)
    # Note: A more robust way might be to pass these flags from render_prompt
    
    if success:
        log_event("PROMPT_STAGED", _SOURCE, {**log_context, "state_included": state_included_flag, "scan_included": scan_included_flag})
        # print(f"[PromptStagingService ✅] Staged prompt from '{template_name}' to {config.CURSOR_INPUT_FILE}")
    else:
        log_event("PROMPT_STAGE_FAILED", _SOURCE, {**log_context, "state_included": state_included_flag, "scan_included": scan_included_flag})
        # print(f"[PromptStagingService Error ❌] Failed to stage prompt from '{template_name}' to {config.CURSOR_INPUT_FILE}")

    return success

def fetch_cursor_response() -> dict | None:
    """
    Reads and parses the JSON response from the cursor output file.

    Returns:
        The parsed JSON dictionary, or None if the file doesn't exist or parsing fails.
    """
    # Use config path
    log_context = {"source": config.CURSOR_OUTPUT_FILE}
    response_data = read_from_cursor_output(target_path=config.CURSOR_OUTPUT_FILE) # Assuming read_from_cursor_output takes path
    if response_data is not None:
        log_event("RESPONSE_FETCHED", _SOURCE, {**log_context, "status": "Success"})
        # print(f"[PromptStagingService ✅] Fetched response from {config.CURSOR_OUTPUT_FILE}")
    else:
        # Log might depend on whether None means error or just no file yet
        # read_from_cursor_output logs details; this log indicates failure at this level
        log_event("RESPONSE_FETCH_FAILED", _SOURCE, {**log_context, "status": "NotFoundOrError"})
        # print(f"[PromptStagingService Info/Error] Failed to fetch/parse response from {config.CURSOR_OUTPUT_FILE} (or file not present).")

    return response_data

# --- NEW FUNCTION: Stage and Execute (Synchronous) ---
def stage_and_execute_prompt(prompt_text: str, agent_id: str, purpose: str, timeout_seconds: int = 60) -> dict | None:
    """
    Writes a pre-rendered prompt text to the cursor input, waits for, 
    and fetches the response from the cursor output file.

    Args:
        prompt_text: The pre-rendered text to send to the cursor bridge.
        agent_id: The ID of the agent initiating the request (for logging).
        purpose: The purpose of the prompt (for logging).
        timeout_seconds: How long to wait for the response file.

    Returns:
        The parsed JSON response dictionary, or None if an error occurs or it times out.
    """
    _SOURCE = "PromptStagingService.stage_and_execute" # More specific source
    # Use config paths
    log_context = {"agent_id": agent_id, "purpose": purpose, "target": config.CURSOR_INPUT_FILE, "response_target": config.CURSOR_OUTPUT_FILE}
    
    # 1. Write the prompt to the input file
    log_event("PROMPT_EXECUTE_START", _SOURCE, {**log_context, "status": "Writing prompt"})
    write_success = write_to_cursor_input(prompt_text, target_path=config.CURSOR_INPUT_FILE) # Assuming write_to_cursor_input takes path
    if not write_success:
        log_event("PROMPT_EXECUTE_FAILED", _SOURCE, {**log_context, "error": "Failed to write prompt to cursor input"})
        return None
        
    log_event("PROMPT_EXECUTE_WAIT", _SOURCE, {**log_context, "status": "Waiting for response", "timeout": timeout_seconds})
    
    # 2. Poll for the response file
    start_time = time.monotonic()
    response = None
    while time.monotonic() - start_time < timeout_seconds:
        response = read_from_cursor_output(target_path=config.CURSOR_OUTPUT_FILE) # Assuming read_from_cursor_output takes path
        if response is not None:
            log_event("PROMPT_EXECUTE_SUCCESS", _SOURCE, {**log_context, "status": "Response received"})
            # Optionally, clear the output file after reading?
            # try: os.remove(config.CURSOR_OUTPUT_FILE) except OSError: pass
            return response
        time.sleep(1) # Poll every second

    # 3. Timeout reached
    log_event("PROMPT_EXECUTE_FAILED", _SOURCE, {**log_context, "error": "Timeout waiting for cursor response file"})
    return None

# --- Optional: Archiving ---
# def archive_prompt_and_response(template_name, context, response):
#     # Implementation for saving files to an archive location with timestamps/ids
#     pass

# --- Example Usage (Updated for state & scan injection) ---
if __name__ == "__main__":
    print("--- Testing PromptStagingService (with State & Scan Injection) ---")

    if not dependencies_loaded:
        print("\n[FATAL ❌] Core dependencies failed to load. Cannot run full test.")
        sys.exit(1)

    # Create/ensure supervisor state exists for test
    try:
        from core.memory.supervisor_memory import save_state, load_state
        test_state = load_state() # Load or create default
        test_state["active_goals"] = ["Test state injection"] # Add test goal
        save_state(test_state)
        print("Ensured supervisor_state.json exists for testing.")
    except Exception as e:
        print(f"Error preparing supervisor state for test: {e}")

    # Ensure dummy project analysis exists for test
    if not os.path.exists(config.PROJECT_ANALYSIS_FILE):
        print(f"Creating dummy project analysis file: {config.PROJECT_ANALYSIS_FILE}")
        dummy_scan = {
            "scan_timestamp": datetime.now().isoformat(),
            "files": {"/d:/Dream.os/core/test.py": {"language": ".py", "functions": ["test_func"], "complexity": 1}},
            "summary": {"total_files": 1, "total_complexity": 1}
        }
        try:
            with open(config.PROJECT_ANALYSIS_FILE, 'w') as f:
                json.dump(dummy_scan, f, indent=2)
        except Exception as e:
            print(f"Error creating dummy analysis file: {e}")

    # Ensure template exists (using a name that reflects both contexts)
    dummy_template_name = 'test_full_context_prompt.j2'
    if template_engine and template_engine.template_dir:
        dummy_template_path = os.path.join(template_engine.template_dir, dummy_template_name)
        if not os.path.exists(dummy_template_path):
            try:
                with open(dummy_template_path, 'w') as f:
                    f.write("User: {{ user }}\n")
                    f.write("Supervisor Focus: {{ supervisor_state.current_focus.purpose }}\n")
                    f.write("Project Scan Summary: {{ project_scan.summary.total_files }} files, Complexity: {{ project_scan.summary.total_complexity }}\n")
                print(f"Created dummy template: {dummy_template_path}")
            except Exception as e:
                print(f"Error creating dummy template: {e}")
    else:
        print("Cannot verify/create dummy template: Template engine path unknown.")

    # 1. Test rendering with state & scan injection
    print("\n1. Testing render_prompt with state & scan injection...")
    test_user_context = {"user": "Dream.OS Test"}
    rendered = render_prompt(dummy_template_name, test_user_context) 
    if rendered:
        print(f"   Rendered output:\n---\n{rendered}\n---")

    # 2. Test staging (implicitly uses state & scan)
    print("\n2. Testing stage_prompt_for_cursor...")
    staged = stage_prompt_for_cursor(dummy_template_name, test_user_context)
    if staged:
        print(f"   Check {config.CURSOR_INPUT_FILE}")

    # 3. Test fetching (unchanged, requires manual file creation)
    print("\n3. Testing fetch_cursor_response...")
    print(f"   Manually create '{config.CURSOR_OUTPUT_FILE}' with JSON content like:")
    print('   {\"status\": \"complete\", \"result\": \"Test response processed\"}')
    input("   Press Enter after creating the file...") 

    response = fetch_cursor_response()
    if response:
        print(f"   Fetched response:\n{json.dumps(response, indent=2)}")
    else:
        print("   No response fetched (or error).")

    print("\n--- Test Complete ---") 