# utils/browser_controller.py

import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

class BrowserController:
    """Provides a shared browser interface for agents requiring headless or interactive automation."""

    def __init__(self, headless: bool = True, user_agent: str = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.headless = headless
        self.user_agent = user_agent
        self.driver = None
        self._setup_browser()

    def _setup_browser(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-dev-shm-usage")

        if self.user_agent:
            options.add_argument(f"user-agent={self.user_agent}")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.logger.info("Chrome WebDriver initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome WebDriver: {e}", exc_info=True)
            raise

    def get(self, url: str):
        """Navigate to the specified URL."""
        if self.driver:
            self.logger.info(f"Navigating to: {url}")
            self.driver.get(url)

    def find_by_selector(self, selector: str, timeout: int = 10):
        """Find a DOM element using a CSS selector."""
        if not self.driver:
            raise RuntimeError("Browser driver not initialized.")

        try:
            return self.driver.find_element(By.CSS_SELECTOR, selector)
        except Exception as e:
            self.logger.warning(f"Element not found for selector '{selector}': {e}")
            return None

    def screenshot(self, path: str):
        """Capture a screenshot to the specified file path."""
        if self.driver:
            self.driver.save_screenshot(path)
            self.logger.info(f"Screenshot saved to {path}")

    def quit(self):
        """Cleanly shut down the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Browser session terminated.")

    def __del__(self):
        self.quit()
