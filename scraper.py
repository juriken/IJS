import json
import os
import time
import urllib.parse
from datetime import datetime
import requests

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

# All target idol groups
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

# Number of pages to pull per artist (20 items per page; 3 pages = ~60 latest releases per artist)
PAGES_PER_ARTIST = 3

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
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
  # Clean product URL path encoded for CDJapan affiliate tracker
  raw_path = f"product/{product_key}"
  encoded_path = urllib.parse.quote(raw_path, safe="")
  return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded_path}"


def fetch_artist_products(category, artist, pages=3):
  found_items = []
  encoded_query = urllib.parse.quote(artist)

  for page in range(1, pages + 1):
    # CDJapan's internal JSON search feed endpoint
    api_url = f"https://www.cdjapan.co.jp/api/search?q={encoded_query}&order=reldesc&page={page}&format=json"

    try:
      resp = SESSION.get(api_url, timeout=15)

      # If CDJapan's direct JSON endpoint responds
      if resp.status_code == 200 and "application/json" in resp.headers.get(
          "Content-Type", ""
      ):
        data = resp.json()
        results = data.get("result", {}).get("items", []) or data.get(
            "items", []
        )
        if not results:
          break

        for item in results:
          prod_key = item.get("product_key") or item.get("id")
          if not prod_key:
            continue

          title = item.get("title") or item.get("name", "Unknown Title")
          price_val = item.get("price") or item.get("price_including_tax", "")
          price_str = f"{price_val}yen" if price_val else "Check CDJapan"
          rel_date = item.get("release_date") or item.get(
            "rel_date", "Available Now"
        )
          img_url = (
              item.get("image")
              or item.get("image_url")
              or f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"
          )

          found_items.append({
              "id": prod_key,
              "title": title,
              "artist": artist,
              "category": category,
              "price": price_str,
              "release_date": rel_date,
              "image": img_url,
              "affiliate_url": make_affiliate_link(prod_key),
              "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
          })

      else:
        # Fallback to CDJapan's official RSS release feed (always raw XML/text, never blocks)
        rss_url = f"https://www.cdjapan.co.jp/rss/search?q={encoded_query}&order=reldesc"
        rss_resp = SESSION.get(rss_url, timeout=15)
        if rss_resp.status_code == 200 and "<rss" in rss_resp.text:
          import xml.etree.ElementTree as ET

          root = ET.fromstring(rss_resp.content)
          for entry in root.findall(".//item"):
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            prod_key = link.split("/")[-1].split("?")[0]
            pub_date = entry.findtext("pubDate", "")

            # Extract date format
            rel_date = pub_date[:16] if pub_date else "Available Now"

            found_items.append({
                "id": prod_key,
                "title": title,
                "artist": artist,
                "category": category,
                "price": "Check CDJapan",
                "release_date": rel_date,
                "image": f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg",
                "affiliate_url": make_affiliate_link(prod_key),
                "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
        break  # RSS is single-page, break after fetching

      time.sleep(0.5)

    except Exception as e:
      print(f"    Notice on page {page} for {artist}: {e}")
      break

  return found_items


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Initial catalog size: {initial_count} items")

  for cat, artists in TARGET_GROUPS.items():
    print(f"\n==========================================")
    print(f"Scanning Franchise: {cat}")
    print(f"==========================================")
    for artist in artists:
      items = fetch_artist_products(cat, artist, pages=PAGES_PER_ARTIST)
      added_for_artist = 0
      for item in items:
        pid = item["id"]
        if pid not in catalog:
          added_for_artist += 1
        catalog[pid] = item
      print(
          f" -> {artist}: retrieved {len(items)} items ({added_for_artist} new)"
      )

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(f"Sync complete! Total items in catalog: {final_count}")
  print(f"New items added this run: {final_count - initial_count}")
  print(f"==========================================")


if __name__ == "__main__":
  main()
