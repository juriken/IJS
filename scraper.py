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

TARGET_GROUPS = [
    # Hello! Project
    ("Hello! Project", "Morning Musume", "Morning Musume", ["Morning Musume", "Morning Musume."]),
    ("Hello! Project", "ANGERME", "ANGERME", ["ANGERME", "Smileage", "S/mileage"]),
    ("Hello! Project", "Juice=Juice", "Juice=Juice", ["Juice=Juice"]),
    ("Hello! Project", "Tsubaki Factory", "Tsubaki Factory", ["Tsubaki Factory"]),
    ("Hello! Project", "BEYOOOOONDS", "BEYOOOOONDS", ["BEYOOOOONDS"]),
    ("Hello! Project", "OCHA NORMA", "OCHA NORMA", ["OCHA NORMA", "OCHA"]),
    ("Hello! Project", "Rosy Chronicle", "Rosy Chronicle", ["Rosy Chronicle", "Rosy"]),
    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46", "Nogizaka46", ["Nogizaka46", "Nogizaka", "乃木坂"]),
    ("Sakamichi Series", "Sakurazaka46", "Sakurazaka46", ["Sakurazaka46", "Sakurazaka", "櫻坂"]),
    ("Sakamichi Series", "Hinatazaka46", "Hinatazaka46", ["Hinatazaka46", "Hinatazaka", "日向坂"]),
    # AKB48 Group
    ("AKB48 Group", "AKB48", "AKB48", ["AKB48"]),
    ("AKB48 Group", "SKE48", "SKE48", ["SKE48"]),
    ("AKB48 Group", "NMB48", "NMB48", ["NMB48"]),
    ("AKB48 Group", "HKT48", "HKT48", ["HKT48"]),
    ("AKB48 Group", "NGT48", "NGT48", ["NGT48"]),
    ("AKB48 Group", "STU48", "STU48", ["STU48"]),
    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", "Equal Love", ["=LOVE", "Equal Love", "イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", "Not Equal ME", ["≠ME", "Not Equal ME", "Noime"]),
    ("=LOVE / Sister Groups", "≒JOY", "Nearly Equal Joy", ["≒JOY", "Nearly Equal Joy", "Niajoy"]),
    # Other Key Units
    ("Momoiro Clover Z", "Momoiro Clover Z", "Momoiro Clover Z", ["Momoiro Clover", "Momoclo"]),
    ("Babymetal", "BABYMETAL", "BABYMETAL", ["BABYMETAL"]),
]

PAGES_PER_TARGET = 3
BATCH_SIZE = 7


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


def is_relevant_product(card_text, keywords):
  if not keywords:
    return True
  lower_text = card_text.lower()
  return any(kw.lower() in lower_text for kw in keywords)


def extract_verified_products(html, category, canonical_artist, keywords):
  soup = BeautifulSoup(html, "html.parser")
  items_dict = {}

  cards = (
      soup.select(".item-detail")
      or soup.select(".n-item")
      or soup.select(".item")
      or soup.select("div[class*='item-']")
  )

  for card in cards:
    link_el = card.select_one("a[href*='/product/']")
    if not link_el:
      continue

    href = link_el.get("href", "")
    match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
    if not match:
      continue

    prod_key = match.group(1)

    if prod_key.lower() in [
        "cart", "login", "help", "contact", "about",
        "tokuten", "ranking", "app"
    ]:
      continue

    title_el = (
        card.select_one(".title a")
        or card.select_one("a.item-title")
        or card.select_one(".title")
        or link_el
    )
    raw_title = clean_text(title_el.get_text()) if title_el else ""

    artist_el = (
        card.select_one(".artist")
        or card.select_one(".item-artist")
        or card.select_one(".cast")
    )
    raw_artist = clean_text(artist_el.get_text()) if artist_el else ""

    img_el = card.select_one("img")
    img_url = ""
    if img_el:
      img_url = (
          img_el.get("src")
          or img_el.get("data-src")
          or img_el.get("data-original")
          or ""
      )
      if not raw_title and img_el.get("alt"):
        raw_title = clean_text(img_el.get("alt"))

    if not raw_title:
      continue

    if (
        not img_url
        or "spacer" in img_url
        or "blank" in img_url
        or "no_image" in img_url
    ):
      img_url = f"https://www.cdjapan.co.jp/pictures/l/{prod_key}.jpg"
    elif img_url.startswith("//"):
      img_url = "https:" + img_url
    elif img_url.startswith("/"):
      img_url = "https://www.cdjapan.co.jp" + img_url

    img_url = img_url.replace("/pictures/s/", "/pictures/l/").replace(
        "/pictures/m/", "/pictures/l/"
    )

    price_el = (
        card.select_one(".price")
        or card.select_one(".item-price")
        or card.select_one(".price-value")
        or card.select_one("span.bold")
    )
    price_str = "Check CDJapan"
    if price_el:
      p_match = re.search(
          r"(\d[\d,]*\s*(?:yen|JPY|円)?)",
          clean_text(price_el.get_text()),
          re.IGNORECASE,
      )
      if p_match and p_match.group(1).strip():
        num_only = re.sub(r"[^\d]", "", p_match.group(1))
        if num_only:
          price_str = f"{int(num_only):,}yen"
    else:
      p_match = re.search(
          r"(\d[\d,]*)\s*(?:yen|JPY|円)", clean_text(card.get_text())
      )
      if p_match:
        price_str = f"{p_match.group(1)}yen"

    date_el = (
        card.select_one(".release_date")
        or card.select_one(".item-date")
        or card.select_one(".date")
    )
    rel_date = "Available Now"
    if date_el:
      d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", date_el.get_text())
      if d_match:
        rel_date = d_match.group(1).replace("-", "/")
    else:
      d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", card.get_text())
      if d_match:
        rel_date = d_match.group(1).replace("-", "/")

    searchable_card_text = (
        f"{raw_title} {raw_artist} {clean_text(card.get_text())}"
    )
    if not is_relevant_product(searchable_card_text, keywords):
      continue

    items_dict[prod_key] = {
        "id": prod_key,
        "title": raw_title,
        "artist": canonical_artist,
        "category": category,
        "price": price_str,
        "release_date": rel_date,
        "image": img_url,
        "affiliate_url": make_affiliate_link(prod_key),
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
    }

  return list(items_dict.values())


def execute_session_search(page, category, canonical_artist, query, keywords, max_pages):
  results = []
  print(f"\n-> In-Session Search for: {canonical_artist} (Query: '{query}')")

  for attempt in range(1, 3):
    try:
      # Scroll to top to ensure header input is accessible
      page.evaluate("window.scrollTo(0, 0)")
      time.sleep(0.5)

      # Target the search form and input inside the active session
      search_input = page.locator("input[name='q']").first

      # If page is not in a searchable state, navigate back to the main search hub
      if not search_input.is_visible():
        page.goto("https://www.cdjapan.co.jp/searchuni?q=idol", wait_until="domcontentloaded", timeout=20000)
        time.sleep(1.0)
        search_input = page.locator("input[name='q']").first

      # Fill and submit directly through the browser session
      search_input.click()
      search_input.fill("")
      search_input.fill(query)
      time.sleep(0.3)

      with page.expect_navigation(wait_until="domcontentloaded", timeout=20000):
        search_input.press("Enter")

      time.sleep(1.5)

      # Harvest pages via the active session 'Next' button
      for p_num in range(1, max_pages + 1):
        page.evaluate("window.scrollBy(0, 800)")
        time.sleep(0.8)

        html = page.content()
        verified = extract_verified_products(
            html, category, canonical_artist, keywords
        )
        print(f"   [Page {p_num}] Extracted {len(verified)} verified products")
        results.extend(verified)

        if p_num < max_pages:
          next_btn = page.locator("a[rel='next'], a.next, a:has-text('Next')")
          if next_btn.count() > 0 and next_btn.first.is_visible():
            with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
              next_btn.first.click()
            time.sleep(random.uniform(2.5, 3.5))
          else:
            break

      return results

    except Exception as e:
      print(f"   Attempt {attempt} notice for {canonical_artist}: {e}")
      time.sleep(3.0)

  return results


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Current catalog size: {initial_count} items")

  # Select a shuffled batch of 7 targets per execution
  batch = random.sample(TARGET_GROUPS, min(BATCH_SIZE, len(TARGET_GROUPS)))

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

    # Initial session establishment on the search interface
    try:
      page.goto(
          "https://www.cdjapan.co.jp/searchuni?q=Morning+Musume&order=reldesc",
          wait_until="domcontentloaded",
          timeout=25000,
      )
      time.sleep(2.0)
    except Exception:
      pass

    new_total = 0

    for idx, (cat, artist, query, keywords) in enumerate(batch, 1):
      print(f"\n[{idx}/{len(batch)}] Target: {artist}")
      items = execute_session_search(
          page, cat, artist, query, keywords, max_pages=PAGES_PER_TARGET
      )
      added_for_artist = 0

      for it in items:
        pid = it["id"]
        if pid not in catalog:
          added_for_artist += 1
          new_total += 1
        catalog[pid] = it

      print(
          f"   => Verified items for {artist}: {len(items)} found"
          f" ({added_for_artist} new to database)"
      )
      time.sleep(random.uniform(3.5, 5.5))

    browser.close()

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  final_count = len(catalog)
  print(f"\n==========================================")
  print(f"Batch Complete! Added {new_total} brand-new verified products.")
  print(f"Total active catalog size: {final_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
