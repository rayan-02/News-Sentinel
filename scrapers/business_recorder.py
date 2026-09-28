import requests
import feedparser
from bs4 import BeautifulSoup
import csv
import os
import re
import time

BASE_URL = "https://www.brecorder.com"
FEED_PATH = "/feeds/latest-news"
HEADERS = {"User-Agent": "Mozilla/5.0"}

session = requests.Session()
session.headers.update(HEADERS)

def get_feed():
    url = BASE_URL + FEED_PATH
    print("Fetching feed:", url)
    try:
        response = session.get(url, timeout=15)
        print("Status:", response.status_code)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except requests.RequestException as error:
        print("Could not open:", url)
        print(error)
        return None

def get_soup(url):
    try:
        response = session.get(url, timeout=15)
        print("Status:", response.status_code)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as error:
        print("Could not open:", url)
        print(error)
        return None

def clean_text(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)

def get_article_date(url, fallback_date=""):
    soup = get_soup(url)
    if soup is None:
        return fallback_date
    date_tag = soup.find("meta", property="article:published_time")
    if date_tag and date_tag.get("content"):
        return date_tag["content"].strip()
    time_tag = soup.find("time")
    if time_tag:
        if time_tag.get("datetime"):
            return time_tag["datetime"].strip()
        time_text = time_tag.get_text(" ", strip=True)
        if time_text:
            return time_text
    published_tag = soup.find(string=re.compile(r"Published", re.IGNORECASE))
    if published_tag:
        parent_text = published_tag.parent.get_text(" ", strip=True)
        match = re.search(r"Published\s*:?\s*(.+?)(?:Updated|$)", parent_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    page_text = soup.get_text(" ", strip=True)
    match = re.search(r"Published\s*:?\s*([A-Za-z]+\s+\d{1,2},\s+\d{4}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM))?)", page_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return fallback_date

def entry_to_article(entry):
    title = entry.get("title", "").strip()
    url = entry.get("link", "").strip()
    if not title or not url:
        return None
    author = ""
    if entry.get("author_detail"):
        author = entry["author_detail"].get("name", "").strip()
    rss_date = entry.get("published", "").strip()
    date = get_article_date(url, rss_date)
    category = ""
    if entry.get("tags"):
        category = entry["tags"][0].get("term", "").strip()
    if entry.get("content"):
        body = entry["content"][0].get("value", "")
    else:
        body = entry.get("summary", "")
    text = clean_text(body)
    description = clean_text(entry.get("summary", ""))
    if not text:
        return None
    return {"source": "Business Recorder", "title": title, "author": author, "date": date, "category": category, "url": url, "description": description, "text": text}

def save_articles(articles):
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_folder, exist_ok=True)
    file_path = os.path.join(data_folder, "articles.csv")
    columns = ["source", "title", "author", "date", "category", "url", "description", "text"]
    existing_urls = set()
    if os.path.isfile(file_path):
        with open(file_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get("url"):
                    existing_urls.add(row["url"])
    new_articles = [article for article in articles if article["url"] not in existing_urls]
    skipped = len(articles) - len(new_articles)
    file_exists = os.path.isfile(file_path)
    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        if not file_exists or os.path.getsize(file_path) == 0:
            writer.writeheader()
        writer.writerows(new_articles)
    print()
    print("Articles scraped:", len(articles))
    print("Saved", len(new_articles), "new articles")
    if skipped:
        print("Skipped", skipped, "already-saved duplicates")
    print("File:", file_path)

def main():
    print("Starting Business Recorder scraper...")
    print()
    feed = get_feed()
    if feed is None:
        print("Could not fetch the feed. Stopping.")
        return
    print()
    print("Found", len(feed.entries), "items in the feed")
    print()
    articles = []
    for number, entry in enumerate(feed.entries, 1):
        print(f"[{number}/{len(feed.entries)}] Processing entry...")
        article = entry_to_article(entry)
        if article:
            articles.append(article)
            print("  ✓", article["title"])
            print("    Date:", article["date"])
        else:
            print("  ✗ Could not process")
        time.sleep(1)
    save_articles(articles)

if __name__ == "__main__":
    main()