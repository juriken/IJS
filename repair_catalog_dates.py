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
import unicodedata
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
PROGRESS_FILE = "repair_progress.json"

DEFAULT_BATCH_SIZE = 250
DEFAULT_MAX_WORKERS = 4

# File: repair_catalog_dates.py | Block/Target: INVALID_STOPWORDS
INVALID_STOPWORDS = {
    "none", "tbd", "n/a", "na", "-", "--", "null", "undefined", "unknown",
    "cd", "dvd", "bd", "bluray", "blu-ray", "goods", "0", "1", "false", "true",
    "items", "products", "all", "type-a", "type-b", "type-c", "type-d",
    "type a", "type b", "type c", "type d", "typea", "typeb", "typec", "typed",
    "regular", "limited", "edition", "first press", "firstpress", "regular edition",
    "limited edition", "standard edition", "special edition", "normal edition",
    "single", "album", "mini album", "minialbum", "ep", "lp", "box set", "boxset",
    "photobook", "calendar", "poster", "badge", "t-shirt", "tshirt", "t shirt",
    "clear file", "clearfile", "keychain", "strap", "acrylic stand", "acsta",
    "japan", "jp", "us", "usa", "en", "official", "complete", "version", "ver"
}

def is_invalid_identifier(cand):
    if not cand:
        return True
    s = str(cand).strip().lower()
    if len(s) < 3:
        return True
    norm = re.sub(r"[\s\-_]+", "", s)
    if s in INVALID_STOPWORDS or norm in INVALID_STOPWORDS:
        return True
    tokens = set(re.split(r"[\s\-_/]+", s))
    generic_tokens = {
        "type", "a", "b", "c", "d", "regular", "limited", "first",
        "press", "edition", "ver", "version", "cd", "dvd", "bd",
        "goods", "single", "album", "set", "box", "standard", "special"
    }
    if tokens and tokens.issubset(generic_tokens):
        return True
    return False

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

# Thread-local storage guarantees isolated cookie jars per worker thread
_thread_local = threading.local()

# File: repair_catalog_dates.py | Block/Target: build_http_session
def build_http_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin"
    })
    # File: repair_catalog_dates.py | Block/Target: build_http_session
    retry_kwargs = {
        "total": 5,
        "backoff_factor": 1.0,
        "status_forcelist": [429, 500, 502, 503, 504],
        "raise_on_status": False
    }
    try:
        retries = Retry(**retry_kwargs, backoff_jitter=0.5)
    except TypeError:
        retries = Retry(**retry_kwargs)
    pool_cap = max(16, int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS)) * 2)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=pool_cap, pool_maxsize=pool_cap)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def get_thread_session():
    if not hasattr(_thread_local, "session"):
        _thread_local.session = build_http_session()
    return _thread_local.session

def close_thread_session():
    if hasattr(_thread_local, "session"):
        try:
            _thread_local.session.close()
        except Exception:
            pass
        del _thread_local.session

def is_calendar_valid(year, month, day):
    try:
        datetime(year, month, day)
        return 1900 <= year <= 2099
    except (ValueError, OverflowError):
        return False

def parse_cdjapan_date(raw_text):
    if not raw_text:
        return ""
    text = unicodedata.normalize("NFKC", str(raw_text))
    text = re.sub(r"\s+", " ", text).strip()

    # Match YYYY/MM/DD, YYYY-MM-DD, YYYY.MM.DD, or ISO-8601 with optional whitespace
    m1 = re.search(r"(?<!\d)(19\d\d|20\d\d)\s*[/\-.]\s*(\d{1,2})\s*[/\-.]\s*(\d{1,2})(?!\d)", text)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match isolated compact 8-digit date: YYYYMMDD (must not be part of a longer barcode or serial)
    m_compact = re.search(r"(?<!\d)(19\d\d|20\d\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)", text)
    if m_compact and len(re.sub(r"\D", "", text)) == 8:
        y, m, d = int(m_compact.group(1)), int(m_compact.group(2)), int(m_compact.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match Japanese format YYYY年MM月DD日 or YYYY年MM月
    m2 = re.search(r"(\d{4})\s*年\s*(\d{1,2})\s*月(?:\s*(\d{1,2})\s*日)?", text)
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

    # Match YYYY Month DD (e.g., 2024 October 25 or 2024 Oct. 25)
    m_ymd = re.search(r"\b(19\d\d|20\d\d)\s+([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b", text)
    if m_ymd:
        mon_str = m_ymd.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(m_ymd.group(1)), MONTH_MAP[mon_str], int(m_ymd.group(3))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    # Match YYYY Month (e.g., 2024 October) -> default to 1st of month
    m_ym = re.search(r"\b(19\d\d|20\d\d)\s+([A-Za-z]+)\.?\b", text)
    if m_ym:
        mon_str = m_ym.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m = int(m_ym.group(1)), MONTH_MAP[mon_str]
            if 1 <= m <= 12:
                return f"{y}/{str(m).zfill(2)}/01"

    # Match Month YYYY (e.g., September 2024) -> default to 1st of month
    m5 = re.search(r"\b([A-Za-z]+)\.?,?\s+(19\d\d|20\d\d)\b", text)
    if m5:
        mon_str = m5.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m = int(m5.group(2)), MONTH_MAP[mon_str]
            if 1 <= m <= 12:
                return f"{y}/{str(m).zfill(2)}/01"

    # Match Year & Month with slash or hyphen only (no dots, to prevent matching version numbers): YYYY/MM or YYYY-MM
    m6 = re.search(r"(?<![/\-.\d])\b(19\d\d|20\d\d)\s*[/\-]\s*(\d{1,2})\b(?![/\-.\d])", text)
    if m6:
        y, m = int(m6.group(1)), int(m6.group(2))
        if 1 <= m <= 12:
            return f"{y}/{str(m).zfill(2)}/01"

    return ""
    
# File: repair_catalog_dates.py | Block/Target: fetch_official_date
def fetch_official_date(pid, entry=None, session=None):
    if session is None:
        session = get_thread_session()

    # File: repair_catalog_dates.py | Block/Target: fetch_official_date
    target_candidate = None
    if isinstance(entry, dict):
        url_field = entry.get("url")
        if url_field:
            u_str = str(url_field).strip()
            key_m = re.search(r"[?&]KEY=([^&#]+)", u_str, re.IGNORECASE)
            prod_m = re.search(r"(?:cdjapan\.co\.jp|neowing\.co\.jp)?/product/([^/?#]+)", u_str, re.IGNORECASE)
            if key_m:
                target_candidate = key_m.group(1).strip()
            elif prod_m and ("cdjapan.co.jp" in u_str or "neowing.co.jp" in u_str or u_str.startswith("/product/")):
                target_candidate = prod_m.group(1).strip()

        if not target_candidate:
            # Check canonical catalog numbers first, then product codes and identifiers
            for k in ["cat_no", "catalog_no", "catno", "catalog_number", "catalogNumber", "product_id", "productId", "pid", "id"]:
                val = entry.get(k)
                if val and not is_invalid_identifier(val):
                    target_candidate = str(val).strip()
                    break

    if not target_candidate:
        target_candidate = str(pid).strip()

    if is_invalid_identifier(target_candidate):
        return pid, ""

    key_match = re.search(r"[?&]KEY=([^&#]+)", target_candidate, re.IGNORECASE)
    if key_match:
        clean_pid = key_match.group(1).strip()
    else:
        clean = str(target_candidate).strip()
        clean = re.sub(r"^(?:https?://)?(?:www\.)?(?:cdjapan\.co\.jp|neowing\.co\.jp)/product/", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^/product/", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"^(?:cdjapan|cdj)[-_:]?", "", clean, flags=re.IGNORECASE)
        clean_pid = clean.split("#")[0].split("?")[0].strip("/ \t")

    if not clean_pid or is_invalid_identifier(clean_pid) or clean_pid.startswith("http://") or clean_pid.startswith("https://"):
        return pid, ""
    url = f"https://www.cdjapan.co.jp/product/{clean_pid}"

    try:
        time.sleep(random.uniform(0.6, 1.4))
        res = session.get(url, timeout=(5.0, 15.0))

        if res.status_code == 200:
            is_valid_dest = (
                "cdjapan.co.jp/product/" in res.url or
                "detailview.html" in res.url
            ) and not any(k in res.url for k in ["/department/", "/search.html", "/person/"])
            if not is_valid_dest:
                return pid, ""

            soup = BeautifulSoup(res.text, "html.parser")

            title_tag = soup.find("title")
            if not title_tag or "cdjapan" not in title_tag.get_text().lower():
                return pid, "BLOCKED"

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
                            if "mainEntity" in item:
                                if isinstance(item["mainEntity"], dict):
                                    queue.append(item["mainEntity"])
                                elif isinstance(item["mainEntity"], list):
                                    queue.extend(item["mainEntity"])
                            if "offers" in item:
                                if isinstance(item["offers"], dict):
                                    queue.append(item["offers"])
                                elif isinstance(item["offers"], list):
                                    queue.extend(item["offers"])

                            props = item.get("additionalProperty")
                            if isinstance(props, dict):
                                props = [props]
                            if isinstance(props, list):
                                for prop in props:
                                    if isinstance(prop, dict):
                                        p_name = str(prop.get("name", "")).strip().lower()
                                        if any(k in p_name for k in ["release date", "発売日", "発売予定日", "street date"]) or (
                                            any(k in p_name for k in ["release", "発売"]) and not any(k in p_name for k in ["発売元", "発売国", "発売レーベル", "publisher", "label", "distributor", "press", "event"])
                                        ):
                                            parsed = parse_cdjapan_date(prop.get("value", ""))
                                            if parsed:
                                                return pid, parsed

                            if item.get("releaseDate"):
                                parsed = parse_cdjapan_date(item["releaseDate"])
                                if parsed:
                                    return pid, parsed

                            item_type = str(item.get("@type", "")).lower()
                            if any(k in item_type for k in ["product", "musicalbum", "book", "musicrecording"]):
                                if item.get("datePublished"):
                                    parsed = parse_cdjapan_date(item["datePublished"])
                                    if parsed:
                                        return pid, parsed
                except Exception:
                    pass

            # File: repair_catalog_dates.py | Block/Target: fetch_official_date
            # Strip non-product areas before DOM parsing to prevent extracting dates from related releases
            for noise in soup.find_all(["script", "style", "noscript", "svg", "aside", "nav", "footer"]):
                noise.decompose()
            for noisy_section in soup.find_all(attrs={"class": re.compile(r"sidebar|related|recommend|review|ranking|banner", re.I)}):
                noisy_section.decompose()
            for noisy_section in soup.find_all(attrs={"id": re.compile(r"sidebar|related|recommend|review|ranking|banner", re.I)}):
                noisy_section.decompose()

            # 2. Check Definition Lists & Key-Value Spec Tables
            target_labels = {"release", "release date", "発売", "発売日", "発売予定日", "street date"}
            negative_labels = {"press", "news", "event", "label", "distributor", "country", "発売元", "発売国", "発売レーベル"}
            for label in soup.find_all(["dt", "th", "td"]):
                raw_label_txt = label.get_text(" ", strip=True)
                if not raw_label_txt or len(raw_label_txt) > 35:
                    continue
                label_txt = raw_label_txt.lower()
                if any(neg in label_txt for neg in negative_labels):
                    continue
                norm_label = re.sub(r"\s+", " ", label_txt).rstrip(":")
                is_target = norm_label in target_labels or any(
                    k in label_txt for k in ["release date", "street date", "発売日", "発売予定日"]
                )
                if is_target:
                    val = label.find_next_sibling(["dd", "td"])
                    cand_text = val.get_text(" ", strip=True) if val else raw_label_txt
                    parsed = parse_cdjapan_date(cand_text)
                    if parsed:
                        return pid, parsed

            # 3. Check Canonical OpenGraph / Meta Tags
            meta_selectors = [
                ("meta", {"itemprop": "releaseDate"}),
                ("meta", {"property": "product:release_date"}),
                ("meta", {"property": "music:release_date"}),
                ("meta", {"name": "release_date"}),
                ("meta", {"property": "og:release_date"}),
                ("time", {"itemprop": "releaseDate"})
            ]
            for tag_name, attrs in meta_selectors:
                for el in soup.find_all(tag_name, attrs):
                    raw_val = el.get("content") or el.get("datetime") or el.get_text(" ", strip=True)
                    parsed = parse_cdjapan_date(raw_val)
                    if parsed:
                        return pid, parsed

            # 4. Check Scoped Table Rows
            for tr in soup.find_all("tr"):
                if tr.find(["table"]):
                    continue
                raw_row = tr.get_text(" ", strip=True)
                m = re.search(
                    r"(?<![a-zA-Z])(?<!press\s)(?<!news\s)(?:release(?:\s*date)?|street\s*date|発売予定日|発売日)\s*[:：.\-–]?\s*([^\n\r,;<>()]{4,35})",
                    raw_row,
                    re.IGNORECASE
                )
                if m:
                    parsed = parse_cdjapan_date(m.group(1))
                    if parsed:
                        return pid, parsed

            return pid, ""

        elif res.status_code in (404, 410):
            return pid, ""
        elif res.status_code in (403, 429):
            return pid, "BLOCKED"

    except Exception:
        pass

    return pid, "TIMEOUT"
    
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
    atomic_save_json(PROGRESS_FILE, sorted([str(k) for k in processed_set]))
    
# File: repair_catalog_dates.py | Block/Target: is_valid_date_format
def is_valid_date_format(d_str):
    if not d_str:
        return False
    clean = str(d_str).strip()
    m = re.match(r"^(\d{4})[/\-](\d{2})[/\-](\d{2})$", clean)
    if not m:
        return False
    y, mon, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return is_calendar_valid(y, mon, d) and (1900 <= y <= 2099)

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

    if not os.path.exists(INDEX_FILE):
        print(f"[Error] Index file {INDEX_FILE} not found. Dual-file synchronization requires both {DATA_FILE} and {INDEX_FILE}.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_catalog = len(catalog)
    processed_keys = load_progress()

    # File: repair_catalog_dates.py | Block/Target: pending_items_queue
    def extract_entry_raw_date(item):
        if not isinstance(item, dict):
            return ""
        for alias in ("release_date", "releaseDate", "date", "street_date", "streetDate"):
            val = item.get(alias)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    pending_items = sorted(
        [
            str(pid).strip()
            for pid, val in catalog.items()
            if str(pid).strip() not in processed_keys and isinstance(val, dict) and not is_invalid_identifier(pid)
        ],
        key=lambda pid: (
            0 if not is_valid_date_format(extract_entry_raw_date(catalog.get(pid))) else 1,
            str(pid)
        )
    )
    
    total_pending = len(pending_items)
    audited_count = len(processed_keys.intersection(catalog.keys()))
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

    updated_count = 0
    updated_dates = {}
    preserved_count = 0
    consecutive_blocks = 0
    max_consecutive_blocks = 8
    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pid = {
                executor.submit(fetch_official_date, pid, catalog.get(pid)): pid
                for pid in current_batch
            }

            for idx, future in enumerate(as_completed(future_to_pid), 1):
                try:
                    pid, confirmed_date = future.result()
                except Exception as e:
                    pid = future_to_pid[future]
                    confirmed_date = "TIMEOUT"
                    print(f"   [{idx}/{batch_size}] ⚠ Worker thread error for [{pid}]: {e}", flush=True)

                entry = catalog.get(pid)
                if not isinstance(entry, dict):
                    processed_keys.add(pid)
                    continue
                old_date = str(entry.get("release_date") or entry.get("releaseDate") or entry.get("date") or "").strip()

                if confirmed_date == "BLOCKED":
                    consecutive_blocks += 1
                    print(f"   [{idx}/{batch_size}] ⚠ [{pid}] Request blocked by CDJapan WAF (consecutive blocks: {consecutive_blocks}/{max_consecutive_blocks})", flush=True)
                    if consecutive_blocks >= max_consecutive_blocks:
                        print(f"\n[Warning] {consecutive_blocks} consecutive WAF blocks. Aborting batch early to protect IP reputation.")
                        for f in future_to_pid:
                            f.cancel()
                        break
                    continue
                elif confirmed_date == "TIMEOUT":
                    print(f"   [{idx}/{batch_size}] ⚠ [{pid}] Network timeout / transient error. Will retry in subsequent run.", flush=True)
                    continue

                consecutive_blocks = 0

                # File: repair_catalog_dates.py | Block/Target: main
                if confirmed_date:
                    processed_keys.add(pid)
                    has_canonical_release_date = (catalog[pid].get("release_date") == confirmed_date)
                    if confirmed_date != old_date or not has_canonical_release_date:
                        catalog[pid]["release_date"] = confirmed_date
                        for date_alias in ("releaseDate", "date", "street_date", "streetDate"):
                            if date_alias in catalog[pid]:
                                catalog[pid][date_alias] = confirmed_date
                        updated_dates[pid] = confirmed_date
                        updated_count += 1
                        print(f"   [{idx}/{batch_size}] ✓ [{pid}] {old_date} -> {confirmed_date}", flush=True)
                    else:
                        preserved_count += 1
                else:
                    processed_keys.add(pid)
                    if is_valid_date_format(old_date):
                        preserved_count += 1
                    else:
                        print(f"   [{idx}/{batch_size}] ⚠ [{pid}] Unresolved: CDJapan returned no valid date (catalog has '{old_date}'). Marked audited to unblock queue.", flush=True)

    finally:
        if updated_count > 0:
            if not os.path.exists(INDEX_FILE):
                raise FileNotFoundError(f"[Critical] {INDEX_FILE} disappeared during execution. Aborting to preserve dual-file parity.")

            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    idx_data = json.load(f)

                def extract_product_key_from_url(u):
                    if not u:
                        return ""
                    u_str = str(u).strip()
                    key_m = re.search(r"[?&]KEY=([^&#]+)", u_str, re.IGNORECASE)
                    if key_m:
                        return key_m.group(1).strip()
                    prod_m = re.search(r"cdjapan\.co\.jp/product/([^/?#]+)", u_str, re.IGNORECASE)
                    if prod_m:
                        return prod_m.group(1).strip()
                    return ""

                date_lookup = {}
                id_fields = ["id", "pid", "product_id", "productId", "catalog_id", "catalogId", "cat_no", "catno", "catalog_no", "catalog_number", "catalogNumber", "sku"]

                for p in updated_dates:
                    val = catalog.get(p)
                    if isinstance(val, dict):
                        d = val.get("release_date")
                        if d and is_valid_date_format(d):
                            stripped_p = re.sub(r"^(?:cdjapan[-_:]?|cdj[-_:]?)", "", str(p).strip(), flags=re.IGNORECASE)
                            raw_keys = [p, stripped_p, f"cdjapan-{stripped_p}"]
                            for field in id_fields:
                                f_val = val.get(field)
                                if f_val and not is_invalid_identifier(f_val):
                                    raw_keys.append(str(f_val).strip())
                            clean_u = extract_product_key_from_url(val.get("url"))
                            if clean_u and not is_invalid_identifier(clean_u):
                                raw_keys.append(clean_u)
                            for raw_k in raw_keys:
                                if raw_k is not None and not is_invalid_identifier(raw_k):
                                    k_str = str(raw_k).strip()
                                    date_lookup[k_str] = str(d).strip()
                                    date_lookup[k_str.lower()] = str(d).strip()

                # File: repair_catalog_dates.py | Block/Target: sync_item
                def sync_item(entry, key_id=None):
                    if not isinstance(entry, dict):
                        return
                    # Require concrete product attributes or existing date keys so category containers are never modified
                    has_product_traits = any(k in entry for k in ["price", "cat_no", "catno", "catalog_no", "sku", "jan", "barcode", "release_date", "releaseDate", "date"]) or (
                        ("title" in entry or "name" in entry) and any(k in entry for k in ["id", "pid", "artist", "url"])
                    )
                    if not has_product_traits:
                        return

                    candidate_keys = []
                    if key_id and not is_invalid_identifier(key_id):
                        candidate_keys.append(str(key_id).strip())
                    for field in id_fields:
                        cand = entry.get(field)
                        if cand and not is_invalid_identifier(cand):
                            candidate_keys.append(str(cand).strip())
                    clean_u = extract_product_key_from_url(entry.get("url"))
                    if clean_u and not is_invalid_identifier(clean_u):
                        candidate_keys.append(clean_u)

                    target_date = None
                    for raw_cand in candidate_keys:
                        cand_str = str(raw_cand).strip()
                        if cand_str in date_lookup:
                            target_date = date_lookup[cand_str]
                            break
                        if cand_str.lower() in date_lookup:
                            target_date = date_lookup[cand_str.lower()]
                            break

                    if target_date:
                        entry["release_date"] = target_date
                        for alias in ("releaseDate", "date", "street_date", "streetDate"):
                            if alias in entry:
                                entry[alias] = target_date

                # 2 lines of existing code before:
                def sync_catalog_tree(node, key_id=None):
                    if isinstance(node, dict):

                        sync_item(node, key_id=key_id)
                        for k, v in list(node.items()):
                            if isinstance(v, (dict, list)):

# 2 lines of existing code after:
                                sync_catalog_tree(v, key_id=k)
                    elif isinstance(node, list):
                        for elem in node:
                            if isinstance(elem, (dict, list)):
                                sync_catalog_tree(elem)

                sync_catalog_tree(idx_data)

                # Stage both files atomically to guarantee dual-file parity
                tmp_idx = f"{INDEX_FILE}.tmp"
                tmp_data = f"{DATA_FILE}.tmp"
                with open(tmp_idx, "w", encoding="utf-8") as f_idx:
                    json.dump(idx_data, f_idx, indent=2, ensure_ascii=False)
                with open(tmp_data, "w", encoding="utf-8") as f_data:
                    json.dump(catalog, f_data, indent=2, ensure_ascii=False)

                os.replace(tmp_idx, INDEX_FILE)
                os.replace(tmp_data, DATA_FILE)
            except Exception as e:
                print(f"[Critical] Failed to synchronize catalog files: {e}")
                raise RuntimeError(f"Catalog synchronization failed: {e}")

        save_progress(processed_keys)
    new_audited = len(processed_keys.intersection(catalog.keys()))
    remaining_pending = max(0, total_catalog - new_audited)
    new_progress_pct = (new_audited / total_catalog * 100) if total_catalog > 0 else 0
    new_batches_left = math.ceil(remaining_pending / batch_size) if batch_size > 0 and remaining_pending > 0 else 0

    elapsed_time = time.time() - start_time
    mins, secs = divmod(int(elapsed_time), 60)

    print("\n==========================================================")
    print(f"Batch Complete in {mins}m {secs}s!")
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
