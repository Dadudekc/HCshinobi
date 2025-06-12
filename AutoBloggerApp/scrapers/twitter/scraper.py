import time
import pickle
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Constants ---
COOKIE_FILE = "../../data/raw/twitter_cookies.pkl"
USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")
SEARCH_QUERY = os.getenv("TWITTER_SEARCH_QUERY", "trading loss TSLA")

# --- Setup Chrome WebDriver ---
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_experimental_option(
    "detach", True
)  # 🔥 Keeps browser open after script finishes
driver = webdriver.Chrome(options=options)


# --- Load Cookies ---
def load_cookies():
    """Loads cookies if available, otherwise logs in manually."""
    driver.get("https://twitter.com/home")
    time.sleep(5)

    if os.path.exists(COOKIE_FILE):
        with open(COOKIE_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)
        print("✅ Loaded cookies, skipping login.")

    # 🚨 **Verify if login was successful**
    if "login" in driver.current_url:
        print("❌ Login required despite cookies. Retrying login...")
        twitter_login()
        save_cookies()
    else:
        print("✅ Successfully logged in with cookies.")


# --- Save Cookies ---
def save_cookies():
    """Saves cookies to a file after login."""
    with open(COOKIE_FILE, "wb") as file:
        pickle.dump(driver.get_cookies(), file)
    print("✅ Cookies saved for future logins.")


# --- Login Function ---
def twitter_login():
    """Logs into Twitter manually if cookies are missing."""
    if not USERNAME or not PASSWORD:
        raise ValueError("Twitter credentials not found in environment variables")

    driver.get("https://twitter.com/login")
    time.sleep(5)

    try:
        username_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//input[@name="text"]'))
        )
        username_input.send_keys(USERNAME)
        username_input.send_keys(Keys.RETURN)
        time.sleep(5)  # 🔥 Extended wait

        password_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, '//input[@name="password"]'))
        )
        password_input.send_keys(PASSWORD)
        password_input.send_keys(Keys.RETURN)
        time.sleep(5)

        # 🚨 **Final check: Are we actually logged in?**
        if "login" in driver.current_url:
            driver.save_screenshot(
                "../../data/raw/debug_failed_login.png"
            )  # 📸 Debug failed login
            raise Exception("❌ Login failed! Check debug_failed_login.png.")
        else:
            print("✅ Logged in successfully.")

    except Exception as e:
        driver.save_screenshot(
            "../../data/raw/debug_login_error.png"
        )  # 📸 Debug login issue
        print(f"❌ Error logging in. Screenshot saved as debug_login_error.png")
        raise e  # Stop execution if login fails


# --- Search Function ---
def search_tweets():
    """Searches Twitter for live tweets matching a query."""
    driver.get(f"https://twitter.com/search?q={SEARCH_QUERY}&f=live")
    time.sleep(5)

    # Debug: Capture Screenshot
    driver.save_screenshot("../../data/raw/debug_search.png")
    print("📸 Screenshot saved as debug_search.png")

    try:
        tweets = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//article"))
        )
        print(f"✅ Found {len(tweets)} tweets.")
        return tweets
    except Exception:
        print("❌ No tweets found. Check debug_search.png for issues.")
        return []


# --- Run the Bot ---
if __name__ == "__main__":
    load_cookies()
    search_tweets()
