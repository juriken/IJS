"""
IdolJapan.store — Intelligent CDJapan Catalog Healthcheck Engine
Audits URLs, verifies stock availability, checks street dates, and transitions
pre-orders using an automated priority queue and rolling state ledger.
Includes DOM-scoped availability detection and HTTP 429 exponential backoff.
"""

import json
import os
import random
import re
import time
from datetime import datetime
import requests

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

DATA_FILE = "products.json"
STATE_FILE = "scraper_state.json"

DEFAULT_BATCH_SIZE = 500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/",
}

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_date_passed(date_str):
    if not date_str or date_str.lower().strip() == "available now":
        return False
    m = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", date_str)
    if not m:
        return False
    val = (int(m.group(1)) * 10000) + (int(m.group(2)) * 100) + int(m.group(3))
    now = datetime.utcnow()
    today_val = (now.year * 10000) + (now.month * 100) + now.day
    return val <= today_val

def get_target_batch(catalog, state, batch_size):
    history = state.get("healthcheck_history", {})
    all_keys = list(catalog.keys())

    # Priority 1: Items marked OOP (to heal false positives) or pre-orders due for release
    urgent_queue = []
    normal_queue = []

    for pid in all_keys:
        item = catalog[pid]
        avail = item.get("availability", "instock")
        rel_date = item.get("release_date", "")
        last_checked = history.get(pid, 0)

        if avail in ["preorder", "oop"] or is_date_passed(rel_date):
            urgent_queue.append((pid, last_checked))
        else:
            normal_queue.append((pid, last_checked))

    urgent_queue.sort(key=lambda x: x[1])
    normal_queue.sort(key=lambda x: x[1])

    selected = [p[0] for p in urgent_queue[:batch_size]]
    remaining_slots = batch_size - len(selected)

    if remaining_slots > 0:
        selected.extend([p[0] for p in normal_queue[:remaining_slots]])

    return selected

def check_item_url(session, pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            res = session.get(url, headers=HEADERS, timeout=15)
            
            if res.status_code == 429:
                wait_time = attempt * 8 + random.uniform(1.0, 3.0)
                print(f"      [429 Rate Limit] Backing off for {wait_time:.1f}s (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue

            if res.status_code == 200:
                html_text = res.text

                if HAS_BS4:
                    soup = BeautifulSoup(html_text, "html.parser")
                    cart_btn = soup.select_one("button.cart-button, input[value*='Cart'], input[value*='Pre-order'], .btn-cart, #btn_cart")
                    cart_btn_text = cart_btn.get_text().lower() if cart_btn else ""
                    
                    avail_el = soup.select_one(".availability, .item_availability, td.availability, div.detail-availability, table.item-spec")
                    avail_text = avail_el.get_text().lower() if avail_el else ""
                else:
                    # Pure regex fallback if bs4 is ever unavailable
                    btn_match = re.search(r"(?:cart-button|btn-cart|btn_cart)[^>]*>([^<]*)", html_text, re.IGNORECASE)
                    cart_btn_text = btn_match.group(1).lower() if btn_match else ("cart" if "btn-cart" in html_text else "")
                    
                    avail_match = re.search(r'<td[^>]*class="[^"]*availability[^"]*"[^>]*>(.*?)</td>', html_text, re.IGNORECASE | re.DOTALL)
                    avail_text = avail_match.group(1).lower() if avail_match else ""

                is_oop = (
                    "out of print" in avail_text or
                    "no longer available" in avail_text or
                    "discontinued" in avail_text or
                    "廃盤" in avail_text or
                    "取扱終了" in avail_text or
                    "sold out" in avail_text
                )

                if cart_btn_text and not is_oop:
                    if "pre-order" in cart_btn_text or "pre-order" in avail_text or "予約" in avail_text:
                        return 200, False, True
                    return 200, False, False

                is_preorder = "pre-order" in avail_text or "予約" in avail_text
                return 200, is_oop, is_preorder

            return res.status_code, False, False

        except requests.RequestException:
            if attempt < max_retries:
                time.sleep(2.0)
                continue
            return 0, False, False

    return 429, False, False

def main():
    print("==========================================")
    print("Starting CDJapan Catalog Priority Health Check")
    print("==========================================")

    catalog = load_json(DATA_FILE)
    if not catalog:
        print(f"Error: {DATA_FILE} is empty or missing.")
        return

    state = load_json(STATE_FILE)
    if "healthcheck_history" not in state:
        state["healthcheck_history"] = {}

    env_batch = os.environ.get("HEALTHCHECK_BATCH_SIZE", "").strip()
    batch_size = int(env_batch) if env_batch.isdigit() and int(env_batch) > 0 else DEFAULT_BATCH_SIZE

    target_pids = get_target_batch(catalog, state, batch_size)
    total_skus = len(catalog)

    print(f"Auditing Priority Batch of {len(target_pids)} releases out of {total_skus:,} total SKUs...")

    session = requests.Session()
    oop_count = 0
    in_stock_recovered = 0
    preorder_count = 0
    error_count = 0
    now_epoch = int(time.time())

    for idx, pid in enumerate(target_pids, 1):
        item = catalog[pid]
        current_avail = item.get("availability", "instock")
        title = item.get("title", "")[:32]

        status, is_oop, is_preorder = check_item_url(session, pid)
        state["healthcheck_history"][pid] = now_epoch

        if status == 200:
            if is_oop:
                if current_avail != "oop":
                    item["availability"] = "oop"
                oop_count += 1
                print(f"[{idx}/{len(target_pids)}] 📦 OOP: {pid} — {title}")
            elif is_preorder:
                if current_avail != "preorder":
                    item["availability"] = "preorder"
                preorder_count += 1
                print(f"[{idx}/{len(target_pids)}] ⏳ Pre-Order Active: {pid} — {title}")
            else:
                if current_avail != "instock":
                    item["availability"] = "instock"
                    in_stock_recovered += 1
                    print(f"[{idx}/{len(target_pids)}] 🔄 Restored to In-Stock: {pid} — {title}")
                else:
                    print(f"[{idx}/{len(target_pids)}] ✅ In Stock: {pid} (Status: 200)")
        elif status == 404:
            item["availability"] = "oop"
            oop_count += 1
            print(f"[{idx}/{len(target_pids)}] ❌ 404 Not Found (Marked OOP): {pid}")
        else:
            error_count += 1
            print(f"[{idx}/{len(target_pids)}] ⚠️ Warning: {pid} returned HTTP {status}")

        time.sleep(random.uniform(1.1, 1.8))

    save_json(DATA_FILE, catalog)
    state["last_healthcheck"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_json(STATE_FILE, state)

    print("==========================================")
    print(f"Audit Finished: {len(target_pids)} Checked | {oop_count} Confirmed OOP | {in_stock_recovered} Restored to In-Stock | {preorder_count} Active Pre-orders | {error_count} Errors")
    print("==========================================")

if __name__ == "__main__":
    main()
