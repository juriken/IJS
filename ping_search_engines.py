"""
IdolJapan.store — Search Engine Rapid Indexing Dispatcher
Submits priority franchise hubs & newest releases to IndexNow (Bing/Yandex/Naver),
ensures root key verification, and pings sitemap discovery endpoints.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HOST = "idoljapan.store"
INDEXNOW_KEY = "a1b2c3d4e5f67890123456789abcdef0"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"
API_ENDPOINT = "https://api.indexnow.org/indexnow"
CATALOG_INDEX_FILE = "catalog-index.json"
MAX_SUBMIT_URLS = 100

def ensure_indexnow_key_file():
    """Guarantees the IndexNow verification text file exists for edge deployment."""
    key_filename = f"{INDEXNOW_KEY}.txt"
    if not os.path.exists(key_filename):
        try:
            with open(key_filename, "w", encoding="utf-8") as f:
                f.write(INDEXNOW_KEY)
            print(f"Created IndexNow verification key file: {key_filename}")
        except Exception as e:
            print(f"Notice creating key file: {e}")

def load_priority_urls():
    urls = [
        f"https://{HOST}/",
        f"https://{HOST}/sitemap.xml",
        f"https://{HOST}/feed.xml"
    ]
    
    # Priority franchise category filters
    franchises = [
        "Hello!+Project",
        "Up-Front+Alumni",
        "AKB48+Group",
        "Sakamichi+Series",
        "Stardust+Planet",
        "=LOVE+/+Sister+Groups",
        "KAWAII+LAB.",
        "Modern+Idols",
        "Babymetal"
    ]
    for cat in franchises:
        urls.append(f"https://{HOST}/?cat={cat}")

    # Inject latest 100 product deep links sorted by newest street date
    if os.path.exists(CATALOG_INDEX_FILE):
        try:
            with open(CATALOG_INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = list(data.values()) if isinstance(data, dict) else data
                items.sort(key=lambda x: str(x.get("release_date", "")), reverse=True)
                
                count = 0
                for it in items:
                    pid = it.get("id")
                    if pid:
                        urls.append(f"https://{HOST}/?id={pid}")
                        count += 1
                        if count >= MAX_SUBMIT_URLS:
                            break
        except Exception as e:
            print(f"Notice: Could not read {CATALOG_INDEX_FILE} for URL list: {e}")

    return urls

def ping_standard_endpoints():
    sitemap_url = f"https://{HOST}/sitemap.xml"
    endpoints = [
        f"https://www.google.com/ping?sitemap={urllib.parse.quote_plus(sitemap_url)}",
        f"https://www.bing.com/ping?sitemap={urllib.parse.quote_plus(sitemap_url)}"
    ]
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "IdolJapan-Pinger/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"  [OK] Pinged {url.split('?')[0]} (Status: {resp.status})")
        except Exception as e:
            # Google permanently deprecated /ping; HTTP 404 is normal and should not halt execution
            pass

def submit_indexnow():
    print("==========================================")
    print(f"Starting IndexNow Notification for: {HOST}")
    print("==========================================")

    ensure_indexnow_key_file()
    ping_standard_endpoints()

    url_list = load_priority_urls()
    print(f"Submitting {len(url_list)} priority URLs to IndexNow gateway...")

    payload = {
        "host": HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": url_list
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_ENDPOINT,
        data=req_data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "IdolJapan-IndexNow/2.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.getcode()
            if status in [200, 202]:
                print(f"IndexNow: {len(url_list)} URLs successfully accepted (HTTP {status}).")
            else:
                print(f"IndexNow: Gateway responded with HTTP {status}.")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"IndexNow HTTP Notice ({e.code}): {error_body}")
    except Exception as err:
        print(f"IndexNow Network notice: {err}")

    print("==========================================")
    print("Search engine synchronization routine complete.")
    print("==========================================")

if __name__ == "__main__":
    submit_indexnow()
