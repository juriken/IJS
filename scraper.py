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

# Target idol roster (Strictly English terms)
TARGET_GROUPS = [
    # Hello! Project
    ("Hello! Project", "Morning Musume"),
    ("Hello! Project", "ANGERME", "Smileage"),  # Searches S/mileage & ANGERME releases
    ("Hello! Project", "Juice=Juice"),
    ("Hello! Project", "Tsubaki Factory"),
    ("Hello! Project", "BEYOOOOONDS"),
    ("Hello! Project", "OCHA NORMA"),
    ("Hello! Project", "Rosy Chronicle"),
    ("Hello! Project", "Hello! Project"),
    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46"),
    ("Sakamichi Series", "Sakurazaka46"),
    ("Sakamichi Series", "Hinatazaka46"),
    # AKB48 Group
    ("AKB48 Group", "AKB48"),
    ("AKB48 Group", "SKE48"),
    ("AKB48 Group", "NMB48"),
    ("AKB48 Group", "HKT48"),
    ("AKB48 Group", "NGT48"),
    ("AKB48 Group", "STU48"),
    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE"),
    ("=LOVE / Sister Groups", "≠ME", "Not Equal ME"),
    ("=LOVE / Sister Groups", "≒JOY", "Nearly Equal Joy"),
    # Momoclo & Babymetal
    ("Momoiro Clover Z", "Momoiro Clover Z"),
    ("Babymetal", "BABYMETAL"),
]

# Number of pages to paginate through using the on-screen Next button
PAGES_PER_ARTIST = 3


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


def extract_products(html, category, artist_name):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  # Find all anchors that link to individual product pages
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Filter out navigation links
    if prod_key.lower() in [
        "cart",
        "login",
        "help",
        "contact",
        "about",
        "tokuten",
        "ranking",
        "app",
    ]:
      continue

    if prod_key not in items_dict:
      items_dict[prod_key] = {
          "id": prod_key,
          "title": "",
          "artist": artist_name,
          "category": category,
          "price": "",
          "release_date": "",
          "image": "",
          "affiliate_url": make_affiliate_link(prod_key),
          "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
      }

    entry = items_dict[prod_key]

    # Title extraction
    t_text = clean_text(a.get_text())
    if t_text and len(t_text) > len(entry["title"]):
      entry["title"] = t_text

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

    # Parent card inspection for price and release date
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
      data["title"] = f"{artist_name} Official Release ({prod_key})"
    if not data["price"]:
      data["price"] = "Check CDJapan"
    if not data["release_date"]:
      data["release_date"] = "Available"
    if not data["image"]:
      data["image"] = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"
    cleaned.append(data)

  return cleaned


def search_via_ui(page, category, artist_name, max_pages=3):
  found_items = []
  print(f"\n-> Initiating Search-Bar Flow for: {artist_name}")

  try:
    # 1. Start from homepage to initialize valid session cookies & referer
    page.goto(
        "https://www.cdjapan.co.jp/",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    time.sleep(1.5)

    # 2. Locate the search input box
    search_input = page.locator("input[name='q']").first
    search_input.click()
    search_input.fill("")
    # Type artist in English
    search_input.fill(artist_name)
    time.sleep(0.5)

    # 3. Submit search via Enter
    search_input.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2.0)

    print(f"   Landed on results page: {page.url}")

    # 4. Paginate using the on-screen 'Next' button
    for current_p in range(1, max_pages + 1):
      # Wait for product links to render
      try:
        page.wait_for_selector("a[href*='/product/']", timeout=8000)
      except Exception:
        pass

      page.evaluate("window.scrollBy(0, 1000)")
      time.sleep(1.0)

      html = page.content()
      page_items = extract_products(html, category, artist_name)
      print(f"   [Page {current_p}] Extracted {len(page_items)} products")
      found_items.extend(page_items)

      if current_p < max_pages:
        # Locate the Next page link/button
        next_btn = page.locator("a[rel='next'], a.next, a:has-text('Next')")
        if next_btn.count() > 0 and next_btn.first.is_visible():
          next_btn.first.click()
          page.wait_for_load_state("domcontentloaded")
          time.sleep(random.uniform(2.5, 4.0))
        else:
          print("   No further Next button available.")
          break

  except Exception as e:
    print(f"   Notice during search for {artist_name}: {e}")

  return found_items


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  # Process 6 targets per run to maintain human-paced requests
  selected_targets = random.sample(TARGET_GROUPS, min(6, len(TARGET_GROUPS)))

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox"],
    )
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1440, "height": 900},
    )
    page = context.new_page()

    new_total = 0
    for idx, target in enumerate(selected_targets, 1):
      cat = target[0]
      name = target[1]
      search_term = target[2] if len(target) > 2 else name

      print(f"\n[{idx}/{len(selected_targets)}] Target: {name} ({cat})")
      items = search_via_ui(page, cat, search_term, max_pages=PAGES_PER_ARTIST)
      new_for_artist = 0

      for it in items:
        # Normalize artist label back to the canonical group name
        it["artist"] = name
        pid = it["id"]
        if pid not in catalog:
          new_for_artist += 1
          new_total += 1
        catalog[pid] = it

      print(f"   Added {new_for_artist} brand-new items for {name}")
      time.sleep(random.uniform(3.0, 5.0))

    browser.close()

  # Write back catalog
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(f"Run complete! Added {new_total} brand-new products.")
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
