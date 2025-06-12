from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import pickle

# --- Setup Selenium WebDriver ---
options = webdriver.ChromeOptions()
options.add_argument(
    "--disable-blink-features=AutomationControlled"
)  # Prevent bot detection
options.add_argument("--start-maximized")  # Ensure everything is visible
options.add_argument("--disable-popup-blocking")  # Prevent popups
options.add_argument("--log-level=3")  # Reduce console clutter

driver = webdriver.Chrome(options=options)


# --- Login Functions ---
def is_logged_in():
    """Checks if the user is logged into LinkedIn."""
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)

    if "login" in driver.current_url:
        print("❌ Not logged in. Redirected to login page.")
        return False
    print("✅ Already logged in.")
    return True


def manual_login():
    """Manually logs in to LinkedIn and saves cookies."""
    driver.get("https://www.linkedin.com/login")
    print("🔹 Please log in manually. Press ENTER here when you're logged in.")
    input("👉 Press ENTER after logging in...")

    if is_logged_in():
        pickle.dump(
            driver.get_cookies(), open("../../data/raw/linkedin_cookies.pkl", "wb")
        )
        print("✅ Login cookies saved for future sessions.")
    else:
        print("⚠️ Login failed. Try again.")


def load_cookies():
    """Loads saved cookies if available, verifies login, and refreshes cookies if needed."""
    try:
        driver.get("https://www.linkedin.com/")
        cookies = pickle.load(open("../../data/raw/linkedin_cookies.pkl", "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
        time.sleep(2)

        if not is_logged_in():
            raise Exception("Saved cookies are invalid. Manual login required.")

        print("✅ Loaded saved cookies.")
    except Exception as e:
        print(f"⚠️ {e} Logging in manually...")
        manual_login()


# --- Scraping Functions ---
def scroll_and_wait():
    """Scrolls down dynamically until no new posts load."""
    scroll_pause = 2
    last_height = driver.execute_script("return document.body.scrollHeight")
    max_scrolls = 15  # Limit to prevent infinite loops

    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("🔹 No more new posts loaded.")
            break
        last_height = new_height


def expand_hidden_content(post):
    """Expands 'see more' buttons to reveal full post text."""
    try:
        see_more = post.find_element(
            By.XPATH, './/button[contains(text(), "see more")]'
        )
        driver.execute_script("arguments[0].click();", see_more)
        time.sleep(1)
    except Exception:
        pass  # No "see more" button found


def get_engagement_count(post):
    """Retrieves engagement metrics (likes, comments, shares) with fallback methods."""
    try:
        engagement = post.find_element(
            By.XPATH, './/span[contains(@class, "social-details-social-counts")]'
        ).text.strip()
    except Exception:
        try:
            engagement = post.find_element(
                By.XPATH, './/span[contains(@aria-label, "reactions")]'
            ).text.strip()
        except Exception:
            engagement = "Unknown"
    return engagement


def fetch_posts():
    """Scrapes LinkedIn posts with text, media, and engagement metrics."""
    print("🔹 Navigating to your LinkedIn activity page...")
    driver.get(
        "https://www.linkedin.com/in/victor-dixon-18450b279/detail/recent-activity/shares/"
    )
    time.sleep(5)

    scroll_and_wait()  # Scroll dynamically

    posts = driver.find_elements(
        By.XPATH, '//div[contains(@data-urn, "urn:li:activity")]'
    )

    data = []
    for index, post in enumerate(posts[:10]):
        try:
            expand_hidden_content(post)  # Reveal hidden text

            text = post.find_element(
                By.XPATH, './/span[contains(@class, "break-words")]'
            ).text.strip()
            images = [
                img.get_attribute("src")
                for img in post.find_elements(
                    By.XPATH, './/img[contains(@src, "media")]'
                )
            ]
            videos = [
                vid.get_attribute("src")
                for vid in post.find_elements(By.XPATH, ".//video")
            ]
            reactions = get_engagement_count(post)

            post_data = {
                "text": text,
                "images": images,
                "videos": videos,
                "reactions": reactions,
            }

            if text or images or videos:
                data.append(post_data)
                print(f"✅ Collected Post {index + 1}: {text[:50]}...")

        except Exception as e:
            print(f"⚠️ Skipping post {index + 1} due to error: {e}")

    if data:
        with open("../../data/raw/linkedin_posts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        print(f"✅ Collected {len(data)} LinkedIn posts with media and engagement data.")
    else:
        print("⚠️ No valid posts found.")

    return data


# --- Run Scraper ---
driver.get("https://www.linkedin.com/")
load_cookies()
fetch_posts()
driver.quit()
