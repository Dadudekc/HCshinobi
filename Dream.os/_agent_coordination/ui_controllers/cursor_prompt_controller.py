import pyautogui
import time
import logging
import pyperclip # For reliable pasting

# Configure logging
logger = logging.getLogger("CursorPromptController")
if not logger.hasHandlers():
    # Avoid double logging if root logger is configured
    if not logging.getLogger().hasHandlers():
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Constants (Potentially move to config) ---
# These might need adjustment based on screen resolution, OS, and Cursor layout
CURSOR_WINDOW_TITLE = "Cursor" # Default title, might need adjustment
# Coordinates are highly unreliable - use image recognition or activation sequences instead
# INPUT_FIELD_COORDS = (500, 950) # Example - VERY UNRELIABLE

# Time delays for UI actions (seconds)
ACTIVATE_DELAY = 0.5
TYPE_INTERVAL = 0.01 # Faster typing
PASTE_DELAY = 0.2
ENTER_DELAY = 0.1
SUBMIT_WAIT_DELAY = 1.0 # Wait after submitting

class CursorPromptController:
    """Uses pyautogui to send prompts to the Cursor chat interface."""

    def _activate_cursor_window(self):
        """Attempts to find and activate the Cursor window."""
        try:
            windows = pyautogui.getWindowsWithTitle(CURSOR_WINDOW_TITLE)
            if not windows:
                logger.error(f"Could not find Cursor window with title '{CURSOR_WINDOW_TITLE}'.")
                # Fallback: Try activating without title check? Risky.
                # pyautogui.getActiveWindow().activate() # Might not be Cursor
                return False
            
            cursor_window = windows[0] # Assume first match
            if not cursor_window.isActive:
                logger.info(f"Activating Cursor window: {cursor_window.title}")
                # Different activation methods depending on OS / window state
                try:
                    cursor_window.activate()
                except Exception as activate_err:
                     logger.warning(f"Standard activate failed ({activate_err}), trying alternative...")
                     try: 
                         cursor_window.minimize() # Try minimizing/maximizing
                         time.sleep(0.1)
                         cursor_window.maximize()
                     except Exception as alt_activate_err:
                          logger.error(f"Alternative activation failed: {alt_activate_err}. Cannot ensure focus.")
                          return False
                time.sleep(ACTIVATE_DELAY) # Wait for activation
            
            # Verify activation (optional, might not be reliable)
            # active_window = pyautogui.getActiveWindow()
            # if CURSOR_WINDOW_TITLE not in active_window.title:
            #     logger.warning(f"Activation might have failed. Active window: {active_window.title}")
            #     return False
                 
            logger.info("Cursor window presumed active.")
            return True
        except Exception as e:
            logger.error(f"Error activating Cursor window: {e}", exc_info=True)
            return False

    def _focus_chat_input(self):
        """Attempts to focus the chat input field. Highly dependent on layout/hotkeys."""
        logger.info("Attempting to focus Cursor chat input...")
        # Method 1: Assume a hotkey (e.g., Ctrl+L - common in VSCode based apps)
        # This is a GUESS - needs verification in Cursor
        try:
            pyautogui.hotkey('ctrl', 'l') # Check Cursor's actual shortcut
            time.sleep(PASTE_DELAY)
            logger.info("Sent Ctrl+L hotkey to focus chat input.")
            return True
        except Exception as e:
            logger.error(f"Failed to send focus hotkey: {e}")
            # Fallback? Click coordinates? Image recognition? Too unreliable for now.
            logger.warning("Focusing chat input failed. Pasting might go to wrong location.")
            return False

    def send_prompt_to_chat(self, prompt: str) -> bool:
        """Activates Cursor, focuses chat (best effort), pastes, and submits prompt."""
        logger.info(f"Attempting to send prompt to Cursor chat: '{prompt[:100]}...'")

        if not self._activate_cursor_window():
            return False

        # Attempt to focus the input field (best effort)
        self._focus_chat_input() 
        # Proceed even if focus fails, but log warning

        # Use pyperclip for reliable pasting, especially for long/complex prompts
        try:
            pyperclip.copy(prompt)
            time.sleep(PASTE_DELAY) # Give clipboard time
            pyautogui.hotkey('ctrl', 'v') # Paste
            logger.info("Pasted prompt using Ctrl+V.")
            time.sleep(PASTE_DELAY) 
        except Exception as e:
             logger.error(f"Failed to paste prompt using pyperclip/pyautogui: {e}", exc_info=True)
             # Fallback: Try typing (can be slow and error-prone for long prompts)
             logger.info("Falling back to typing prompt...")
             try:
                 pyautogui.write(prompt, interval=TYPE_INTERVAL)
                 logger.info("Finished typing prompt.")
             except Exception as type_e:
                 logger.error(f"Fallback typing also failed: {type_e}")
                 return False

        # Submit the prompt
        try:
            pyautogui.press('enter')
            logger.info("Pressed Enter to submit prompt.")
            time.sleep(SUBMIT_WAIT_DELAY) # Give Cursor time to process
            return True
        except Exception as e:
            logger.error(f"Failed to press Enter: {e}")
            return False

# Example Usage Block
if __name__ == "__main__":
    print("Running CursorPromptController example...")
    
    # --- IMPORTANT SAFETY NOTICE --- 
    # This script will take control of your mouse and keyboard.
    # Ensure the Cursor window is visible and potentially active before running.
    # Be prepared to manually stop the script (e.g., Ctrl+C in terminal) if needed.
    # PyAutoGUI has a failsafe (move mouse to corner), but be cautious.
    # --- --- --- --- --- --- --- --- 
    
    controller = CursorPromptController()
    
    test_prompt = "Hello Cursor! This is an automated test prompt from CursorPromptController. Please write a short python function to add two numbers." 
    
    print(f"Will attempt to send the following prompt in 5 seconds:")
    print(f"---\n{test_prompt}\n---")
    print("SWITCH TO CURSOR NOW if needed. Press Ctrl+C to abort.")
    
    try:
        time.sleep(5) 
        print("Attempting to send prompt...")
        success = controller.send_prompt_to_chat(test_prompt)
        if success:
            print("Prompt sent successfully (check Cursor!).")
        else:
            print("Failed to send prompt.")
            
    except KeyboardInterrupt:
        print("\nOperation aborted by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        logger.error("Error in example usage block", exc_info=True)

    print("CursorPromptController example finished.") 