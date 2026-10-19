import json
import os
import re
from datetime import datetime

DATA_FILE = "products.json"


def normalize_date(date_str, title_str):
  if not date_str:
    date_str = ""

  clean = str(date_str).strip()

  # 1. Full YYYY/MM/DD or YYYY-MM-DD
  m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", clean)
  if m:
    y = int(m.group(1))
    mon = int(m.group(2))
    d = int(m.group(3))
    if 1990 <= y <= 2030 and 1 <= mon <= 12 and 1 <= d <= 31:
      return f"{y:04d}-{mon:02d}-{d:02d}"

  # 2. Year/Month: YYYY/MM or YYYY-MM
  m = re.search(r"(\d{4})[./-](\d{1,2})", clean)
  if m:
    y = int(m.group(1))
    mon = int(m.group(2))
    if 1990 <= y <= 2030 and 1 <= mon <= 12:
      return f"{y:04d}-{mon:02d}-01"

  # 3. Check year in title (e.g. "Tour 2023", "Single 2021")
  m = re.search(r"\b(199\d|20[0-2]\d)\b", str(title_str or ""))
  if m:
    return f"{m.group(1)}-01-01"

  # Fallback: Undated
  return "2000-01-01"


def main():
  if not os.path.exists(DATA_FILE):
    print("Catalog file not found.")
    return

  with open(DATA_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

  print(f"Total items in catalog before cleanup: {len(catalog)}")

  cleaned_catalog = {}
  for prod_id, item in catalog.items():
    raw_date = item.get("release_date", "")
    title = item.get("title", "")

    # Clean release date to strict ISO format
    standard_date = normalize_date(raw_date, title)
    item["release_date"] = standard_date

    # Ensure clean price formatting
    raw_price = item.get("price", "")
    price_digits = re.sub(r"[^\d]", "", str(raw_price))
    if price_digits:
      item["price_num"] = int(price_digits)
      item["price"] = f"{int(price_digits):,}yen"
    else:
      item["price_num"] = 0
      item["price"] = "Check CDJapan"

    cleaned_catalog[prod_id] = item

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

  print(f"Cleanup complete. Standardized dates for {len(cleaned_catalog)} items.")


if __name__ == "__main__":
  main()
