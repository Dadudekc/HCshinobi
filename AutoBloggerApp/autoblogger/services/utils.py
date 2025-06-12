import re
from bs4 import BeautifulSoup


def extract_title(html_content: str) -> str:
    """
    Extracts the title from HTML content.
    First tries to find an h1 tag, then falls back to the first heading.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Try to find h1 first
    h1 = soup.find("h1")
    if h1:
        return h1.get_text().strip()

    # Fall back to first heading
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        return heading.get_text().strip()

    return "Untitled"


def extract_introduction(html_content: str) -> str:
    """
    Extracts the introduction (first paragraph) from HTML content.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    first_p = soup.find("p")
    if first_p:
        return first_p.get_text().strip()
    return ""
