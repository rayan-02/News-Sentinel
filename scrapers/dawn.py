import requests
from bs4 import BeautifulSoup
import csv
import re
import time
import os


BASE_URL = "https://www.dawn.com"

PAGES = ["/", "/latest-news", "/pakistan", "/business", "/world"]

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,image/webp,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
})


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

        url = BASE_URL + page

        print("Checking:", url)

        soup = get_soup(url)

        if soup is None:
            continue

        for a in soup.find_all("a", href=True):

            href = a["href"]

            if href.startswith("/"):
                full_url = BASE_URL + href
            else:
                full_url = href

            if not re.match(r"https://www\.dawn\.com/news/\d+", full_url):
                continue

            if full_url in seen:
                continue

            seen.add(full_url)
            links.append(full_url)

            if len(links) >= limit:
                return links

        time.sleep(1)

    return links


# --------------------------------------------------
# SCRAPE ONE ARTICLE
# --------------------------------------------------


def scrape_article(url):

    soup = get_soup(url)

    if soup is None:
        return None

    # Title
    title_tag = soup.find("meta", property="og:title")

    title = title_tag["content"] if title_tag else ""

    # Author
    author_tag = soup.find("meta", attrs={"name": "author"})

    author = author_tag["content"] if author_tag else ""

    # Date
    date_tag = soup.find("meta", property="article:published_time")

    date = date_tag["content"] if date_tag else ""

    # Category
    category_tag = soup.find("meta", property="article:section")

    category = category_tag["content"] if category_tag else ""

    # Description
    description_tag = soup.find("meta", property="og:description")

    description = description_tag["content"] if description_tag else ""

    # Article text
    article = soup.find("div", class_="story__content")

    if article is None:
        return None

    paragraphs = article.find_all("p")

    text = "\n".join(p.get_text(" ", strip=True)
        for p in paragraphs
        if len(p.get_text(strip=True)) > 30
    )

    # If we didn't get text, skip the article
    if not title or not text:
        return None

    return {
        "source": "Dawn",
        "title": title,
        "author": author,
        "date": date,
        "category": category,
        "url": url,
        "description": description,
        "text": text,
    }


# --------------------------------------------------
# SAVE ARTICLES
# --------------------------------------------------


def save_articles(articles):
 
    # Go from scrapers/ to data/
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data")
 
    os.makedirs(data_folder, exist_ok=True)
 
    # Shared file -- both dawn.py and tribune.py write here now.
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
 
    # If the file already exists (e.g. tribune.py already ran), read the
    # URLs already saved so we don't add the same article twice.
    existing_urls = set()
    file_already_exists = os.path.isfile(file_path)
 
    if file_already_exists:
        with open(file_path, "r", newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_urls.add(row["url"])

    new_articles = [a for a in articles if a["url"] not in existing_urls]
    skipped = len(articles) - len(new_articles)

    with open(file_path, "a", newline="", encoding="utf-8") as file:
 
        writer = csv.DictWriter(file, fieldnames=columns)
 
        if not file_already_exists:
            writer.writeheader()
 
        writer.writerows(new_articles)
 
    print()
    print("Saved", len(new_articles), "new articles")
    if skipped:
        print("Skipped", skipped, "already-saved duplicates")
    print("File:", file_path)

# --------------------------------------------------
# MAIN PROGRAM
# --------------------------------------------------


def main():

    print("Starting Dawn scraper...")
    print()

    # Warm-up request: visiting the homepage first lets us pick up any
    # cookies/consent tokens Dawn sets, before we start hitting article
    # pages directly. The shared session above then carries those cookies
    # into every request that follows.
    get_soup(BASE_URL + "/")

    # Get article URLs
    links = get_article_links(limit=20)

    print()
    print("Found", len(links), "articles")
    print()

    articles = []

    # Scrape every article
    for number, url in enumerate(links, 1):

        print(f"[{number}/{len(links)}] Scraping article...")

        article = scrape_article(url)

        if article:
            articles.append(article)
            print("  ✓", article["title"])
        else:
            print("  ✗ Could not scrape")

        # Wait before next request
        time.sleep(1)

    # Save everything
    save_articles(articles)


if __name__ == "__main__":
    main()