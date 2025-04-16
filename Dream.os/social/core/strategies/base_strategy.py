"""
Base strategy class for social media platform interactions.
"""

import os
import json
import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from social.exceptions import StrategyError
from utils.common import retry_on_exception
from utils.selenium_utils import wait_for_element, safe_click, safe_send_keys, navigate_to
from utils.logging_utils import get_logger, log_event, setup_logging
from utils.retry_utils import retry_on_stale_element
from core.exceptions.strategy_exceptions import LoginError, PostError, ScrapeError, AuthenticationError, RateLimitError, ContentError
from utils.browser_utils import get_driver

logger = get_logger("BaseSocialStrategy")

class BaseSocialStrategy(ABC):
    """Abstract base class for social media platform interactions."""
    
    def __init__(self, driver: WebDriver, config_override: Dict[str, Any]):
        """Initialize base strategy.
        
        Args:
            driver: Selenium WebDriver instance
            config_override: Platform configuration and credentials.
        """
        self.driver = get_driver() # Use utility to get driver
        self.logged_in = False
        self.logger = logging.getLogger(__name__)
        self.config = config_override if config_override else {} # Store config, ensure it's a dict
        
        # Use provided config or hardcoded defaults
        self.timeout = self.config.get("timeout", 15) # Default to 15 seconds
        self.max_retries = self.config.get("max_retries", 2) # Default to 2 retries
        # Credentials (username/password) are expected within self.config
        
        log_event("init", f"Initialized {self.__class__.__name__}", {
            "timeout": self.timeout,
            "max_retries": self.max_retries
        })
        
    @abstractmethod
    def login(self, username: Optional[str] = None, password: Optional[str] = None, cookies: Optional[str] = None) -> bool:
        """Log into the social media platform.
        
        Returns:
            bool: True if login successful
        """
        if not self.driver:
            self.logger.error("Driver is not initialized.")
            return False
        
        # try:
        #     self.driver.get(url)
        #     self.logger.info(f"Navigated to {url}")
        # except Exception as e:
        #     self.logger.error(f"Failed to navigate to {url}: {e}")
        #     raise StrategyError(f"Navigation failed: {e}", platform=self.__class__.__name__, action="navigate", original_exception=e)
        # Commenting out direct navigation - subclasses should handle this via specific methods
        # or a dedicated navigation method should be implemented if truly generic.
        self.logger.warning("Generic navigate_to called - subclasses should implement specific navigation logic or call a more specific base method.")
        
        return False
        
    @abstractmethod
    def create_post(self, content: Dict[str, Any]) -> bool:
        """Create a new post.
        
        Args:
            content: Post content and metadata
            
        Returns:
            bool: True if post created successfully
        """
        pass
        
    @abstractmethod
    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """Get analytics for a specific post.
        
        Args:
            post_id: Post identifier
            
        Returns:
            dict: Analytics data
        """
        pass
        
    def check_login_status(self) -> bool:
        """Check if currently logged in.
        
        Returns:
            bool: True if logged in
        """
        try:
            # Check for common logged-in indicators
            profile_button = wait_for_element(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="Profile"]'),
                timeout=5,
                source=self.__class__.__name__
            )
            return bool(profile_button)
        except Exception as e:
            log_event("error", f"Failed to check login status: {str(e)}", 
                     {"source": self.__class__.__name__})
            return False
            
    def upload_media(self, media_files: List[str]) -> bool:
        """Upload media files to post.
        
        Args:
            media_files: List of media file paths
            
        Returns:
            bool: True if all files uploaded successfully
        """
        try:
            for file_path in media_files:
                # Find and interact with media upload input
                upload_input = wait_for_element(
                    self.driver,
                    (By.CSS_SELECTOR, 'input[type="file"]'),
                    source=self.__class__.__name__
                )
                if not upload_input:
                    return False
                    
                upload_input.send_keys(file_path)
                
                # Wait for upload completion indicator
                if not wait_for_element(
                    self.driver,
                    (By.CSS_SELECTOR, '[data-testid="mediaPreview"]'),
                    timeout=self.timeout,
                    source=self.__class__.__name__
                ):
                    return False
                    
            log_event("media", f"Uploaded {len(media_files)} media files", 
                     {"source": self.__class__.__name__})
            return True
            
        except Exception as e:
            log_event("error", f"Failed to upload media: {str(e)}", 
                     {"source": self.__class__.__name__})
            return False
            
    def add_tags(self, tags: List[str], textarea_locator: Optional[Tuple[str, str]] = None) -> bool:
        """Add hashtags to post.
        
        Args:
            tags: List of hashtags (without # symbol)
            textarea_locator: Optional locator for the specific text input field.
                              If None, attempts a default common selector.
            
        Returns:
            bool: True if tags added successfully
        """
        try:
            # Use provided locator or a default guess
            # Defaulting to Twitter's for now, but this should ideally be abstract
            # or subclasses should always provide it.
            locator = textarea_locator or (By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]')

            # Format tags and append to post
            formatted_tags = " ".join(f"#{tag.strip('#')}" for tag in tags)

            # Use safe_send_keys which handles waiting
            if not safe_send_keys(self.driver, locator, " " + formatted_tags, source=self.__class__.__name__):
                log_event("error", "Could not find or send keys to text area for tags.", {"source": self.__class__.__name__})
                return False

            log_event("tags", f"Added {len(tags)} hashtags", {"source": self.__class__.__name__})
            return True

        except Exception as e:
            log_event("error", f"Failed to add tags: {str(e)}", {"source": self.__class__.__name__})
            return False
            
    def schedule_post(self, schedule_time: datetime) -> bool:
        """Schedule post for later publication.
        
        Args:
            schedule_time: When to publish the post
            
        Returns:
            bool: True if scheduling successful
        """
        try:
            # Click schedule button
            if not safe_click(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="scheduleButton"]'),
                source=self.__class__.__name__
            ):
                return False
                
            # Set date and time
            date_input = wait_for_element(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="datePicker"]'),
                source=self.__class__.__name__
            )
            if not date_input:
                return False
                
            date_str = schedule_time.strftime("%Y-%m-%d")
            time_str = schedule_time.strftime("%H:%M")
            
            date_input.send_keys(date_str)
            
            time_input = wait_for_element(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="timePicker"]'),
                source=self.__class__.__name__
            )
            if not time_input:
                return False
                
            time_input.send_keys(time_str)
            
            # Confirm scheduling
            if not safe_click(
                self.driver,
                (By.CSS_SELECTOR, '[data-testid="confirmScheduleButton"]'),
                source=self.__class__.__name__
            ):
                return False
                
            log_event("schedule", f"Scheduled post for {schedule_time.isoformat()}", 
                     {"source": self.__class__.__name__})
            return True
            
        except Exception as e:
            log_event("error", f"Failed to schedule post: {str(e)}", 
                     {"source": self.__class__.__name__})
            return False

    def navigate_to(self, url: str) -> None:
        """Navigate to a URL and wait for page load.
        
        Args:
            url: URL to navigate to
        """
        # try:
        #     self.driver.get(url)
        #     self.logger.info(f"Navigated to {url}")
        # except Exception as e:
        #     self.logger.error(f"Failed to navigate to {url}: {e}")
        #     raise StrategyError(f"Navigation failed: {e}", platform=self.__class__.__name__, action="navigate", original_exception=e)
        # Commenting out direct navigation - subclasses should handle this via specific methods
        # or a dedicated navigation method should be implemented if truly generic.
        self.logger.warning("Generic navigate_to called - subclasses should implement specific navigation logic or call a more specific base method.")

    def wait_for_element(self, locator: Tuple[str, str], timeout: int = 10) -> Any:
        """Wait for an element to be present and visible.
        
        Args:
            locator: Tuple of (By, selector)
            timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found, None otherwise
        """
        try:
            element = wait_for_element(self.driver, locator, timeout)
            return element
        except TimeoutException:
            log_event('error', f'Element not found: {locator}')
            return None
            
    def _validate_media_files(self, media_files: List[str]) -> List[str]:
        """Validate media files exist and are accessible.
        
        Args:
            media_files: List of media file paths
            
        Returns:
            List[str]: List of validated file paths
            
        Raises:
            StrategyError: If any files are invalid/inaccessible
        """
        valid_files = []
        for file_path in media_files:
            if not os.path.exists(file_path):
                log_event("STRATEGY_ERROR", self.__class__.__name__, {
                    "error": "Media file not found",
                    "file": file_path
                })
                raise StrategyError(f"Media file not found: {file_path}")
                
            if not os.access(file_path, os.R_OK):
                log_event("STRATEGY_ERROR", self.__class__.__name__, {
                    "error": "Media file not readable",
                    "file": file_path
                })
                raise StrategyError(f"Media file not readable: {file_path}")
                
            valid_files.append(file_path)
            
        return valid_files

    def _wait_for_element(self, by: By, value: str, timeout: Optional[int] = None) -> bool:
        """Wait for element to be present and visible.
        
        Args:
            by: Selenium By locator
            value: Locator value
            timeout: Optional custom timeout
            
        Returns:
            bool: True if element found within timeout
        """
        timeout = timeout or self.timeout
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return bool(element)
        except TimeoutException:
            log_event("STRATEGY_WARNING", self.__class__.__name__, {
                "warning": "Element wait timeout",
                "locator": f"{by}={value}",
                "timeout": timeout
            })
            return False

    def _handle_verification(self, verification_type: str, verification_value: str) -> bool:
        """Handle platform verification requests.
        
        Args:
            verification_type: Type of verification (email, phone, etc)
            verification_value: Value to use for verification
            
        Returns:
            bool: True if verification successful
        """
        log_event("STRATEGY_VERIFICATION", self.__class__.__name__, {
            "type": verification_type,
            "status": "started"
        })
        
        try:
            if verification_type == "email":
                # Handle email verification
                success = self._handle_email_verification(verification_value)
            elif verification_type == "phone":
                # Handle phone verification
                success = self._handle_phone_verification(verification_value)
            else:
                log_event("STRATEGY_ERROR", self.__class__.__name__, {
                    "error": "Unknown verification type",
                    "type": verification_type
                })
                return False
                
            log_event("STRATEGY_VERIFICATION", self.__class__.__name__, {
                "type": verification_type,
                "status": "completed",
                "success": success
            })
            return success
            
        except Exception as e:
            log_event("STRATEGY_ERROR", self.__class__.__name__, {
                "error": "Verification failed",
                "type": verification_type,
                "details": str(e)
            })
            return False

    def _handle_email_verification(self, email: str) -> bool:
        """Handle email verification flow.
        
        Args:
            email: Email address to verify
            
        Returns:
            bool: True if verification successful
        """
        # Platform-specific implementation
        raise NotImplementedError

    def _handle_phone_verification(self, phone: str) -> bool:
        """Handle phone verification flow.
        
        Args:
            phone: Phone number to verify
            
        Returns:
            bool: True if verification successful
        """
        # Platform-specific implementation
        raise NotImplementedError

    def _extract_error_details(self) -> Tuple[str, Dict[str, Any]]:
        """Extract error details from current page state.
        
        Returns:
            Tuple[str, Dict[str, Any]]: Error message and additional details
        """
        try:
            # Get page title and URL
            title = self.driver.title
            url = self.driver.current_url
            
            # Try to find error messages
            error_elements = self.driver.find_elements(By.CLASS_NAME, "error-message")
            error_messages = [el.text for el in error_elements if el.text]
            
            # Get page source for debugging
            page_source = self.driver.page_source
            
            details = {
                "title": title,
                "url": url,
                "error_messages": error_messages,
                "page_source": page_source[:500]  # Truncate for logging
            }
            
            message = " | ".join(error_messages) if error_messages else "Unknown error"
            return message, details
            
        except WebDriverException as e:
            return str(e), {"traceback": traceback.format_exc()}

if __name__ == "__main__":
    # 🔍 Example usage — Standalone run for debugging, onboarding, agentic simulation
    import os
    import uuid
    import traceback
    import json
    from selenium import webdriver # Keep for type hints if needed
    # from selenium.webdriver.chrome.service import Service - Removed, handled in setup_driver
    # from webdriver_manager.chrome import ChromeDriverManager - Removed, handled in setup_driver
    from datetime import datetime, timedelta
    from social.exceptions import StrategyError # Assuming StrategyError is defined here or imported
    from tests.utils.test_utils import setup_driver # Import consolidated setup_driver

    # --- Agent Coordination Placeholders ---
    # These functions simulate interactions with an agent framework/orchestrator
    def log_agent_task(task_id, status, message, details=None):
        """Placeholder for logging agent task status to a central system."""
        timestamp = datetime.now().isoformat()
        log_entry = {
            "timestamp": timestamp,
            "task_id": task_id,
            "status": status,
            "message": message,
            "details": details or "N/A"
        }
        # In a real system, this would write to a database, file, or logging service
        print(f"[AGENT TASK LOG] {json.dumps(log_entry)}")

    def update_agent_mailbox(agent_id, message_type, content):
        """Placeholder for sending a message to an agent's mailbox."""
        timestamp = datetime.now().isoformat()
        message = {
            "timestamp": timestamp,
            "recipient_agent_id": agent_id,
            "message_type": message_type,
            "content": content
        }
        # In a real system, this would enqueue a message (e.g., RabbitMQ, Redis Pub/Sub)
        print(f"[AGENT MAILBOX UPDATE] {json.dumps(message)}")

    def sync_task_board(task_id, status, result=None):
        """Placeholder for syncing task status with a project management board."""
        timestamp = datetime.now().isoformat()
        sync_data = {
             "timestamp": timestamp,
            "task_id": task_id,
            "status": status, # e.g., TODO, IN_PROGRESS, COMPLETED, FAILED, ERROR
            "result_summary": result or "N/A"
        }
        # In a real system, this would interact with an API (Jira, Trello, Asana)
        print(f"[TASK BOARD SYNC] {json.dumps(sync_data)}")
    # --- End Placeholders ---

    # Setup standard Python logging for debug visibility
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def run_strategy_demo_task(strategy_class, task_id, agent_id):
        """Demonstrate strategy execution within a simulated agent task framework."""
        log_agent_task(task_id, "RECEIVED", f"Received task to execute demo for {strategy_class.__name__}")
        sync_task_board(task_id, "TODO") # Mark as ready to start

        logging.info(f"Starting Task {task_id} for {strategy_class.__name__}...")
        log_agent_task(task_id, "STARTED", f"Beginning execution for {strategy_class.__name__}")
        sync_task_board(task_id, "IN_PROGRESS")

        driver = None
        success = False
        result_details = {"steps": {}}

        try:
            # --- Step 1: Initialization ---
            step_name = "Initialization"
            logging.info(f"[{step_name}] Setting up strategy...")
            driver = setup_driver() # Setup driver within the task scope
            platform_key = strategy_class.__name__.upper().replace('STRATEGY', '')

            # Use os.getenv for demo credentials as before
            username_key = f"{platform_key}_USERNAME"
            password_key = f"{platform_key}_PASSWORD"
            username = os.getenv(username_key, "test_user_demo")
            password = os.getenv(password_key, "test_pass_demo")

            # Construct the config override dictionary for the strategy instance
            strategy_config = {
                "username": username,
                "password": password,
                # Timeout/retries use defaults set in Strategy __init__
                # "timeout": 25 # Example override
            }

            # Log which username is being used (avoid logging password)
            logging.info(f"Using username from env key '{username_key}' (or demo fallback).")

            # Pass the constructed config dict to the strategy
            strategy = strategy_class(driver, strategy_config)

            logging.info(f"✓ [{step_name}] Initialized {strategy_class.__name__}")
            log_agent_task(task_id, "RUNNING", f"{step_name} complete.")
            result_details["steps"][step_name] = {"status": "Success"}
            # -----------------------------

            # --- Step 2: Login ---
            step_name = "Login"
            logging.info(f"[{step_name}] Attempting login...")
            if strategy.login():
                logging.info(f"  ✓ [{step_name}] Successful")
                result_details["steps"][step_name] = {"status": "Success"}
                log_agent_task(task_id, "RUNNING", f"{step_name} successful.")
            else:
                logging.warning(f"  ✗ [{step_name}] Failed")
                result_details["steps"][step_name] = {"status": "Failed"}
                # Decide if this is critical. For demo, we'll raise an error.
                raise StrategyError(f"{step_name} failed. Cannot proceed with dependent steps.")
            # --------------------

            # --- Step 3: Create Post ---
            step_name = "CreatePost"
            logging.info(f"[{step_name}] Attempting post creation...")
            # Ensure a dummy media file exists for the demo
            media_dir = "./temp_media_for_demo"
            media_path = os.path.join(media_dir, "sample_image.png")
            if not os.path.exists(media_path):
                 os.makedirs(media_dir, exist_ok=True)
                 try:
                     with open(media_path, 'w') as f: f.write("dummy image data") # Create dummy file
                     logging.info(f"  (Created dummy media file for demo: {media_path})")
                 except IOError as e:
                     logging.error(f"  Could not create dummy media file: {e}")
                     media_path = None # Proceed without media if creation fails

            post_content = {
                "text": f"Agent {agent_id} - Task {task_id}: Autonomous Test Post @ {datetime.now().isoformat()} UTC #AgentDemo #{strategy_class.__name__}",
                "media": [media_path] if media_path else [],
                "tags": ["AgentDemo", "Automation", "Testing"]
                # "schedule_time": datetime.now(timezone.utc) + timedelta(minutes=10) # Example scheduling
            }

            if strategy.create_post(post_content):
                logging.info(f"  ✓ [{step_name}] Successful")
                result_details["steps"][step_name] = {"status": "Success", "content_length": len(post_content['text'])}
                log_agent_task(task_id, "RUNNING", f"{step_name} successful.")
            else:
                logging.warning(f"  ✗ [{step_name}] Failed")
                result_details["steps"][step_name] = {"status": "Failed"}
                # Log failure but continue the demo if possible
                log_agent_task(task_id, "WARNING", f"{step_name} failed.")
            # -------------------------

            # --- Step 4: Get Analytics ---
            step_name = "GetAnalytics"
            logging.info(f"[{step_name}] Attempting analytics retrieval...")
            # Use a placeholder ID; real analytics require a valid, existing post ID
            test_post_id = "DUMMY_POST_ID_1234567890"
            analytics = strategy.get_analytics(test_post_id)
            if analytics: # Check if analytics dict is not empty
                logging.info(f"  ✓ [{step_name}] Retrieved (Structure depends on platform & ID validity): {analytics}")
                result_details["steps"][step_name] = {"status": "Success (Dummy ID)", "data": analytics}
                log_agent_task(task_id, "RUNNING", f"{step_name} retrieval attempted.", details=analytics)
            else:
                # This is expected to fail or return empty for a dummy ID
                logging.info(f"  ✓ [{step_name}] Returned empty/failed as expected for dummy ID.")
                result_details["steps"][step_name] = {"status": "Success (No Data Expected)"}
                log_agent_task(task_id, "RUNNING", f"{step_name} - No data retrieved (expected for dummy ID).")
            # ---------------------------

            # --- Task Completion ---
            success = True # Mark task as successful if all critical steps passed
            logging.info(f"Task {task_id} completed successfully.")
            log_agent_task(task_id, "COMPLETED", "Strategy demo finished successfully.")
            sync_task_board(task_id, "COMPLETED", result=result_details)
            update_agent_mailbox(agent_id, "TASK_RESULT", {"task_id": task_id, "status": "COMPLETED", "result": result_details})
            # -----------------------

        except StrategyError as se: # Handle known strategy errors gracefully
            step_name = step_name or "UnknownStep"
            logging.error(f"✗ Strategy Error during {step_name} in task {task_id}: {se}")
            result_details["steps"][step_name] = {"status": "Failed", "error": str(se)}
            log_agent_task(task_id, "FAILED", f"Strategy Error in {step_name}: {se}")
            sync_task_board(task_id, "FAILED", result={"error": str(se), **result_details})
            update_agent_mailbox(agent_id, "TASK_ERROR", {"task_id": task_id, "status": "FAILED", "step": step_name, "error": str(se)})
            success = False

        except Exception as e: # Catch unexpected errors
            step_name = step_name or "UnknownStep"
            logging.error(f"✗ Unexpected Error during {step_name} in task {task_id}: {e}", exc_info=True)
            trace = traceback.format_exc()
            result_details["steps"][step_name] = {"status": "ERROR", "error": str(e)}
            log_agent_task(task_id, "ERROR", f"Unexpected Error in {step_name}: {e}", details=trace)
            sync_task_board(task_id, "ERROR", result={"error": str(e), "traceback": trace, **result_details})
            update_agent_mailbox(agent_id, "SYSTEM_ERROR", {"task_id": task_id, "status": "ERROR", "step": step_name, "error": str(e), "traceback": trace})
            success = False

        finally:
            if driver:
                logging.info("Closing WebDriver.")
                driver.quit()
            final_status = "Success" if success else ("Failed" if any(s.get("status") == "Failed" for s in result_details["steps"].values()) else "Error")
            logging.info(f"Task {task_id} finished with status: {final_status}")
            print(f"{'='*60}\n")
            return success, result_details

    # --- Agentic Kickoff Simulation ---
    # This section simulates how an agent orchestrator might trigger this script
    agent_id = "Agent-Executor-001"
    task_id = f"SocialMediaDemoTask-{uuid.uuid4()}" # Unique ID for this run

    print(f"\n{'#'*10} AGENTIC KICKOFF SIMULATION {'#'*10}")
    print(f"Agent '{agent_id}' initiating Task ID: {task_id}")

    # Simulate receiving the task assignment
    update_agent_mailbox(agent_id, "TASK_ASSIGNED", {"task_id": task_id, "type": "SocialMediaStrategyDemo"})
    log_agent_task(task_id, "ASSIGNED", f"Task assigned to agent {agent_id}")

    # Select the strategy to test (change this to test others)
    # Available: TwitterStrategy, FacebookStrategy, LinkedInStrategy
    # from strategies import TwitterStrategy, FacebookStrategy, LinkedInStrategy
    strategy_to_run = TwitterStrategy

    # --- Execute the Task ---
    task_success, task_results = run_strategy_demo_task(strategy_to_run, task_id, agent_id)
    # ------------------------

    # --- Post-Execution Summary ---
    print(f"\n{'#'*10} TASK EXECUTION SUMMARY {'#'*10}")
    print(f"Agent '{agent_id}' Task '{task_id}' Final Status: {'Success' if task_success else 'Failure/Error'}")
    print("Execution Results:")
    print(json.dumps(task_results, indent=2))
    print(f"{'#'*40}\n")
    # ---------------------------- 