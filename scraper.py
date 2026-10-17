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

# Key franchise queries tailored for deep release discovery
TARGET_QUERIES = [
    # Hello! Project core & flagship groups
    ("Hello! Project", "Morning Musume"),
    ("Hello! Project", "ANGERME"),
    ("Hello! Project", "Juice=Juice"),
    ("Hello! Project", "Tsubaki Factory"),
    ("Hello! Project", "BEYOOOOONDS"),
    ("Hello! Project", "OCHA NORMA"),
    ("Hello! Project", "Rosy Chronicle"),
    ("Hello! Project", "Hello! Project"),
    # Sakamichi Series (46)
    ("Sakamichi Series", "Nogizaka46"),
    ("Sakamichi Series", "Sakurazaka46"),
    ("Sakamichi Series", "Hinatazaka46"),
    # AKB48 Franchise
    ("AKB48 Group", "AKB48"),
    ("AKB48 Group", "SKE48"),
    ("AKB48 Group", "NMB48"),
    ("AKB48 Group", "HKT48"),
    ("AKB48 Group", "NGT48"),
    ("AKB48 Group", "STU48"),
    # Sashihara-produced & Stardust / Amuse
    ("=LOVE / Sister Groups", "=LOVE"),
    ("=LOVE / Sister Groups", "≠ME"),
    ("=LOVE / Sister Groups", "≒JOY"),
    ("Momoiro Clover Z", "Momoiro Clover Z"),
    ("Babymetal", "BABYMETAL"),
]


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


def parse_rendered_html(html, category, query_term):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  # Find all product anchor links across standard result items and tables
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Exclude system and utility links
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
          "artist": query_term,
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

    # Parent container for price, date, and fallback cover photo
    parent = a.find_parent(["div", "li", "tr", "td"])
    if parent:
      p_text = clean_text(parent.get_text())

      # Match prices (e.g. 1300yen, 1,300 JPY, 1400円)
      if not entry["price"]:
        p_match = re.search(r"(\d[\d,]*\s*(?:yen|JPY|円))", p_text, re.IGNORECASE)
        if p_match:
          entry["price"] = p_match.group(1)

      # Match release dates (e.g. 2024/08/14, 2024-08-14)
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
      data["title"] = f"{query_term} Official Release ({prod_key})"
    if not data["price"]:
      data["price"] = "Check CDJapan"
    if not data["release_date"]:
      data["release_date"] = "Available"
    if not data["image"]:
      data["image"] = f"https://www.cdjapan.co.jp/pictures/s/{prod_key}.jpg"

    cleaned.append(data)

  return cleaned


def scrape_query(page, category, query_term):
  q = urllib.parse.quote_plus(query_term)
  # Full catalog query targeting available items sorted newest first
  url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldesc&opt.include_eoa=0"

  for attempt in range(1, 3):
    try:
      page.goto(url, wait_until="domcontentloaded", timeout=35000)

      # Wait for product links to render
      try:
        page.wait_for_selector("a[href*='/product/']", timeout=7000)
      except Exception:
        pass

      # Gradual scrolling triggers all lazy-loaded elements and images
      page.evaluate("window.scrollBy(0, 1000)")
      time.sleep(1.0)
      page.evaluate("window.scrollBy(0, 1500)")
      time.sleep(1.0)

      rendered_html = page.content()
      html_size = len(rendered_html)

      # Check for 110-byte rate limiting
      if html_size < 3000:
        print(
            f"    [Rate-Limit Notice] Received {html_size} bytes. Cooling down"
            " 10 seconds..."
        )
        time.sleep(10.0)
        continue

      items = parse_rendered_html(rendered_html, category, query_term)
      print(
          f"    Rendered: {html_size:,} bytes | Extracted: {len(items)}"
          " candidate releases"
      )
      return items

    except Exception as e:
      print(f"    Notice on attempt {attempt} for {query_term}: {e}")
      time.sleep(5.0)

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

    # Warm up session with CDJapan homepage
    try:
      page.goto("https://www.cdjapan.co.jp/", timeout=25000)
      time.sleep(2.0)
    except Exception:
      pass

    total_added_this_run = 0

    for idx, (cat, term) in enumerate(TARGET_QUERIES, start=1):
      print(f"\n[{idx}/{len(TARGET_QUERIES)}] Querying: {term} ({cat})")
      items = scrape_query(page, cat, term)
      new_for_term = 0

      for it in items:
        pid = it["id"]
        if pid not in catalog:
          new_for_term += 1
          total_added_this_run += 1
        catalog[pid] = it

      print(
          f"    Results for {term}: {len(items)} found ({new_for_term} new to"
          " catalog)"
      )

      # Dynamic cooling delay to stay below CDJapan's firewall threshold
      cooling = random.uniform(3.5, 5.5)
      time.sleep(cooling)

    browser.close()

  # Write back catalog
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(f"Run complete! Added {total_added_this_run} brand-new products.")
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
