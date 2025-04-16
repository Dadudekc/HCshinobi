import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import random
import os
import traceback

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (NoSuchElementException, TimeoutException, 
                                      StaleElementReferenceException, ElementClickInterceptedException)

# Add project root to sys.path
# ... (path setup)

# Local imports
from .browser_utils import get_undetected_driver

# --- Governance Memory Import ---
try:
    from governance_memory_engine import log_event
except ImportError:
    log_event = None

AGENT_ID = "BrowserControllerUtil"

class BrowserController:
    def __init__(self, user_data_dir="chrome_user_data", headless=True, cookies_path="openai_cookies.json"):
        """Initializes the browser controller."""
        self.driver = None
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.cookies_path = cookies_path
        
        # Ensure logger exists
        global log_event
        if log_event is None:
             print(f"[{AGENT_ID}] Warning: Real log_event not imported. Using dummy logger.")
             def dummy_log_event(etype, src, dtls):
                  try: details_str = json.dumps(dtls)
                  except: details_str = str(dtls)
                  print(f"[DUMMY GME LOG] {etype} | {src} | {details_str}")
             log_event = dummy_log_event
             
        log_event("UTIL_INIT", AGENT_ID, {"headless": headless, "cookies": cookies_path})

        # Common CSS Selectors (These might change, update if needed)
        self.selectors = {
            "chat_list_item": "a.flex.py-3.px-3", # Selector for items in the conversation list
            "chat_title": ".flex-1.text-ellipsis.max-h-5", # Selector for the title within a list item
            "textarea": "#prompt-textarea", # Input textarea
            "send_button": '[data-testid="send-button"]', # Send button
            "response_block": ".markdown.prose", # Block containing a GPT response
            "regenerate_button": ".btn-primary.justify-center", # Often present while GPT is generating or if there was an error
            "login_page_indicator": 'button[type="submit"]' # An element typically present on the login page
        }

    def _initialize_driver(self):
        """Initializes the undetected ChromeDriver."""
        if not self.driver:
            # print("Initializing WebDriver...") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "init_driver"})
            try:
                self.driver = get_undetected_driver(user_data_dir=self.user_data_dir, headless=self.headless)
                # print("WebDriver initialized.") # Verbose
            except Exception as e:
                # print(f"Error initializing WebDriver: {e}") # Use logger
                log_event("UTIL_ERROR", AGENT_ID, {"error": "Driver init failed", "details": str(e), "traceback": traceback.format_exc()})
                raise # Re-raise as this is critical
        return self.driver

    def _load_cookies(self):
        """Loads cookies from the specified file."""
        if not os.path.exists(self.cookies_path):
            # print(f"Error: Cookies file not found at {self.cookies_path}") # Use logger
            # print("Please ensure you have exported cookies using scripts/export_cookies.py") # Docs/Warning
            log_event("UTIL_WARNING", AGENT_ID, {"warning": "Cookies file not found", "path": self.cookies_path})
            return False

        try:
            with open(self.cookies_path, 'r') as f:
                cookies = json.load(f)
            for cookie in cookies:
                # Handle potential SameSite attribute issues if needed
                if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
                     # print(f"Adjusting SameSite attribute for cookie: {cookie['name']}")
                     cookie['sameSite'] = 'Lax' # Example adjustment
                self.driver.add_cookie(cookie)
            # print("Cookies loaded successfully.") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "load_cookies", "status": "success", "count": len(cookies)})
            return True
        except Exception as e:
            # print(f"Error loading cookies: {e}") # Use logger
            log_event("UTIL_ERROR", AGENT_ID, {"error": "Failed to load cookies", "path": self.cookies_path, "details": str(e)})
            return False

    def login_to_chatgpt(self):
        """Navigates to ChatGPT and uses cookies to authenticate."""
        # print("Navigating to chat.openai.com...") # Verbose
        log_event("UTIL_STEP", AGENT_ID, {"step": "navigate_chatgpt"})
        self._initialize_driver()
        self.driver.get("https://chat.openai.com/")
        time.sleep(2) # Allow initial page load

        if not self._load_cookies():
            # print("Proceeding without cookies. Manual login might be required.") # Logged in _load_cookies
            return False # Indicate potential failure if cookies are essential

        # print("Refreshing page to apply cookies...") # Verbose
        log_event("UTIL_STEP", AGENT_ID, {"step": "refresh_after_cookies"})
        self.driver.refresh()
        time.sleep(5) # Wait for page to potentially redirect/reload after login

        # Check if login was successful (presence of textarea is a good indicator)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
            # print("Login via cookies appears successful.") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "login_chatgpt", "status": "success"})
            return True
        except TimeoutException:
            # print("Login via cookies failed or session expired. Textarea not found.") # Use logger
            log_event("UTIL_WARNING", AGENT_ID, {"warning": "Login failed (textarea not found)"})
            # Optional: Check for login page elements
            try:
                 self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log in')]")
                 # print("Detected elements suggesting a login page. Manual intervention might be needed.") # Use logger
                 log_event("UTIL_WARNING", AGENT_ID, {"warning": "Login page detected after cookie load attempt"})
            except NoSuchElementException:
                 # print("Could not confirm if on login page, but login seems to have failed.") # Logged above
                 pass
            return False

    def find_and_click_chat(self, title_keyword):
        """Finds and clicks on a chat based on a keyword in its title."""
        # print(f"Searching for chat containing keyword: '{title_keyword}'...") # Verbose
        log_event("UTIL_STEP", AGENT_ID, {"step": "find_chat", "keyword": title_keyword})
        try:
            # Wait for chat list items to be present
            chat_list_items = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//nav//a[contains(@href, '/c/')]"))
            )
            # print(f"Found {len(chat_list_items)} potential chats.") # Verbose
            
            matched_element = None
            for chat_element in chat_list_items:
                try:
                    # Extract title (handle potential stale elements)
                    title_element = chat_element.find_element(By.XPATH, ".//div[1]") # Assuming title is in the first div
                    title = title_element.text
                    # # print(f"Checking chat: {title}") # Debugging: print titles
                    if title_keyword.lower() in title.lower():
                        # print(f"Match found: '{title_element.text}'") # Verbose
                        log_event("UTIL_INFO", AGENT_ID, {"info": "Chat found by keyword", "title": title})
                        matched_element = chat_element
                        break
                except StaleElementReferenceException:
                    continue # Skip if element went stale
                except Exception as e:
                    # print(f"Error processing chat element: {e}") # Use logger
                    log_event("UTIL_WARNING", AGENT_ID, {"warning": "Error processing chat element", "details": str(e)})
                    continue

            if matched_element:
                # print("Clicking matched chat...") # Verbose
                log_event("UTIL_STEP", AGENT_ID, {"step": "click_chat"})
                matched_element.click()
                time.sleep(2) # Wait for chat content to load
                return True
            else:
                 # print("Keyword not found. Falling back to the latest chat.") # Use logger
                 log_event("UTIL_INFO", AGENT_ID, {"info": "Keyword not found, using latest chat"})
                 if chat_list_items: # Check if list exists
                      chat_list_items[0].click() # Click the first (latest) chat
                      time.sleep(2)
                      return True
                 else:
                      # print("Keyword not found, and no fallback or no chats available.") # Use logger
                      log_event("UTIL_WARNING", AGENT_ID, {"warning": "Chat keyword not found, no fallback available"})
                      return False

        except TimeoutException:
             # print("Could not find chat list items. Is the page loaded correctly?") # Use logger
             log_event("UTIL_ERROR", AGENT_ID, {"error": "Chat list not found (Timeout)"})
             return False
        except Exception as e:
            # print(f"An error occurred while searching for chat: {e}") # Use logger
            log_event("UTIL_ERROR", AGENT_ID, {"error": "Error finding chat", "details": str(e), "traceback": traceback.format_exc()})
            return False

    def send_message(self, message, type_speed=0.05):
        """Sends a message to the currently open chat."""
        # print("Sending message...") # Verbose
        log_event("UTIL_STEP", AGENT_ID, {"step": "send_message", "length": len(message)})
        try:
            # Ensure textarea is present and clear it first
            textarea = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "prompt-textarea"))
            )
            textarea.clear()

            if type_speed > 0:
                 # print("Simulating typing...") # Verbose
                 for char in message:
                     textarea.send_keys(char)
                     time.sleep(random.uniform(type_speed * 0.5, type_speed * 1.5))
                 time.sleep(0.5) # Pause after typing
            else:
                 # print("Sending instantly...") # Verbose
                 textarea.send_keys(message)
                 time.sleep(0.1) # Small delay even for instant send
            
            # Find and click the send button
            send_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='send-button']"))
            )
            send_button.click()
            # print("Message sent.") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "send_message", "status": "success"})
            return True

        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
             # print("Error: Textarea or Send button not found/clickable in time.") # Use logger
             log_event("UTIL_ERROR", AGENT_ID, {"error": "Send message failed (element issue)", "details": str(e)})
             return False
        except Exception as e:
            # print(f"An error occurred while sending message: {e}") # Use logger
            log_event("UTIL_ERROR", AGENT_ID, {"error": "Send message failed (unexpected)", "details": str(e), "traceback": traceback.format_exc()})
            return False

    def get_latest_response(self, timeout=120):
        """Waits for and retrieves the latest response from ChatGPT."""
        # print("Waiting for response...") # Verbose
        log_event("UTIL_STEP", AGENT_ID, {"step": "get_response", "timeout": timeout})
        start_time = time.time()
        last_response_element = None
        try:
            # Wait until the response generation seems complete (e.g., send button re-appears/enables)
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='send-button']"))
                # Alternate check: wait for the "Stop generating" button to disappear?
                # EC.invisibility_of_element_located((By.XPATH, "//button[contains(., 'Stop generating')]"))
            )
            
            # Give a brief moment for the final content to settle
            time.sleep(1)
            
            # Find all response blocks (adjust selector as needed)
            response_blocks = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'text-message')]//div[contains(@class, 'markdown')]")
            
            if not response_blocks:
                 # print("No response blocks found.") # Use logger
                 log_event("UTIL_WARNING", AGENT_ID, {"warning": "No response blocks found after wait"})
                 return None
                 
            # Get the text from the last response block
            last_response_element = response_blocks[-1]
            response_text = last_response_element.text
            # print(f"Response received (took {time.time() - start_time:.2f}s).") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "get_response", "status": "success", "duration": time.time() - start_time})
            return response_text

        except TimeoutException:
            # print(f"Error: Timed out waiting for response (>{timeout}s).") # Use logger
            log_event("UTIL_ERROR", AGENT_ID, {"error": "Timeout waiting for response", "duration": timeout})
            # Check if a response block appeared just after timeout
            try:
                response_blocks = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'text-message')]//div[contains(@class, 'markdown')]")
                if response_blocks:
                    # print("Found a response block after timeout, attempting to retrieve.") # Log as warning
                    log_event("UTIL_WARNING", AGENT_ID, {"warning": "Response found after timeout", "duration": time.time() - start_time})
                    return response_blocks[-1].text
            except Exception:
                 pass # Ignore errors trying to recover after timeout
            return None
        except Exception as e:
            # print(f"An error occurred while getting response: {e}") # Use logger
            log_event("UTIL_ERROR", AGENT_ID, {"error": "Failed to get response", "details": str(e), "traceback": traceback.format_exc()})
            return None

    def close(self):
        """Closes the browser."""
        if self.driver:
            # print("Closing browser...") # Verbose
            log_event("UTIL_STEP", AGENT_ID, {"step": "close_browser"})
            try:
                self.driver.quit()
                # print("Browser closed.") # Verbose
            except Exception as e:
                 log_event("UTIL_ERROR", AGENT_ID, {"error": "Failed to quit driver", "details": str(e)})
            self.driver = None

# Example Usage (for testing purposes)
if __name__ == '__main__':
    controller = BrowserController(headless=False) # Run non-headless for easy viewing
    
    # Ensure logger exists for testing this block
    if 'log_event' not in globals() or log_event is None:
         def dummy_log_event(etype, src, dtls): print(f"[MAIN DUMMY LOG] {etype} | {src} | {dtls}")
         log_event = dummy_log_event
         print("Using dummy log_event in main block.")
         
    try:
        if controller.login_to_chatgpt():
            # Example: Find a chat and send a message
            if controller.find_and_click_chat("Cursor"): # Find chat with "Cursor" or latest
                 if controller.send_message("Hello from the Browser Controller! How are you?"):
                     response = controller.get_latest_response()
                     if response:
                         print("\n--- Latest Response ---")
                         print(response)
                         print("-----------------------\n")
                     else:
                         print("Failed to get response.")
                 else:
                     print("Failed to send message.")
            else:
                print("Failed to find specified chat.")
        else:
            print("Login failed. Cannot proceed.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
    finally:
        controller.close() 