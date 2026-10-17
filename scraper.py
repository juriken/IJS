import json
import os
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

# 2 pages per group = ~40 items per group (~800 products total)
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

  # Look for product links across the fully rendered DOM
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Ignore generic header/footer links
    if prod_key.lower() in ["cart", "login", "help", "contact", "about"]:
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

    # Extract Title
    title_text = clean_text(a.get_text())
    if title_text and len(title_text) > len(entry["title"]):
      entry["title"] = title_text

    # Extract Cover Image
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

    # Extract Price & Date from parent container
    parent = a.find_parent(["div", "li", "tr", "td"])
    if parent:
      parent_text = clean_text(parent.get_text())

      # Search for price (e.g. 1300yen / 1,300 JPY)
      if not entry["price"]:
        p_match = re.search(
            r"(\d[\d,]*\s*(?:yen|JPY|円))", parent_text, re.IGNORECASE
        )
        if p_match:
          entry["price"] = p_match.group(1)

      # Search for release date (e.g. 2024/08/14 or 2024-08-14)
      if not entry["release_date"]:
        d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", parent_text)
        if d_match:
          entry["release_date"] = d_match.group(1)

      # Fallback image inside container
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

  # Apply fallback values
  cleaned_list = []
  for prod_key, data in items_dict.items():
    if not data["title"]:
      data["title"] = f"{artist} Official Release ({prod_key})"
    if not data["price"]:
      data["price"] = "Check CDJapan"
    if not data["release_date"]:
      data["release_date"] = "Available"
    if not data["image"]:
      data["image"] = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"

    cleaned_list.append(data)

  return cleaned_list


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  with sync_playwright() as p:
    # Launch real headless Chromium browser
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 900},
    )
    page = context.new_page()

    for cat, artists in TARGET_GROUPS.items():
      print(f"\n==========================================")
      print(f"Scanning Franchise: {cat}")
      print(f"==========================================")

      for artist in artists:
        print(f" -> Fetching releases for: {artist}")
        artist_found = 0

        for page_num in range(1, PAGES_PER_ARTIST + 1):
          q = urllib.parse.quote_plus(artist)
          url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&page={page_num}"

          try:
            # Navigate and let JavaScript execute
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait up to 3 seconds for client-side JavaScript to finish populating cards
            time.sleep(2.5)

            rendered_html = page.content()
            items = parse_rendered_html(rendered_html, cat, artist)
            print(
                f"    [Page {page_num}] Rendered HTML:"
                f" {len(rendered_html):,} bytes | Extracted: {len(items)}"
                " releases"
            )

            if not items:
              break

            for it in items:
              pid = it["id"]
              if pid not in catalog:
                artist_found += 1
              catalog[pid] = it

          except Exception as e:
            print(f"    [Page {page_num}] Browser error for {artist}: {e}")
            break

        print(f"    Total new items added for {artist}: {artist_found}")

    browser.close()

  # Save catalog
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
