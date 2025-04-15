# tools/user_prompt_dispatcher.py

import argparse
import sys
import time
from pathlib import Path

try:
    import pyperclip # For cross-platform clipboard access
    import pyautogui # For simulating keyboard input and screen interaction
except ImportError:
    print("Error: Required libraries 'pyperclip' or 'pyautogui' not found.")
    print("Please install them using: pip install pyautogui pyperclip")
    sys.exit(1)

# Configuration
SCRIPT_DIR = Path(__file__).parent
WORKSPACE_ROOT = SCRIPT_DIR.parent # Assumes tools/ is one level down
PROMPT_LIBRARY_DIR = WORKSPACE_ROOT / "user_prompts"
# --- > NEW: Button Image Config < ---
BUTTON_IMAGES_DIR = WORKSPACE_ROOT / "button_images" # <<< YOU MUST CREATE THIS DIRECTORY
# <<< YOU MUST PLACE SCREENSHOTS OF BUTTONS IN button_images/ WITH THESE EXACT NAMES >>>
ACCEPT_BUTTON_IMG = BUTTON_IMAGES_DIR / "accept_button.png"
EXPLORE_BUTTON_IMG = BUTTON_IMAGES_DIR / "explore_button.png"
COPY_MESSAGE_BUTTON_IMG = BUTTON_IMAGES_DIR / "copy_message_button.png"
# --- > End NEW < ---

PASTE_DELAY_SECONDS = 0.5 # Small delay before pasting
DEFAULT_WAIT_AFTER_SEND = 5 # Default seconds to wait before looking for buttons
DEFAULT_BUTTON_TIMEOUT = 3 # Max seconds to look for each button
DEFAULT_CONFIDENCE = 0.8 # Confidence level for image matching (adjust as needed)

# --- Helper Functions ---

def list_available_prompts():
    """Lists available prompt files in the library directory."""
    print(f"Available prompts in '{PROMPT_LIBRARY_DIR}':")
    try:
        available = sorted([f.stem for f in PROMPT_LIBRARY_DIR.iterdir() if f.is_file() and f.suffix == '.txt'])
        if available:
            print("  - " + "\n  - ".join(available))
        else:
            print("  (No prompts found)")
    except Exception as e:
         print(f"  (Error listing prompts: {e})")

def click_button_if_found(button_image_path: Path, confidence=DEFAULT_CONFIDENCE, timeout=DEFAULT_BUTTON_TIMEOUT):
    """Attempts to find and click a button image on screen."""
    if not button_image_path.is_file():
        print(f"Warning: Button image not found: {button_image_path}. Skipping click attempt.")
        print(f"         Ensure screenshot exists in '{BUTTON_IMAGES_DIR}'.")
        return False

    print(f"Attempting to find button: {button_image_path.name} (Timeout: {timeout}s)...")
    start_time = time.time()
    button_location = None
    while time.time() - start_time < timeout:
        try:
            # Provide full path to locateOnScreen
            button_location = pyautogui.locateCenterOnScreen(
                str(button_image_path), 
                confidence=confidence
            )
            if button_location:
                print(f"  Found button at: {button_location}")
                pyautogui.click(button_location)
                print(f"  Clicked button: {button_image_path.name}")
                time.sleep(0.2) # Small pause after click
                return True
        except pyautogui.ImageNotFoundException:
            pass # Expected if button not visible yet
        except Exception as e:
            print(f"  Error during image search for {button_image_path.name}: {e}")
            # Don't retry on other errors
            break 
        time.sleep(0.5) # Check periodically
        
    print(f"  Button not found within timeout: {button_image_path.name}")
    return False

def dispatch_prompt(prompt_name: str):
    """Reads a prompt, copies it, and simulates pasting into active window."""
    prompt_file = PROMPT_LIBRARY_DIR / f"{prompt_name}.txt"
    
    if not prompt_file.is_file():
        print(f"Error: Prompt file not found: {prompt_file}")
        print(f"Available prompts in {PROMPT_LIBRARY_DIR}:")
        try:
            available = [f.stem for f in PROMPT_LIBRARY_DIR.iterdir() if f.is_file() and f.suffix == '.txt']
            if available:
                print("  - " + "\n  - ".join(available))
            else:
                print("  (No prompts found)")
        except Exception as e:
             print(f"  (Error listing prompts: {e})")
        return False
        
    try:
        prompt_text = prompt_file.read_text(encoding='utf-8').strip()
        if not prompt_text:
             print(f"Error: Prompt file '{prompt_file.name}' is empty.")
             return False
             
        # 1. Copy to clipboard
        pyperclip.copy(prompt_text)
        print(f"Prompt '{prompt_name}' copied to clipboard.")
        print("--- Action Required --- ")
        print("Please CLICK into the target Cursor chat input field NOW.")
        
        # Give user time to click
        # TODO: Replace with more robust window/field detection later
        time.sleep(3) 
        
        # 2. Simulate Paste
        print("Simulating paste (Ctrl+V / Cmd+V)...")
        time.sleep(PASTE_DELAY_SECONDS)
        pyautogui.hotkey('ctrl', 'v') # Use hotkey for better compatibility
        # For macOS, uncomment the line below and comment the one above
        # pyautogui.hotkey('command', 'v') 
        
        print("Paste simulation complete.")
        print("--- Action Required --- ")
        print("Please PRESS ENTER or CLICK SEND in the Cursor chat window.")
        print("----------------------")
        
        return True
        
    except Exception as e:
        print(f"An error occurred during dispatch: {e}")
        return False

# --- Main Execution --- #
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch a predefined user prompt and optionally click response buttons.")
    parser.add_argument("prompt_name", nargs='?', default=None,
                        help="Optional: The name of the prompt file (without .txt) in user_prompts. Lists prompts if omitted.")
    # --- > NEW: Button Click Arguments < ---
    parser.add_argument("--click-accept", action="store_true", help="Attempt to click the 'Accept' button after waiting.")
    parser.add_argument("--click-copy", action="store_true", help="Attempt to click the 'Copy Message' button after waiting.")
    parser.add_argument("--click-explore", action="store_true", help="Attempt to click the 'Explore' button after waiting.")
    parser.add_argument("--wait-after-send", type=int, default=DEFAULT_WAIT_AFTER_SEND, 
                        help=f"Seconds to wait after user sends prompt before looking for buttons (default: {DEFAULT_WAIT_AFTER_SEND})")
    parser.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE,
                         help=f"Confidence level for button image matching (0.0-1.0, default: {DEFAULT_CONFIDENCE})")
    parser.add_argument("--button-timeout", type=int, default=DEFAULT_BUTTON_TIMEOUT,
                         help=f"Seconds to search for each button image (default: {DEFAULT_BUTTON_TIMEOUT})")
    # --- > End NEW < ---
    
    args = parser.parse_args()
    
    # --- > NEW: List prompts if name is missing < ---
    if args.prompt_name is None:
        list_available_prompts()
        sys.exit(0)
    # --- > End NEW < ---
    
    print(f"Attempting to dispatch prompt: {args.prompt_name}")
    success = dispatch_prompt(args.prompt_name)
    
    if not success:
        print("Dispatch process failed during prompt preparation/paste.")
        sys.exit(1)
        
    # --- > NEW: Wait and Click Logic < ---
    if args.click_accept or args.click_copy or args.click_explore:
        print(f"\nWaiting {args.wait_after_send} seconds for AI response before looking for buttons...")
        print("(Ensure Cursor window is visible and has focus)")
        time.sleep(args.wait_after_send)
        print("Starting button search...")
        
        # Attempt to click requested buttons
        if args.click_copy:
            click_button_if_found(COPY_MESSAGE_BUTTON_IMG, args.confidence, args.button_timeout)
            
        if args.click_explore:
            click_button_if_found(EXPLORE_BUTTON_IMG, args.confidence, args.button_timeout)
            
        if args.click_accept:
            click_button_if_found(ACCEPT_BUTTON_IMG, args.confidence, args.button_timeout)
            
        print("Button click attempts finished.")
    # --- > End NEW < ---
        
    print("\nDispatch process complete.")
    sys.exit(0) 