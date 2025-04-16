# Automated ChatGPT → Cursor Bridge Framework

## 🎯 Vision

Create a system that bridges **ChatGPT/Thea (strategy)** directly into a **Cursor IDE instance (execution)** by automatically scanning stalled agent conversations, categorizing issues, and dispatching contextually-aware prompts **to Cursor**.

This enables a self-healing, self-executing agentic loop:

- **ChatGPT (Thea)** detects stalled agents or stalled project loops.
- Uses **`StallCategorizer`** logic to identify the stall reason from the context (project state, logs, inboxes, memory states).
- Produces detailed, structured **project-context data** (JSON/Jinja2).
- Automatically dispatches this structured prompt directly into **Cursor's IDE**, activating Cursor's context-aware code-level AI generation.

---

## 🌀 **AUTOMATED CHATGPT → CURSOR BRIDGE FLOW**

```plaintext
[Stalled Agent] → [ChatGPT/Thea] → [StallCategorizer]
                        ↓ (categorizes stall reason)
               [ProjectContextProducer] → (structured JSON)
                        ↓
                 [CursorDispatcher] → Cursor IDE
                        ↓
           (Cursor auto-generates solution or recovery)
                        ↓
                Cursor executes and commits fix
                        ↓
          ChatGPT reviews & loops back to agent execution
```

---

## ⚙️ **SYSTEM COMPONENT BREAKDOWN**

To implement this, we need these **core scripts** (likely within the `tools/` directory or a dedicated `bridge/` directory):

| Component                  | Purpose                                                           |
|----------------------------|-------------------------------------------------------------------|
| ✅ `stall_detector.py`       | Categorizes stalled states based on logs/context (Needs Implementation) |
| 🆕 `project_context_producer.py` | Builds structured project context (JSON/Jinja2) for Cursor prompt execution |
| 🆕 `cursor_dispatcher.py`       | Automates Cursor IDE interaction (e.g., via pyautogui, shortcuts, or future API) |
| 🆕 `agent_cursor_bridge.py`     | Integrates the detector, producer, and dispatcher into a single workflow |

---

## 🚀 **PROJECT CONTEXT PRODUCER (`project_context_producer.py`) - Proposed**

This script converts stall states into structured JSON/Jinja context Cursor can immediately act upon.

```python
import json
# from stall_detector import categorize_stall # Assumes stall_detector exists
from pathlib import Path

def categorize_stall(log_snippet: str) -> str:
    # Placeholder - needs actual implementation based on log analysis
    if "awaiting Agent Commander signal" in log_snippet.lower():
        return "AWAIT_CONFIRM"
    if "No new messages found" in log_snippet:
         return "NO_INPUT" # Needs cross-check with task list
    # Add more sophisticated categorization logic here
    return "UNCLEAR_OBJECTIVE"

def produce_project_context(conversation_log: str, project_dir_str: str):
    project_dir = Path(project_dir_str)
    if not project_dir.is_dir():
        print(f"Error: Project directory not found: {project_dir}")
        return None
        
    log_snippet = conversation_log[-1000:] # Last 1000 chars for analysis
    stall_category = categorize_stall(log_snippet)
    
    # Basic file gathering - enhance later with context relevance
    try:
        project_files = [str(p.relative_to(project_dir)) for p in project_dir.rglob("*.py") if ".venv" not in str(p)]
    except Exception as e:
        print(f"Error scanning project files: {e}")
        project_files = []
    
    context = {
        "stall_category": stall_category,
        "conversation_snippet": log_snippet, 
        "relevant_files": project_files[:10],  # Limit for brevity
        "project_root": str(project_dir),
        "suggested_action_keyword": { # Keywords for Cursor prompt generation
            "NO_INPUT": "Check task list and resume autonomous operation.",
            "NEEDS_TASKS": "Generate next logical task based on project goals.",
            "LOOP_BREAK": "Diagnose and fix the execution loop error.",
            "MISSING_CONTEXT": "Attempt context reload or state reset.",
            "AWAIT_CONFIRM": "Analyze context and proceed if safe, else summarize required confirmation.",
            "UNCLEAR_OBJECTIVE": "Review onboarding/goals and define next step."
        }.get(stall_category, "Perform general diagnostics.")
    }

    # Define output path (consider making this configurable)
    # Using a more generic name accessible by other tools
    output_path = project_dir / "agent_bridge_context.json" 
    # output_path.parent.mkdir(parents=True, exist_ok=True) # Ensure parent exists if needed

    try:
        with output_path.open("w", encoding='utf-8') as f:
            json.dump(context, f, indent=2)
        print(f"Project context saved to: {output_path}")
        return output_path
    except Exception as e:
        print(f"Error writing project context file: {e}")
        return None

# Example Usage:
# if __name__ == "__main__":
#     # Example log snippet (replace with actual log reading)
#     log_example = "...Awaiting Agent Commander signal..." 
#     produce_project_context(log_example, project_dir_str=".") # Run from workspace root
```

---

## 🎯 **AUTOMATED CURSOR DISPATCHER (`cursor_dispatcher.py`) - Proposed**

Auto-opens Cursor and triggers prompts via the generated `agent_bridge_context.json`.

```python
import subprocess
import pyautogui
import time
import json
from pathlib import Path

# --- Configuration --- #
# !!! IMPORTANT: Adjust this path to your actual Cursor installation !!!
CURSOR_EXE_PATH = r"C:\Users\User\AppData\Local\Programs\Cursor\Cursor.exe" # Example Windows path
# CURSOR_EXE_PATH = "/Applications/Cursor.app/Contents/MacOS/Cursor" # Example macOS path

# --- Functions --- #

def generate_cursor_prompt_from_context(context: dict) -> str:
    """Generates a natural language prompt for Cursor based on context."""
    # Basic prompt generation - can be enhanced significantly (e.g., using Jinja2)
    prompt = f"Context Analysis:\n"
    prompt += f"- Stall Category: {context.get('stall_category', 'Unknown')}\n"
    prompt += f"- Suggested Action Keyword: {context.get('suggested_action_keyword', 'N/A')}\n"
    prompt += f"- Project Root: {context.get('project_root', 'N/A')}\n"
    if context.get('relevant_files'):
        prompt += f"- Relevant Files: {', '.join(context['relevant_files'])}\n"
    prompt += f"\nConversation Snippet:\n```\n{context.get('conversation_snippet', 'N/A')}\n```\n"
    prompt += f"\nTask: Based on the stall category and context, please {context.get('suggested_action_keyword', 'diagnose the issue and propose a fix')}. Use the relevant files and conversation snippet for context."
    return prompt

def dispatch_to_cursor(context_json_path: Path):
    # 1. Read the context file
    if not context_json_path.is_file():
        print(f"Error: Context JSON file not found: {context_json_path}")
        return
    try:
        with context_json_path.open("r", encoding='utf-8') as f:
            context_data = json.load(f)
    except Exception as e:
        print(f"Error reading context JSON file: {e}")
        return

    # 2. Generate the prompt for Cursor
    cursor_prompt = generate_cursor_prompt_from_context(context_data)

    # 3. Launch Cursor (if not already running - checking is complex)
    print(f"Attempting to launch Cursor: {CURSOR_EXE_PATH}")
    try:
        subprocess.Popen([CURSOR_EXE_PATH])
        print("Allowing time for Cursor to launch/focus...")
        time.sleep(7) # Increased wait time
    except FileNotFoundError:
        print(f"Error: Cursor executable not found at: {CURSOR_EXE_PATH}")
        print("Please update CURSOR_EXE_PATH in cursor_dispatcher.py")
        return
    except Exception as e:
        print(f"Error launching Cursor: {e}")
        # Continue anyway, maybe it was already open
        pass 
        
    # 4. Copy prompt and paste into Cursor (using clipboard method)
    print("Copying generated prompt to clipboard...")
    try:
        import pyperclip
        pyperclip.copy(cursor_prompt)
    except ImportError:
        print("Warning: pyperclip not found. Cannot copy prompt automatically.")
        print("--- Please manually copy the following prompt: ---")
        print(cursor_prompt)
        print("-----------------------------------------------------")
        input("Press Enter after manually copying the prompt...") # Wait for user
    except Exception as e:
        print(f"Error copying prompt to clipboard: {e}")
        # Fallback or exit?

    # Give user time to manually focus Cursor chat
    print("\n--- ACTION REQUIRED --- ")
    print("Please ensure the Cursor window is active and CLICK into the chat input field.")
    print("(Will attempt paste in 5 seconds...)")
    time.sleep(5)
    
    # 5. Simulate Paste
    print("Simulating paste (Ctrl+V / Cmd+V)...")
    try:
        pyautogui.hotkey('ctrl', 'v') 
        # pyautogui.hotkey('command', 'v') # For macOS
        print("Paste simulation complete.")
        print("--- ACTION REQUIRED --- ")
        print("Please review the pasted prompt and PRESS ENTER or CLICK SEND in Cursor.")
        print("----------------------")
    except Exception as e:
        print(f"Error simulating paste: {e}")

    # Optionally automate "accept" button click later
    # print("Waiting for Cursor generation...")
    # time.sleep(15)
    # click_button_if_found(ACCEPT_BUTTON_IMG) # Assumes function exists

    print("Cursor dispatch process initiated.")

# Example Usage:
# if __name__ == "__main__":
#    context_path = Path("./agent_bridge_context.json") # Assume it exists
#    if context_path.exists():
#        dispatch_to_cursor(context_path)
#    else:
#        print("Run project_context_producer first to generate context file.")
```

---

## 🎖️ **FULL AUTOMATION FLOW (`agent_cursor_bridge.py`) - Proposed**

Integrates all steps into a single script:

```python
import sys
from pathlib import Path

# Add tools directory to path if needed
SCRIPT_DIR = Path(__file__).parent
# Assumes bridge script is in tools/
# sys.path.insert(0, str(SCRIPT_DIR))
# sys.path.insert(0, str(SCRIPT_DIR.parent)) # Add workspace root

# Import components (handle potential import errors)
try:
    # from stall_recovery_dispatcher import recover_from_stall # If exists
    from project_context_producer import produce_project_context
    from cursor_dispatcher import dispatch_to_cursor
except ImportError as e:
    print(f"Error importing bridge components: {e}")
    print("Ensure stall_detector.py (if used), project_context_producer.py, and cursor_dispatcher.py are in the Python path or same directory.")
    sys.exit(1)

def recover_from_stall(log_snippet: str):
    # Placeholder: Implement actual recovery logic if desired before Cursor dispatch
    print("Placeholder: Attempting automatic stall recovery...")
    pass

def automated_agent_cursor_bridge(conversation_log_path: str, project_dir_str: str):
    print("--- Starting Automated Agent -> Cursor Bridge --- ")
    # 1. Read conversation log
    log_file = Path(conversation_log_path)
    if not log_file.is_file():
        print(f"Error: Conversation log file not found: {log_file}")
        return
    try:
        conversation_log = log_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"Error reading conversation log: {e}")
        return

    # 2. Attempt automatic recovery first (optional)
    recover_from_stall(conversation_log[-1000:])

    # 3. Produce structured project context for Cursor
    print("Producing project context...")
    context_json_path = produce_project_context(conversation_log, project_dir_str)

    if not context_json_path:
        print("Failed to produce project context. Aborting bridge.")
        return

    # 4. Dispatch the structured context to Cursor IDE for handling
    print("Dispatching context to Cursor...")
    dispatch_to_cursor(context_json_path)
    
    print("--- Agent -> Cursor Bridge Process Initiated --- ")

# Usage Example:
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Automated bridge to send agent context to Cursor IDE.")
    parser.add_argument("log_file", help="Path to the conversation log file of the stalled agent.")
    parser.add_argument("project_dir", help="Path to the root project directory.")
    
    args = parser.parse_args()
    
    automated_agent_cursor_bridge(args.log_file, args.project_dir)
```

---

## 🔮 **FUTURE IMPACT**

Once fully automated, this system:

- Enables **hands-free agentic self-healing**.
- Turns stalls into immediate **Cursor IDE actions**.
- Creates a robust **ChatGPT (Thea) → Cursor** bridge.
- Scales to handle multiple agents, projects, and integration with real-time UI/chat interfaces.

---

*(Note: The Python code snippets above are illustrative and require creation as actual `.py` files, likely within the `tools/` directory. They also depend on the `stall_detector.py` logic being implemented and potential libraries like `pyautogui` and `pyperclip` being installed.)* 