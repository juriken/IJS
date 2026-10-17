import json
import os
import random
import re
import time
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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

# 2 pages per artist x 20 items per page = ~40 items per group (Catalog will grow to ~500-800 items)
PAGES_PER_ARTIST = 2


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


def parse_rendered_html(html, category, artist):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  # Find all product anchor tags
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Exclude non-product system anchors
    if prod_key.lower() in [
        "cart",
        "login",
        "help",
        "contact",
        "about",
        "tokuten",
        "ranking",
    ]:
      continue

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

    # Title extraction
    title_text = clean_text(a.get_text())
    if title_text and len(title_text) > len(entry["title"]):
      entry["title"] = title_text

    # Image extraction
    img_el = a.find("img")
    if img_el:
      src = (
          img_el.get("src")
          or img_el.get("data-src")
          or img_el.get("data-original")
          or ""
      )
      if src and "spacer" not in src and "blank" not in src:
        if src.startswith("//"):
          src = "https:" + src
        elif src.startswith("/"):
          src = "https://www.cdjapan.co.jp" + src
        entry["image"] = src

      if not entry["title"] and img_el.get("alt"):
        entry["title"] = clean_text(img_el.get("alt"))

    # Parent container extraction for price and date
    parent = a.find_parent(["div", "li", "tr", "td"])
    if parent:
      p_text = clean_text(parent.get_text())

      if not entry["price"]:
        p_match = re.search(r"(\d[\d,]*\s*(?:yen|JPY|円))", p_text, re.IGNORECASE)
        if p_match:
          entry["price"] = p_match.group(1)

      if not entry["release_date"]:
        d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", p_text)
        if d_match:
          entry["release_date"] = d_match.group(1)

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

  cleaned = []
  for prod_key, data in items_dict.items():
    if not data["title"]:
      data["title"] = f"{artist} Official Release ({prod_key})"
    if not data["price"]:
      data["price"] = "Check CDJapan"
    if not data["release_date"]:
      data["release_date"] = "Available"
    if not data["image"]:
      data["image"] = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"

    cleaned.append(data)

  return cleaned


def scrape_artist_page(page, category, artist, page_num):
  q = urllib.parse.quote_plus(artist)
  url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&page={page_num}"

  for attempt in range(1, 3):
    try:
      # Navigate and wait until all network requests (AJAX/Fetch) settle
      page.goto(url, wait_until="networkidle", timeout=30000)

      # Smooth scroll to ensure bottom rows and lazy images finish loading
      page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
      time.sleep(0.8)
      page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
      time.sleep(0.8)

      rendered_html = page.content()
      html_size = len(rendered_html)

      # Handle temporary rate limits
      if html_size < 2000:
        print(
            f"    [Page {page_num}] Response {html_size} bytes. Backing off 8"
            " seconds..."
        )
        time.sleep(8.0)
        continue

      items = parse_rendered_html(rendered_html, category, artist)
      print(
          f"    [Page {page_num}] Rendered: {html_size:,} bytes | Extracted:"
          f" {len(items)} releases"
      )
      return items

    except Exception as e:
      print(
          f"    [Page {page_num}] Attempt {attempt} notice for {artist}: {e}"
      )
      time.sleep(3.0)

  return []


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
    )
    page = context.new_page()

    for cat, artists in TARGET_GROUPS.items():
      print(f"\n==========================================")
      print(f"Scanning Franchise: {cat}")
      print(f"==========================================")

      for artist in artists:
        print(f" -> Fetching releases for: {artist}")
        artist_new = 0

        for p_idx in range(1, PAGES_PER_ARTIST + 1):
          items = scrape_artist_page(page, cat, artist, p_idx)
          if not items:
            break

          for it in items:
            pid = it["id"]
            if pid not in catalog:
              artist_new += 1
            catalog[pid] = it

          time.sleep(random.uniform(2.5, 3.5))

        print(f"    Total new items added for {artist}: {artist_new}")
        time.sleep(random.uniform(2.0, 3.0))

    browser.close()

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
