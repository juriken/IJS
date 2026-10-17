import json
import os
import time
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

TARGET_GROUPS = {
    "Hello! Project": ["Morning Musume", "ANGERME", "Juice=Juice"],
    "AKB48 Group": ["AKB48", "SKE48", "NMB48"],
    "Sakamichi Series": ["Nogizaka46", "Sakurazaka46", "Hinatazaka46"],
    "=LOVE / Sister Groups": ["=LOVE", "≠ME"],
    "Momoiro Clover Z": ["Momoiro Clover Z"],
    "Babymetal": ["BABYMETAL"],
}

# Full browser mimicry to avoid basic Cloudflare / bot filters
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    "Referer": "https://www.cdjapan.co.jp/",
    "Sec-Ch-Ua": (
        '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
})


def load_catalog():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def make_affiliate_link(product_url):
  clean = product_url.replace("https://www.cdjapan.co.jp/", "").replace(
      "http://www.cdjapan.co.jp/", ""
  )
  encoded = urllib.parse.quote(clean, safe="")
  return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded}"


def scrape_artist(category, artist):
  products = []
  q = urllib.parse.quote_plus(artist)
  # Standard search endpoint
  url = f"https://www.cdjapan.co.jp/searchuni?q={q}&order=reldate"

  try:
    print(f" -> Connecting to: {url}")
    resp = SESSION.get(url, timeout=20)
    print(f"    [HTTP Status: {resp.status_code}]")

    if resp.status_code != 200:
      print(f"    WARNING: CDJapan returned status code {resp.status_code}")
      return products

    # Check if we were redirected to a verification or captcha page
    if (
        "Checking your browser" in resp.text
        or "Just a moment..." in resp.text
        or "cloudflare" in resp.text.lower()
    ):
      print("    WARNING: CDJapan Cloudflare bot protection intercepted.")
      return products

    soup = BeautifulSoup(resp.text, "html.parser")

    # Match multiple possible CDJapan result selectors
    items = (
        soup.select(".item-list .item-detail")
        or soup.select(".n-item")
        or soup.select(".item")
        or soup.select("table.item-list tr")
    )

    print(f"    Found {len(items)} raw HTML candidate cards.")

    for item in items:
      title_el = (
          item.select_one(".title a")
          or item.select_one("a.item-title")
          or item.select_one("a[href*='/product/']")
      )
      if not title_el:
        continue

      link = title_el.get("href", "")
      if not link:
        continue
      if not link.startswith("http"):
        link = "https://www.cdjapan.co.jp" + link

      prod_id = link.split("/")[-1].split("?")[0]
      title = title_el.get_text(strip=True)

      price_el = (
          item.select_one(".price")
          or item.select_one(".item-price")
          or item.select_one(".price-value")
          or item.select_one("span.bold")
      )
      price = price_el.get_text(strip=True) if price_el else "Check Price"

      date_el = (
          item.select_one(".release_date")
          or item.select_one(".item-date")
          or item.select_one(".date")
      )
      rel_date = date_el.get_text(strip=True) if date_el else "Available Now"

      img_el = item.select_one("img")
      img_src = ""
      if img_el:
        img_src = (
            img_el.get("src")
            or img_el.get("data-src")
            or img_el.get("data-original")
            or ""
        )
      if not img_src or "spacer" in img_src:
        img_src = "https://via.placeholder.com/300x300?text=CDJapan+Release"
      if img_src.startswith("//"):
        img_src = "https:" + img_src

      products.append({
          "id": prod_id,
          "title": title,
          "artist": artist,
          "category": category,
          "price": price,
          "release_date": rel_date,
          "image": img_src,
          "affiliate_url": make_affiliate_link(link),
          "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
      })

    time.sleep(1.5)
  except Exception as e:
    print(f"    Error scraping {artist}: {e}")

  return products


def main():
  catalog = load_catalog()
  initial_count = len(catalog)
  print(f"Starting catalog size: {initial_count}")

  for cat, artists in TARGET_GROUPS.items():
    print(f"\nProcessing Franchise: {cat}")
    for artist in artists:
      items = scrape_artist(cat, artist)
      for it in items:
        catalog[it["id"]] = it
      print(f"  > Scraped {len(items)} items for {artist}")

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  new_count = len(catalog)
  print(
      f"\nSync Complete! Added {new_count - initial_count} new items. Total"
      f" catalog: {new_count}"
  )


if __name__ == "__main__":
  main()
