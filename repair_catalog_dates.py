import json
import os
import random
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

DATA_FILE = "products.json"
PROGRESS_FILE = "repair_progress.json"
BATCH_SIZE = 150

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/"
}

def is_calendar_valid(year, month, day):
    try:
        datetime(year, month, day)
        return True
    except (ValueError, OverflowError):
        return False

def parse_cdjapan_date(raw_text):
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", str(raw_text)).strip()

    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    m2 = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if m2:
        y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    m3 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if m3:
        mon_str = m3.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m3.group(3)), MONTH_MAP[mon_str], int(m3.group(2))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    m4 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", text)
    if m4:
        mon_str = m4.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m4.group(3)), MONTH_MAP[mon_str], int(m4.group(1))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    m5 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", text)
    if m5:
        y, m = int(m5.group(1)), int(m5.group(2))
        if 1 <= m <= 12:
            return f"{y}/{str(m).zfill(2)}/01"

    return ""

def fetch_official_date(pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    try:
        time.sleep(random.uniform(0.3, 0.7))
        res = requests.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            date_th = soup.find(lambda el: el.name in ["th", "td", "span", "dt"] and "release date" in el.get_text().lower())
            if date_th:
                sibling = date_th.find_next_sibling(["td", "dd", "span"])
                if sibling:
                    d = parse_cdjapan_date(sibling.get_text())
                    if d:
                        return pid, d

            meta_date = soup.find("meta", {"itemprop": "releaseDate"}) or soup.find("meta", {"property": "product:release_date"})
            if meta_date and meta_date.get("content"):
                d = parse_cdjapan_date(meta_date["content"])
                if d:
                    return pid, d

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

def is_date_corrupted_or_suspect(d_str):
    if not d_str or d_str.strip() == "Available Now":
        return True
    
    clean_str = d_str.strip().replace("-", "/")
    parts = clean_str.split("/")
    if len(parts) == 3:
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if not is_calendar_valid(y, m, d):
                return True
            if m == 1 and d == 1:
                return True
        except ValueError:
            return True
    else:
        return True

    return False

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    processed_keys = load_progress()

    suspect_items = []
    for pid, it in catalog.items():
        d = str(it.get("release_date", "")).strip()
        if is_date_corrupted_or_suspect(d):
            if pid in processed_keys:
                clean_d = d.replace("-", "/")
                parts = clean_d.split("/")
                if len(parts) == 3:
                    try:
                        y, m, day_val = int(parts[0]), int(parts[1]), int(parts[2])
                        if not is_calendar_valid(y, m, day_val):
                            processed_keys.discard(pid)
                    except ValueError:
                        processed_keys.discard(pid)

            if pid not in processed_keys:
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
            else:
                curr_d = str(catalog[pid].get("release_date", "")).strip()
                if is_date_corrupted_or_suspect(curr_d):
                    catalog[pid]["release_date"] = "Available Now"

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    save_progress(processed_keys)

    print("\n==========================================")
    print(f"Batch Complete! Updated {updated_count} release dates.")
    print(f"Remaining suspect items in catalog: {max(0, total_remaining - len(current_batch))}.")
    print("==========================================")

if __name__ == "__main__":
    main()
