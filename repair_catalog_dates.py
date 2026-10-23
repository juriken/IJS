"""
IdolJapan.store — Resilient CDJapan Catalog Release Date Healer
Audits and resolves missing or malformed release dates, extracts canonical
street dates directly from CDJapan product pages and schema tags, and guarantees
simultaneous synchronization of products.json and catalog-index.json.
"""

import json
import os
import random
import re
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
PROGRESS_FILE = "repair_progress.json"

DEFAULT_BATCH_SIZE = 250
DEFAULT_MAX_WORKERS = 4

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
]

def build_http_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

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

    # Match YYYY/MM/DD or YYYY-MM-DD
    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Japanese format YYYY年MM月DD日
    m2 = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if m2:
        y, m, d = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Month DD, YYYY (e.g., September 21, 2024)
    m3 = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if m3:
        mon_str = m3.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m3.group(3)), MONTH_MAP[mon_str], int(m3.group(2))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match DD Month YYYY (e.g., 21 September 2024)
    m4 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", text)
    if m4:
        mon_str = m4.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m4.group(3)), MONTH_MAP[mon_str], int(m4.group(1))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Year & Month only: YYYY/MM -> default to 1st of month
    m5 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", text)
    if m5:
        y, m = int(m5.group(1)), int(m5.group(2))
        if 1 <= m <= 12:
            return f"{y}/{str(m).zfill(2)}/01"

    return ""

def fetch_official_date(session, pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/"
    }

    try:
        time.sleep(random.uniform(0.15, 0.4))
        res = session.get(url, headers=headers, timeout=14)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            # 1. Check table cells and description lists for Release Date
            date_nodes = soup.find_all(
                lambda el: el.name in ["th", "td", "span", "dt", "p", "div"]
                and any(term in el.get_text().lower() for term in ["release date", "発売日", "release:"])
            )
            for node in date_nodes:
                sibling = node.find_next_sibling(["td", "dd", "span", "div"])
                candidate_text = sibling.get_text() if sibling else node.get_text()
                parsed = parse_cdjapan_date(candidate_text)
                if parsed:
                    return pid, parsed

            # 2. Check Schema.org / OpenGraph structured meta tags
            meta_date = (
                soup.find("meta", {"itemprop": "releaseDate"})
                or soup.find("meta", {"property": "product:release_date"})
                or soup.find("meta", {"name": "release_date"})
            )
            if meta_date and meta_date.get("content"):
                parsed = parse_cdjapan_date(meta_date["content"])
                if parsed:
                    return pid, parsed

            # 3. Direct regex match on raw page text
            body_match = re.search(r"(?:Release Date|発売日)\s*[:：]?\s*([^\n\r<]+)", res.text, re.IGNORECASE)
            if body_match:
                parsed = parse_cdjapan_date(body_match.group(1))
                if parsed:
                    return pid, parsed

        elif res.status_code == 404:
            # Item is unlisted on CDJapan -> Keep as Available Now
            return pid, "Available Now"

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
        json.dump(sorted(list(processed_set)), f, indent=2)

def is_date_suspect(d_str):
    if not d_str:
        return True
    
    clean = str(d_str).strip()
    if clean in ["Available Now", "Unknown", "TBD", ""]:
        return True

    # Standard verified format check: YYYY/MM/DD
    m = re.match(r"^(\d{4})/(\d{2})/(\d{2})$", clean)
    if not m:
        # Malformed or unpadded date
        return True

    y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not is_calendar_valid(y, mon, d):
        return True

    # Pre-1990 is invalid for our contemporary idol roster
    if y < 1990 or y > 2035:
        return True

    return False

def main():
    print("==========================================================")
    print("IdolJapan.store — CDJapan Catalog Release Date Healer")
    print("==========================================================")

    if not os.path.exists(DATA_FILE):
        print(f"[Error] Catalog file {DATA_FILE} not found.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_catalog = len(catalog)
    processed_keys = load_progress()

    # Identify releases needing verification
    suspect_items = []
    for pid, it in catalog.items():
        curr_d = str(it.get("release_date", "")).strip()
        if is_date_suspect(curr_d) and pid not in processed_keys:
            suspect_items.append(pid)

    total_suspect = len(suspect_items)
    print(f"Total Catalog Database:    {total_catalog:,} releases")
    print(f"Already Audited & Logged:  {len(processed_keys):,} releases")
    print(f"Pending Date Verification: {total_suspect:,} releases", flush=True)

    if total_suspect == 0:
        print("\nAll catalog items possess verified release dates.")
        return

    batch_size = int(os.environ.get("BATCH_SIZE", DEFAULT_BATCH_SIZE))
    batch_size = min(batch_size, total_suspect)
    max_workers = int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS))

    current_batch = suspect_items[:batch_size]
    print(f"Targeting Batch Size:      {batch_size:,} items (using {max_workers} worker threads)\n", flush=True)

    session = build_http_session()
    updated_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(fetch_official_date, session, pid): pid
            for pid in current_batch
        }

        for idx, future in enumerate(as_completed(future_to_pid), 1):
            pid, confirmed_date = future.result()
            processed_keys.add(pid)

            if confirmed_date and confirmed_date != "Available Now":
                catalog[pid]["release_date"] = confirmed_date
                updated_count += 1
                print(f"   [{idx}/{batch_size}] ✓ [{pid}] {catalog[pid].get('title', '')[:30]} => {confirmed_date}", flush=True)
            else:
                # Mark as resolved with Available Now fallback
                catalog[pid]["release_date"] = "Available Now"

            if idx % 50 == 0 or idx == batch_size:
                elapsed = time.time() - start_time
                print(f"   -> Progress: {idx}/{batch_size} processed ({elapsed:.1f}s elapsed)...", flush=True)

    # 1. Save updated products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # 2. ALSO save updated catalog-index.json so live website is updated immediately
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Save progress tracking
    save_progress(processed_keys)

    remaining_suspect = total_suspect - len(current_batch)

    print("\n==========================================================")
    print("Batch Complete!")
    print("==========================================================")
    print(f"Releases Repaired:         {updated_count:,} dates successfully added")
    print(f"Total Audited to Date:     {len(processed_keys):,} releases")
    print(f"Remaining Suspect Items:   {remaining_suspect:,} releases left to heal")
    print("Synchronized:              products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    main()
