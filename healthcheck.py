"""
IdolJapan.store — Intelligent CDJapan Catalog Healthcheck Engine
Audits URLs, verifies stock availability, checks street dates, and transitions
pre-orders using an automated priority queue and rolling state ledger.
"""

import json
import os
import random
import re
import time
from datetime import datetime
import requests

DATA_FILE = "products.json"
STATE_FILE = "scraper_state.json"

# Configurable batch size: 500 items takes ~5-7 minutes safely
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

    # Priority 1: Active pre-orders or items whose street date has arrived
    preorders = []
    # Priority 2: In-stock items never checked or checked longest ago
    normal_queue = []

    for pid in all_keys:
        item = catalog[pid]
        avail = item.get("availability", "instock")
        rel_date = item.get("release_date", "")

        last_checked = history.get(pid, 0)

        if avail == "preorder" or is_date_passed(rel_date):
            preorders.append((pid, last_checked))
        else:
            normal_queue.append((pid, last_checked))

    # Sort each tier by oldest checked first
    preorders.sort(key=lambda x: x[1])
    normal_queue.sort(key=lambda x: x[1])

    selected = [p[0] for p in preorders[:batch_size]]
    remaining_slots = batch_size - len(selected)

    if remaining_slots > 0:
        selected.extend([p[0] for p in normal_queue[:remaining_slots]])

    return selected

def check_item_url(session, pid):
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    try:
        res = session.get(url, headers=HEADERS, timeout=12)
        if res.status_code == 200:
            text = res.text.lower()
            is_oop = (
                "out of print" in text or
                "no longer available" in text or
                "sold out" in text or
                "廃盤" in text or
                "取扱終了" in text or
                "archive" in text
            )
            is_preorder = "pre-order" in text or "予約" in text
            return 200, is_oop, is_preorder
        return res.status_code, False, False
    except requests.RequestException:
        return 0, False, False

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
    transition_count = 0
    error_count = 0
    now_epoch = int(time.time())

    for idx, pid in enumerate(target_pids, 1):
        item = catalog[pid]
        current_avail = item.get("availability", "instock")
        title = item.get("title", "")[:35]

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
                    transition_count += 1
                print(f"[{idx}/{len(target_pids)}] ⏳ Pre-Order Active: {pid}")
            else:
                if current_avail != "instock":
                    item["availability"] = "instock"
                    transition_count += 1
                print(f"[{idx}/{len(target_pids)}] ✅ In Stock: {pid} (Status: 200)")
        elif status == 404:
            item["availability"] = "oop"
            oop_count += 1
            print(f"[{idx}/{len(target_pids)}] ❌ 404 Not Found (Marked OOP): {pid}")
        else:
            error_count += 1
            print(f"[{idx}/{len(target_pids)}] ⚠️ Warning: {pid} returned HTTP {status}")

        # Gentle cadence to respect CDJapan edge rate-limits
        time.sleep(random.uniform(0.4, 0.9))

    save_json(DATA_FILE, catalog)
    state["last_healthcheck"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_json(STATE_FILE, state)

    print("==========================================")
    print(f"Audit Finished: {len(target_pids)} Checked | {oop_count} Marked OOP | {transition_count} Status Transitions | {error_count} Errors")
    print("==========================================")

if __name__ == "__main__":
    main()
