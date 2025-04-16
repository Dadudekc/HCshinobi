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