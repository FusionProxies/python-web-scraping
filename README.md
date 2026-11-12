<p align="center">
  <a href="https://fusionproxy.net/?utm_source=github&utm_medium=python-web-scraping">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-dark.png">
      <img src="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-light.png" alt="Fusion Proxy" height="52">
    </picture>
  </a>
</p>

# Web scraping with Python: requests and BeautifulSoup

A complete, working Python web scraper in about 100 lines: download pages with `requests`, extract data with BeautifulSoup CSS selectors, follow pagination, retry failed requests, stay polite, route traffic through a proxy, and save the results to CSV and JSON.

The example scrapes [books.toscrape.com](https://books.toscrape.com), a sandbox site made for scraping practice, so you can run it without worrying about anyone's terms.

```bash
pip install -r requirements.txt
python scraper.py --pages 3
```

```
page 1: 20 books
page 2: 20 books
page 3: 20 books
saved 60 books to books.csv and books.json
```

## Contents

1. [Download a page](#1-download-a-page)
2. [Extract data with BeautifulSoup](#2-extract-data-with-beautifulsoup)
3. [Follow pagination](#3-follow-pagination)
4. [Retries and timeouts](#4-retries-and-timeouts)
5. [Be polite](#5-be-polite)
6. [Use a proxy](#6-use-a-proxy)
7. [Save to CSV and JSON](#7-save-to-csv-and-json)
8. [When requests is not enough](#8-when-requests-is-not-enough)

## 1. Download a page

```python
import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
})
r = session.get("https://books.toscrape.com/catalogue/page-1.html", timeout=30)
r.raise_for_status()
html = r.text
```

A `Session` reuses the connection and keeps cookies between requests. The default `python-requests` User-Agent is blocked by many sites, so send a normal browser one. Always pass `timeout`.

## 2. Extract data with BeautifulSoup

Open the page in your browser, right-click a book and choose **Inspect**. Every book is an `<article class="product_pod">`, so a CSS selector finds them all:

```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
for card in soup.select("article.product_pod"):
    title = card.select_one("h3 a")["title"]
    price = card.select_one("p.price_color").get_text(strip=True)
    print(title, price)
```

- `select()` returns all matches, `select_one()` the first or `None`.
- Read attributes like a dictionary: `tag["href"]`, `tag["class"]`.
- `get_text(strip=True)` gives the text without surrounding whitespace.

## 3. Follow pagination

Don't guess page URLs. Follow the site's own "next" link until there is none:

```python
from urllib.parse import urljoin

next_link = soup.select_one("li.next a")
next_url = urljoin(page_url, next_link["href"]) if next_link else None
```

`urljoin` turns relative links such as `page-2.html` into full URLs.

## 4. Retries and timeouts

Networks fail and servers return `429` or `503` now and then. Let urllib3 retry with growing pauses instead of crashing:

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], respect_retry_after_header=True)
session.mount("https://", HTTPAdapter(max_retries=retry))
```

[python-requests-retry](https://github.com/FusionProxies/python-requests-retry) covers retries in depth, including switching IP after a block.

## 5. Be polite

- Read the site's `robots.txt` and terms, and scrape only public data.
- Pause between requests (`--delay`, one second by default). A scraper that hammers a site gets blocked and can hurt the site.
- Scrape only the pages you need and cache what you already have.

## 6. Use a proxy

Sites limit how many requests one IP may send, and show different content by country. A residential proxy gives you a real household IP in the country you choose. The scraper uses one when `FUSION_USER` and `FUSION_PASS` are set, with a sticky session so the whole run keeps the same IP:

```python
session_user = f"{user}-country-us-sessid-4821937-sessTime-1800s"   # one US IP for 30 minutes
proxy = f"http://{session_user}:{password}@resi.fusionproxy.net:12286"
session.proxies.update({"http": proxy, "https": proxy})
```

```bash
export FUSION_USER="your_username"
export FUSION_PASS="your_password"
python scraper.py --pages 3
```

Drop `-sessid-...-sessTime-...` to get a new IP on every connection instead. More in [python-requests-proxy](https://github.com/FusionProxies/python-requests-proxy).

## 7. Save to CSV and JSON

```python
import csv, json

with open("books.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(books[0].keys()))
    w.writeheader()
    w.writerows(books)

with open("books.json", "w", encoding="utf-8") as f:
    json.dump(books, f, indent=2, ensure_ascii=False)
```

Each row has `title`, `price`, `rating` (1 to 5), `in_stock` and `url`.

## 8. When requests is not enough

`requests` sees the HTML the server sends. If the data appears only after JavaScript runs (the page source in your browser does not contain it), first look in the browser's **Network** tab for the JSON API the page calls and request that directly. If there is none, use a headless browser: see [playwright-proxy](https://github.com/FusionProxies/playwright-proxy) and [puppeteer-proxy](https://github.com/FusionProxies/puppeteer-proxy). For large crawls, Scrapy handles queues, concurrency and retries for you.

## Related

- [python-requests-proxy](https://github.com/FusionProxies/python-requests-proxy): every way to use a proxy in requests
- [python-requests-retry](https://github.com/FusionProxies/python-requests-retry): retries, backoff and IP rotation

Need reliable IPs for scraping? [Fusion Proxy residential proxies](https://fusionproxy.net/proxies/residential?utm_source=github&utm_medium=python-web-scraping) start at $2.95/GB, with a [free trial](https://fusionproxy.net/free-trial?utm_source=github&utm_medium=python-web-scraping).

## License

MIT, see [LICENSE](LICENSE).
