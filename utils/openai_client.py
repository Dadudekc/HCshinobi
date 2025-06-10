import os
import time
import json
import pickle
import logging
import shutil
import platform
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse
import getpass

# Standard logger - configuration should be handled externally
logger = logging.getLogger(__name__)

class OpenAIClient:
    # Static tracking of booted state
    _booted = False
    _instance = None
    # Thread executor for blocking operations
    _executor = ThreadPoolExecutor(max_workers=1)

    def __init__(self, profile_dir=None, cookie_dir=None, target_gpt_url=None, headless=False, driver_path=None, api_key=None):
        """
        Initialize the OpenAIClient.

        Args:
            profile_dir (str, optional): Path to the Chrome user data directory. Not required for API key auth.
            cookie_dir (str, optional): Path to the directory where cookies should be stored. Not required for API key auth.
            target_gpt_url (str, optional): The URL of the specific custom GPT to interact with. Not required for API key auth.
            headless (bool): Whether to run Chrome in headless mode. Defaults to False.
            driver_path (str): Optional custom path to a ChromeDriver binary (not recommended).
            api_key (str, optional): OpenAI API key. If provided, will use API authentication instead of web scraping.
        """
        self.api_key = api_key
        self.profile_dir = str(Path(profile_dir)) if profile_dir else None
        self.cookie_dir = str(Path(cookie_dir)) if cookie_dir else None
        self.target_gpt_url = target_gpt_url
        self.headless = headless
        self.driver_path = driver_path
        self.driver = None
        self._booted = False  # Instance boot state
        self.using_api = bool(api_key)  # Track if we're using API or web client

        # API client setup if API key is provided
        if self.api_key:
            try:
                # Try importing the OpenAI package - this assumes it's installed
                import openai
                self.openai = openai
                self.openai.api_key = self.api_key
                logger.info("✅ Initialized OpenAI client with API key")
            except ImportError:
                logger.error("❌ Failed to import OpenAI package. Please install with: pip install openai")
                raise ImportError("OpenAI package not installed. Please run: pip install openai")
        # Web scraping setup if no API key
        elif all([self.profile_dir, self.cookie_dir, self.target_gpt_url]):
            # Configuration for web client
            self.COOKIE_FILE = str(Path(self.cookie_dir) / "openai_custom_gpt.pkl") # Use specific cookie name

            # Extract base domain for some checks if needed, though target_gpt_url is primary
            parsed_url = urlparse(self.target_gpt_url)
            self.base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            logger.info("✅ Initialized OpenAI web scraping client")
        else:
            logger.warning("⚠️ Insufficient configuration for both API and web scraping modes.")

        # Set as class instance (consider potential issues if multiple instances are created)
        OpenAIClient._instance = self

    @staticmethod
    def prompt_for_api_key():
        """
        Prompt the user to input their OpenAI API key if not found in environment.
        
        Returns:
            str: The OpenAI API key
        """
        print("\n" + "="*50)
        print("🔑 OpenAI API Key Required")
        print("="*50)
        print("Your OpenAI API key was not found in the environment.")
        print("You can get your API key from: https://platform.openai.com/api-keys")
        print("\nThe API key will be used for this session only unless you save it to your .env file.")
        api_key = getpass.getpass("Enter your OpenAI API key: ")
        print("="*50)
        
        if api_key:
            # Offer to save to .env file
            save_to_env = input("Would you like to save this API key to your .env file for future use? (y/n): ").lower()
            if save_to_env in ('y', 'yes'):
                try:
                    # Read current .env file if it exists
                    env_path = Path('.env')
                    env_content = env_path.read_text() if env_path.exists() else ""
                    
                    # Check if OPENAI_API_KEY is already in the file
                    if "OPENAI_API_KEY=" in env_content:
                        # Replace existing key
                        import re
                        env_content = re.sub(r'OPENAI_API_KEY=.*', f'OPENAI_API_KEY="{api_key}"', env_content)
                    else:
                        # Add new key
                        env_content += f'\nOPENAI_API_KEY="{api_key}"\n'
                    
                    # Write back to .env file
                    env_path.write_text(env_content)
                    print("✅ API key saved to .env file")
                except Exception as e:
                    print(f"❌ Failed to save API key to .env file: {e}")
                    print("You'll need to enter your API key again next time.")
        
        # Set in environment for current session
        os.environ["OPENAI_API_KEY"] = api_key
        return api_key

    @classmethod
    def is_booted(cls):
        """Check if any instance of OpenAIClient has been booted."""
        return cls._booted

    def get_openai_driver(self):
        """
        Returns a stealth Chrome driver using undetected_chromedriver.
        Only used for web scraping mode.
        """
        if self.using_api:
            logger.info("🔧 Using API mode, no browser driver needed.")
            return None
            
        logger.info("🔧 Initializing undetected_chromedriver for OpenAIClient...")

        try:
            options = uc.ChromeOptions()

            # Recommended settings
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--start-maximized") # Start maximized unless headless

            if self.profile_dir:
                options.add_argument(f"--user-data-dir={self.profile_dir}")
                logger.info(f"Using Chrome profile directory: {self.profile_dir}")
            else:
                 logger.warning("⚠️ No profile directory specified. Session might not persist well.")

            if self.headless:
                # Use the new headless mode for more reliability
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--window-size=1920,1080") # Ensure a standard window size
                logger.info("Running in headless mode.")

            # Let undetected_chromedriver manage driver automatically
            logger.info("🔄 Letting undetected_chromedriver automatically manage driver version.")
            driver = uc.Chrome(options=options, use_subprocess=True)

            logger.info("✅ Undetected Chrome driver initialized for OpenAI.")
            return driver

        except Exception as e:
            error_msg = f"❌ Failed to initialize Chrome driver: {e}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) # Re-raise for calling code to handle

    def save_openai_cookies(self):
        """
        Save OpenAI cookies to a pickle file.
        """
        os.makedirs(self.cookie_dir, exist_ok=True)
        try:
            cookies = self.driver.get_cookies()
            with open(self.COOKIE_FILE, "wb") as f:
                pickle.dump(cookies, f)
            logger.info(f"✅ Saved OpenAI cookies to {self.COOKIE_FILE}")
        except Exception as e:
            logger.error(f"❌ Failed to save cookies: {e}")

    async def load_openai_cookies(self):
        """
        Load OpenAI cookies from file and refresh session. Async version.
        """
        if not os.path.exists(self.COOKIE_FILE):
            logger.warning(f"⚠️ No OpenAI cookie file found at {self.COOKIE_FILE}. Manual login may be required.")
            return False

        # Navigate to the base domain first to set cookies
        self.driver.get(self.base_domain + "/")
        await asyncio.sleep(2)  # Non-blocking sleep

        try:
            with open(self.COOKIE_FILE, "rb") as f:
                cookies = pickle.load(f)

            # Delete existing cookies for the domain before adding new ones
            self.driver.delete_all_cookies()

            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as cookie_err:
                    logger.debug(f"⚠️ Error adding cookie: {cookie_err}")
                    
            logger.info("✅ Loaded OpenAI cookies")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load cookies: {e}")
            return False

    def is_logged_in(self):
        """
        Checks if the user is logged in to ChatGPT by navigating to the target custom GPT URL
        and verifying the URL doesn't redirect to a login page.
        """
        logger.info(f"Checking login status by navigating to: {self.target_gpt_url}")
        self.driver.get(self.target_gpt_url)
        time.sleep(5) # Allow time for potential redirects
        current_url = self.driver.current_url
        logger.info(f"Current URL after navigation: {current_url}")

        # Check if the current URL still points to the target GPT or the main chat interface
        # and doesn't contain login/auth paths. This is a heuristic.
        if current_url.startswith(self.target_gpt_url) or \
           (current_url.startswith(self.base_domain) and "/auth/" not in current_url and "/login" not in current_url):
            logger.info(f"✅ Seems logged in. Current URL is {current_url}")
            # Optional: Add a check for a known element on the logged-in page
            # try:
            #     WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "prompt-textarea"))) # Example element
            #     logger.info("✅ Found prompt textarea, confirming login.")
            #     return True
            # except:
            #     logger.warning("⚠️ Could not find prompt textarea, login state uncertain.")
            #     return False # Or True based on URL check confidence
            return True
        else:
            logger.warning(f"⚠️ Redirected or unable to confirm login state. Current URL: {current_url}")
            return False

    def boot(self):
        """Initialize the OpenAI driver or API client."""
        if self._booted:
            logger.info("⚠️ OpenAIClient instance already booted.")
            return
        if OpenAIClient._booted and OpenAIClient._instance is not self:
            logger.warning("⚠️ Another OpenAIClient instance is already booted. Managing multiple clients can be complex.")

        try:
            # For API mode, just set the API key if needed
            if self.using_api:
                if not self.api_key:
                    # Check environment for API key
                    self.api_key = os.environ.get("OPENAI_API_KEY")
                    
                    # If still not found, prompt the user
                    if not self.api_key:
                        self.api_key = self.prompt_for_api_key()
                        
                    # Update the OpenAI client with the API key
                    self.openai.api_key = self.api_key
                    
                logger.info("🚀 OpenAI API client ready.")
            # For web scraping mode, initialize the driver
            else:
                self.driver = self.get_openai_driver()
                
            # Set both instance and class booted flags upon successful initialization
            self._booted = True
            OpenAIClient._booted = True  # Mark that *a* client is booted
            logger.info("🚀 OpenAIClient boot complete.")
        except Exception as e:
            logger.error(f"❌ OpenAIClient boot failed during initialization: {e}", exc_info=True)
            self._booted = False
            # Only turn off class flag if this *was* the primary instance or no instance exists
            if OpenAIClient._instance is self or not OpenAIClient._instance:
                 OpenAIClient._booted = False
            raise  # Re-raise the exception

    def _assert_ready(self):
        """Check if the client is ready for use."""
        if not self._booted:
            raise RuntimeError("❌ OpenAIClient not booted. Call `.boot()` first.")
        
        if not self.using_api and not self.driver:
            raise RuntimeError("❌ Web scraping driver not initialized. Call `.boot()` first.")

    async def process_prompt(self, prompt, timeout=180, model_url=None, model=None):
        """
        Send a prompt to OpenAI using the specified model and get the response.
        Async version that doesn't block the event loop.
        
        Args:
            prompt: The user prompt.
            timeout: Maximum time to wait for a response in seconds.
            model_url: Optional URL to a specific model when using web interface.
            model: Optional model name to use when using API (defaults to "gpt-4").
        """
        if self.using_api:
            # This directly uses the API for a clean, reliable experience
            try:
                # Use the specified model or fall back to gpt-4
                model_name = model if model else "gpt-4"
                logger.info(f"Using model: {model_name} via API")
                
                response = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.openai.ChatCompletion.create(
                        model=model_name,  # Use the specified model
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ]
                    )
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"❌ API call failed: {e}")
                return f"Error: {str(e)}"
        
        # Web-based approach for the rest
        self._assert_ready()
        
        # Use the specified model URL or default to the configured target
        target_url = model_url or self.target_gpt_url
        
        # If a model is specified and we're using web interface, try to update the URL
        if model and not model_url and "chat.openai.com" in self.target_gpt_url:
            # Attempt to construct a URL with the model parameter
            base_url = self.target_gpt_url.split("?")[0]
            target_url = f"{base_url}?model={model}"
            logger.info(f"Using model-specific URL: {target_url}")
        
        # Navigate to the model URL
        await asyncio.get_event_loop().run_in_executor(
            self._executor,
            lambda: self.driver.get(target_url)
        )
        
        # Wait for page load
        await asyncio.sleep(3)  # Non-blocking sleep
            
        try:
            # Wait for the textarea to be present
            prompt_textarea = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
            )
            
            # Clear any existing text and send our prompt
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: prompt_textarea.clear()
            )
            
            # Send the prompt with a natural typing effect
            await self.send_prompt_smoothly(prompt_textarea, prompt)
            
            # Press Enter to submit
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: prompt_textarea.send_keys(Keys.RETURN)
            )
            
            await asyncio.sleep(3)  # Non-blocking wait after sending
            
            # Now get the full response
            return await self.get_full_response(timeout)
            
        except Exception as e:
            error_msg = f"❌ Error processing prompt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._save_page_source("error_processing_prompt")
            return f"Error: {error_msg}"

    async def get_chatgpt_response(self, prompt, timeout=180, model_url=None, model=None):
        """
        Async wrapper around process_prompt that returns just the text response.
        This is the main external-facing method most callers should use.
        
        Args:
            prompt: The user prompt.
            timeout: Maximum time to wait for a response in seconds.
            model_url: Optional URL to a specific model when using web interface.
            model: Optional model name to use when using API (defaults to "gpt-4").
        """
        if self.using_api:
            # If using the API, process_prompt already returns clean text
            return await self.process_prompt(prompt, timeout, model_url, model)
        
        # For web scraping, we need to run this in the executor to prevent blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            lambda: self.process_prompt_sync(prompt, timeout, model_url, model)
        )
    
    def process_prompt_sync(self, prompt, timeout=180, model_url=None, model=None):
        """
        Synchronous version of process_prompt for use with run_in_executor.
        This should NOT be called directly by external code.
        
        Args:
            prompt: The user prompt.
            timeout: Maximum time to wait for a response in seconds.
            model_url: Optional URL to a specific model when using web interface.
            model: Optional model name to use when using API (defaults to "gpt-4").
        """
        # Implementation similar to original process_prompt but synchronous
        self._assert_ready()
        
        # Handle API mode
        if self.using_api:
            try:
                # Use the specified model or fall back to gpt-4
                model_name = model if model else "gpt-4"
                logger.info(f"Using model: {model_name} via API (sync)")
                
                response = self.openai.ChatCompletion.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"❌ API call failed: {e}")
                return f"Error: {str(e)}"
        
        # Use the specified model URL or default to the configured target
        target_url = model_url or self.target_gpt_url
        
        # If a model is specified and we're using web interface, try to update the URL
        if model and not model_url and "chat.openai.com" in self.target_gpt_url:
            # Attempt to construct a URL with the model parameter
            base_url = self.target_gpt_url.split("?")[0]
            target_url = f"{base_url}?model={model}"
            logger.info(f"Using model-specific URL: {target_url}")
        
        # Navigate to the model URL
        self.driver.get(target_url)
        
        # Wait for page load
        time.sleep(5)
            
        try:
            # Wait for the textarea to be present
            prompt_textarea = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
            )
            
            # Clear any existing text and send our prompt
            prompt_textarea.clear()
            
            # Send the prompt with a natural typing effect
            self.send_prompt_smoothly_sync(prompt_textarea, prompt)
            
            # Press Enter to submit
            prompt_textarea.send_keys(Keys.RETURN)
            
            time.sleep(3)
            
            # Now get the full response
            return self.get_full_response_sync(timeout)
            
        except Exception as e:
            error_msg = f"❌ Error processing prompt: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._save_page_source("error_processing_prompt")
            return f"Error: {error_msg}"

    def get_full_response(self, timeout=180):
        """
        Waits for the full response from ChatGPT, handling 'Continue generating'.
        Targets the container holding the latest response message.
        """
        self._assert_ready()
        logger.info(f"🔄 Waiting for full response (timeout: {timeout}s)...")
        start_time = time.time()
        full_response_text = ""
        last_response_text = ""
        stalled_time = None # Time when the response first appeared unchanged

        response_container_selector = "div[data-message-author-role='assistant']" # Selector for assistant messages
        response_text_selector = ".markdown" # Selector for the text content within the message

        wait = WebDriverWait(self.driver, 10) # Shorter wait for loops, longer for initial


        while True:
            current_time = time.time()
            if current_time - start_time > timeout:
                logger.warning("⚠️ Timeout reached while waiting for ChatGPT response.")
                break

            time.sleep(2) # Poll interval

            try:
                # Find all assistant message containers
                assistant_messages = self.driver.find_elements(By.CSS_SELECTOR, response_container_selector)

                if assistant_messages:
                    # Get the last assistant message container
                    latest_message_container = assistant_messages[-1]

                    # Find the text element within the last container
                    response_elements = latest_message_container.find_elements(By.CSS_SELECTOR, response_text_selector)
                    if response_elements:
                         # Combine text from potentially multiple markdown divs within the last message
                         current_response_part = "\n".join([elem.text for elem in response_elements]).strip()

                         if current_response_part != last_response_text:
                              logger.debug(f"🔄 Response updated. Length: {len(current_response_part)}")
                              last_response_text = current_response_part
                              stalled_time = None # Reset stalled timer
                         else:
                              # Response text hasn't changed
                              if stalled_time is None:
                                   stalled_time = current_time
                              elif current_time - stalled_time > 10: # If unchanged for 10 seconds
                                   logger.info("✅ Response appears complete (stable for 10s).")
                                   break # Assume completion
                    else:
                         # Container exists, but no text found yet, wait...
                         logger.debug("Found assistant message container, but no text yet...")
                         pass


                # Check for "Continue generating" button regardless of text stability
                try:
                    # Use a more specific selector if possible
                    continue_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Continue generating')]")
                    if continue_button.is_displayed() and continue_button.is_enabled():
                        logger.info("🔘 Clicking 'Continue generating'...")
                        continue_button.click()
                        stalled_time = None # Reset stalled timer after clicking continue
                        time.sleep(3) # Wait a bit after clicking
                        continue # Restart loop check immediately
                except:
                    # Button not found or not clickable, expected case when response is finishing/finished
                    pass

                # Check for the 'regenerate' button *only* if the response seems stalled,
                # as an indicator that generation might have finished.
                if stalled_time is not None and current_time - stalled_time > 5:
                     try:
                          # Check for a button typically present after generation stops
                          regen_button = self.driver.find_element(By.XPATH, "//button[contains(., 'Regenerate')]")
                          if regen_button.is_displayed():
                               logger.info("✅ Found 'Regenerate' button, likely end of response.")
                               break
                     except:
                          pass # Regenerate button not found, continue waiting


            except Exception as e:
                logger.error(f"❌ Error during response fetch loop: {e}", exc_info=True)
                # Decide whether to continue or break on error
                time.sleep(5) # Wait longer after an error
                continue # Or break

        # Final capture of the last response text found
        full_response_text = last_response_text
        logger.info(f"✅ Final response captured. Length: {len(full_response_text)}")
        return full_response_text

    async def send_prompt_smoothly(self, element, prompt, delay=0.05):
        """
        Send the prompt with a more natural typing cadence.
        Uses asyncio.sleep to avoid blocking the event loop.
        """
        # Implementation that uses async sleep and runs typing in executor
        for chunk in self._chunk_prompt(prompt):
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: element.send_keys(chunk)
            )
            await asyncio.sleep(delay)  # Non-blocking sleep between chunks
    
    def send_prompt_smoothly_sync(self, element, prompt, delay=0.05):
        """
        Synchronous version of send_prompt_smoothly for use with run_in_executor.
        """
        for char in prompt:
            element.send_keys(char)
            time.sleep(delay)
    
    def _chunk_prompt(self, prompt, chunk_size=3):
        """Helper to break prompt into chunks for smoother typing simulation"""
        return [prompt[i:i+chunk_size] for i in range(0, len(prompt), chunk_size)]

    def login_openai(self):
        """
        Login handler for OpenAI/ChatGPT.
        Checks if session is active; if not, tries to load cookies or falls back to manual login.
        """
        self._assert_ready()
        logger.info("🔐 Starting OpenAI login process...")

        # Attempt to load cookies and check login status first
        if self.load_openai_cookies() and self.is_logged_in():
            logger.info("✅ OpenAI auto-login successful with cookies.")
            return True

        # If cookie login fails, explicitly check if already logged in (maybe profile had session)
        if self.is_logged_in():
             logger.info("✅ Session active (possibly from profile). Login check passed.")
             # Save cookies even if loaded from profile to ensure they are current
             self.save_openai_cookies()
             return True

        logger.warning("⚠️ Auto-login failed or session invalid. Manual login required.")
        self.driver.get(self.base_domain + "/auth/login") # Navigate to generic login page
        time.sleep(5)

        # Rudimentary check for headless mode - cannot prompt for input
        if self.headless:
             logger.error("❌ Cannot prompt for manual login in headless mode. Login failed.")
             # Consider raising an exception or specific error handling here
             return False # Indicate failure

        input("👉 Please manually complete the login + verification in the browser window and press ENTER here...")

        if self.is_logged_in():
            self.save_openai_cookies()
            logger.info("✅ Manual OpenAI login successful. Cookies saved.")
            return True
        else:
            logger.error("❌ Manual OpenAI login failed after prompt. Please check the browser.")
            return False

    def _save_page_source(self, context="debug"):
        """Saves the current page source for debugging purposes."""
        try:
             debug_dir = Path(os.getcwd()) / "debug_pages"
             debug_dir.mkdir(exist_ok=True)
             filename = debug_dir / f"{context}_{int(time.time())}.html"
             with open(filename, "w", encoding="utf-8") as f:
                  f.write(self.driver.page_source)
             logger.info(f"📄 Saved page source for debugging to: {filename}")
        except Exception as e:
             logger.error(f"❌ Failed to save page source: {e}")

    async def shutdown(self):
        """
        Cleanly close the browser driver.
        Async version that doesn't block the event loop.
        """
        if self.driver:
            try:
                logger.info("Closing Chrome driver...")
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self.driver.quit()
                )
                self.driver = None
                self._booted = False
                logger.info("✅ Chrome driver closed successfully")
            except Exception as e:
                logger.error(f"❌ Error closing Chrome driver: {e}", exc_info=True)
                # Try force killing as a fallback
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    self._force_kill_chromedriver
                )
        
        # Also shut down the executor
        self._executor.shutdown(wait=False)
        
        logger.info("✅ OpenAI client shutdown complete")

    def _force_kill_chromedriver(self):
        """
        Force kill any remaining ChromeDriver processes. (Use cautiously)
        """
        try:
            import subprocess
            logger.warning("🔄 Attempting to force kill ChromeDriver processes...")
            proc_name = "chromedriver"
            chrome_proc_name = "chrome"
            if platform.system() == "Windows":
                proc_name += ".exe"
                chrome_proc_name += ".exe"
                subprocess.run(["taskkill", "/f", "/im", proc_name], check=False, capture_output=True)
                subprocess.run(["taskkill", "/f", "/im", chrome_proc_name], check=False, capture_output=True)
            else: # Linux & macOS
                subprocess.run(["pkill", "-f", proc_name], check=False, capture_output=True)
                # Be careful with pkill chrome/Chrome as it might kill user's normal browser
                # subprocess.run(["pkill", "-f", chrome_proc_name], check=False, capture_output=True)
            logger.info("✅ Forced termination attempt of ChromeDriver processes completed.")
        except FileNotFoundError:
             logger.warning(f"Could not find taskkill/pkill command. Skipping force kill.")
        except Exception as e:
            logger.error(f"❌ Error during force kill: {e}")

    # Example method to handle application close if integrated with a GUI framework
    # def closeEvent(self, event):
    #     """ Handle application close event. """
    #     logger.info("Close event triggered. Shutting down OpenAIClient.")
    #     self.shutdown()
    #     if event: # Check if event object is passed
    #         event.accept()

