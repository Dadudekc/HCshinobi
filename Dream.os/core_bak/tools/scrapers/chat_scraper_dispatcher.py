import time
import os
import sys # Keep sys if path manipulation needed, otherwise remove
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Add core directory to path to find modules IF this script is run from root
# If run from core/, imports should work directly.
script_dir = os.path.dirname(__file__)
if os.path.basename(script_dir) != 'core':
    core_path = os.path.join(script_dir, 'core') # Assumes script at root, core is subdir
    # Check if core exists before adding, handle if script isn't at root
    if not os.path.isdir(core_path):
        # If script is elsewhere, adjust relative path or use absolute
        # This might need better logic depending on final run location
        core_path = os.path.abspath("core") # Guess core is at root relative to CWD

    if os.path.isdir(core_path) and core_path not in sys.path:
        sys.path.insert(0, core_path)
        print(f"[CSD] Added {core_path} to sys.path for core module imports.")
else: # Running from core/ directory
    # Add project root (parent of core) to path if needed for other potential imports
    project_root = os.path.abspath(os.path.join(script_dir, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        # print(f"[CSD] Added project root {project_root} to sys.path.")
        pass # Usually not needed if all imports are self-contained or use core

# Import from core modules (now using updated path)
try:
    from governance_scraper import generate_governance_data
    from template_engine import render_template
    core_imports_ok = True
except ImportError as e:
    print(f"[CSD] Error importing core modules (governance_scraper, template_engine): {e}")
    print("[CSD] Ensure these files exist in the 'core' directory and PYTHONPATH is correct if running from elsewhere.")
    core_imports_ok = False
    # Exit or raise? For now, allow script to fail later if imports missing.

# --- Configuration ---
# Path to your Chrome profile (find yours at chrome://version -> Profile Path)
# Example: r"C:\Users\YourUser\AppData\Local\Google\Chrome\User Data\Profile 1"
# Set to None to use default browser session (might require login)
CHROME_PROFILE_PATH = None

# URL of the ChatGPT interface
CHATGPT_URL = "https://chatgpt.com/"

# CSS Selectors (HIGHLY LIKELY TO CHANGE - Inspect element on chat.openai.com)
CHAT_INPUT_SELECTOR = "textarea#prompt-textarea" # Selector for the prompt input textarea
SEND_BUTTON_SELECTOR = "button[data-testid=\"send-button\"]" # Selector for the send button (often near the textarea)
# Selector for the main area containing chat messages
CHAT_AREA_SELECTOR = "div[class*=\"react-scroll-to-bottom\"] > div > div"
# Selector for individual message blocks within the chat area
MESSAGE_BLOCK_SELECTOR = "div[data-message-author-role]"
# Selector specifically for assistant messages within a block
ASSISTANT_MESSAGE_SELECTOR = "div.markdown.prose"
# Selector for the button/indicator that shows ChatGPT is generating response
GENERATING_INDICATOR_SELECTOR = "button[aria-label=\"Stop generating\"]"

# Timeout for waiting for elements (seconds)
WAIT_TIMEOUT = 20
RESPONSE_WAIT_TIMEOUT = 180 # Wait longer for ChatGPT response

# Define path relative to project root
if os.path.basename(os.path.dirname(__file__)) == 'core':
     PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
else:
     PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__)) # Assume run from root if not in core/
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
RESPONSE_OUTPUT_FILE = os.path.join(ANALYSIS_DIR, "latest_gpt_response.txt")

def find_chatgpt_tab(driver):
    """Finds the browser tab/window already open at chatgpt.com."""
    original_window = driver.current_window_handle
    found_window = None

    for window_handle in driver.window_handles:
        try:
            driver.switch_to.window(window_handle)
            if CHATGPT_URL in driver.current_url:
                print(f"[CSD] Found ChatGPT tab: {driver.current_url}")
                found_window = window_handle
                break # Stop after finding the first matching tab
        except Exception as e:
            print(f"[CSD] Error switching to window {window_handle}: {e}")
            continue

    if not found_window:
        print(f"[CSD] Error: Could not find an open tab/window with URL containing '{CHATGPT_URL}'")
        print("[CSD] Please ensure you have ChatGPT open in a tab.")
        # Optionally, open a new tab: driver.switch_to.new_window('tab'); driver.get(CHATGPT_URL)
        # But this usually requires login etc.
        driver.switch_to.window(original_window) # Switch back if not found
        return None

    # Switch back to the original window before returning the handle (or stay switched?)
    # For this use case, staying switched is probably better.
    # driver.switch_to.window(original_window)
    return found_window

def inject_prompt_and_send(driver, prompt_text):
    """Finds the chat input, pastes the prompt, and sends it."""
    try:
        print("[CSD] Locating chat input...")
        chat_input = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, CHAT_INPUT_SELECTOR))
        )
        print("[CSD] Injecting prompt...")
        # Send prompt using JavaScript to handle potential complexities/newlines better
        # Escape backticks, backslashes, and newlines for JS string literal
        escaped_prompt = prompt_text.replace('\\', '\\\\').replace('`', '`').replace('\n', '\\n')
        driver.execute_script(f"arguments[0].value = `{escaped_prompt}`; arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));", chat_input)

        # Find and click the send button
        send_button = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEND_BUTTON_SELECTOR))
        )
        print("[CSD] Clicking send button...")
        send_button.click()
        return True

    except TimeoutException:
        print(f"[CSD] Error: Timed out waiting for chat input or send button ({CHAT_INPUT_SELECTOR} / {SEND_BUTTON_SELECTOR})")
    except NoSuchElementException:
        print(f"[CSD] Error: Could not find chat input or send button. Check CSS Selectors.")
    except Exception as e:
        print(f"[CSD] Error injecting or sending prompt: {e}")
    return False

def wait_for_response_completion(driver):
    """Waits until the generating indicator disappears."""
    try:
        print("[CSD] Waiting for response generation to start...")
        # Wait briefly for the indicator to potentially appear
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, GENERATING_INDICATOR_SELECTOR))
        )
        print("[CSD] Response generation detected. Waiting for completion...")

        # Now wait for the indicator to disappear
        WebDriverWait(driver, RESPONSE_WAIT_TIMEOUT).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, GENERATING_INDICATOR_SELECTOR))
        )
        print("[CSD] Response generation complete.")
        return True
    except TimeoutException:
        # It might have finished very quickly or not started (e.g., error message)
        print("[CSD] Warning: Timed out waiting for generating indicator to appear or disappear.")
        print("[CSD] Assuming response is complete or failed. Proceeding to scrape.")
        # Check if it just finished very fast
        try:
            driver.find_element(By.CSS_SELECTOR, GENERATING_INDICATOR_SELECTOR)
            print("[CSD] Indicator still present after timeout. Response might be stuck.")
            return False # Indicate potential issue
        except NoSuchElementException:
            print("[CSD] Indicator not found after timeout, assuming complete.")
            return True # Assume finished if indicator isn't there
    except Exception as e:
        print(f"[CSD] Error waiting for response completion: {e}")
        return False

def scrape_latest_response(driver):
    """Finds the latest assistant message block and extracts its text."""
    try:
        print("[CSD] Locating chat messages...")
        # Find all message blocks
        message_blocks = driver.find_elements(By.CSS_SELECTOR, MESSAGE_BLOCK_SELECTOR)
        if not message_blocks:
            print("[CSD] Error: Could not find any message blocks.")
            return None

        # Get the last message block
        latest_block = message_blocks[-1]

        # Check if the last block is from the assistant
        author_role = latest_block.get_attribute('data-message-author-role')
        if author_role != 'assistant':
            print("[CSD] Warning: Last message block is not from the assistant (role: {author_role}). Cannot scrape response.")
            # Could optionally check the second-to-last block
            return None

        print("[CSD] Scraping latest assistant response...")
        # Find the actual message content within the block
        assistant_message_element = latest_block.find_element(By.CSS_SELECTOR, ASSISTANT_MESSAGE_SELECTOR)
        response_text = assistant_message_element.text
        print(f"[CSD] Scraped response length: {len(response_text)} characters.")
        return response_text

    except NoSuchElementException:
        print(f"[CSD] Error: Could not find assistant message element within the last block. Check CSS Selectors.")
    except Exception as e:
        print(f"[CSD] Error scraping latest response: {e}")
    return None

def main():
    print("[🚀] Starting Chat Scraper Dispatcher...")
    # Check if core imports succeeded
    if not core_imports_ok:
        print("[CSD] Cannot proceed due to missing core module imports. Exiting.")
        sys.exit(1)

    driver = None
    try:
        # --- Setup WebDriver ---
        options = webdriver.ChromeOptions()
        if CHROME_PROFILE_PATH:
            options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
            print(f"[CSD] Using Chrome profile: {CHROME_PROFILE_PATH}")
        else:
            print("[CSD] Using default Chrome session.")
        # Add arguments to potentially keep browser open after script finishes (optional)
        # options.add_experimental_option("detach", True)

        # Consider using webdriver_manager to automatically handle driver download
        # from selenium.webdriver.chrome.service import Service as ChromeService
        # from webdriver_manager.chrome import ChromeDriverManager
        # driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        # --- OR --- specify path manually if needed:
        # service = webdriver.ChromeService(executable_path='/path/to/chromedriver')
        # driver = webdriver.Chrome(service=service, options=options)
        # --- OR --- Simplest (if chromedriver is in PATH):
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(5) # Small implicit wait

        # --- Find ChatGPT Tab --- 
        if not find_chatgpt_tab(driver):
             raise Exception("Failed to find ChatGPT tab.")

        # --- Generate Governance DATA (changed from summary) --- 
        governance_data = generate_governance_data()
        if not governance_data:
            raise Exception("Failed to generate governance data.")

        # --- Render Prompt using Jinja2 Template --- 
        print("[CSD] Rendering prompt using template: templates/chatgpt_governance.md.j2")
        try:
            full_prompt = render_template("chatgpt_governance.md.j2", governance_data)
        except Exception as e:
            print(f"[CSD] Error rendering Jinja2 template: {e}")
            # Optionally log the raw data for debugging
            # print("Raw data:", json.dumps(governance_data, indent=2))
            raise Exception("Failed to render prompt template.")

        print(f"\n--- Rendered Prompt to Inject (length: {len(full_prompt)}) ---\n{full_prompt[:400]}...\n--------------------")

        # --- Inject and Send --- 
        if not inject_prompt_and_send(driver, full_prompt):
            raise Exception("Failed to inject or send prompt.")

        # --- Wait for Response --- 
        if not wait_for_response_completion(driver):
            # Decide whether to proceed if response didn't complete cleanly
            print("[CSD] Warning: Response may not have completed cleanly.")

        # --- Scrape Response --- 
        response_text = scrape_latest_response(driver)

        if response_text:
            print(f"\n--- Scraped Response (length: {len(response_text)}) ---
{response_text[:500]}...\n--------------------")
            # --- Save Response --- 
            try:
                # Ensure analysis directory exists
                os.makedirs(os.path.dirname(RESPONSE_OUTPUT_FILE), exist_ok=True)
                with open(RESPONSE_OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    f.write(response_text)
                print(f"[💾] Response saved to {RESPONSE_OUTPUT_FILE}")
                # --- TODO: Trigger gpt_command_router.py --- 
                print("[下一步] Trigger core/gpt_command_router.py to process the response.")
            except Exception as e:
                print(f"[❌] Failed to save response file: {e}")
        else:
            print("[❌] Failed to scrape a response from ChatGPT.")

    except Exception as e:
        print(f"\n[💥] An unexpected error occurred: {e}")
    finally:
        if driver:
            print("\n[CSD] Closing browser driver (unless detached)...")
            # driver.quit() # Uncomment to close browser window automatically
        print("[🏁] Chat Scraper Dispatcher finished.")

if __name__ == "__main__":
    main() 