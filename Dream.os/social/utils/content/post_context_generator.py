import sys
import os
import json # Moved import to top
import re
import traceback

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # social/
project_root = os.path.abspath(os.path.join(script_dir, '..')) # Go up one level from social/
if project_root not in sys.path:
    sys.path.insert(0, project_root)
del sys # Remove sys from module scope after use

# Core imports
try:
    from governance_memory_engine import load_memory # Corrected import path (assuming root)
    # Import prompt staging service and template engine
    from core.prompt_staging_service import stage_and_execute_prompt
    from template_engine import render_template
except ImportError as e:
    # print(f"[PostContextGenerator] Warning: Failed to import dependencies: {e}")
    # Log the import error before exiting
    log_event("AGENT_CRITICAL", "PostContextGenerator", {"error": "Failed to import dependencies", "details": str(e)})
    # Re-import sys to use sys.exit
    import sys 
    sys.exit(f"Critical dependency missing: {e}")

# Define source for logging
_SOURCE = "PostContextGenerator"

# Constants
MAX_GOVERNANCE_EVENTS = 5
LATEST_EVENT_INDEX = -1
JSON_BLOCK_REGEX_GROUP = 1

def generate_context_from_governance(max_events=MAX_GOVERNANCE_EVENTS):
    """Generates a simple context dictionary based on recent governance events."""
    # print("[context_gen] Generating post context from governance memory...")
    log_event("AGENT_INFO", _SOURCE, {"message": "Generating post context from governance memory..."})
    context = {
        "title": None,
        "proposal_summary": None,
        # TODO: Integrate LLM call here. Blocked: Requires clarification on how internal
        # components should invoke LLM services (directly? via PromptStagingService? other?)
        "gpt_decision": None, # Placeholder - Populated by LLM analysis below
        "reflection_snippet": None,
        "general_update": None,
        "status_update": None,
        "governance_update": False
    }

    try:
        memory = load_memory()
        if not memory:
            context["general_update"] = "No recent governance activity."
            # Use log_event (need to import/handle dummy)
            # print("[context_gen] No memory found.")
            log_event("AGENT_WARNING", _SOURCE, {"warning": "No memory found"})
            return context

        # Get the latest relevant event (customize this logic heavily)
        latest_event = memory[LATEST_EVENT_INDEX] # Assuming memory is list of dicts
        context["governance_update"] = True
        event_type = latest_event.get("event_type", "UNKNOWN_EVENT")
        details = latest_event.get("details", {})
        context['event_type'] = event_type # Add event type to context

        # --- Example Logic (Highly Simplistic - Needs Significant Enhancement) ---
        if event_type == "PROPOSAL_CREATED":
            context["title"] = "New Proposal Submitted"
            context["proposal_summary"] = details.get("proposal_header", "See details in log.")
            context["status_update"] = details.get("status")
        elif event_type == "PROPOSAL_STATUS_UPDATED":
            context["title"] = "Proposal Status Change"
            context["proposal_summary"] = f"{details.get('proposal_header', 'Proposal')} -> {details.get('new_status', 'Updated')}"
            context["status_update"] = details.get('new_status')
            context["reflection_snippet"] = details.get("reason") # Maybe use reason as a snippet
        elif event_type == "DISAGREEMENT_LOGGED":
            context["title"] = "Disagreement Logged"
            context["reflection_snippet"] = f"Objection on Ref: {details.get('reflection_id')} - {details.get('objection_summary', '')}"
            context["status_update"] = details.get('status')
        elif event_type == "HUMAN_DECISION":
            context["title"] = "Human Review Decision"
            item_type = details.get("item_type", "Item")
            item_header = details.get("item_header", "")
            action = details.get("human_action", "processed")
            context["general_update"] = f"Human reviewer {action} {item_type} '{item_header}'"
            context["status_update"] = details.get('new_status')
        else:
            context["general_update"] = f"Recent system activity logged: {event_type}"

        # print(f"[context_gen] Generated context based on event: {event_type}")
        log_event("AGENT_INFO", _SOURCE, {"info": "Generated context based on event", "event_type": event_type})

        # --- Call LLM to analyze context --- 
        try:
            # Pass the context built so far to the analysis template
            analysis_context = {"current_context": context}
            template_path = "prompts/social/analyze_context.j2"
            prompt_text = render_template(template_path, analysis_context)

            if prompt_text:
                # Assuming stage_and_execute_prompt exists and works
                llm_response = stage_and_execute_prompt(prompt_text, agent_id="PostContextGenerator", purpose="analyze_social_context")
                if llm_response:
                    # Parse the JSON response from the LLM
                    try:
                        # Basic parsing, assuming ```json block
                        json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL | re.IGNORECASE)
                        if json_match:
                            analysis_result = json.loads(json_match.group(JSON_BLOCK_REGEX_GROUP))
                            context["gpt_decision"] = analysis_result # Store the whole analysis
                            log_event("LLM_ANALYSIS_SUCCESS", _SOURCE, {"info": "LLM context analysis successful", "analysis": analysis_result})
                        else:
                            log_event("LLM_ANALYSIS_WARNING", _SOURCE, {"warning": "LLM analysis JSON block not found", "llm_response": llm_response})
                            context["gpt_decision"] = {"error": "Parsing failed: JSON block not found"}
                    except json.JSONDecodeError as json_e:
                        log_event("LLM_ANALYSIS_ERROR", _SOURCE, {"error": "LLM analysis JSON decode error", "details": str(json_e), "llm_response": llm_response})
                        context["gpt_decision"] = {"error": f"Parsing failed: {str(json_e)}"}
                    except Exception as parse_e:
                        log_event("LLM_ANALYSIS_ERROR", _SOURCE, {"error": "LLM analysis parsing failed", "details": str(parse_e)})
                        context["gpt_decision"] = {"error": f"Parsing failed: {str(parse_e)}"}
                else:
                    log_event("LLM_ANALYSIS_WARNING", _SOURCE, {"warning": "LLM analysis returned no response"})
                    context["gpt_decision"] = {"error": "LLM did not respond"}
            else:
                log_event("LLM_ANALYSIS_ERROR", _SOURCE, {"error": "Failed to render analysis template", "template": template_path})
                context["gpt_decision"] = {"error": "Template rendering failed"}
        except Exception as llm_e:
            log_event("LLM_ANALYSIS_ERROR", _SOURCE, {"error": "Error during LLM context analysis", "details": str(llm_e)})
            context["gpt_decision"] = {"error": f"LLM analysis failed: {str(llm_e)}"}
        # --- End LLM Context Analysis --- 

    except Exception as e:
        # print(f"[context_gen] Error generating context: {e}")
        log_event("AGENT_ERROR", _SOURCE, {"error": "Failed to generate context", "details": str(e), "traceback": traceback.format_exc()})
        context["general_update"] = "Error retrieving latest governance status."
        context["gpt_decision"] = {"error": "Context generation failed"}

    return context

# --- Example Usage --- #
if __name__ == "__main__":
    # Ensure Agent1/governance_memory.json exists and has some data for testing
    test_context = generate_context_from_governance()
    print("\n--- Generated Context ---")
    print(json.dumps(test_context, indent=2))
    print("-----------------------")