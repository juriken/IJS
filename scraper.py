import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

# Base CDJapan URLs and Affiliate Parameters
BASE_URL = "https://www.cdjapan.co.jp"
AFFILIATE_ID = "A033398"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Catalog Target Registry
TARGET_ARTISTS = [
    # Hello! Project
    {"artist": "Morning Musume", "category": "Hello! Project", "query": "Morning Musume"},
    {"artist": "ANGERME", "category": "Hello! Project", "query": "ANGERME"},
    {"artist": "Juice=Juice", "category": "Hello! Project", "query": "Juice=Juice"},
    {"artist": "Tsubaki Factory", "category": "Hello! Project", "query": "Tsubaki Factory"},
    {"artist": "BEYOOOOONDS", "category": "Hello! Project", "query": "BEYOOOOONDS"},
    {"artist": "OCHA NORMA", "category": "Hello! Project", "query": "OCHA NORMA"},
    {"artist": "Rosy Chronicle", "category": "Hello! Project", "query": "Rosy Chronicle"},
    {"artist": "Hello Pro Kenshuusei", "category": "Hello! Project", "query": "Hello Pro Kenshuusei"},
    {"artist": "Berryz Kobo", "category": "Hello! Project", "query": "Berryz Kobo"},
    {"artist": "℃-ute", "category": "Hello! Project", "query": "℃-ute"},
    {"artist": "Buono!", "category": "Hello! Project", "query": "Buono!"},
    {"artist": "Country Girls", "category": "Hello! Project", "query": "Country Girls"},
    {"artist": "Kobushi Factory", "category": "Hello! Project", "query": "Kobushi Factory"},
    {"artist": "Melon Kinenbi", "category": "Hello! Project", "query": "Melon Kinenbi"},
    {"artist": "Minimoni", "category": "Hello! Project", "query": "Minimoni"},
    {"artist": "Tanpopo", "category": "Hello! Project", "query": "Tanpopo"},
    {"artist": "v-u-den", "category": "Hello! Project", "query": "v-u-den"},
    {"artist": "LoVendoR", "category": "Hello! Project", "query": "LoVendoR"},
    {"artist": "PINK CRES.", "category": "Hello! Project", "query": "PINK CRES."},
    {"artist": "Sayumi Michishige", "category": "Hello! Project", "query": "Sayumi Michishige"},
    {"artist": "Aya Matsuura", "category": "Hello! Project", "query": "Aya Matsuura"},
    {"artist": "Maki Goto", "category": "Hello! Project", "query": "Maki Goto"},
    {"artist": "Natsumi Abe", "category": "Hello! Project", "query": "Natsumi Abe"},
    {"artist": "Erina Mano", "category": "Hello! Project", "query": "Erina Mano"},
    {"artist": "Airi Suzuki", "category": "Hello! Project", "query": "Airi Suzuki"},
    # Up-Front Alumni
    {"artist": "You Kikkawa", "category": "Up-Front Alumni", "query": "You Kikkawa"},
    {"artist": "Up Up Girls (Kari)", "category": "Up-Front Alumni", "query": "Up Up Girls (Kari)"},
    {"artist": "Up Up Girls (2)", "category": "Up-Front Alumni", "query": "Up Up Girls (2)"},
    # AKB48 Group
    {"artist": "AKB48", "category": "AKB48 Group", "query": "AKB48"},
    {"artist": "SKE48", "category": "AKB48 Group", "query": "SKE48"},
    {"artist": "NMB48", "category": "AKB48 Group", "query": "NMB48"},
    {"artist": "HKT48", "category": "AKB48 Group", "query": "HKT48"},
    {"artist": "NGT48", "category": "AKB48 Group", "query": "NGT48"},
    {"artist": "STU48", "category": "AKB48 Group", "query": "STU48"},
    {"artist": "Sayaka Yamamoto", "category": "AKB48 Group", "query": "Sayaka Yamamoto"},
    # Sakamichi Series & 22/7
    {"artist": "Nogizaka46", "category": "Sakamichi Series", "query": "Nogizaka46"},
    {"artist": "Sakurazaka46", "category": "Sakamichi Series", "query": "Sakurazaka46"},
    {"artist": "Hinatazaka46", "category": "Sakamichi Series", "query": "Hinatazaka46"},
    {"artist": "Keyakizaka46", "category": "Sakamichi Series", "query": "Keyakizaka46"},
    {"artist": "22/7", "category": "Sakamichi Series", "query": "22/7"},
    # Stardust Planet
    {"artist": "Momoiro Clover Z", "category": "Stardust Planet", "query": "Momoiro Clover Z"},
    {"artist": "Shiritsu Ebisu Chugaku", "category": "Stardust Planet", "query": "Shiritsu Ebisu Chugaku"},
    {"artist": "Chou Tokimeki Sendenbu", "category": "Stardust Planet", "query": "Chou Tokimeki Sendenbu"},
    # =LOVE & Sisters
    {"artist": "=LOVE", "category": "=LOVE / Sister Groups", "query": "=LOVE"},
    {"artist": "≠ME", "category": "=LOVE / Sister Groups", "query": "≠ME"},
    {"artist": "≒JOY", "category": "=LOVE / Sister Groups", "query": "≒JOY"},
    # KAWAII LAB.
    {"artist": "FRUITS ZIPPER", "category": "KAWAII LAB.", "query": "FRUITS ZIPPER"},
    {"artist": "CUTIE STREET", "category": "KAWAII LAB.", "query": "CUTIE STREET"},
    # Modern Idols
    {"artist": "NiziU", "category": "Modern Idols", "query": "NiziU"},
    {"artist": "ME:I", "category": "Modern Idols", "query": "ME:I"},
    # Babymetal
    {"artist": "BABYMETAL", "category": "Babymetal", "query": "BABYMETAL"}
]

TITLE_PRICE_CLEANUP_REGEX = re.compile(
    r'(?:\s*[\(\[【]?\s*(?:¥\s*[\d,]+|[\d,]+\s*(?:yen|JPY))\s*(?:\([^)]*\)|（[^）]*）|tax\s*(?:incl|included|\.|\s*in)?|税込)?\s*[\)\]】]?)+$',
    re.IGNORECASE
)

def clean_product_title(raw_title: str) -> str:
    if not raw_title:
        return ""
    cleaned = TITLE_PRICE_CLEANUP_REGEX.sub('', raw_title).strip()
    cleaned = re.sub(r'[\s\-_—]+$', '', cleaned).strip()
    return cleaned

def extract_numeric_price(price_str: str) -> int:
    if not price_str:
        return 0
    digits = re.sub(r'[^\d]', '', price_str)
    return int(digits) if digits else 0

def format_affiliate_url(direct_url: str) -> str:
    if not direct_url:
        return ""
    sep = "&" if "?" in direct_url else "?"
    return f"{direct_url}{sep}affi={AFFILIATE_ID}"

def parse_availability(status_text: str, rel_date_str: str) -> str:
    status_lower = (status_text or "").lower()
    
    # Check Out-of-Print / No Longer Available
    if any(k in status_lower for k in ["no longer available", "out of print", "sold out", "discontinued", "廃盤", "取扱終了"]):
        return "oop"
    
    # Check Pre-Order status based on text or future street date
    if "pre-order" in status_lower or "preorder" in status_lower:
        return "preorder"

    if rel_date_str:
        date_match = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', rel_date_str)
        if date_match:
            y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
            now = time.gmtime()
            today_val = (now.tm_year * 10000) + (now.tm_mon * 100) + now.tm_mday
            item_val = (y * 10000) + (m * 100) + d
            if item_val > today_val:
                return "preorder"

    return "instock"

def scrape_search_page(session, target, page=1):
    search_url = f"{BASE_URL}/searchresult.html?q={quote_plus(target['query'])}&order=scoredesc&page={page}"
    try:
        resp = session.get(search_url, timeout=15)
        if resp.status_code != 200:
            return []
    except Exception as e:
        print(f"Error fetching page {page} for {target['artist']}: {e}")
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    items = []
    product_nodes = soup.select('div.item-list > div.item, ul.product-list > li, div.n-product-list-item')

    for node in product_nodes:
        # Title & Product Link
        title_el = node.select_one('a.title, a.n-title, .title a')
        if not title_el:
            continue
        
        raw_title = title_el.get_text(strip=True)
        title = clean_product_title(raw_title)
        href = title_el.get('href', '')
        detail_url = urljoin(BASE_URL, href)
        
        # Catalog ID / SKU
        sku_el = node.select_one('.item-sku, .sku, .code')
        sku = sku_el.get_text(strip=True) if sku_el else ""
        if not sku:
            m = re.search(r'detail/([^/]+)/?', href)
            sku = m.group(1) if m else ""

        if not sku:
            continue

        # Image Extraction
        img_el = node.select_one('img')
        img_url = ""
        if img_el:
            img_url = img_el.get('data-src') or img_el.get('data-original') or img_el.get('src') or ""
            if img_url:
                img_url = urljoin(BASE_URL, img_url)

        # Price
        price_el = node.select_one('.price, .item-price, .n-price')
        price_str = price_el.get_text(strip=True) if price_el else ""
        price_num = extract_numeric_price(price_str)

        # Release Date
        date_el = node.select_one('.release-date, .date, .n-release-date')
        rel_date = date_el.get_text(strip=True).replace('Release Date:', '').strip() if date_el else "Available Now"

        # Stock / Availability parsing
        avail_el = node.select_one('.stock-status, .availability, .status')
        avail_text = avail_el.get_text(strip=True) if avail_el else ""
        availability = parse_availability(avail_text, rel_date)

        # Audio / Video Preview Detection
        sample_audio = None
        sample_audio_el = node.select_one('a.sample-listen, [data-audio-sample]')
        if sample_audio_el:
            sample_audio = sample_audio_el.get('href') or sample_audio_el.get('data-audio-sample')

        items.append({
            "id": sku,
            "title": title,
            "artist": target["artist"],
            "category": target["category"],
            "price": price_str or "Check CDJapan",
            "price_num": price_num,
            "release_date": rel_date,
            "availability": availability,
            "image": img_url,
            "sample_audio": sample_audio,
            "url": detail_url,
            "affiliate_url": format_affiliate_url(detail_url)
        })

    return items

def main():
    print("Starting Catalog Sync Pipeline...")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    existing_products = {}
    if os.path.exists("products.json"):
        try:
            with open("products.json", "r", encoding="utf-8") as f:
                existing_products = json.load(f)
            print(f"Loaded {len(existing_products)} existing records from products.json.")
        except Exception as e:
            print(f"Warning: Could not read existing products.json: {e}")

    new_additions = 0
    updated_records = 0

    for idx, target in enumerate(TARGET_ARTISTS, 1):
        print(f"[{idx}/{len(TARGET_ARTISTS)}] Syncing: {target['artist']} ({target['category']})")
        for page in range(1, 4):
            scraped = scrape_search_page(session, target, page=page)
            if not scraped:
                break

            for item in scraped:
                item_id = item["id"]
                if item_id not in existing_products:
                    existing_products[item_id] = item
                    new_additions += 1
                else:
                    # Update dynamic pricing, status, and clean title if needed
                    existing_products[item_id]["title"] = clean_product_title(item["title"])
                    existing_products[item_id]["price"] = item["price"]
                    existing_products[item_id]["price_num"] = item["price_num"]
                    existing_products[item_id]["availability"] = item["availability"]
                    if item.get("sample_audio"):
                        existing_products[item_id]["sample_audio"] = item["sample_audio"]
                    updated_records += 1

            time.sleep(1.0)

    # Save full products.json
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(existing_products, f, ensure_ascii=False, indent=2)

    # Build and save minified catalog-index.json for ultra-fast frontend hydration
    summary_index = {}
    for pid, it in existing_products.items():
        summary_index[pid] = {
            "id": it.id if hasattr(it, "id") else it.get("id"),
            "title": it.get("title"),
            "artist": it.get("artist"),
            "category": it.get("category"),
            "price_num": it.get("price_num", 0),
            "price": it.get("price", ""),
            "release_date": it.get("release_date", ""),
            "availability": it.get("availability", "instock"),
            "image": it.get("image", ""),
            "sample_audio": it.get("sample_audio")
        }

    with open("catalog-index.json", "w", encoding="utf-8") as f:
        json.dump(summary_index, f, ensure_ascii=False, separators=(',', ':'))

    print("==========================================")
    print(f"Sync Complete! Added: {new_additions} | Updated: {updated_records}")
    print(f"Total live SKUs in catalog: {len(existing_products)}")
    print("Generated both 'products.json' and 'catalog-index.json'.")
    print("==========================================")

if __name__ == "__main__":
    main()
