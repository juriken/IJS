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

# File: repair_catalog_dates.py | Block/Target: MONTH_MAP
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
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

# File: repair_catalog_dates.py | Block/Target: parse_cdjapan_date
def parse_cdjapan_date(raw_text):
    if not raw_text:
        return ""
    import unicodedata
    text = unicodedata.normalize("NFKC", str(raw_text))
    text = re.sub(r"\s+", " ", text).strip()

    # Match YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD, or ISO-8601 (e.g. 2024-09-25T00:00:00)
    m1 = re.search(r"(?<!\d)(19\d\d|20\d\d)[/\-.](\d{1,2})[/\-.](\d{1,2})(?!\d)", text)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Japanese format YYYY年MM月DD日 or YYYY年MM月
    m2 = re.search(r"(\d{4})年\s*(\d{1,2})月(?:\s*(\d{1,2})日)?", text)
    if m2:
        y, m = int(m2.group(1)), int(m2.group(2))
        d = int(m2.group(3)) if m2.group(3) else 1
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Month DD, YYYY (e.g., September 21, 2024 or Oct. 23, 2024)
    m3 = re.search(r"\b([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if m3:
        mon_str = m3.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m3.group(3)), MONTH_MAP[mon_str], int(m3.group(2))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match DD Month YYYY (e.g., 21 September 2024 or 21 Oct. 2024)
    m4 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\.?,?\s+(19\d\d|20\d\d)\b", text)
    if m4:
        mon_str = m4.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m4.group(3)), MONTH_MAP[mon_str], int(m4.group(1))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Month YYYY (e.g., September 2024 or Oct. 2024) -> default to 1st of month
    m5 = re.search(r"\b([A-Za-z]+)\.?,?\s+(19\d\d|20\d\d)\b", text)
    if m5:
        mon_str = m5.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m = int(m5.group(2)), MONTH_MAP[mon_str]
            if 1 <= m <= 12:
                return f"{y}/{str(m).zfill(2)}/01"

    # Match Year & Month only: YYYY/MM -> default to 1st of month
    m6 = re.search(r"(?<![/\-\d])\b(19\d\d|20\d\d)[/-](\d{1,2})\b(?![/\-\d])", text)
    if m6:
        y, m = int(m6.group(1)), int(m6.group(2))
        if 1 <= m <= 12:
            return f"{y}/{str(m).zfill(2)}/01"

    return ""
    
# File: repair_catalog_dates.py | Block/Target: fetch_official_date
def fetch_official_date(session, pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/"
    }

    try:
        time.sleep(random.uniform(0.6, 1.4))
        res = session.get(url, headers=headers, timeout=14)

        if res.status_code == 200:
            # Guard against redirects to homepage or department landing pages for deleted items
            if not res.url.startswith("https://www.cdjapan.co.jp/product/"):
                return pid, ""

            soup = BeautifulSoup(res.text, "html.parser")

            # Guard against WAF/Cloudflare soft-blocks returning HTTP 200
            if not soup.find("title") or "cdjapan" not in soup.find("title").get_text().lower():
                return pid, None

           # 1. Parse JSON-LD structured data
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    raw_content = script.get_text(strip=True)
                    if not raw_content:
                        continue
                    js_data = json.loads(raw_content)
                    queue = js_data if isinstance(js_data, list) else [js_data]
                    while queue:
                        item = queue.pop(0)
                        if isinstance(item, dict):
                            if "@graph" in item and isinstance(item["@graph"], list):
                                queue.extend(item["@graph"])
                            if "offers" in item:
                                if isinstance(item["offers"], dict):
                                    queue.append(item["offers"])
                                elif isinstance(item["offers"], list):
                                    queue.extend(item["offers"])
                            if "additionalProperty" in item and isinstance(item["additionalProperty"], list):
                                for prop in item["additionalProperty"]:
                                    if isinstance(prop, dict) and any(k in str(prop.get("name", "")).lower() for k in ["release", "発売"]):
                                        parsed = parse_cdjapan_date(prop.get("value", ""))
                                        if parsed:
                                            return pid, parsed
                            for key in ["releaseDate", "datePublished"]:
                                if item.get(key):
                                    parsed = parse_cdjapan_date(item[key])
                                    if parsed:
                                        return pid, parsed
                except Exception:
                    pass

            # 2. Check Definition Lists & Key-Value Table Cells
            label_nodes = soup.find_all(
                lambda el: el.name in ["dt", "th", "td"] and any(term in el.get_text().lower() for term in ["release date", "発売日", "release:"])
            )
            for label in label_nodes:
                val = label.find_next_sibling(["dd", "td"])
                if val:
                    parsed = parse_cdjapan_date(val.get_text(" ", strip=True))
                    if parsed:
                        return pid, parsed

            # 3. Check Canonical OpenGraph / Microdata Meta & Time Tags
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

            # 4. Check Leaf Table Rows and Specific List Items
            for tr in soup.find_all(["tr", "li"]):
                if tr.find(["tr", "table"]):
                    continue
                row_text = tr.get_text(" ", strip=True).lower()
                if "release date" in row_text or "発売日" in row_text:
                    parsed = parse_cdjapan_date(tr.get_text(" ", strip=True))
                    if parsed:
                        return pid, parsed

            # 5. Fallback regex across stripped page text
            page_text = soup.get_text(" ", strip=True)
            body_match = re.search(r"(?:Release Date|発売日)\s*[:：]?\s*([^\n\r]{6,40})", page_text, re.IGNORECASE)
            if body_match:
                parsed = parse_cdjapan_date(body_match.group(1))
                if parsed:
                    return pid, parsed

            return pid, ""

        elif res.status_code == 404:
            return pid, ""

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
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception:
            pass

    return set()

def atomic_save_json(filepath, data):
    tmp_file = f"{filepath}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_file, filepath)

def save_progress(processed_set):
    atomic_save_json(PROGRESS_FILE, sorted(list(processed_set)))
    
# File: repair_catalog_dates.py | Block/Target: is_valid_date_format
def is_valid_date_format(d_str):
    if not d_str:
        return False
    clean = str(d_str).strip()
    m = re.match(r"^(\d{4})[/\-](\d{2})[/\-](\d{2})$", clean)
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
    # File: repair_catalog_dates.py | Block/Target: main
    print(f"Worker Threads:            {max_workers} concurrent connections\n", flush=True)

    # File: repair_catalog_dates.py | Block/Target: main_execution_loop
    session = build_http_session()
    updated_count = 0
    preserved_count = 0
    consecutive_blocks = 0
    max_consecutive_blocks = 8
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pid = {
                executor.submit(fetch_official_date, session, pid): pid
                for pid in current_batch
            }

            for idx, future in enumerate(as_completed(future_to_pid), 1):
                pid, confirmed_date = future.result()
                old_date = str(catalog[pid].get("release_date", "")).strip()

                if confirmed_date is None:
                    consecutive_blocks += 1
                    if is_valid_date_format(old_date):
                        preserved_count += 1
                    if consecutive_blocks >= max_consecutive_blocks:
                        print(f"\n[Warning] {consecutive_blocks} consecutive network/WAF blocks. Aborting batch early to protect IP reputation.")
                        for f in future_to_pid:
                            f.cancel()
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    continue

                consecutive_blocks = 0
                processed_keys.add(pid)

                if confirmed_date:
                    if confirmed_date != old_date:
                        catalog[pid]["release_date"] = confirmed_date
                        updated_count += 1
                        print(f"   [{idx}/{batch_size}] ✓ [{pid}] {old_date} -> {confirmed_date}", flush=True)
                    else:
                        preserved_count += 1
                else:
                    if is_valid_date_format(old_date):
                        preserved_count += 1

                if idx % 50 == 0 or idx == batch_size:
                    elapsed = time.time() - start_time
                    print(f"   -> Progress: {idx}/{batch_size} processed ({elapsed:.1f}s elapsed)...", flush=True)

    finally:
        # Atomic commit guarantees no half-written JSON files if runner exits
        atomic_save_json(DATA_FILE, catalog)
        if os.path.exists(INDEX_FILE):
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    idx_data = json.load(f)
                
                date_lookup = {p: val.get("release_date") for p, val in catalog.items() if isinstance(val, dict)}

                if isinstance(idx_data, dict):
                    if "items" in idx_data and isinstance(idx_data["items"], list):
                        target_list = idx_data["items"]
                    elif "products" in idx_data and isinstance(idx_data["products"], list):
                        target_list = idx_data["products"]
                    else:
                        target_list = None

                    if target_list is not None:
                        for entry in target_list:
                            if isinstance(entry, dict):
                                eid = entry.get("id") or entry.get("pid") or entry.get("productId")
                                if eid in date_lookup and date_lookup[eid]:
                                    entry["release_date"] = date_lookup[eid]
                    else:
                        for p, val in catalog.items():
                            if p in idx_data and isinstance(idx_data[p], dict) and "release_date" in val:
                                idx_data[p]["release_date"] = val["release_date"]
                    atomic_save_json(INDEX_FILE, idx_data)
                elif isinstance(idx_data, list):
                    for entry in idx_data:
                        if isinstance(entry, dict):
                            eid = entry.get("id") or entry.get("pid") or entry.get("productId")
                            if eid in date_lookup and date_lookup[eid]:
                                entry["release_date"] = date_lookup[eid]
                    atomic_save_json(INDEX_FILE, idx_data)
                else:
                    atomic_save_json(INDEX_FILE, catalog)
            except Exception:
                atomic_save_json(INDEX_FILE, catalog)
        else:
            atomic_save_json(INDEX_FILE, catalog)
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
