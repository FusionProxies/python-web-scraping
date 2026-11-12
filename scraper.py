"""Web scraping with Python: requests + BeautifulSoup, end to end.

Scrapes https://books.toscrape.com (a sandbox site built for scraping practice):
follows the pagination, extracts every book, and saves the result as CSV and JSON.

    pip install -r requirements.txt
    python scraper.py --pages 3                 # direct connection
    FUSION_USER=... FUSION_PASS=... python scraper.py --pages 3   # through a residential proxy
"""
import argparse
import csv
import json
import os
import random
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START_URL = "https://books.toscrape.com/catalogue/page-1.html"
RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def make_session() -> requests.Session:
    s = requests.Session()
    # look like a normal browser visit
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    # retry temporary failures with growing pauses: 1 s, 2 s, 4 s
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], respect_retry_after_header=True)
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    # optional proxy: one residential IP for the whole run (sticky session)
    user, password = os.environ.get("FUSION_USER"), os.environ.get("FUSION_PASS")
    if user and password:
        country = os.environ.get("FUSION_COUNTRY", "us")
        session_user = f"{user}-country-{country}-sessid-{random.randint(1000000, 9999999)}-sessTime-1800s"
        proxy = f"http://{session_user}:{password}@resi.fusionproxy.net:12286"
        s.proxies.update({"http": proxy, "https": proxy})
    return s


def parse_books(html: str, page_url: str) -> tuple[list[dict], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    books = []
    for card in soup.select("article.product_pod"):
        link = card.select_one("h3 a")
        rating_class = card.select_one("p.star-rating")["class"]
        books.append({
            "title": link["title"],
            "price": float(card.select_one("p.price_color").get_text(strip=True).lstrip("£Â")),
            "rating": next((RATINGS[c] for c in rating_class if c in RATINGS), None),
            "in_stock": "In stock" in card.select_one("p.availability").get_text(),
            "url": urljoin(page_url, link["href"]),
        })
    next_link = soup.select_one("li.next a")
    return books, urljoin(page_url, next_link["href"]) if next_link else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=3, help="how many listing pages to scrape (the site has 50)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds to wait between pages")
    args = ap.parse_args()

    session = make_session()
    if session.proxies:
        print("exit IP:", session.get("https://ipinfo.io/ip", timeout=30).text.strip())

    url, books, page = START_URL, [], 0
    while url and page < args.pages:
        page += 1
        r = session.get(url, timeout=30)
        r.raise_for_status()
        found, url = parse_books(r.text, r.url)
        books.extend(found)
        print(f"page {page}: {len(found)} books")
        if url:
            time.sleep(args.delay)  # be polite: one page per second is plenty

    with open("books.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(books[0].keys()))
        w.writeheader()
        w.writerows(books)
    with open("books.json", "w", encoding="utf-8") as f:
        json.dump(books, f, indent=2, ensure_ascii=False)
    print(f"saved {len(books)} books to books.csv and books.json")


if __name__ == "__main__":
    main()
