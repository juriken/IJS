import json
import os
import re
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

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

# 2 pages per artist = ~40 to 60 latest releases per group
PAGES_PER_ARTIST = 2

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/",
})


def load_catalog():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def make_affiliate_link(product_key):
  raw_path = f"product/{product_key}"
  encoded_path = urllib.parse.quote(raw_path, safe="")
  return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded_path}"


def clean_text(text):
  return re.sub(r"\s+", " ", text).strip() if text else ""


def extract_products_from_html(html, category, artist):
  soup = BeautifulSoup(html, "html.parser")
  extracted = []
  seen_keys = set()

  # 1. Primary extraction: standard CDJapan result item blocks
  item_nodes = (
      soup.select(".item-list .item-detail")
      or soup.select(".item-list .item")
      or soup.select(".n-item")
      or soup.select(".item")
      or soup.select("table.item-list tr")
  )

  for node in item_nodes:
    link_el = node.select_one("a[href*='/product/']")
    if not link_el:
      continue

    href = link_el.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)
    if prod_key in seen_keys:
      continue

    # Title
    title_el = (
        node.select_one(".title a")
        or node.select_one("a.item-title")
        or node.select_one(".title")
        or link_el
    )
    title = (
        clean_text(title_el.get_text()) if title_el else f"{artist} Release"
    )

    # Price
    price_el = (
        node.select_one(".price")
        or node.select_one(".item-price")
        or node.select_one("span.bold")
    )
    if price_el:
      price = clean_text(price_el.get_text())
    else:
      price_match = re.search(
          r"(\d[\d,]*\s*(?:yen|JPY|円))", node.get_text(), re.IGNORECASE
      )
      price = price_match.group(1) if price_match else "Check CDJapan"

    # Release Date
    date_el = (
        node.select_one(".release_date")
        or node.select_one(".item-date")
        or node.select_one(".date")
    )
    if date_el:
      rel_date = clean_text(date_el.get_text())
    else:
      date_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", node.get_text())
      rel_date = date_match.group(1) if date_match else "Available"

    # Image
    img_el = node.select_one("img")
    img_url = ""
    if img_el:
      img_url = (
          img_el.get("src")
          or img_el.get("data-src")
          or img_el.get("data-original")
          or ""
      )

    if not img_url or "spacer" in img_url or "blank" in img_url:
      img_url = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"
    elif img_url.startswith("//"):
      img_url = "https:" + img_url

    seen_keys.add(prod_key)
    extracted.append({
        "id": prod_key,
        "title": title,
        "artist": artist,
        "category": category,
        "price": price,
        "release_date": rel_date,
        "image": img_url,
        "affiliate_url": make_affiliate_link(prod_key),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
    })

  # 2. Resilient fallback: scan all anchor tags linking to /product/
  if not extracted:
    all_links = soup.find_all("a", href=re.compile(r"/product/([A-Za-z0-9_-]+)"))
    for a in all_links:
      href = a.get("href", "")
      match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
      if not match:
        continue
      prod_key = match.group(1)
      if prod_key in seen_keys:
        continue

      # Find parent container
      parent = a.find_parent(["div", "li", "tr"]) or a
      parent_text = clean_text(parent.get_text())

      title = clean_text(a.get_text())
      if not title or len(title) < 3:
        img_child = a.find("img")
        if img_child and img_child.get("alt"):
          title = clean_text(img_child.get("alt"))
        else:
          title = f"{artist} Official Release"

      price_match = re.search(
          r"(\d[\d,]*\s*(?:yen|JPY|円))", parent_text, re.IGNORECASE
      )
      price = price_match.group(1) if price_match else "Check CDJapan"

      date_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", parent_text)
      rel_date = date_match.group(1) if date_match else "Available"

      img_el = parent.find("img")
      img_url = ""
      if img_el:
        img_url = (
            img_el.get("src")
            or img_el.get("data-src")
            or img_el.get("data-original")
            or ""
        )

      if not img_url or "spacer" in img_url or "blank" in img_url:
        img_url = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"
      elif img_url.startswith("//"):
        img_url = "https:" + img_url

      seen_keys.add(prod_key)
      extracted.append({
          "id": prod_key,
          "title": title,
          "artist": artist,
          "category": category,
          "price": price,
          "release_date": rel_date,
          "image": img_url,
          "affiliate_url": make_affiliate_link(prod_key),
          "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
      })

  return extracted


def scrape_artist_releases(category, artist, pages=2):
  all_items = []
  q = urllib.parse.quote_plus(artist)

  for page in range(1, pages + 1):
    url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&page={page}"
    try:
      resp = SESSION.get(url, timeout=20)
      body_len = len(resp.text)
      print(
          f"    [Page {page}] Status: {resp.status_code} | HTML Size:"
          f" {body_len:,} bytes"
      )

      if resp.status_code != 200:
        break

      page_items = extract_products_from_html(resp.text, category, artist)
      print(f"    [Page {page}] Extracted: {len(page_items)} products")

      if not page_items:
        break

      all_items.extend(page_items)
      time.sleep(1.0)
    except Exception as e:
      print(f"    Error scraping {artist} page {page}: {e}")
      break

  return all_items


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  for cat, artists in TARGET_GROUPS.items():
    print(f"\n==========================================")
    print(f"Scanning Franchise: {cat}")
    print(f"==========================================")
    for artist in artists:
      print(f" -> Fetching releases for: {artist}")
      items = scrape_artist_releases(cat, artist, pages=PAGES_PER_ARTIST)
      new_for_artist = 0
      for item in items:
        pid = item["id"]
        if pid not in catalog:
          new_for_artist += 1
        catalog[pid] = item
      print(
          f"    Total for {artist}: {len(items)} found ({new_for_artist} new to"
          " catalog)"
      )

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(
      f"Run complete! Added {final_count - initial_count} brand-new products."
  )
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
