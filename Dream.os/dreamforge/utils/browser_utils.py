import os
# import sys # No longer needed after path setup
import time
from typing import Optional
import sys # Added sys back temporarily for path

import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# Import specific WebDriver exceptions
from selenium.common.exceptions import WebDriverException 

# Add project root to sys.path
script_dir = os.path.dirname(__file__) # social/utils
# project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..')) # Still correct (up two levels)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# del sys # Remove sys from module scope after use - Keep for now

# Import Governance Logger
try:
    from dreamforge.core.governance_memory_engine import log_event # UPDATED IMPORT
except ImportError as import_err:
    import json # Need json for fallback
    # print(f"[BrowserUtils] Warning: Failed to import log_event: {import_err}")
    def log_event(event_type, agent_source, details):
        try:
            details_str = json.dumps(details)
        except TypeError:
             details_str = str(details)
        print(f"[Dummy Logger] Event: {event_type}, Source: {agent_source}, Details: {details_str}")
        return False

# Removed placeholder example imports

# Define a source name for logging
_SOURCE = "BrowserUtils"

# --- Constants ---
DEFAULT_WAIT_TIMEOUT_SECONDS = 10
# Removed hardcoded version
# DEFAULT_CHROME_VERSION = 119 
# ---------------

def get_undetected_driver(headless=False, user_data_dir=None, chrome_version: Optional[int] = None):
    """Initializes and returns an undetected ChromeDriver instance.

    Args:
        headless (bool): Whether to run Chrome in headless mode.
        user_data_dir (Optional[str]): Path to Chrome user data directory for session persistence.
        chrome_version (Optional[int]): Specific Chrome major version to use. If None, undetected_chromedriver attempts auto-detection.

    Returns:
        Optional[uc.Chrome]: An initialized ChromeDriver instance or None on failure.
    """
    options = uc.ChromeOptions()
    # --- Common Options --- 
    # options.add_argument('--disable-gpu') # May be needed on some systems/VMs
    # options.add_argument('--no-sandbox') # Often required in containerized environments
    # options.add_argument('--disable-dev-shm-usage') # Overcomes limited resource issues
    
    # Attempt to make the browser look less like an automated tool
    options.add_argument('--disable-blink-features=AutomationControlled') 
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    if headless:
        options.add_argument('--headless=new') # Use the modern headless mode
        # Headless mode often requires disabling the GPU
        options.add_argument('--disable-gpu')

    if user_data_dir:
        abs_user_data_dir = os.path.abspath(user_data_dir)
        log_event("AGENT_INFO", _SOURCE, {"info": "Using user data directory", "path": abs_user_data_dir})
        options.add_argument(f"--user-data-dir={abs_user_data_dir}")
        # Optional: Specify profile directory within user_data_dir if needed
        # options.add_argument('--profile-directory=Default') 

    driver = None
    try:
        log_details = {"step": "Initializing undetected ChromeDriver"}
        if chrome_version:
            log_details["chrome_version_target"] = chrome_version
        else:
            log_details["chrome_version_target"] = "Auto-detect"
        log_event("AGENT_STEP", _SOURCE, log_details)
        
        # Initialize uc.Chrome, specifying version if provided
        driver = uc.Chrome(options=options, version_main=chrome_version) 
        
        # Additional step after driver init to prevent detection (common practice)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        log_event("AGENT_INFO", _SOURCE, {"info": "Undetected ChromeDriver initialized successfully"})
        
    except WebDriverException as wde:
        error_msg = f"WebDriverException initializing ChromeDriver: {wde.msg}"
        log_details = {
            "error": "WebDriverException during ChromeDriver initialization", 
            "exception_type": type(wde).__name__,
            "message": wde.msg,
            "details": str(wde), 
            "troubleshooting": f"Check Chrome browser version compatibility (Target: {chrome_version or 'Auto'}), chromedriver executable/permissions, and network connectivity."
        }
        log_event("AGENT_ERROR", _SOURCE, log_details)
        if driver:
            try: driver.quit() 
            except Exception: pass
        return None
    except Exception as e:
        error_msg = f"Unexpected error initializing ChromeDriver: {e}"
        log_event("AGENT_ERROR", _SOURCE, {
            "error": "Unexpected error initializing undetected ChromeDriver", 
            "exception_type": type(e).__name__,
            "details": str(e), 
            "troubleshooting": "Review system setup, dependencies, and previous logs for context."
        })
        if driver:
            try: driver.quit() 
            except Exception: pass
        return None

    return driver

# --- Helper Functions (Add more as needed) ---

def wait_and_click(driver, by_locator, timeout=DEFAULT_WAIT_TIMEOUT_SECONDS):
    """Waits for an element to be clickable and then clicks it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(by_locator)
        )
        element.click()
        return True
    except Exception as e:
        # print(f"Error clicking element {by_locator}: {e}")
        log_event("AGENT_WARNING", _SOURCE, {"warning": "Error clicking element", "locator": str(by_locator), "details": str(e)})
        return False

def wait_and_send_keys(driver, by_locator, text, timeout=DEFAULT_WAIT_TIMEOUT_SECONDS):
    """Waits for an element to be visible and then sends keys to it."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(by_locator)
        )
        element.clear()
        element.send_keys(text)
        return True
    except Exception as e:
        # print(f"Error sending keys to element {by_locator}: {e}")
        log_event("AGENT_WARNING", _SOURCE, {"warning": "Error sending keys to element", "locator": str(by_locator), "details": str(e)})
        return False 

# --- Removed Unused Function ---
# def setup_driver(profile_path=None):
#     # ... (rest of function)
#     pass 