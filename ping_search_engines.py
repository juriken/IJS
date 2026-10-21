import sys
import urllib.parse
import urllib.request

SITEMAP_URL = "https://idoljapan.store/sitemap.xml"

# Endpoints for search engine notification
SEARCH_ENGINES = [
    {
        "name": "Google",
        "url": f"https://www.google.com/ping?sitemap={urllib.parse.quote(SITEMAP_URL)}"
    },
    {
        "name": "Bing / IndexNow",
        "url": f"https://www.bing.com/ping?sitemap={urllib.parse.quote(SITEMAP_URL)}"
    }
]

def ping_engines():
    print("==========================================")
    print(f"Notifying Search Engines for: {SITEMAP_URL}")
    print("==========================================")
    
    headers = {
        "User-Agent": "IdolJapan-SitemapNotifier/1.0 (+https://idoljapan.store)"
    }
    
    for engine in SEARCH_ENGINES:
        try:
            req = urllib.request.Request(engine["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                status = response.getcode()
                print(f"✅ {engine['name']}: Ping delivered successfully (HTTP {status}).")
        except Exception as err:
            # Pings are non-critical notifications; log warnings without failing CI
            print(f"⚠️ {engine['name']}: Ping request returned notice: {err}")

    print("==========================================")
    print("Search engine notification step complete.")
    print("==========================================")

if __name__ == "__main__":
    ping_engines()
