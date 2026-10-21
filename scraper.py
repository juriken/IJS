"""
IdolJapan.store — Official Japanese Idol CDJapan Catalog Scraper
Automated batch crawler with Playwright Chromium rendering, direct Person ID routing,
archive EOA parameter support, and header/footer decomposition.
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

# Try importing Playwright; fallback to requests if unavailable
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

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

# Master Registry
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
    # Hello Pro Kenshuusei
    {
        "name": "Hello Pro Kenshuusei",
        "category": "Hello! Project",
        "targets": [
            "Hello Pro Kenshusei",
            "ハロプロ研修生",
            "Hello Pro Kenshuusei"
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
    # Kobushi Factory
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
    # Up Up Girls (2) — Direct Person ID + Japanese Kanji/Katakana
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
    Constructs target search/person URLs including EOA (out of print) archives.
    """
    if target.startswith("http://") or target.startswith("https://"):
        sep = "&" if "?" in target else "?"
        return f"{target}{sep}page={page}&order=reldate_desc"
    else:
        encoded_q = urllib.parse.quote_plus(target)
        return f"{BASE_URL}/searchuni?q={encoded_q}&order=reldate_desc&opt.include_eoa=1&page={page}"

def extract_products_from_html(html_content, artist_name, category_name):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Decompose header, footer, nav, and sidebar widgets to avoid promo card leakage
    for el in soup.select("header, footer, nav, aside, #header, #footer, .header, .footer, .global-nav, .cart-nav, .recommend_list, .ranking_list"):
        el.decompose()

    extracted = []
    products_by_id = {}

    anchors = soup.select('a[href*="/product/"]')
    for a in anchors:
        href = a.get("href", "")
        m = re.search(r'/product/([A-Za-z0-9\-]+)', href)
        if not m:
            continue
        pid = m.group(1).upper()

        if pid in ["REVIEW", "CART", "SEARCH", "HELP", "RANKING", "INDEX"]:
            continue

        if pid not in products_by_id:
            products_by_id[pid] = {
                "anchors": [],
                "images": [],
                "texts": []
            }
        products_by_id[pid]["anchors"].append(a)

        txt = clean_text(a.get_text())
        if txt and len(txt) > 2 and txt.lower() not in ["buy", "order", "details", "pre-order", "view", "more", "add to cart", "cart", "next", "prev"]:
            products_by_id[pid]["texts"].append(txt)

        img = a.select_one("img")
        if img:
            alt = clean_text(img.get("alt", ""))
            if alt and len(alt) > 2:
                products_by_id[pid]["texts"].append(alt)
            src = img.get("data-original") or img.get("data-src") or img.get("src") or ""
            if src and "no_image" not in src:
                if src.startswith("//"):
                    src = f"https:{src}"
                elif src.startswith("/"):
                    src = f"{BASE_URL}{src}"
                products_by_id[pid]["images"].append(
                    src.replace("/pictures/s/", "/pictures/l/").replace("/pictures/m/", "/pictures/l/")
                )

    for pid, data in products_by_id.items():
        title = ""
        if data["texts"]:
            title = max(data["texts"], key=len)

        first_anchor = data["anchors"][0]
        card = (
            first_anchor.find_parent("tr") or
            first_anchor.find_parent("li") or
            first_anchor.find_parent("div", class_=re.compile(r'item|product|unit|box', re.I))
        )
        if not card:
            card = first_anchor.parent

        if not title and card:
            t_elem = card.select_one(".title, .item_title, .item-title, h3, h2, h4, .name")
            if t_elem:
                title = clean_text(t_elem.get_text())

        if not title or len(title) < 2:
            continue

        image_url = ""
        if data["images"]:
            image_url = data["images"][0]
        elif card:
            card_img = card.select_one("img")
            if card_img:
                src = card_img.get("data-original") or card_img.get("data-src") or card_img.get("src") or ""
                if src and "no_image" not in src:
                    if src.startswith("//"):
                        src = f"https:{src}"
                    elif src.startswith("/"):
                        src = f"{BASE_URL}{src}"
                    image_url = src.replace("/pictures/s/", "/pictures/l/").replace("/pictures/m/", "/pictures/l/")

        if not image_url or "no_image" in image_url:
            image_url = f"https://www.cdjapan.co.jp/pictures/l/{pid}.jpg"

        release_date = "Available Now"
        card_text = card.get_text() if card else ""
        date_match = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', card_text)
        if date_match:
            release_date = f"{date_match.group(1)}/{date_match.group(2).zfill(2)}/{date_match.group(3).zfill(2)}"

        price_str = "Check CDJapan"
        price_match = re.search(r'([\d,]+)\s*(?:yen|JPY)', card_text, re.IGNORECASE)
        if price_match:
            price_str = f"¥{price_match.group(1)}"
        elif "¥" in card_text:
            yen_match = re.search(r'¥\s*([\d,]+)', card_text)
            if yen_match:
                price_str = f"¥{yen_match.group(1)}"

        card_text_lower = card_text.lower()
        if is_date_upcoming(release_date) or "pre-order" in card_text_lower:
            availability = "preorder"
        elif "out of print" in card_text_lower or "sold out" in card_text_lower or "archive" in card_text_lower or "no longer available" in card_text_lower:
            availability = "oop"
        else:
            availability = "instock"

        affiliate_url = f"https://www.cdjapan.co.jp/product/{pid}?affi={AFFILIATE_ID}"

        extracted.append({
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
        })

    return extracted

def fetch_html_content(url, playwright_page=None, requests_session=None):
    """
    Renders via Playwright Chromium if available; falls back to requests.Session.
    """
    if playwright_page:
        for attempt in range(1, 4):
            try:
                playwright_page.goto(url, wait_until="domcontentloaded", timeout=40000)
                try:
                    playwright_page.wait_for_selector('a[href*="/product/"]', timeout=8000)
                except Exception:
                    pass
                playwright_page.wait_for_timeout(1000)
                return playwright_page.content()
            except Exception as e:
                time.sleep(attempt * 2.0)
        return ""
    elif requests_session:
        for attempt in range(1, 4):
            try:
                resp = requests_session.get(url, headers=get_request_headers(), timeout=15)
                if resp.status_code == 200:
                    return resp.text
            except Exception:
                time.sleep(attempt * 2.0)
        return ""
    return ""

def scrape_artist_target(target, artist_name, category_name, playwright_page=None, requests_session=None, max_pages=3):
    total_found = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        url = build_target_url(target, page=page)
        html = fetch_html_content(url, playwright_page=playwright_page, requests_session=requests_session)
        if not html:
            break

        items = extract_products_from_html(html, artist_name, category_name)
        if not items:
            break

        new_on_page = 0
        for it in items:
            if it["id"] not in seen_ids:
                seen_ids.add(it["id"])
                total_found.append(it)
                new_on_page += 1

        if new_on_page == 0:
            break

        time.sleep(random.uniform(0.8, 1.6))

    return total_found

def get_filtered_registry():
    raw_filter = os.environ.get("TARGET_ARTIST", "").strip()
    if not raw_filter or raw_filter.lower() == "all groups":
        return ARTIST_REGISTRY

    if "updated 3 groups" in raw_filter.lower():
        target_names = ["Up Up Girls (2)", "Hello Pro Kenshuusei", "Kobushi Factory"]
        return [a for a in ARTIST_REGISTRY if a["name"] in target_names]

    matched = [a for a in ARTIST_REGISTRY if a["name"].lower() == raw_filter.lower()]
    return matched if matched else ARTIST_REGISTRY

def run_catalog_sync():
    print(f"🚀 Starting IdolJapan Catalog Scraper Sync at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}...")
    print(f"⚙️ Engine Mode: {'Playwright Headless Chromium' if HAS_PLAYWRIGHT else 'Requests (Fallback)'}")

    active_registry = get_filtered_registry()
    print(f"📋 Active Filter: Running {len(active_registry)} artist group(s): {[a['name'] for a in active_registry]}")

    existing_catalog = {}
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                existing_catalog = json.load(f)
            print(f"Loaded existing database with {len(existing_catalog)} releases.")
        except Exception as e:
            print(f"Warning: Could not read existing {PRODUCTS_FILE}: {e}")

    total_new_or_updated = 0

    # Initialize crawler engine
    playwright_instance = None
    browser = None
    playwright_page = None
    requests_session = None

    if HAS_PLAYWRIGHT:
        playwright_instance = sync_playwright().start()
        browser = playwright_instance.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="en-US"
        )
        playwright_page = context.new_page()
    else:
        requests_session = requests.Session()

    try:
        for artist_cfg in active_registry:
            canonical_name = artist_cfg["name"]
            category = artist_cfg["category"]
            targets = artist_cfg.get("targets", [canonical_name])

            print(f"\nScanning: {canonical_name} ({category}) across {len(targets)} targets...")
            artist_items_map = {}

            for target in targets:
                found_items = scrape_artist_target(
                    target, 
                    canonical_name, 
                    category, 
                    playwright_page=playwright_page, 
                    requests_session=requests_session
                )
                print(f"  Target '{target}' -> Extracted {len(found_items)} items.")

                for item in found_items:
                    pid = item["id"]
                    if pid not in artist_items_map:
                        artist_items_map[pid] = item
                    else:
                        if artist_items_map[pid]["price"] == "Check CDJapan" and item["price"] != "Check CDJapan":
                            artist_items_map[pid]["price"] = item["price"]
                            artist_items_map[pid]["price_num"] = item["price_num"]

            print(f"  ==> Total unique releases for {canonical_name}: {len(artist_items_map)}")

            for pid, item in artist_items_map.items():
                if pid not in existing_catalog or existing_catalog[pid] != item:
                    existing_catalog[pid] = item
                    total_new_or_updated += 1

            time.sleep(random.uniform(0.5, 1.2))

    finally:
        if browser:
            browser.close()
        if playwright_instance:
            playwright_instance.stop()

    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_catalog, f, ensure_ascii=False, indent=2)

    state_data = {
        "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_catalog_size": len(existing_catalog),
        "items_updated_this_pass": total_new_or_updated,
        "last_targeted_filter": [a["name"] for a in active_registry]
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Sync finished successfully!")
    print(f"   Total items stored: {len(existing_catalog)}")
    print(f"   Items added or updated this run: {total_new_or_updated}")

if __name__ == "__main__":
    run_catalog_sync()
