import json
import os
import time
import urllib.parse
from datetime import datetime
import requests

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

# 3 pages per artist = up to 60 releases per group (Total catalog: 800 - 1,200 items)
PAGES_PER_ARTIST = 3

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/",
    "X-Requested-With": "XMLHttpRequest",
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


def fetch_artist_releases(category, artist, pages=3):
  products = []
  q = urllib.parse.quote_plus(artist)

  for page in range(1, pages + 1):
    # CDJapan's actual search items API
    api_url = f"https://www.cdjapan.co.jp/api/search/item?q={q}&order=reldesc&page={page}"

    try:
      resp = SESSION.get(api_url, timeout=20)
      print(f"    [Page {page}] Status: {resp.status_code}")

      if resp.status_code != 200:
        break

      data = resp.json()
      # Extract item collection
      items = (
          data.get("items")
          or data.get("result", {}).get("items")
          or data.get("results")
          or []
      )

      print(f"    [Page {page}] Extracted: {len(items)} items via API")

      if not items:
        break

      for it in items:
        # Resolve CDJapan product ID
        prod_key = (
            it.get("product_key")
            or it.get("item_key")
            or it.get("key")
            or it.get("id")
        )
        if not prod_key:
          continue

        # Clean product title
        title = (
            it.get("title")
            or it.get("name")
            or it.get("product_name")
            or f"{artist} Release"
        )

        # Price formatting
        price_val = (
            it.get("price")
            or it.get("price_tax_incl")
            or it.get("price_tax_included")
            or it.get("list_price")
        )
        if price_val:
          price_str = (
              f"{price_val}yen" if "yen" not in str(price_val) else str(price_val)
          )
        else:
          price_str = "Check CDJapan"

        # Release date
        rel_date = (
            it.get("release_date")
            or it.get("reldate")
            or it.get("sale_date")
            or "Available Now"
        )

        # Cover artwork
        img_url = (
            it.get("image_url")
            or it.get("image")
            or it.get("thumbnail")
            or f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"
        )
        if img_url.startswith("//"):
          img_url = "https:" + img_url

        products.append({
            "id": str(prod_key),
            "title": str(title).strip(),
            "artist": artist,
            "category": category,
            "price": price_str,
            "release_date": str(rel_date).strip(),
            "image": img_url,
            "affiliate_url": make_affiliate_link(prod_key),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        })

      time.sleep(1.0)
    except Exception as e:
      print(f"    Error processing {artist} page {page}: {e}")
      break

  return products


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
      items = fetch_artist_releases(cat, artist, pages=PAGES_PER_ARTIST)
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
