"""
Consolidated Selenium utilities for browser automation.
"""

from typing import Any, Optional, Tuple
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from utils.logging_utils import log_event

def wait_for_element(
    driver: WebDriver,
    locator: Tuple[str, str],
    timeout: int = 10,
    visible: bool = True,
    source: str = "SeleniumUtils"
) -> Any:
    """Wait for element to be present and optionally visible.
    
    Args:
        driver: Selenium WebDriver instance
        locator: Tuple of (By, selector)
        timeout: Maximum time to wait in seconds
        visible: Whether element should be visible
        source: Source for logging
        
    Returns:
        WebElement if found, None otherwise
    """
    try:
        condition = (
            EC.visibility_of_element_located if visible
            else EC.presence_of_element_located
        )
        element = WebDriverWait(driver, timeout).until(condition(locator))
        return element
    except TimeoutException:
        log_event("selenium", f"Element not found: {locator}", {"source": source})
        return None
    except WebDriverException as e:
        log_event("error", f"WebDriver error: {str(e)}", {"source": source})
        return None

def safe_click(
    driver: WebDriver,
    locator: Tuple[str, str],
    timeout: int = 10,
    retries: int = 3,
    source: str = "SeleniumUtils"
) -> bool:
    """Safely click an element with retries.
    
    Args:
        driver: Selenium WebDriver instance
        locator: Tuple of (By, selector)
        timeout: Maximum time to wait in seconds
        retries: Number of retry attempts
        source: Source for logging
        
    Returns:
        bool: True if click successful
    """
    for attempt in range(retries):
        try:
            element = wait_for_element(driver, locator, timeout, source=source)
            if not element:
                continue
            element.click()
            return True
        except WebDriverException as e:
            if attempt == retries - 1:
                log_event("error", f"Click failed after {retries} attempts: {str(e)}", 
                         {"source": source})
                return False
    return False

def safe_send_keys(
    driver: WebDriver,
    locator: Tuple[str, str],
    text: str,
    timeout: int = 10,
    retries: int = 3,
    source: str = "SeleniumUtils"
) -> bool:
    """Safely send keys to an element with retries.
    
    Args:
        driver: Selenium WebDriver instance
        locator: Tuple of (By, selector)
        text: Text to send
        timeout: Maximum time to wait in seconds
        retries: Number of retry attempts
        source: Source for logging
        
    Returns:
        bool: True if send keys successful
    """
    for attempt in range(retries):
        try:
            element = wait_for_element(driver, locator, timeout, source=source)
            if not element:
                continue
            element.send_keys(text)
            return True
        except WebDriverException as e:
            if attempt == retries - 1:
                log_event("error", f"Send keys failed after {retries} attempts: {str(e)}", 
                         {"source": source})
                return False
    return False

def navigate_to(
    driver: WebDriver,
    url: str,
    source: str = "SeleniumUtils"
) -> bool:
    """Navigate to URL and wait for page load.
    
    Args:
        driver: Selenium WebDriver instance
        url: URL to navigate to
        source: Source for logging
        
    Returns:
        bool: True if navigation successful
    """
    try:
        driver.get(url)
        log_event("navigation", f"Navigated to {url}", {"source": source})
        return True
    except WebDriverException as e:
        log_event("error", f"Navigation failed: {str(e)}", {"source": source})
        return False 