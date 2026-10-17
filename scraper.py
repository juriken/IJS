import json
import os
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

# All target groups and franchises requested
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
    "AKB48 Group": [
        "AKB48",
        "SKE48",
        "NMB48",
        "HKT48",
        "NGT48",
        "STU48",
    ],
    "Sakamichi Series": [
        "Nogizaka46",
        "Sakurazaka46",
        "Hinatazaka46",
    ],
    "=LOVE / Sister Groups": [
        "=LOVE",
        "≠ME",
        "≒JOY",
    ],
    "Momoiro Clover Z": [
        "Momoiro Clover Z",
    ],
    "Babymetal": [
        "BABYMETAL",
    ],
}

# Number of search pages to scrape per artist (20-30 items per page)
# 3 pages = ~60 to 90 items per group (gives an initial batch of ~1,000+ items)
PAGES_PER_ARTIST = 3

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
})


def load_catalog():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def make_affiliate_link(product_url):
  clean_path = product_url.replace("https://www.cdjapan.co.jp/", "").replace(
      "http://www.cdjapan.co.jp/", ""
  )
  encoded_path = urllib.parse.quote(clean_path, safe="")
  return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded_path}"


def scrape_artist_page(category, artist, page=1):
  products = []
  q = urllib.parse.quote_plus(artist)
  # Corrected order parameter: reldesc (Release Date Descending)
  url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&page={page}"

  try:
    resp = SESSION.get(url, timeout=20)
    if resp.status_code != 200:
      print(f"    Page {page} returned status {resp.status_code}")
      return products

    soup = BeautifulSoup(resp.text, "html.parser")

    # CDJapan renders product items in .item-detail or .item blocks
    items = (
        soup.select(".item-list .item-detail")
        or soup.select(".item")
        or soup.select(".n-item")
        or soup.select("table.item-list tr")
    )

    for item in items:
      # Locate the product title anchor
      title_el = (
          item.select_one(".title a")
          or item.select_one("a.item-title")
          or item.select_one("a[href*='/product/']")
      )
      if not title_el:
        continue

      link = title_el.get("href", "")
      if not link or "javascript:" in link:
        continue

      if not link.startswith("http"):
        link = "https://www.cdjapan.co.jp" + link

      # Extract CDJapan product code (e.g. NEODAI-12345 or EPCE-7860)
      prod_id = link.split("/")[-1].split("?")[0]
      title = title_el.get_text(strip=True)

      # Locate price
      price_el = (
          item.select_one(".price")
          or item.select_one(".item-price")
          or item.select_one(".price-value")
          or item.select_one("span.bold")
      )
      price = price_el.get_text(strip=True) if price_el else "Check CDJapan"

      # Locate release date
      date_el = (
          item.select_one(".release_date")
          or item.select_one(".item-date")
          or item.select_one(".date")
      )
      rel_date = date_el.get_text(strip=True) if date_el else "Available Now"

      # Locate album cover / product photo
      img_el = item.select_one("img")
      img_src = ""
      if img_el:
        img_src = (
            img_el.get("src")
            or img_el.get("data-src")
            or img_el.get("data-original")
            or ""
        )

      if not img_src or "spacer" in img_src or "blank" in img_src:
        img_src = "https://via.placeholder.com/300x300?text=CDJapan+Release"

      if img_src.startswith("//"):
        img_src = "https:" + img_src

      products.append({
          "id": prod_id,
          "title": title,
          "artist": artist,
          "category": category,
          "price": price,
          "release_date": rel_date,
          "image": img_src,
          "affiliate_url": make_affiliate_link(link),
          "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
      })

    # Polite interval between page hits
    time.sleep(1.0)
  except Exception as e:
    print(f"    Error scraping page {page} for {artist}: {e}")

  return products


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count}")

  for cat, artists in TARGET_GROUPS.items():
    print(f"\n==========================================")
    print(f"Scanning Franchise: {cat}")
    print(f"==========================================")
    for artist in artists:
      print(f" -> Fetching releases for: {artist}")
      artist_new_count = 0
      for page_num in range(1, PAGES_PER_ARTIST + 1):
        page_items = scrape_artist_page(cat, artist, page=page_num)
        if not page_items:
          break
        for it in page_items:
          pid = it["id"]
          if pid not in catalog:
            artist_new_count += 1
          catalog[pid] = it

      print(f"    Added/updated items for {artist}. (New: {artist_new_count})")

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(
      f"Run Complete! Added {final_count - initial_count} brand-new products."
  )
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
