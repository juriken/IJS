import json
import os
import re
import time
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

# Generic fallback dates assigned previously that indicate unverified items
PLACEHOLDER_DATES = [
    "2018/06/01", "2016/02/17", "2021/04/14", "2022/05/25",
    "2018/10/19", "2024/01/10", "2024/08/10", "2023/08/10",
    "2022/01/01", "2023/01/01", "2024/01/01", "2025/01/01",
    "2026/01/01", "2000-01-01", "2000/01/01", "Available Now"
]


def extract_date_from_string(text):
  if not text:
    return None

  clean = str(text).strip()

  # 1. Standard YYYY/MM/DD or YYYY-MM-DD
  m = re.search(r"\b(199\d|20[0-2]\d)[./-](\d{1,2})[./-](\d{1,2})\b", clean)
  if m:
    y = m.group(1)
    mon = m.group(2).zfill(2)
    d = m.group(3).zfill(2)
    return f"{y}/{mon}/{d}"

  # 2. English text date: "August 14, 2024" or "14 Aug 2024"
  m_text = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(199\d|20[0-2]\d)", clean)
  if m_text:
    mon_name = m_text.group(1).lower()
    if mon_name in MONTH_MAP:
      return f"{m_text.group(3)}/{MONTH_MAP[mon_name]}/{m_text.group(2).zfill(2)}"

  m_text_rev = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(199\d|20[0-2]\d)", clean)
  if m_text_rev:
    mon_name = m_text_rev.group(2).lower()
    if mon_name in MONTH_MAP:
      return f"{m_text_rev.group(3)}/{MONTH_MAP[mon_name]}/{m_text_rev.group(1).zfill(2)}"

  # 3. Japanese format: 2024年8月14日
  m_jp = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", clean)
  if m_jp:
    return f"{m_jp.group(1)}/{m_jp.group(2).zfill(2)}/{m_jp.group(3).zfill(2)}"

  # 4. Japanese Month only: 2024年8月
  m_jp_m = re.search(r"(\d{4})年(\d{1,2})月", clean)
  if m_jp_m:
    return f"{m_jp_m.group(1)}/{m_jp_m.group(2).zfill(2)}/01"

  # 5. Month & Year: "August 2024"
  m_my = re.search(r"([A-Za-z]+)\s+(199\d|20[0-2]\d)", clean)
  if m_my:
    mon_name = m_my.group(1).lower()
    if mon_name in MONTH_MAP:
      return f"{m_my.group(2)}/{MONTH_MAP[mon_name]}/01"

  return None


def fetch_deep_metadata(session, prod_id):
  url = f"https://www.cdjapan.co.jp/product/{prod_id}"
  try:
    resp = session.get(url, headers=HEADERS, timeout=12)
    if resp.status_code != 200:
      return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Check all table rows for Publication Date, Issue Date, Release Date, or 出版日
    for row in soup.select("tr, li, div.item-detail-spec, div.spec, table.spec"):
      row_text = row.get_text()
      if any(key in row_text for key in [
          "Publication Date", "Issue Date", "Release Date",
          "Date of Release", "発売日", "発行日", "出版年月"
      ]):
        parsed = extract_date_from_string(row_text)
        if parsed:
          return parsed

    # 2. Check meta tags and microdata
    for meta in soup.select("meta[property*='date'], meta[itemprop*='date'], meta[name*='date']"):
      content = meta.get("content", "")
      parsed = extract_date_from_string(content)
      if parsed:
        return parsed

    # 3. Check book specification definition list (<dl class="spec">)
    for dt in soup.select("dt"):
      dt_text = dt.get_text()
      if any(k in dt_text for k in ["Publication", "Release", "Date", "発売"]):
        dd = dt.find_next_sibling("dd")
        if dd:
          parsed = extract_date_from_string(dd.get_text())
          if parsed:
            return parsed

    # 4. Scan product description for publication announcements
    desc = soup.select_one(".description, .product-description, #spec, div.contents-main")
    if desc:
      parsed = extract_date_from_string(desc.get_text())
      if parsed:
        return parsed

  except Exception as e:
    print(f"    Error querying {prod_id}: {e}")

  return None


def main():
  if not os.path.exists(DATA_FILE):
    print(f"Error: {DATA_FILE} not found.")
    return

  with open(DATA_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

  # Identify only the unverified / fallback items
  missing_items = []
  for prod_id, item in catalog.items():
    current_date = str(item.get("release_date", "")).strip()
    if not current_date or current_date in PLACEHOLDER_DATES:
      missing_items.append((prod_id, item))

  total_missing = len(missing_items)
  print(f"Total catalog size: {len(catalog)} items.")
  print(f"Identified {total_missing} items requiring date verification.\n")

  if total_missing == 0:
    print("All items in catalog already have verified dates. Nothing to do!")
    return

  session = requests.Session()
  resolved_count = 0

  for idx, (prod_id, item) in enumerate(missing_items, 1):
    artist = item.get("artist", "")
    title = item.get("title", "")
    print(f"[{idx}/{total_missing}] Deep Inspect: {prod_id} ({artist})...")

    # 1. Check title first for Magazine/Book Issue dates (e.g. "UTB 2023 August Issue")
    title_date = extract_date_from_string(title)
    if title_date:
      item["release_date"] = title_date
      resolved_count += 1
      print(f"    => Resolved via Title: {title_date}")
      continue

    # 2. Query CDJapan's deep specification sheet for Book/Publication metadata
    deep_date = fetch_deep_metadata(session, prod_id)
    if deep_date:
      item["release_date"] = deep_date
      resolved_count += 1
      print(f"    => Resolved via Deep Metadata: {deep_date}")
    else:
      print("    => Retained fallback era date.")

    time.sleep(0.4)

    # Checkpoint save every 25 items
    if idx % 25 == 0:
      with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
      print(f"--- Saved checkpoint ({idx}/{total_missing}) ---")

  # Final Save
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  print("\n==========================================")
  print(f"Deep Scan Finished!")
  print(f"Successfully resolved dates for {resolved_count} out of {total_missing} items.")
  print(f"Total active catalog size: {len(catalog)} items.")
  print("==========================================")


if __name__ == "__main__":
  main()
