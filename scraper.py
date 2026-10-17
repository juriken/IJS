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

# Target idol queries with both English and Japanese designations for maximum catalog depth
TARGET_QUERIES = [
    # Hello! Project
    ("Hello! Project", "Morning Musume", "モーニング娘"),
    ("Hello! Project", "ANGERME", "アンジュルム"),
    ("Hello! Project", "Juice=Juice", "Juice=Juice"),
    ("Hello! Project", "Tsubaki Factory", "つばきファクトリー"),
    ("Hello! Project", "BEYOOOOONDS", "BEYOOOOONDS"),
    ("Hello! Project", "OCHA NORMA", "OCHA NORMA"),
    ("Hello! Project", "Rosy Chronicle", "ロージークロニクル"),
    ("Hello! Project", "Hello! Project", "ハロー!プロジェクト"),
    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46", "乃木坂46"),
    ("Sakamichi Series", "Sakurazaka46", "櫻坂46"),
    ("Sakamichi Series", "Hinatazaka46", "日向坂46"),
    # AKB48 Group
    ("AKB48 Group", "AKB48", "AKB48"),
    ("AKB48 Group", "SKE48", "SKE48"),
    ("AKB48 Group", "NMB48", "NMB48"),
    ("AKB48 Group", "HKT48", "HKT48"),
    ("AKB48 Group", "NGT48", "NGT48"),
    ("AKB48 Group", "STU48", "STU48"),
    # =LOVE Franchise
    ("=LOVE / Sister Groups", "=LOVE", "=LOVE"),
    ("=LOVE / Sister Groups", "≠ME", "≠ME"),
    ("=LOVE / Sister Groups", "≒JOY", "≒JOY"),
    # Others
    ("Momoiro Clover Z", "Momoiro Clover Z", "ももいろクローバーZ"),
    ("Babymetal", "BABYMETAL", "BABYMETAL"),
]

PAGES_PER_QUERY = 2


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


def parse_rendered_html(html, category, artist_name):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  # Scan for all product links on the full searches page
  product_links = soup.find_all(
      "a", href=re.compile(r"/product/([A-Za-z0-9_-]+)")
  )

  for a in product_links:
    href = a.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    # Exclude site-wide nav / system anchors
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

    # Title
    t_text = clean_text(a.get_text())
    if t_text and len(t_text) > len(entry["title"]):
      entry["title"] = t_text

    # Image
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

    # Parent card extraction for price and release date
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


def scrape_full_searches(page, category, display_name, search_term, page_num):
  q = urllib.parse.quote_plus(search_term)
  # Target the true full catalog listing endpoint (not the searchuni teaser)
  url = f"https://www.cdjapan.co.jp/searches?term.media_format=&q={q}&order=reldesc&page={page_num}"

  for attempt in range(1, 3):
    try:
      page.goto(url, wait_until="domcontentloaded", timeout=35000)

      try:
        page.wait_for_selector("a[href*='/product/']", timeout=8000)
      except Exception:
        pass

      # Gradual scrolling loads lazy images and multi-row items
      page.evaluate("window.scrollBy(0, 1000)")
      time.sleep(0.8)
      page.evaluate("window.scrollBy(0, 1500)")
      time.sleep(0.8)

      rendered_html = page.content()
      html_size = len(rendered_html)

      # Catch 110-byte temporary blocks
      if html_size < 3000:
        print(
            f"    [Cooldown] Received {html_size} bytes. Pausing 10 seconds..."
        )
        time.sleep(10.0)
        continue

      items = parse_rendered_html(rendered_html, category, display_name)
      print(
          f"    [Page {page_num}] Size: {html_size:,} bytes | Extracted:"
          f" {len(items)} items"
      )
      return items

    except Exception as e:
      print(
          f"    Notice on attempt {attempt} for {display_name} (Page"
          f" {page_num}): {e}"
      )
      time.sleep(4.0)

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

    # Pre-warm connection
    try:
      page.goto("https://www.cdjapan.co.jp/", timeout=25000)
      time.sleep(2.0)
    except Exception:
      pass

    total_added_this_run = 0

    for idx, (cat, display_name, search_term) in enumerate(
        TARGET_QUERIES, start=1
    ):
      print(f"\n[{idx}/{len(TARGET_QUERIES)}] Querying: {display_name} ({cat})")
      new_for_artist = 0

      for p_idx in range(1, PAGES_PER_QUERY + 1):
        items = scrape_full_searches(
            page, cat, display_name, search_term, p_idx
        )
        if not items:
          break

        for it in items:
          pid = it["id"]
          if pid not in catalog:
            new_for_artist += 1
            total_added_this_run += 1
          catalog[pid] = it

        time.sleep(random.uniform(2.5, 4.0))

      print(f"    Total new items added for {display_name}: {new_for_artist}")
      time.sleep(random.uniform(2.0, 3.5))

    browser.close()

  # Save updated catalog
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(f"Run complete! Added {total_added_this_run} brand-new products.")
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
