import json
import os
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

# Target groups categorized by franchise
TARGET_GROUPS = {
    "Hello! Project": [
        "Morning Musume",
        "ANGERME",
        "Juice=Juice",
        "Tsubaki Factory",
        "BEYOOOOONDS",
        "OCHA NORMA",
        "Rosy Chronicle",
    ],
    "AKB48 Group": ["AKB48", "SKE48", "NMB48", "HKT48", "NGT48", "STU48"],
    "Sakamichi Series": ["Nogizaka46", "Sakurazaka46", "Hinatazaka46"],
    "=LOVE / Sister Groups": ["=LOVE", "≠ME", "≒JOY"],
    "Momoiro Clover Z": ["Momoiro Clover Z"],
    "Babymetal": ["BABYMETAL"],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def load_existing_catalog():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def make_affiliate_link(product_url):
  # Standard CDJapan affiliate redirect structure
  clean_path = product_url.replace("https://www.cdjapan.co.jp/", "").replace(
      "http://www.cdjapan.co.jp/", ""
  )
  encoded_path = urllib.parse.quote(clean_path, safe="")
  return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded_path}"


def scrape_artist_releases(category, artist_name, max_pages=1):
  products = []
  query = urllib.parse.quote_plus(artist_name)

  for page in range(1, max_pages + 1):
    search_url = f"https://www.cdjapan.co.jp/searchuni?q={query}&order=reldate&page={page}"
    try:
      response = requests.get(search_url, headers=HEADERS, timeout=15)
      if response.status_code != 200:
        break

      soup = BeautifulSoup(response.text, "html.parser")
      items = soup.select(".item-list .item-detail") or soup.select(".n-item")

      if not items:
        # Fallback selector for different CDJapan layout templates
        items = soup.find_all("div", class_="item")

      for item in items:
        title_el = item.select_one(".title a") or item.select_one("a.item-title")
        if not title_el:
          continue

        raw_url = title_el.get("href", "")
        if not raw_url.startswith("http"):
          raw_url = "https://www.cdjapan.co.jp" + raw_url

        product_id = raw_url.split("/")[-1].split("?")[0]
        title = title_el.get_text(strip=True)

        price_el = (
            item.select_one(".price")
            or item.select_one(".item-price")
            or item.select_one("span.bold")
        )
        price = price_el.get_text(strip=True) if price_el else "Check CDJapan"

        date_el = item.select_one(".release_date") or item.select_one(
            ".item-date"
        )
        rel_date = date_el.get_text(strip=True) if date_el else "Available"

        img_el = item.select_one("img")
        img_url = (
            img_el.get("src")
            or img_el.get("data-src")
            or "https://via.placeholder.com/300x300?text=No+Cover"
        )
        if img_url.startswith("//"):
          img_url = "https:" + img_url

        products.append({
            "id": product_id,
            "title": title,
            "artist": artist_name,
            "category": category,
            "price": price,
            "release_date": rel_date,
            "image": img_url,
            "affiliate_url": make_affiliate_link(raw_url),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        })

      time.sleep(1)  # Respectful crawling delay
    except Exception as e:
      print(f"Error scraping {artist_name}: {e}")
      break

  return products


def main():
  catalog = load_existing_catalog()
  total_added = 0

  for category, artists in TARGET_GROUPS.items():
    print(f"\nScanning Category: {category}")
    for artist in artists:
      print(f" -> Fetching releases for {artist}...")
      items = scrape_artist_releases(category, artist, max_pages=10)
      for item in items:
        pid = item["id"]
        if pid not in catalog:
          total_added += 1
        catalog[pid] = item

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  print(
      f"\nSync complete. Added {total_added} new items. Total in catalog:"
      f" {len(catalog)}"
  )


if __name__ == "__main__":
  main()
