import json
import os
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

DATA_FILE = "products.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
}

MONTH_MAP = {
    "january": "01", "jan": "01",
    "february": "02", "feb": "02",
    "march": "03", "mar": "03",
    "april": "04", "apr": "04",
    "may": "05",
    "june": "06", "jun": "06",
    "july": "07", "jul": "07",
    "august": "08", "aug": "08",
    "september": "09", "sep": "09", "sept": "09",
    "october": "10", "oct": "10",
    "november": "11", "nov": "11",
    "december": "12", "dec": "12"
}


def parse_clean_date(text):
  if not text:
    return None

  clean = str(text).strip()

  # 1. Standard YYYY/MM/DD or YYYY-MM-DD
  m = re.search(r"\b(199\d|20[0-3]\d)[./-](\d{1,2})[./-](\d{1,2})\b", clean)
  if m:
    y = m.group(1)
    mon = m.group(2).zfill(2)
    d = m.group(3).zfill(2)
    return f"{y}/{mon}/{d}"

  # 2. English text date: "August 14, 2024" or "14 Aug 2024"
  m_text = re.search(
      r"([A-Za-z]+)\s+(\d{1,2}),?\s+(199\d|20[0-3]\d)", clean
  )
  if m_text:
    mon_name = m_text.group(1).lower()
    if mon_name in MONTH_MAP:
      return f"{m_text.group(3)}/{MONTH_MAP[mon_name]}/{m_text.group(2).zfill(2)}"

  m_text_rev = re.search(
      r"(\d{1,2})\s+([A-Za-z]+)\s+(199\d|20[0-3]\d)", clean
  )
  if m_text_rev:
    mon_name = m_text_rev.group(2).lower()
    if mon_name in MONTH_MAP:
      return f"{m_text_rev.group(3)}/{MONTH_MAP[mon_name]}/{m_text_rev.group(1).zfill(2)}"

  # 3. Year/Month: YYYY/MM
  m_ym = re.search(r"\b(199\d|20[0-3]\d)[./-](\d{1,2})\b", clean)
  if m_ym:
    return f"{m_ym.group(1)}/{m_ym.group(2).zfill(2)}/01"

  return None


def fetch_exact_date_for_product(session, prod_id):
  url = f"https://www.cdjapan.co.jp/product/{prod_id}"
  try:
    resp = session.get(url, headers=HEADERS, timeout=12)
    if resp.status_code != 200:
      return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Look for 'Release Date' row inside product specs table
    for row in soup.select("tr, li, div.item-detail-spec"):
      text = row.get_text()
      if "Release Date" in text or "発売日" in text:
        parsed = parse_clean_date(text)
        if parsed:
          return parsed

    # 2. Check meta tags and JSON-LD microdata
    meta_date = (
        soup.select_one("meta[property='product:release_date']")
        or soup.select_one("meta[itemprop='releaseDate']")
    )
    if meta_date and meta_date.get("content"):
      parsed = parse_clean_date(meta_date.get("content"))
      if parsed:
        return parsed

    # 3. General page scan for explicit date near description
    desc_node = soup.select_one(".description, .product-description, #spec")
    if desc_node:
      parsed = parse_clean_date(desc_node.get_text())
      if parsed:
        return parsed

  except Exception as e:
    print(f"    Error on {prod_id}: {e}")

  return None


def main():
  if not os.path.exists(DATA_FILE):
    print(f"Error: {DATA_FILE} not found.")
    return

  with open(DATA_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

  total_items = len(catalog)
  print(f"Loaded {total_items} items from {DATA_FILE}.")

  session = requests.Session()
  updated_count = 0
  items_list = list(catalog.items())

  for idx, (prod_id, item) in enumerate(items_list, 1):
    current_date = str(item.get("release_date", "")).strip()

    # Prioritize items that currently lack a verified specific date
    print(f"[{idx}/{total_items}] Checking {prod_id} ({item.get('artist')})...")
    exact_date = fetch_exact_date_for_product(session, prod_id)

    if exact_date:
      item["release_date"] = exact_date
      updated_count += 1
      print(f"    => Found Official Date: {exact_date}")
    else:
      print(f"    => Retained fallback date: {current_date}")

    # Polite delay to prevent rate limiting
    time.sleep(0.4)

    # Periodic checkpoint save every 50 items so work is never lost
    if idx % 50 == 0:
      with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
      print(f"--- Saved checkpoint ({idx}/{total_items}) ---")

  # Final save
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  print(f"\n==========================================")
  print(f"Finished! Successfully updated official dates for {updated_count} items.")
  print(f"==========================================")


if __name__ == "__main__":
  main()
