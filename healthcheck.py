"""
IdolJapan.store — Catalog Healthcheck & SKU Availability Auditor
Tracks ongoing audit cycles across 19,000+ items, identifies out-of-print
transitions, updates live pricing, and reports exact audit progress.
"""

import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
STATE_FILE = "healthcheck_state.json"
LOG_FILE = "healthcheck_log.txt"

# Default batch size per execution (override with BATCH_SIZE environment variable)
DEFAULT_BATCH_SIZE = 500

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"
]

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Warning] Failed to load {filepath}: {e}")
            return {}
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_or_init_state(total_catalog_size):
    state = load_json(STATE_FILE)
    if not state or "audited_ids" not in state:
        state = {
            "cycle": 1,
            "cycle_started_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            "audited_ids": [],
            "total_cycles_completed": 0,
            "last_run_timestamp": ""
        }
    return state

def get_progress_bar(percentage, width=24):
    filled = int(width * (percentage / 100))
    bar = "=" * filled + "-" * (width - filled)
    return f"[{bar}] {percentage:.1f}%"

def audit_single_product(session, item):
    pid = item.get("id")
    url = f"https://www.cdjapan.co.jp/product/{pid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/"
    }

    try:
        res = session.get(url, headers=headers, timeout=12)
        if res.status_code == 404:
            return {"status": "oop", "price": item.get("price"), "changed": item.get("availability") != "oop"}

        if res.status_code != 200:
            return {"status": item.get("availability", "instock"), "price": item.get("price"), "changed": False}

        soup = BeautifulSoup(res.text, "html.parser")
        body_text = soup.get_text().lower()

        # Availability detection
        if any(term in body_text for term in ["out of print", "no longer available", "sold out", "archive", "廃盤", "取扱終了"]):
            new_avail = "oop"
        elif any(term in body_text for term in ["pre-order", "preorder", "予約"]):
            new_avail = "preorder"
        else:
            new_avail = "instock"

        # Price update
        price_num = item.get("price_num", 0)
        price_str = item.get("price", "Check CDJapan")
        price_el = soup.select_one(".price, .item-price, .price-value")
        if price_el:
            p_match = re.search(r"(\d[\d,]*\s*(?:yen|jpy|円)?)", price_el.get_text(), re.IGNORECASE)
            if p_match:
                cleaned_num = re.sub(r"[^\d]", "", p_match.group(1))
                if cleaned_num:
                    price_num = int(cleaned_num)
                    price_str = f"¥{price_num:,}"

        changed = (new_avail != item.get("availability")) or (price_num != item.get("price_num"))
        return {
            "status": new_avail,
            "price": price_str,
            "price_num": price_num,
            "changed": changed
        }

    except Exception:
        return {"status": item.get("availability", "instock"), "price": item.get("price"), "changed": False}

def main():
    if not os.path.exists(DATA_FILE):
        print(f"[Error] Catalog database {DATA_FILE} not found.")
        sys.exit(1)

    catalog = load_json(DATA_FILE)
    total_skus = len(catalog)

    if total_skus == 0:
        print("[Error] Catalog is empty.")
        sys.exit(1)

    # Load persistent audit progress
    state = load_or_init_state(total_skus)
    audited_set = set(state.get("audited_ids", []))

    # Detect if previous cycle finished
    all_catalog_pids = set(catalog.keys())
    remaining_pids = [pid for pid in catalog.keys() if pid not in audited_set]

    if not remaining_pids:
        # Full cycle completed: roll over to the next cycle
        state["cycle"] += 1
        state["total_cycles_completed"] += 1
        state["cycle_started_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        state["audited_ids"] = []
        audited_set.clear()
        remaining_pids = list(catalog.keys())
        print(f"\n[Info] Full catalog audit cycle completed! Starting Cycle #{state['cycle']}.")

    # Configure batch sizing
    batch_size = int(os.environ.get("BATCH_SIZE", DEFAULT_BATCH_SIZE))
    batch_size = min(batch_size, len(remaining_pids))

    current_batch_pids = remaining_pids[:batch_size]

    already_audited_count = len(audited_set)
    remaining_count_before = len(remaining_pids)
    progress_pct_before = (already_audited_count / total_skus) * 100
    batches_left_before = math.ceil(remaining_count_before / batch_size) if batch_size > 0 else 0

    print("==========================================================")
    print("IdolJapan.store — Continuous Catalog Healthcheck Monitor")
    print("==========================================================")
    print(f"Total Catalog Database:    {total_skus:,} active SKUs")
    print(f"Current Audit Cycle:       Cycle #{state['cycle']}")
    print(f"Already Audited in Cycle:  {already_audited_count:,} releases ({progress_pct_before:.1f}%)")
    print(f"Remaining Left to Audit:   {remaining_count_before:,} releases")
    print(f"Batches Remaining:         ~{batches_left_before:,} batch runs")
    print(f"Current Run Target:        {batch_size:,} releases")
    print(f"Cycle Progress Before Run: {get_progress_bar(progress_pct_before)}")
    print("==========================================================\n")

    session = requests.Session()
    updated_items = 0
    status_changes = []

    start_time = time.time()

    for idx, pid in enumerate(current_batch_pids, 1):
        item = catalog[pid]
        result = audit_single_product(session, item)

        old_status = item.get("availability", "instock")
        new_status = result["status"]

        if result["changed"]:
            updated_items += 1
            item["availability"] = new_status
            if "price" in result:
                item["price"] = result["price"]
            if "price_num" in result:
                item["price_num"] = result["price_num"]
            status_changes.append(f"[{pid}] {item.get('title', '')[:35]} ({old_status} -> {new_status})")

        item["last_healthcheck"] = datetime.utcnow().strftime("%Y-%m-%d")
        audited_set.add(pid)

        # Print progress tick every 50 items
        if idx % 50 == 0 or idx == batch_size:
            elapsed = time.time() - start_time
            print(f"   -> Verified {idx}/{batch_size} SKUs in this run ({elapsed:.1f}s elapsed)...", flush=True)

        time.sleep(random.uniform(0.1, 0.25))

    # Calculate post-run metrics
    already_audited_after = len(audited_set)
    remaining_after = total_skus - already_audited_after
    progress_pct_after = (already_audited_after / total_skus) * 100
    batches_left_after = math.ceil(remaining_after / batch_size) if batch_size > 0 and remaining_after > 0 else 0

    # Save state
    state["audited_ids"] = list(audited_set)
    state["last_run_timestamp"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_json(STATE_FILE, state)

    # Save updated catalog and index
    save_json(DATA_FILE, catalog)
    save_json(INDEX_FILE, catalog)

    # Write log record
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(f"\n--- Healthcheck Batch [{state['last_run_timestamp']}] ---\n")
        log.write(f"Audited: {batch_size} | Modified: {updated_items} | Cycle Progress: {already_audited_after}/{total_skus} ({progress_pct_after:.1f}%)\n")
        for sc in status_changes[:10]:
            log.write(f"  * {sc}\n")

    print("\n==========================================================")
    print("Healthcheck Batch Completed Successfully")
    print("==========================================================")
    print(f"Audited in This Run:       {batch_size:,} releases")
    print(f"Discrepancies Updated:     {updated_items:,} releases")
    print(f"Total Audited in Cycle:    {already_audited_after:,} / {total_skus:,} releases")
    print(f"Remaining to Audit:        {remaining_after:,} releases")
    print(f"Estimated Batches Left:    ~{batches_left_after:,} runs remaining")
    print(f"New Cycle Progress:        {get_progress_bar(progress_pct_after)}")
    print("==========================================================")

if __name__ == "__main__":
    main()
