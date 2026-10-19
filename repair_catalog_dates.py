import json
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

DATA_FILE = "products.json"
PROGRESS_FILE = "repair_progress.json"
BATCH_SIZE = 150  # Safe volume per session to avoid CDJapan WAF throttling

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12"
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/"
}


def parse_cdjapan_date(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", str(raw_text)).strip()

    # 1. YYYY/MM/DD or YYYY-MM-DD
    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m1:
        return f"{m1.group(1)}/{m1.group(2).zfill(2)}/{m1.group(3).zfill(2)}"

    # 2. Japanese format: YYYY年MM月DD日
    m2 = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if m2:
        return f"{m2.group(1)}/{m2.group(2).zfill(2)}/{m2.group(3).zfill(2)}"

    # 3. English format: Month DD, YYYY
    m3 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if m3:
        mon = m3.group(1).lower()
        if mon in MONTH_MAP:
            return f"{m3.group(3)}/{MONTH_MAP[mon]}/{m3.group(2).zfill(2)}"

    # 4. English format: DD Month YYYY
    m4 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", text)
    if m4:
        mon = m4.group(2).lower()
        if mon in MONTH_MAP:
            return f"{m4.group(3)}/{MONTH_MAP[mon]}/{m4.group(1).zfill(2)}"

    # 5. YYYY/MM
    m5 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", text)
    if m5:
        return f"{m5.group(1)}/{m5.group(2).zfill(2)}/01"

    return ""


def fetch_official_date(pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    try:
        time.sleep(random.uniform(0.3, 0.7))
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            # Check explicit release date table row
            date_th = soup.find(lambda el: el.name in ["th", "td", "span", "dt"] and "release date" in el.get_text().lower())
            if date_th:
                sibling = date_th.find_next_sibling(["td", "dd", "span"])
                if sibling:
                    d = parse_cdjapan_date(sibling.get_text())
                    if d:
                        return pid, d

            # Check schema meta tags
            meta_date = soup.find("meta", {"itemprop": "releaseDate"}) or soup.find("meta", {"property": "product:release_date"})
            if meta_date and meta_date.get("content"):
                d = parse_cdjapan_date(meta_date["content"])
                if d:
                    return pid, d

            # General page text fallback
            body_match = re.search(r"Release Date\s*[:：]?\s*([^\n\r<]+)", res.text, re.IGNORECASE)
            if body_match:
                d = parse_cdjapan_date(body_match.group(1))
                if d:
                    return pid, d

    except Exception:
        pass
    return pid, None


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_progress(processed_set):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(processed_set), f, indent=2)


def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    processed_keys = load_progress()

    # Identify suspect items not yet checked
    suspect_items = []
    for pid, it in catalog.items():
        if pid in processed_keys:
            continue
        d = str(it.get("release_date", "")).strip()
        if not d or d == "Available Now" or d.endswith("/01/01") or d.endswith("-01-01"):
            suspect_items.append(pid)

    total_remaining = len(suspect_items)
    print(f"Total catalog size: {len(catalog)} items.")
    print(f"Items previously audited: {len(processed_keys)}.")
    print(f"Items currently needing verification: {total_remaining}.", flush=True)

    if total_remaining == 0:
        print("All catalog items have been verified against CDJapan!")
        return

    current_batch = suspect_items[:BATCH_SIZE]
    print(f"\nProcessing active batch of {len(current_batch)} items...", flush=True)

    updated_count = 0

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_pid = {executor.submit(fetch_official_date, pid): pid for pid in current_batch}
        for future in as_completed(future_to_pid):
            pid, confirmed_date = future.result()
            processed_keys.add(pid)
            if confirmed_date:
                catalog[pid]["release_date"] = confirmed_date
                updated_count += 1
                print(f"   ✓ [{pid}] => {confirmed_date}", flush=True)

    # Save progress and updated database
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    save_progress(processed_keys)

    print("\n==========================================")
    print(f"Batch Complete! Updated {updated_count} release dates.")
    print(f"Remaining suspect items in catalog: {max(0, total_remaining - len(current_batch))}.")
    print("==========================================")


if __name__ == "__main__":
    main()
