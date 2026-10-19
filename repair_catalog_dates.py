import json
import re

DATA_FILE = "products.json"

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12"
}

def clean_date_string(raw_val, title):
    if not raw_val or raw_val == "Available Now":
        return "Available Now"

    s = str(raw_val).strip()

    # 1. YYYY/MM/DD or YYYY-MM-DD
    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", s)
    if m1:
        y, m, d = m1.group(1), m1.group(2).zfill(2), m1.group(3).zfill(2)
        return f"{y}/{m}/{d}"

    # 2. English format: Month DD, YYYY
    m2 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", s)
    if m2:
        mon = m2.group(1).lower()
        if mon in MONTH_MAP:
            return f"{m2.group(3)}/{MONTH_MAP[mon]}/{m2.group(2).zfill(2)}"

    # 3. English format: DD Month YYYY
    m3 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", s)
    if m3:
        mon = m3.group(2).lower()
        if mon in MONTH_MAP:
            return f"{m3.group(3)}/{MONTH_MAP[mon]}/{m3.group(1).zfill(2)}"

    # 4. Japanese format: YYYY年MM月DD日
    m4 = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", s)
    if m4:
        return f"{m4.group(1)}/{m4.group(2).zfill(2)}/{m4.group(3).zfill(2)}"

    # 5. Month & Year: YYYY/MM -> YYYY/MM/01
    m5 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", s)
    if m5:
        return f"{m5.group(1)}/{m5.group(2).zfill(2)}/01"

    # Eliminate invalid dates (e.g., placeholder Jan 1 dates from title matching)
    if s.endswith("/01/01") and any(y in title for y in ["199", "200", "201", "202"]):
        return "Available Now"

    return "Available Now"


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    fixed_count = 0
    now_count = 0

    for pid, item in catalog.items():
        original_date = item.get("release_date", "")
        title = item.get("title", "")
        corrected_date = clean_date_string(original_date, title)

        if corrected_date != original_date:
            item["release_date"] = corrected_date
            fixed_count += 1
            if corrected_date == "Available Now":
                now_count += 1

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"Audited {len(catalog)} items.")
    print(f"Repaired release dates on {fixed_count} items (Cleaned to 'Available Now': {now_count}).")


if __name__ == "__main__":
    main()
