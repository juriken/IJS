"""
IdolJapan.store — Search Engine Rapid Indexing Dispatcher
Submits newly added/updated items to IndexNow (Bing/Yandex/Naver) and pings standard sitemap discovery.
"""

import os
import json
import urllib.request
import urllib.parse

BASE_URL = "https://idoljapan.store"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
CATALOG_INDEX = "catalog-index.json"
PRODUCTS_FILE = "products.json"

def ping_standard_sitemaps():
    endpoints = [
        f"https://www.google.com/ping?sitemap={urllib.parse.quote_plus(SITEMAP_URL)}",
        f"https://www.bing.com/ping?sitemap={urllib.parse.quote_plus(SITEMAP_URL)}"
    ]
    
    print("Pinging sitemap discovery endpoints...")
    for url in endpoints:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "IdolJapan-SitemapPinger/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"  [OK] Pinged {url.split('?')[0]} (Status: {resp.status})")
        except Exception as e:
            print(f"  [Notice] Standard ping note on {url.split('?')[0]}: {e}")

def submit_indexnow_batch():
    # Load recent SKUs
    target_items = []
    source_file = CATALOG_INDEX if os.path.exists(CATALOG_INDEX) else PRODUCTS_FILE
    
    if os.path.exists(source_file):
        try:
            with open(source_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = list(data.values()) if isinstance(data, dict) else data
                # Sort by newest release date and grab the top 100
                items.sort(key=lambda x: str(x.get("release_date", "")), reverse=True)
                target_items = items[:100]
        except Exception as e:
            print(f"Warning loading items for IndexNow: {e}")

    if not target_items:
        print("No items found to submit to IndexNow.")
        return

    url_list = [f"{BASE_URL}/?id={it['id']}" for it in target_items if it.get("id")]
    url_list.append(BASE_URL)
    url_list.append(f"{BASE_URL}/sitemap.xml")

    payload = {
        "host": "idoljapan.store",
        "key": "idoljapan_indexnow_key",
        "keyLocation": f"{BASE_URL}/idoljapan_indexnow_key.txt",
        "urlList": url_list
    }

    print(f"Submitting {len(url_list)} URLs to IndexNow (Bing/Yandex/Naver)...")
    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.indexnow.org/IndexNow",
            data=req_data,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "IdolJapan-Indexer/1.0"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            print(f"  [OK] IndexNow API accepted batch submission (Status: {response.status}).")
    except Exception as err:
        print(f"  [Notice] IndexNow submission note: {err}")

def main():
    ping_standard_sitemaps()
    submit_indexnow_batch()
    print("Search engine notification step complete.")

if __name__ == "__main__":
    main()
