import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import os

BASE_URL = "https://www.geo.tv"

PAGES = ["/", "/latest-news", "/category/pakistan", "/category/business", "/category/world"]

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.google.com/"}

session = requests.Session()
session.headers.update(HEADERS)


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


def get_article_links(limit=20):
    links = []
    seen = set()

    for page in PAGES:
        if len(links) >= limit:
            break

        url = BASE_URL + page
        print("Checking:", url)
        soup = get_soup(url)

        if soup is None:
            continue

        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = BASE_URL + href if href.startswith("/") else href

            if not re.match(r"https://www\.geo\.tv/latest/\d+-", full_url):
                continue

            if full_url in seen:
                continue

            seen.add(full_url)
            links.append(full_url)

            if len(links) >= limit:
                break

        time.sleep(1)

    return links


def get_article_date(soup):
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

    return ""


def scrape_article(url):
    soup = get_soup(url)

    if soup is None:
        return None

    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"].strip() if title_tag and title_tag.get("content") else ""

    date = get_article_date(soup)

    description_tag = soup.find("meta", property="og:description")
    description = description_tag["content"].strip() if description_tag and description_tag.get("content") else ""

    author = ""
    page_text = soup.get_text(" ", strip=True)
    author_match = re.search(r"\bBy\s+([A-Za-z][A-Za-z .]{2,40}?)\s*\|\s*Published", page_text)

    if author_match:
        author = author_match.group(1).strip()

    category = ""
    h1 = soup.find("h1")

    if h1:
        category_link = h1.find_previous("a", href=re.compile(r"/category/"))

        if category_link:
            category = category_link.get_text(strip=True)

    blocked_words = ("copyright", "all rights reserved", "privacy policy", "contact us", "advertising guide", "subscribe")

    paragraphs = []

    for p in soup.find_all("p"):
        text = p.get_text(" ", strip=True)

        if len(text) < 40:
            continue

        if any(word in text.lower() for word in blocked_words):
            continue

        paragraphs.append(text)

    text = "\n".join(paragraphs)

    if not title or not text:
        return None

    return {"source": "Geo News", "title": title, "author": author, "date": date, "category": category, "url": url, "description": description, "text": text}


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
    print("Starting Geo News scraper...")
    print()

    get_soup(BASE_URL + "/")

    links = get_article_links(limit=30)

    print()
    print("Found", len(links), "articles")
    print()

    articles = []

    for number, url in enumerate(links, 1):
        print(f"[{number}/{len(links)}] Scraping article...")
        article = scrape_article(url)

        if article:
            articles.append(article)
            print("  ✓", article["title"])
            print("    Date:", article["date"])
        else:
            print("  ✗ Could not scrape")

        time.sleep(1)

    save_articles(articles)


if __name__ == "__main__":
    main()