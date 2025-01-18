import os
import time
import requests
import base64
from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# GitHub API details
GITHUB_REPO = "shambooz/Repos2"
GITHUB_FILE_PATH = "abc_adelaide_mornings_feed.xml"
GITHUB_TOKEN = "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"

# RSS feed local file
RSS_FEED_FILE = "abc_adelaide_mornings_feed.xml"

# ABC episode page URL
ABC_PAGE_URL = "https://www.abc.net.au/listen/programs/adelaide-mornings/"

def extract_latest_aac_url():
    """Extract the latest .aac URL from the ABC website."""
    service = Service("/Users/darrenchaitman 1/Desktop/python/chromedriver-mac-x64/chromedriver")
 # Update with the correct path to your ChromeDriver
    driver = webdriver.Chrome(service=service)

    try:
        # Step 1: Load the ABC Adelaide Mornings main page
        driver.get(ABC_PAGE_URL)
        time.sleep(5)  # Allow page to load

        # Step 2: Click the "Latest Episode" button
        latest_episode_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Latest Episode')]"))
        )
        latest_episode_button.click()
        print("Clicked 'Latest Episode' button.")
        time.sleep(5)  # Allow the new page to load

        # Step 3: Click the play button on the new page
        play_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label^='Play Audio']"))
        )
        play_button.click()
        print("Play button clicked successfully.")
        time.sleep(10)  # Wait for audio requests to load

        # Step 4: Extract .aac URL from network requests
        for request in driver.requests:
            if request.response and ".aac" in request.url:
                parsed_url = urlparse(request.url)
                query_params = parse_qs(parsed_url.query)
                if "mu" in query_params:
                    return query_params["mu"][0]
        return None

    finally:
        driver.quit()

def update_rss_feed(audio_url, episode_title, episode_description):
    """Update the RSS feed with the new episode."""
    # Load or create the RSS feed
    if os.path.exists(RSS_FEED_FILE):
        tree = ET.parse(RSS_FEED_FILE)
        root = tree.getroot()
        channel = root.find("channel")
    else:
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        ET.SubElement(channel, "title").text = "ABC Adelaide Mornings"
        ET.SubElement(channel, "link").text = ABC_PAGE_URL
        ET.SubElement(channel, "description").text = "Automated RSS feed for Adelaide Mornings audio episodes."
        ET.SubElement(channel, "language").text = "en-au"

    # Check if the episode is already in the feed
    for item in channel.findall("item"):
        if item.find("guid") is not None and item.find("guid").text == audio_url:
            print(f"Episode with URL {audio_url} is already in the RSS feed.")
            return

    # Add the new episode
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = episode_title
    ET.SubElement(item, "description").text = episode_description
    ET.SubElement(item, "enclosure", url=audio_url, type="audio/aac")
    ET.SubElement(item, "guid").text = audio_url
    ET.SubElement(item, "pubDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # Save the updated RSS feed
    tree = ET.ElementTree(root)
    tree.write(RSS_FEED_FILE, encoding="utf-8", xml_declaration=True)
    print(f"RSS feed updated with episode: {episode_title}")

def upload_to_github():
    """Upload the updated RSS feed to GitHub."""
    with open(RSS_FEED_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    # Get the current file SHA (if it exists)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        sha = response.json()["sha"]
    else:
        sha = None

    # Upload the file
    data = {
        "message": "Update RSS feed with new episode",
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "sha": sha,
    }
    response = requests.put(url, json=data, headers=headers)
    if response.status_code in [200, 201]:
        print("RSS feed uploaded to GitHub successfully.")
    else:
        print("Failed to upload RSS feed to GitHub:", response.text)

if __name__ == "__main__":
    # Extract the latest episode
    audio_url = extract_latest_aac_url()
    if not audio_url:
        print("No new audio URL found.")
    else:
        episode_title = "New Adelaide Mornings Episode"
        episode_description = "Automated transcription and delivery for Adelaide Mornings."
        update_rss_feed(audio_url, episode_title, episode_description)
        upload_to_github()
