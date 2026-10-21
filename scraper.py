"""
IdolJapan.store — Official Japanese Idol CDJapan Catalog Scraper
Automated batch crawler with direct Person ID routing, multi-alias queries,
and automatic item deduplication.
"""

import os
import re
import time
import json
import random
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Global Configuration
PRODUCTS_FILE = "products.json"
STATE_FILE = "scraper_state.json"
BASE_URL = "https://www.cdjapan.co.jp"
AFFILIATE_ID = "A033398"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
]

# Targeted Franchise & Artist Master Registry
# Resolves queries, direct person endpoints, and alternate spellings
ARTIST_REGISTRY = [
    # Hello! Project
    {
        "name": "Morning Musume",
        "category": "Hello! Project",
        "targets": ["Morning Musume", "モーニング娘"]
    },
    {
        "name": "ANGERME",
        "category": "Hello! Project",
        "targets": ["ANGERME", "アンジュルム", "S/mileage", "スマイレージ"]
    },
    {
        "name": "Juice=Juice",
        "category": "Hello! Project",
        "targets": ["Juice=Juice", "Juice Juice", "ジュースジュース"]
    },
    {
        "name": "Tsubaki Factory",
        "category": "Hello! Project",
        "targets": ["Tsubaki Factory", "つばきファクトリー"]
    },
    {
        "name": "BEYOOOOONDS",
        "category": "Hello! Project",
        "targets": ["BEYOOOOONDS", "ビヨーンズ"]
    },
    {
        "name": "OCHA NORMA",
        "category": "Hello! Project",
        "targets": ["OCHA NORMA", "オチャノーマ"]
    },
    {
        "name": "Rosy Chronicle",
        "category": "Hello! Project",
        "targets": ["Rosy Chronicle", "ロージークロニクル"]
    },
    # Problem 2 Solved: Multi-query for Hello Pro Kenshuusei
    {
        "name": "Hello Pro Kenshuusei",
        "category": "Hello! Project",
        "targets": [
            "Hello Pro Kenshusei",
            "Hello Pro Kenshuusei",
            "ハロプロ研修生",
            "Hello! Project Kenshusei"
        ]
    },
    {
        "name": "Berryz Kobo",
        "category": "Hello! Project",
        "targets": ["Berryz Kobo", "Berryz工房"]
    },
    {
        "name": "℃-ute",
        "category": "Hello! Project",
        "targets": ["℃-ute", "C-ute"]
    },
    {
        "name": "Buono!",
        "category": "Hello! Project",
        "targets": ["Buono!"]
    },
    {
        "name": "Country Girls",
        "category": "Hello! Project",
        "targets": ["Country Girls", "カントリー・ガールズ"]
    },
    # Problem 3 Solved: Query both Kobushi-Factory and Kobushi Factory
    {
        "name": "Kobushi Factory",
        "category": "Hello! Project",
        "targets": [
            "Kobushi-Factory",
            "Kobushi Factory",
            "こぶしファクトリー"
        ]
    },
    {
        "name": "Airi Suzuki",
        "category": "Hello! Project",
        "targets": ["Airi Suzuki", "鈴木愛理"]
    },
    {
        "name": "Sayumi Michishige",
        "category": "Hello! Project",
        "targets": ["Sayumi Michishige", "道重さゆみ"]
    },

    # Up-Front Alumni
    {
        "name": "You Kikkawa",
        "category": "Up-Front Alumni",
        "targets": ["You Kikkawa", "吉川友"]
    },
    {
        "name": "Up Up Girls (Kari)",
        "category": "Up-Front Alumni",
        "targets": ["Up Up Girls (Kari)", "アップアップガールズ(仮)"]
    },
    # Problem 1 Solved: Direct Person ID Endpoint + Escaped Queries
    {
        "name": "Up Up Girls (2)",
        "category": "Up-Front Alumni",
        "targets": [
            "https://www.cdjapan.co.jp/person/700786352",
            "アップアップガールズ(2)",
            "Up Up Girls 2"
        ]
    },

    # AKB48 Group
    {
        "name": "AKB48",
        "category": "AKB48 Group",
        "targets": ["AKB48"]
    },
    {
        "name": "SKE48",
        "category": "AKB48 Group",
        "targets": ["SKE48"]
    },
    {
        "name": "NMB48",
        "category": "AKB48 Group",
        "targets": ["NMB48"]
    },
    {
        "name": "HKT48",
        "category": "AKB48 Group",
        "targets": ["HKT48"]
    },
    {
        "name": "NGT48",
        "category": "AKB48 Group",
        "targets": ["NGT48"]
    },
    {
        "name": "STU48",
        "category": "AKB48 Group",
        "targets": ["STU48"]
    },

    # Sakamichi Series & 22/7
    {
        "name": "Nogizaka46",
        "category": "Sakamichi Series",
        "targets": ["Nogizaka46", "乃木坂46"]
    },
    {
        "name": "Sakurazaka46",
        "category": "Sakamichi Series",
        "targets": ["Sakurazaka46", "櫻坂46"]
    },
    {
        "name": "Hinatazaka46",
        "category": "Sakamichi Series",
        "targets": ["Hinatazaka46", "日向坂46"]
    },
    {
        "name": "22/7",
        "category": "Sakamichi Series",
        "targets": ["22/7", "ナナブンノニジュウニ"]
    },

    # Stardust Planet
    {
        "name": "Momoiro Clover Z",
        "category": "Stardust Planet",
        "targets": ["Momoiro Clover Z", "ももいろクローバーZ"]
    },
    {
        "name": "Shiritsu Ebisu Chugaku",
        "category": "Stardust Planet",
        "targets": ["Shiritsu Ebisu Chugaku", "私立恵比寿中学"]
    },
    {
        "name": "Chou Tokimeki Sendenbu",
        "category": "Stardust Planet",
        "targets": ["Chou Tokimeki Sendenbu", "超ときめき♡宣伝部"]
    },

    # =LOVE / Sister Groups
    {
        "name": "=LOVE",
        "category": "=LOVE / Sister Groups",
        "targets": ["=LOVE", "イコールラブ"]
    },
    {
        "name": "≠ME",
        "category": "=LOVE / Sister Groups",
        "targets": ["≠ME", "ノットイコールミー"]
    },
    {
        "name": "≒JOY",
        "category": "=LOVE / Sister Groups",
        "targets": ["≒JOY", "ニアリーイコールジョイ"]
    },

    # KAWAII LAB.
    {
        "name": "FRUITS ZIPPER",
        "category": "KAWAII LAB.",
        "targets": ["FRUITS ZIPPER", "フルーツジッパー"]
    },
    {
        "name": "CUTIE STREET",
        "category": "KAWAII LAB.",
        "targets": ["CUTIE STREET", "キューティーストリート"]
    },

    # Modern Idols & Babymetal
    {
        "name": "NiziU",
        "category": "Modern Idols",
        "targets": ["NiziU", "ニジュー"]
    },
    {
        "name": "ME:I",
        "category": "Modern Idols",
        "targets": ["ME:I", "ミーアイ"]
    },
    {
        "name": "BABYMETAL",
        "category": "Babymetal",
        "targets": ["BABYMETAL"]
    }
]

def get_request_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Referer": "https://www.cdjapan.co.jp/",
        "DNT": "1"
    }

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def parse_price_numeric(price_str):
    if not price_str:
        return 0
    digits = re.sub(r'[^\d]', '', price_str)
    return int(digits) if digits else 0

def parse_date_value(date_str):
    if not date_str:
        return 0
    m = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', date_str)
    if m:
        return (int(m.group(1)) * 10000) + (int(m.group(2)) * 100) + int(m.group(3))
    return 0

def is_date_upcoming(date_str):
    val = parse_date_value(date_str)
    if val == 0:
        return False
    now = datetime.utcnow()
    today_val = (now.year * 10000) + (now.month * 100) + now.day
    return val > today_val

def build_target_url(target, page=1):
    """
    Directly routes person/series URLs or formats standard search endpoints.
    """
    if target.startswith("http://") or target.startswith("https://"):
        sep = "&" if "?" in target else "?"
        return f"{target}{sep}term.order=reldate_desc&page={page}"
    else:
        encoded_q = urllib.parse.quote_plus(target)
        return f"{BASE_URL}/searchuni?q={encoded_q}&order=reldate_desc&page={page}"

def extract_products_from_html(html_content, artist_name, category_name):
    soup = BeautifulSoup(html_content, "html.parser")
    extracted = []

    # Product cards on CDJapan appear in various list structures
    product_anchors = soup.select('a[href*="/product/"]')
    seen_ids_on_page = set()

    for anchor in product_anchors:
        href = anchor.get("href", "")
        m = re.search(r'/product/([A-Za-z0-9\-]+)', href)
        if not m:
            continue

        pid = m.group(1).upper()
        if pid in seen_ids_on_page:
            continue
        seen_ids_on_page.add(pid)

        # Locate enclosing card container
        card = anchor.find_parent("tr") or anchor.find_parent("li") or anchor.find_parent("div", class_=re.compile(r'item|product|unit', re.I))
        if not card:
            card = anchor.parent

        # 1. Title Extraction
        title = ""
        title_elem = card.select_one(".title, .item-title, h3, h2, a[title]")
        if title_elem and title_elem.get("title"):
            title = clean_text(title_elem["title"])
        elif title_elem:
            title = clean_text(title_elem.get_text())
        else:
            title = clean_text(anchor.get_text())

        # Discard irrelevant navigation anchors matching product link
        if not title or len(title) < 2 or title.lower() in ["buy", "details", "pre-order", "order"]:
            continue

        # 2. Image Extraction
        image_url = ""
        img_elem = card.select_one("img")
        if img_elem:
            raw_src = img_elem.get("data-original") or img_elem.get("data-src") or img_elem.get("src") or ""
            if raw_src.startswith("//"):
                raw_src = f"https:{raw_src}"
            elif raw_src.startswith("/"):
                raw_src = f"{BASE_URL}{raw_src}"
            image_url = raw_src.replace("/pictures/s/", "/pictures/l/").replace("/pictures/m/", "/pictures/l/")

        if not image_url or "no_image" in image_url:
            image_url = f"https://www.cdjapan.co.jp/pictures/l/{pid}.jpg"

        # 3. Release Date Extraction
        release_date = "Available Now"
        date_match = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', card.get_text())
        if date_match:
            release_date = f"{date_match.group(1)}/{date_match.group(2).zfill(2)}/{date_match.group(3).zfill(2)}"

        # 4. Price Extraction
        price_str = "Check CDJapan"
        price_match = re.search(r'([\d,]+)\s*(?:yen|JPY)', card.get_text(), re.IGNORECASE)
        if price_match:
            price_str = f"¥{price_match.group(1)}"
        elif "¥" in card.get_text():
            yen_match = re.search(r'¥\s*([\d,]+)', card.get_text())
            if yen_match:
                price_str = f"¥{yen_match.group(1)}"

        # 5. Availability Status
        card_text_lower = card.get_text().lower()
        if is_date_upcoming(release_date) or "pre-order" in card_text_lower:
            availability = "preorder"
        elif "out of print" in card_text_lower or "sold out" in card_text_lower or "archive" in card_text_lower:
            availability = "oop"
        else:
            availability = "instock"

        affiliate_url = f"https://www.cdjapan.co.jp/product/{pid}?affi={AFFILIATE_ID}"

        item_record = {
            "id": pid,
            "title": title,
            "artist": artist_name,
            "category": category_name,
            "price": price_str,
            "price_num": parse_price_numeric(price_str),
            "release_date": release_date,
            "image": image_url,
            "availability": availability,
            "affiliate_url": affiliate_url,
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d")
        }

        extracted.append(item_record)

    return extracted

def scrape_artist_target(session, target, artist_name, category_name, max_pages=3):
    total_found = []
    
    for page in range(1, max_pages + 1):
        url = build_target_url(target, page=page)
        success = False

        for attempt in range(1, 4):
            try:
                resp = session.get(url, headers=get_request_headers(), timeout=15)
                if resp.status_code == 200 and len(resp.text) > 1000:
                    items = extract_products_from_html(resp.text, artist_name, category_name)
                    if items:
                        total_found.extend(items)
                        success = True
                        break
                    else:
                        # Page has no more items
                        success = True
                        break
                elif resp.status_code == 404:
                    success = True
                    break
                else:
                    time.sleep(attempt * 2.0)
            except Exception as e:
                time.sleep(attempt * 2.5)

        if not success or not items:
            break

        time.sleep(random.uniform(1.2, 2.4))

    return total_found

def run_catalog_sync():
    print(f"🚀 Starting IdolJapan Catalog Scraper Sync at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}...")

    # Load existing catalog
    existing_catalog = {}
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                existing_catalog = json.load(f)
            print(f"Loaded existing database with {len(existing_catalog)} releases.")
        except Exception as e:
            print(f"Warning: Could not read existing {PRODUCTS_FILE}: {e}")

    session = requests.Session()
    total_new_or_updated = 0

    for artist_cfg in ARTIST_REGISTRY:
        canonical_name = artist_cfg["name"]
        category = artist_cfg["category"]
        targets = artist_cfg.get("targets", [canonical_name])

        print(f"\nScanning: {canonical_name} ({category}) across {len(targets)} targets...")
        artist_items_map = {}

        for target in targets:
            found_items = scrape_artist_target(session, target, canonical_name, category)
            print(f"  Target '{target}' -> Extracted {len(found_items)} items.")
            
            for item in found_items:
                pid = item["id"]
                # Keep latest or more informative data
                if pid not in artist_items_map:
                    artist_items_map[pid] = item
                else:
                    # Update price if previously missing
                    if artist_items_map[pid]["price"] == "Check CDJapan" and item["price"] != "Check CDJapan":
                        artist_items_map[pid]["price"] = item["price"]
                        artist_items_map[pid]["price_num"] = item["price_num"]

        # Merge extracted items into main catalog
        for pid, item in artist_items_map.items():
            if pid not in existing_catalog or existing_catalog[pid] != item:
                existing_catalog[pid] = item
                total_new_or_updated += 1

        time.sleep(random.uniform(1.0, 2.0))

    # Persist updated catalog
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_catalog, f, ensure_ascii=False, indent=2)

    # Persist scraper state
    state_data = {
        "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_catalog_size": len(existing_catalog),
        "items_updated_this_pass": total_new_or_updated
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

    print(f"\n Sync finished successfully!")
    print(f"   Total items stored: {len(existing_catalog)}")
    print(f"   Items added or updated this run: {total_new_or_updated}")

if __name__ == "__main__":
    run_catalog_sync()
