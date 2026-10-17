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

# 3 pages per artist = up to 60 releases per group
PAGES_PER_ARTIST = 3

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


def extract_all_products(html, category, artist):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  # Find every single link on the page that points to a CDJapan product
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Initialize entry if not already present
    if prod_key not in items_dict:
      items_dict[prod_key] = {
          "id": prod_key,
          "title": "",
          "artist": artist,
          "category": category,
          "price": "",
          "release_date": "",
          "image": "",
          "affiliate_url": make_affiliate_link(prod_key),
          "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
      }

    entry = items_dict[prod_key]

    # 1. Extract Title
    link_text = clean_text(a.get_text())
    if link_text and len(link_text) > len(entry["title"]):
      entry["title"] = link_text

    # 2. Extract Image
    img_el = a.find("img")
    if img_el:
      img_src = (
          img_el.get("src")
          or img_el.get("data-src")
          or img_el.get("data-original")
          or ""
      )
      if (
          img_src
          and "spacer" not in img_src
          and "blank" not in img_src
          and not entry["image"]
      ):
        if img_src.startswith("//"):
          img_src = "https:" + img_src
        elif img_src.startswith("/"):
          img_src = "https://www.cdjapan.co.jp" + img_src
        entry["image"] = img_src

      if not entry["title"] and img_el.get("alt"):
        entry["title"] = clean_text(img_el.get("alt"))

    # 3. Look at parent container for Price and Date
    parent = a.find_parent(["div", "li", "tr", "td"])
    if parent:
      parent_text = clean_text(parent.get_text())

      # Search for price (e.g. "1,300yen" or "1300 JPY")
      if not entry["price"]:
        p_match = re.search(
            r"(\d[\d,]*\s*(?:yen|JPY|円))", parent_text, re.IGNORECASE
        )
        if p_match:
          entry["price"] = p_match.group(1)

      # Search for date (e.g. "2024/08/14" or "2024-08-14")
      if not entry["release_date"]:
        d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", parent_text)
        if d_match:
          entry["release_date"] = d_match.group(1)

      # Fallback image search inside parent container
      if not entry["image"]:
        p_img = parent.find("img")
        if p_img:
          p_src = (
              p_img.get("src")
              or p_img.get("data-src")
              or p_img.get("data-original")
              or ""
          )
          if p_src and "spacer" not in p_src and "blank" not in p_src:
            if p_src.startswith("//"):
              p_src = "https:" + p_src
            elif p_src.startswith("/"):
              p_src = "https://www.cdjapan.co.jp" + p_src
            entry["image"] = p_src

  # Fill defaults for anything missed
  final_list = []
  for prod_key, data in items_dict.items():
    if not data["title"]:
      data["title"] = f"{artist} Official Release ({prod_key})"
    if not data["price"]:
      data["price"] = "Check CDJapan"
    if not data["release_date"]:
      data["release_date"] = "Available"
    if not data["image"]:
      data["image"] = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"

    final_list.append(data)

  return final_list


def scrape_artist(category, artist, pages=3):
  results = []
  q = urllib.parse.quote_plus(artist)

  for page in range(1, pages + 1):
    url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&page={page}"
    try:
      resp = SESSION.get(url, timeout=20)
      if resp.status_code != 200:
        print(f"    [Page {page}] HTTP Status: {resp.status_code}")
        break

      extracted = extract_all_products(resp.text, category, artist)
      print(f"    [Page {page}] Extracted {len(extracted)} distinct releases")

      if not extracted:
        break

      results.extend(extracted)
      time.sleep(1.0)
    except Exception as e:
      print(f"    [Page {page}] Error scraping {artist}: {e}")
      break

  return results


def main():
  # 1. Warm up session with CDJapan homepage to acquire cookies
  try:
    SESSION.get("https://www.cdjapan.co.jp/", timeout=15)
  except Exception:
    pass

  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  for cat, artists in TARGET_GROUPS.items():
    print(f"\n==========================================")
    print(f"Scanning Franchise: {cat}")
    print(f"==========================================")
    for artist in artists:
      print(f" -> Fetching releases for: {artist}")
      items = scrape_artist(cat, artist, pages=PAGES_PER_ARTIST)
      new_for_artist = 0
      for item in items:
        pid = item["id"]
        if pid not in catalog:
          new_for_artist += 1
        catalog[pid] = item

      print(
          f"    Total found for {artist}: {len(items)} ({new_for_artist} new to"
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
