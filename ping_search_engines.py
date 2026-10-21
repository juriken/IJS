import json
import os
import sys
import urllib.error
import urllib.request

HOST = "idoljapan.store"
INDEXNOW_KEY = "a1b2c3d4e5f67890123456789abcdef0"
KEY_LOCATION = f"https://{HOST}/{INDEXNOW_KEY}.txt"
API_ENDPOINT = "https://api.indexnow.org/indexnow"
CATALOG_INDEX_FILE = "catalog-index.json"
MAX_SUBMIT_URLS = 100

def load_recent_catalog_urls():
    urls = [
        f"https://{HOST}/",
        f"https://{HOST}/sitemap.xml"
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

    # Inject latest product deep links
    if os.path.exists(CATALOG_INDEX_FILE):
        try:
            with open(CATALOG_INDEX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                count = 0
                for pid in data.keys():
                    urls.append(f"https://{HOST}/?id={pid}")
                    count += 1
                    if count >= MAX_SUBMIT_URLS:
                        break
        except Exception as e:
            print(f"⚠️ Notice: Could not read {CATALOG_INDEX_FILE} for URL list: {e}")

    return urls

def submit_indexnow():
    print("==========================================")
    print(f"Starting IndexNow Notification for: {HOST}")
    print("==========================================")
    print("ℹ️ Note on Google: Googlebot reads sitemaps via robots.txt and <lastmod> tags.")
    print("   Google deprecated /ping endpoints permanently (HTTP 404 is by design).")
    print("   IndexNow directly notifies Bing, Yandex, Seznam, and Naver.\n")

    url_list = load_recent_catalog_urls()
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
                print(f"✅ IndexNow: URLs successfully accepted (HTTP {status}).")
            else:
                print(f"ℹ️ IndexNow: Gateway responded with HTTP {status}.")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"⚠️ IndexNow HTTP Error {e.code}: {error_body}")
    except Exception as err:
        print(f"⚠️ IndexNow Network notice: {err}")

    print("==========================================")
    print("Search engine synchronization routine complete.")
    print("==========================================")

if __name__ == "__main__":
    submit_indexnow()
