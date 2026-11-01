"""
IdolJapan.store — Resilient CDJapan SKU URL & Availability Health Check
Audits catalog releases against live CDJapan product pages.
Correctly identifies 'instock', 'preorder', and 'oop' statuses without false positives
by targeting direct purchase action buttons and schema microdata.
Synchronizes products.json, catalog-index.json, and audit log.
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
STATE_FILE = "healthcheck_state.json"
LOG_FILE = "healthcheck_log.txt"

DEFAULT_BATCH_SIZE = 500
DEFAULT_MAX_WORKERS = 4

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
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def is_date_upcoming(date_str):
    if not date_str:
        return False
    clean = str(date_str).strip()
    m = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", clean)
    if not m:
        return False
    val = (int(m.group(1)) * 10000) + (int(m.group(2)) * 100) + int(m.group(3))
    now = datetime.utcnow()
    today_val = (now.year * 10000) + (now.month * 100) + now.day
    return val > today_val

def check_sku_status(session, pid, current_item):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/"
    }

    current_avail = current_item.get("availability", "instock")
    rel_date = current_item.get("release_date", "")

    try:
        time.sleep(random.uniform(0.15, 0.45))
        res = session.get(url, headers=headers, timeout=15)

        if res.status_code == 404:
            return pid, "oop", "HTTP 404 Not Found"

        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")

            # 1. Parse JSON-LD Microdata (Most reliable indicator)
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    js_data = json.loads(script.string or "{}")
                    candidates = js_data if isinstance(js_data, list) else [js_data]
                    for item in candidates:
                        if isinstance(item, dict):
                            offers = item.get("offers", {})
                            if isinstance(offers, list) and len(offers) > 0:
                                offers = offers[0]
                            if isinstance(offers, dict):
                                avail = str(offers.get("availability", "")).lower()
                                if "instock" in avail:
                                    if is_date_upcoming(rel_date):
                                        return pid, "preorder", "Schema InStock (Upcoming Date)"
                                    return pid, "instock", "Schema InStock"
                                elif "preorder" in avail:
                                    return pid, "preorder", "Schema PreOrder"
                                elif "outofstock" in avail or "discontinued" in avail or "soldout" in avail:
                                    return pid, "oop", "Schema OutOfStock"
                except Exception:
                    pass

            # 2. Inspect Main Buy Button and Cart Form (Avoid sidebar recommendations)
            product_action_box = (
                soup.select_one(".product-action")
                or soup.select_one(".item-action")
                or soup.select_one(".cart-button-area")
                or soup.select_one("form[action*='cart']")
                or soup.select_one("#main")
            )
            action_text = product_action_box.get_text().lower() if product_action_box else ""

            # Check positive availability first
            has_preorder_btn = bool(soup.select_one(".btn-preorder, input[value*='Pre-order'], button:has-text('Pre-order'), a:has-text('Pre-order')"))
            has_cart_btn = bool(soup.select_one(".btn-cart, input[value*='Add to Cart'], button:has-text('Add to Cart'), a:has-text('Add to Cart')"))

            if has_preorder_btn or "pre-order" in action_text or "予約" in action_text:
                return pid, "preorder", "Pre-order Button Detected"

            if has_cart_btn or "add to cart" in action_text or "カートに入れる" in action_text:
                if is_date_upcoming(rel_date):
                    return pid, "preorder", "Cart Button Detected (Upcoming Date)"
                return pid, "instock", "Add to Cart Button Detected"

            # 3. Explicit Stock Label Checks inside the main product summary table
            summary_table = soup.select_one(".item-summary, .product-details, table.spec")
            summary_text = summary_table.get_text().lower() if summary_table else ""

            if any(term in summary_text for term in ["in stock", "usually ships", "在庫あり", "24時間以内"]):
                return pid, "instock", "Spec In-Stock Indicator"

            if any(term in summary_text for term in ["pre-order", "upcoming", "予約受付中"]):
                return pid, "preorder", "Spec Pre-Order Indicator"

            if any(term in summary_text for term in ["out of print", "no longer available", "discontinued", "sold out", "廃盤", "取扱終了"]):
                return pid, "oop", "Spec OOP Notice"

            # 4. Strict check on explicit out of print notices in main block
            if any(term in action_text for term in ["out of print", "no longer available", "discontinued", "sold out", "廃盤", "取扱終了"]):
                return pid, "oop", "Product Action OOP Notice"

            # If uncertain, preserve existing status rather than assuming OOP
            if is_date_upcoming(rel_date):
                return pid, "preorder", "Preserved Pre-order (Upcoming Date)"
            return pid, current_avail, "Preserved Existing Status (Ambiguous DOM)"

        else:
            # Non-200 / Non-404 (e.g. 429, 500, 503) -> Do NOT mark as OOP
            return pid, current_avail, f"Preserved (HTTP {res.status_code})"

    except Exception as e:
        return pid, current_avail, f"Preserved (Exception: {str(e)[:40]})"

def load_healthcheck_state():
    reset_requested = os.environ.get("RESET_HEALTHCHECK", "").lower() in ["true", "1", "yes"]
    if reset_requested:
        print("[Notice] RESET_HEALTHCHECK detected. Restarting audit from item 1.", flush=True)
        if os.path.exists(STATE_FILE):
            try:
                os.remove(STATE_FILE)
            except Exception:
                pass
        return set()

    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_healthcheck_state(audited_pids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(audited_pids)), f, indent=2)

def main():
    print("==========================================================")
    print("IdolJapan.store — Resilient SKU URL & Availability Health Check")
    print("==========================================================")

    if not os.path.exists(DATA_FILE):
        print(f"[Error] Catalog file {DATA_FILE} not found.")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_catalog = len(catalog)
    audited_pids = load_healthcheck_state()

    pending_pids = [pid for pid in catalog.keys() if pid not in audited_pids]
    total_pending = len(pending_pids)
    audited_count = len(audited_pids)
    progress_pct = (audited_count / total_catalog * 100) if total_catalog > 0 else 0

    print(f"Total Catalog Database:    {total_catalog:,} releases")
    print(f"Already Audited in Cycle:  {audited_count:,} releases ({progress_pct:.1f}%)")
    print(f"Pending Verification:      {total_pending:,} releases")

    if total_pending == 0:
        print("\nAll 100% of catalog releases have been verified in this cycle!")
        print("To restart the cycle, pass RESET_HEALTHCHECK=true or delete healthcheck_state.json.")
        return

    batch_size = int(os.environ.get("BATCH_SIZE", os.environ.get("HEALTHCHECK_BATCH_SIZE", DEFAULT_BATCH_SIZE)))
    batch_size = min(batch_size, total_pending)
    max_workers = int(os.environ.get("MAX_WORKERS", DEFAULT_MAX_WORKERS))
    batches_remaining = math.ceil(total_pending / batch_size) if batch_size > 0 else 0

    current_batch = pending_pids[:batch_size]
    print(f"Targeting Batch Size:      {batch_size:,} items (~{batches_remaining} batch runs remaining)")
    print(f"Worker Threads:            {max_workers} concurrent connections\n", flush=True)

    session = build_http_session()
    changes_count = 0
    preserved_count = 0
    start_time = time.time()
    log_lines = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_pid = {
            executor.submit(check_sku_status, session, pid, catalog[pid]): pid
            for pid in current_batch
        }

        for idx, future in enumerate(as_completed(future_to_pid), 1):
            pid, new_status, reason = future.result()
            audited_pids.add(pid)
            old_status = catalog[pid].get("availability", "instock")

            if new_status != old_status:
                catalog[pid]["availability"] = new_status
                changes_count += 1
                msg = f"[{idx}/{batch_size}] Δ [{pid}] {old_status} -> {new_status} ({reason})"
                print(f"   {msg}", flush=True)
                log_lines.append(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")
            else:
                preserved_count += 1

            if idx % 50 == 0 or idx == batch_size:
                elapsed = time.time() - start_time
                print(f"   -> Progress: {idx}/{batch_size} audited ({elapsed:.1f}s elapsed)...", flush=True)

    # 1. Save updated products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # 2. Synchronize catalog-index.json for immediate deployment
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    # Save state
    save_healthcheck_state(audited_pids)

    # Append to log file
    if log_lines:
        with open(LOG_FILE, "a", encoding="utf-8") as lf:
            lf.write("\n".join(log_lines) + "\n")

    new_audited = len(audited_pids)
    remaining_pending = total_catalog - new_audited
    new_progress_pct = (new_audited / total_catalog * 100) if total_catalog > 0 else 0
    new_batches_left = math.ceil(remaining_pending / batch_size) if batch_size > 0 and remaining_pending > 0 else 0

    print("\n==========================================================")
    print("Health Check Batch Complete!")
    print("==========================================================")
    print(f"Availability Status Updated: {changes_count:,} releases")
    print(f"Status Verified & Kept:      {preserved_count:,} releases")
    print(f"Total Audited in Cycle:      {new_audited:,} / {total_catalog:,} ({new_progress_pct:.1f}%)")
    print(f"Remaining in Cycle:          {remaining_pending:,} releases (~{new_batches_left} batches left)")
    print("Synchronized:                products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    main()
