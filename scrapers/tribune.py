import requests
import feedparser
from bs4 import BeautifulSoup
import csv
import time
import os
import re

BASE_URL = "https://tribune.com.pk"

FEEDS = [
    "/feed/latest",
    "/feed/pakistan",
    "/feed/business",
    "/feed/world",
    "/feed/sports",
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_feed(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print("Status:", response.status_code)
        response.raise_for_status()
        return feedparser.parse(response.content)
    except requests.RequestException as error:
        print("Could not open:", url)
        print(error)
        return None


def clean_text(html):
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(["script", "style", "iframe", "img", "video", "figure"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    for char in ["\u200b", "\u200c", "\u200d", "\ufeff", "\u2060"]:
        text = text.replace(char, "")

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)

    return re.sub(r"\s+", " ", text).strip()


def get_article_date(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Try article metadata first
        date_tag = soup.find("meta", property="article:published_time")

        if date_tag and date_tag.get("content"):
            return date_tag["content"].strip()

        # Try datetime attributes
        time_tag = soup.find("time")

        if time_tag:
            if time_tag.get("datetime"):
                return time_tag["datetime"].strip()

            if time_tag.get_text(strip=True):
                return time_tag.get_text(" ", strip=True)

        # Try Tribune's visible published date
        page_text = soup.get_text(" ", strip=True)

        match = re.search(
            r"(?:Published|Updated)\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})",
            page_text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return ""

    except requests.RequestException as error:
        print("Could not get article date:", url)
        print(error)
        return ""


def get_articles(limit=20):
    articles = []
    seen = set()

    for feed_path in FEEDS:
        if len(articles) >= limit:
            break

        url = BASE_URL + feed_path
        print("Checking:", url)

        feed = get_feed(url)

        if feed is None:
            continue

        for entry in feed.entries:
            if len(articles) >= limit:
                break

            title = entry.get("title", "").strip()
            article_url = entry.get("link", "").strip()

            if not title or not article_url:
                continue

            if article_url in seen:
                continue

            seen.add(article_url)

            author = entry.get("author", "").strip()

            # Get the date from the actual article page
            date = get_article_date(article_url)

            if not date:
                date = entry.get("published", "").strip()

            description = clean_text(entry.get("summary", ""))

            if entry.get("content"):
                text = clean_text(entry["content"][0].get("value", ""))
            else:
                text = clean_text(entry.get("summary", ""))

            if not text:
                continue

            category = feed_path.split("/")[-1]

            article = {
                "source": "Express Tribune",
                "title": title,
                "author": author,
                "date": date,
                "category": category,
                "url": article_url,
                "description": description,
                "text": text,
            }

            articles.append(article)

            print("  ✓", title)
            print("    Date:", date)

        time.sleep(0.5)

    return articles


def save_articles(articles):
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data")

    os.makedirs(data_folder, exist_ok=True)

    file_path = os.path.join(data_folder, "articles.csv")

    columns = [
        "source",
        "title",
        "author",
        "date",
        "category",
        "url",
        "description",
        "text",
    ]

    existing_urls = set()
    file_exists = os.path.isfile(file_path)

    if file_exists:
        print("Existing CSV found.")
        print("Checking for duplicate articles...")

        with open(file_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row.get("url"):
                    existing_urls.add(row["url"])

    new_articles = [
        article for article in articles if article["url"] not in existing_urls
    ]

    skipped = len(articles) - len(new_articles)

    with open(file_path, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns)

        if not file_exists:
            writer.writeheader()

        writer.writerows(new_articles)

    print()
    print("Articles scraped:", len(articles))
    print("New articles saved:", len(new_articles))
    print("Duplicates skipped:", skipped)
    print("File:", file_path)


def main():
    print("Starting Express Tribune scraper...")
    print()

    articles = get_articles(limit=30)

    print()
    print("Found", len(articles), "articles")
    print()

    save_articles(articles)


if __name__ == "__main__":
    main()
