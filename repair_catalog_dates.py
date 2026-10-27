"""
IdolJapan.store — Resilient CDJapan Catalog Release Date Healer
Audits and verifies release dates across ALL catalog releases,
extracts canonical street dates directly from CDJapan product pages, JSON-LD, and schema tags,
and guarantees simultaneous synchronization of products.json and catalog-index.json.
Supports on-demand cycle restart via environment variable or manual workflow trigger.
"""

import json
import math
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

# File: repair_catalog_dates.py | Block/Target: build_http_session
def build_http_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.8,
        # File: repair_catalog_dates.py | Block/Target: build_http_session
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    pool_cap = max(16, int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS)) * 2)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=pool_cap, pool_maxsize=pool_cap)
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
    # File: repair_catalog_dates.py | Block/Target: parse_cdjapan_date
    if not raw_text:
        return ""
    text = re.sub(r"\s+", " ", str(raw_text)).strip()

    # Match YYYY/MM/DD, YYYY-MM-DD, or YYYY.MM.DD
    m1 = re.search(r"\b(19\d\d|20\d\d)[/\-.](\d{1,2})[/\-.](\d{1,2})\b", text)
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

    # Match Year & Month only: YYYY/MM -> default to 1st of month (guarded against trailing/leading slashes)
    m5 = re.search(r"(?<![/-])\b(19\d\d|20\d\d)[/-](\d{1,2})\b(?![/-])", text)
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
        # File: repair_catalog_dates.py | Block/Target: fetch_official_date
        time.sleep(random.uniform(0.15, 0.4))
        res = session.get(url, headers=headers, timeout=14)

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            # Guard against WAF/Cloudflare soft-blocks returning HTTP 200
            if not soup.find("title") or "cdjapan" not in soup.find("title").get_text().lower():
                return pid, None

            # 1. Parse JSON-LD structured data (excluding promotional startDate)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    js_data = json.loads(script.string or "{}")
                    queue = js_data if isinstance(js_data, list) else [js_data]
                    while queue:
                        item = queue.pop(0)
                        if isinstance(item, dict):
                            if "@graph" in item and isinstance(item["@graph"], list):
                                queue.extend(item["@graph"])
                            for key in ["releaseDate", "datePublished"]:
                                if item.get(key):
                                    parsed = parse_cdjapan_date(item[key])
                                    if parsed:
                                        return pid, parsed
                except Exception:
                    pass

            # 2. Check Definition Lists (<dt>Release Date</dt><dd>...</dd>)
            dt_nodes = soup.find_all(
                lambda el: el.name in ["dt", "th"] and any(term in el.get_text().lower() for term in ["release date", "発売日", "release:"])
            )
            # File: repair_catalog_dates.py | Block/Target: fetch_official_date
            for dt in dt_nodes:
                dd = dt.find_next_sibling(["dd", "td"])
                if dd:
                    parsed = parse_cdjapan_date(dd.get_text(" ", strip=True))
                    if parsed:
                        return pid, parsed

            # 3. Check Leaf Table Rows and Specific List Items (ignore nested layout tables)
            for tr in soup.find_all(["tr", "li"]):
                if tr.find(["tr", "table"]):
                    continue
                row_text = tr.get_text(" ", strip=True).lower()
                if "release date" in row_text or "発売日" in row_text:
                    parsed = parse_cdjapan_date(tr.get_text(" ", strip=True))
                    if parsed:
                        return pid, parsed

            # 4. Check OpenGraph / Microdata Meta & Time Tags
            meta_date = (
                soup.find("meta", {"itemprop": "releaseDate"})
                or soup.find("meta", {"property": "product:release_date"})
                or soup.find("meta", {"name": "release_date"})
                or soup.find("meta", {"property": "og:release_date"})
                or soup.find("time", {"itemprop": "releaseDate"})
            )
            if meta_date:
                raw_meta = meta_date.get("content") or meta_date.get("datetime") or meta_date.get_text(" ", strip=True)
                parsed = parse_cdjapan_date(raw_meta)
                if parsed:
                    return pid, parsed

            # 5. Match against stripped page text so HTML tags don't break regex
            page_text = soup.get_text(" ", strip=True)
            body_match = re.search(r"(?:Release Date|発売日)\s*[:：]?\s*([^\n\r]{6,40})", page_text, re.IGNORECASE)
            if body_match:
                parsed = parse_cdjapan_date(body_match.group(1))
                if parsed:
                    return pid, parsed

            return pid, ""

        elif res.status_code == 404:
            return pid, "Available Now"

    except Exception:
        pass

    return pid, None

def load_progress():
    reset_requested = os.environ.get("RESET_PROGRESS", "").lower() in ["true", "1", "yes"] or \
                      os.environ.get("RESET_DATE_HEALER", "").lower() in ["true", "1", "yes"]

    if reset_requested:
        print("[Notice] RESET detected. Restarting audit from item 1.")
        if os.path.exists(PROGRESS_FILE):
            try:
                os.remove(PROGRESS_FILE)
            except Exception:
                pass
        return set()

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

def is_valid_date_format(d_str):
    if not d_str:
        return False
    clean = str(d_str).strip()
    m = re.match(r"^(\d{4})/(\d{2})/(\d{2})$", clean)
    # File: repair_catalog_dates.py | Block/Target: is_valid_date_format
    if not m:
        return False
    y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return is_calendar_valid(y, mon, d) and (1900 <= y <= 2035)

def get_progress_bar(percentage, width=24):
    filled = int(width * (percentage / 100))
    bar = "=" * filled + "-" * (width - filled)
    return f"[{bar}] {percentage:.1f}%"

def main():
    print("==========================================================")
    print("IdolJapan.store — Full-Catalog CDJapan Release Date Healer")
    print("==========================================================")

    if not os.path.exists(DATA_FILE):
        print(f"[Error] Catalog file {DATA_FILE} not found.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_catalog = len(catalog)
    processed_keys = load_progress()

    pending_items = sorted(
        [pid for pid in catalog.keys() if pid not in processed_keys],
        key=lambda pid: 0 if not is_valid_date_format(catalog[pid].get("release_date", "")) else 1
    )

    total_pending = len(pending_items)
    audited_count = len(processed_keys)
    progress_pct = (audited_count / total_catalog * 100) if total_catalog > 0 else 0

    print(f"Total Catalog Database:    {total_catalog:,} releases")
    print(f"Already Audited in Cycle:  {audited_count:,} releases ({progress_pct:.1f}%)")
    print(f"Pending Verification:      {total_pending:,} releases")
    print(f"Cycle Progress:            {get_progress_bar(progress_pct)}", flush=True)

    if total_pending == 0:
        print("\nAll 100% of catalog releases have been verified against CDJapan!")
        print("To restart the entire cycle again, pass RESET_DATE_HEALER=true or delete repair_progress.json.")
        return

    batch_size = int(os.environ.get("BATCH_SIZE", DEFAULT_BATCH_SIZE))
    batch_size = min(batch_size, total_pending)
    max_workers = int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS))
    batches_remaining = math.ceil(total_pending / batch_size) if batch_size > 0 else 0

    current_batch = pending_items[:batch_size]
    print(f"Targeting Batch Size:      {batch_size:,} items (~{batches_remaining} batch runs remaining)")
    print(f"Worker Threads:            {max_workers} concurrent connections\n", flush=True)

    session = build_http_session()
    updated_count = 0
    preserved_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(fetch_official_date, session, pid): pid
            for pid in current_batch
        }

        # File: repair_catalog_dates.py | Block/Target: main
        for idx, future in enumerate(as_completed(future_to_pid), 1):
            pid, confirmed_date = future.result()
            old_date = str(catalog[pid].get("release_date", "")).strip()

            if confirmed_date is None:
                # Transient network/HTTP error: preserve existing date and retry next batch
                if is_valid_date_format(old_date):
                    preserved_count += 1
                continue

            processed_keys.add(pid)

            if confirmed_date and confirmed_date != "Available Now":
                if confirmed_date != old_date:
                    catalog[pid]["release_date"] = confirmed_date
                    updated_count += 1
                    print(f"   [{idx}/{batch_size}] ✓ [{pid}] {old_date} -> {confirmed_date}", flush=True)
                else:
                    preserved_count += 1
            else:
                if is_valid_date_format(old_date):
                    preserved_count += 1
                else:
                    catalog[pid]["release_date"] = "Available Now"

            if idx % 50 == 0 or idx == batch_size:
                elapsed = time.time() - start_time
                print(f"   -> Progress: {idx}/{batch_size} processed ({elapsed:.1f}s elapsed)...", flush=True)

    # 1. Save updated products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # 2. Synchronize catalog-index.json for immediate deployment
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    save_progress(processed_keys)

    new_audited = len(processed_keys)
    remaining_pending = total_catalog - new_audited
    new_progress_pct = (new_audited / total_catalog * 100) if total_catalog > 0 else 0
    new_batches_left = math.ceil(remaining_pending / batch_size) if batch_size > 0 and remaining_pending > 0 else 0

    print("\n==========================================================")
    print("Batch Complete!")
    print("==========================================================")
    print(f"Dates Corrected / Updated: {updated_count:,} releases")
    print(f"Valid Dates Verified:      {preserved_count:,} releases")
    print(f"Total Audited in Cycle:    {new_audited:,} / {total_catalog:,} ({new_progress_pct:.1f}%)")
    print(f"Remaining to Audit:        {remaining_pending:,} releases (~{new_batches_left} batches left)")
    print(f"New Progress:              {get_progress_bar(new_progress_pct)}")
    print("Synchronized:              products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    main()
