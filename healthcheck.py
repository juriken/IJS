import os
import sys
import json
import random
import time
import requests

PRODUCTS_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
SAMPLE_SIZE = 60
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def run_health_check():
    print("==========================================")
    print("Starting CDJapan Affiliate URL Health Check")
    print("==========================================")

    if not os.path.exists(PRODUCTS_FILE):
        print(f"❌ Error: {PRODUCTS_FILE} not found.")
        sys.exit(1)

    with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    all_keys = list(products.keys())
    total_products = len(all_keys)
    sample_keys = random.sample(all_keys, min(SAMPLE_SIZE, total_products))

    print(f"Auditing sample of {len(sample_keys)} releases out of {total_products} total SKUs...")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    broken_urls = 0
    updated_oop = 0

    for idx, key in enumerate(sample_keys, 1):
        item = products[key]
        target_url = item.get("affiliate_url") or item.get("url")

        if not target_url:
            print(f"[{idx}/{len(sample_keys)}] ⚠️ Item {key} has no URL.")
            broken_urls += 1
            continue

        try:
            resp = session.get(target_url, timeout=12, allow_redirects=True, stream=True)
            status_code = resp.status_code

            is_dead_redirect = resp.url.strip("/").endswith("cdjapan.co.jp")
            
            if status_code in [404, 410] or is_dead_redirect:
                print(f"[{idx}/{len(sample_keys)}] ⚠️ Dead/Archived release found: {key} ({item.get('title')}) -> Status: {status_code}")
                if item.get("availability") != "oop":
                    item["availability"] = "oop"
                    item["price"] = "Out of Print"
                    updated_oop += 1
            else:
                print(f"[{idx}/{len(sample_keys)}] ✅ Verified: {key} (Status: {status_code})")

        except Exception as err:
            print(f"[{idx}/{len(sample_keys)}] ⚠️ Network timeout on {key}: {err}")
            broken_urls += 1

        time.sleep(0.5)

    if updated_oop > 0:
        print(f"\nPersisting {updated_oop} status updates to {PRODUCTS_FILE} and {INDEX_FILE}...")
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        summary_index = {}
        for pid, it in products.items():
            summary_index[pid] = {
                "id": it.get("id"),
                "title": it.get("title"),
                "artist": it.get("artist"),
                "category": it.get("category"),
                "price_num": it.get("price_num", 0),
                "price": it.get("price", ""),
                "release_date": it.get("release_date", ""),
                "availability": it.get("availability", "instock"),
                "image": it.get("image", "")
            }

        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(summary_index, f, ensure_ascii=False, separators=(',', ':'))

    print("==========================================")
    print(f"Audit Finished: {len(sample_keys)} Checked | {updated_oop} Marked OOP | {broken_urls} Errors")
    print("==========================================")

if __name__ == "__main__":
    run_health_check()
