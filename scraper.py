import json
import os
import random
import re
import time
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

AFFILIATE_ID = "A033398"
DATA_FILE = "products.json"

# Strict song and album signatures for authentic Tanpopo releases
TANPOPO_AUTHENTIC_SIGNATURES = [
    "last kiss", "motto", "seinaru kane", "otome pasta",
    "koi wo shichaimashita", "ouji-sama", "oujisama", "kousaten",
    "tanpopo 1", "all of tanpopo", "single v clips"
]

# Official Up-Front / Zetima / Piccolo Town label prefixes for Tanpopo
TANPOPO_VALID_PREFIXES = ("EPCE", "EPBE", "EPTE", "EPDE", "PKCP", "PKBP", "UFBW", "UFXW")

# Schema: (Category, Canonical Artist, Search Bar Query, Keyword Filter List)
TARGET_GROUPS = [
    # Hello! Project — Active Groups
    ("Hello! Project", "Morning Musume", "Morning Musume", ["Morning Musume", "Morning Musume."]),
    ("Hello! Project", "ANGERME", "ANGERME", ["ANGERME", "Smileage", "S/mileage"]),
    ("Hello! Project", "Juice=Juice", "Juice=Juice", ["Juice=Juice"]),
    ("Hello! Project", "Tsubaki Factory", "Tsubaki Factory", ["Tsubaki Factory"]),
    ("Hello! Project", "BEYOOOOONDS", "BEYOOOOONDS", ["BEYOOOOONDS"]),
    ("Hello! Project", "OCHA NORMA", "OCHA NORMA", ["OCHA NORMA", "OCHA"]),
    ("Hello! Project", "Rosy Chronicle", "Rosy Chronicle", ["Rosy Chronicle", "Rosy"]),

    # Hello! Project — Past Groups & Subunits
    ("Hello! Project", "Minimoni", "Minimoni", ["Minimoni", "Mini Moni", "Mini-Moni", "ミニモニ", "ミニモニ。"]),
    ("Hello! Project", "Berryz Kobo", "Berryz Kobo", ["Berryz Kobo", "Berryz", "Berryz工房"]),
    ("Hello! Project", "℃-ute", "C-ute", ["℃-ute", "C-ute", "Cute"]),
    ("Hello! Project", "Buono!", "Buono!", ["Buono!"]),
    ("Hello! Project", "Country Girls", "Country Girls", ["Country Girls", "Country Musume", "カントリー・ガールズ", "カントリー娘", "Country"]),
    ("Hello! Project", "Kobushi Factory", "Kobushi Factory", ["Kobushi Factory", "こぶしファクトリー", "こぶし"]),
    ("Hello! Project", "Melon Kinenbi", "Melon Kinenbi", ["Melon Kinenbi", "メロン記念日", "メロン"]),
    ("Hello! Project", "Tanpopo", "Tanpopo", TANPOPO_AUTHENTIC_SIGNATURES),
    ("Hello! Project", "Petitmoni", "Petitmoni", ["Petitmoni", "Pucchimoni", "プッチモニ"]),
    ("Hello! Project", "v-u-den", "Biyuden", ["Biyuden", "v-u-den", "V-u-den", "美勇伝"]),

    # Hello! Project — Soloists & OGs
    ("Hello! Project", "Aya Matsuura", "Aya Matsuura", ["Aya Matsuura", "Matsuura Aya", "松浦亜弥"]),
    ("Hello! Project", "Maki Goto", "Maki Goto", ["Maki Goto", "Goto Maki", "後藤真希"]),
    ("Hello! Project", "Natsumi Abe", "Natsumi Abe", ["Natsumi Abe", "Abe Natsumi", "安倍なつみ"]),
    ("Hello! Project", "Erina Mano", "Erina Mano", ["Erina Mano", "Mano Erina", "真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", "Airi Suzuki", ["Airi Suzuki", "Suzuki Airi", "鈴木愛理"]),

    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46", "Nogizaka46", ["Nogizaka46", "Nogizaka", "乃木坂"]),
    ("Sakamichi Series", "Sakurazaka46", "Sakurazaka46", ["Sakurazaka46", "Sakurazaka", "櫻坂"]),
    ("Sakamichi Series", "Hinatazaka46", "Hinatazaka46", ["Hinatazaka46", "Hinatazaka", "日向坂"]),

    # AKB48 Group
    ("AKB48 Group", "AKB48", "AKB48", ["AKB48"]),
    ("AKB48 Group", "SKE48", "SKE48", ["SKE48"]),
    ("AKB48 Group", "NMB48", "NMB48", ["NMB48"]),
    ("AKB48 Group", "HKT48", "HKT48", ["HKT48"]),
    ("AKB48 Group", "NGT48", "NGT48", ["NGT48"]),
    ("AKB48 Group", "STU48", "STU48", ["STU48"]),

    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", "=LOVE", ["=LOVE", "Equal Love", "イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", "≠ME", ["≠ME", "Not Equal ME", "Noime", "ノイミー"]),
    ("=LOVE / Sister Groups", "≒JOY", "≒JOY", ["≒JOY", "Nearly Equal Joy", "ニアジョイ"]),

    # Other Key Units
    ("Momoiro Clover Z", "Momoiro Clover Z", "Momoiro Clover Z", ["Momoiro Clover", "Momoclo"]),
    ("Babymetal", "BABYMETAL", "BABYMETAL", ["BABYMETAL"]),
]

PAGES_PER_TARGET = 3
BATCH_SIZE = 10


def load_catalog():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def make_affiliate_link(product_key):
    raw_path = f"product/{product_key}"
    encoded_path = urllib.parse.quote(raw_path, safe="")
    return f"https://www.cdjapan.co.jp/aff/click.cgi/Psetup/3085/{AFFILIATE_ID}/{encoded_path}"


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip() if text else ""


def is_relevant_product(card_text, canonical_artist, keywords, prod_key):
    if not keywords:
        return True
    lower_text = card_text.lower()
    pid_upper = str(prod_key).upper()

    # Strict check for Tanpopo
    if canonical_artist == "Tanpopo":
        if not any(pid_upper.startswith(pfx) for pfx in TANPOPO_VALID_PREFIXES):
            return False
        has_name = "tanpopo" in lower_text or "タンポポ" in card_text or "たんぽぽ" in card_text
        if not has_name:
            return False
        return any(sig in lower_text or sig in pid_upper.lower() for sig in keywords)

    for kw in keywords:
        kw_clean = kw.strip().lower()
        if len(kw_clean) <= 2:
            if re.search(r"\b" + re.escape(kw_clean) + r"\b", lower_text):
                return True
        else:
            if kw_clean in lower_text:
                return True
    return False


def extract_verified_products(html, category, canonical_artist, keywords):
    soup = BeautifulSoup(html, "html.parser")
    items_dict = {}

    cards = soup.select(".item-detail, .n-item, .item, .search-result-item, div[class*='item-']")
    seen_keys = set()

    for card in cards:
        link_el = card.select_one("a[href*='/product/']")
        if not link_el:
            continue

        href = link_el.get("href", "")
        match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
        if not match:
            continue

        prod_key = match.group(1)
        if prod_key in seen_keys:
            continue

        if prod_key.lower() in [
            "cart", "login", "help", "contact", "about",
            "tokuten", "ranking", "app"
        ]:
            continue

        seen_keys.add(prod_key)

        # Title
        title_el = (
            card.select_one(".title a")
            or card.select_one("a.item-title")
            or card.select_one(".title")
            or link_el
        )
        raw_title = clean_text(title_el.get_text()) if title_el else ""

        # Artist
        artist_el = (
            card.select_one(".artist")
            or card.select_one(".item-artist")
            or card.select_one(".cast")
        )
        raw_artist = clean_text(artist_el.get_text()) if artist_el else ""

        # Image
        img_el = card.select_one("img")
        img_url = ""
        if img_el:
            img_url = (
                img_el.get("src")
                or img_el.get("data-src")
                or img_el.get("data-original")
                or ""
            )
            if not raw_title and img_el.get("alt"):
                raw_title = clean_text(img_el.get("alt"))

        if not raw_title:
            continue

        if (
            not img_url
            or "spacer" in img_url
            or "blank" in img_url
            or "no_image" in img_url
        ):
            img_url = f"https://www.cdjapan.co.jp/pictures/l/{prod_key}.jpg"
        elif img_url.startswith("//"):
            img_url = "https:" + img_url
        elif img_url.startswith("/"):
            img_url = "https://www.cdjapan.co.jp" + img_url

        img_url = img_url.replace("/pictures/s/", "/pictures/l/").replace(
            "/pictures/m/", "/pictures/l/"
        )

        # Price
        price_el = (
            card.select_one(".price")
            or card.select_one(".item-price")
            or card.select_one(".price-value")
            or card.select_one("span.bold")
        )
        price_str = "Check CDJapan"
        price_num = 0
        if price_el:
            p_match = re.search(
                r"(\d[\d,]*\s*(?:yen|JPY|円)?)",
                clean_text(price_el.get_text()),
                re.IGNORECASE,
            )
            if p_match and p_match.group(1).strip():
                num_only = re.sub(r"[^\d]", "", p_match.group(1))
                if num_only:
                    price_num = int(num_only)
                    price_str = f"{price_num:,}yen"

        # Release Date
        card_text = card.get_text()
        rel_date = ""

        date_el = (
            card.select_one(".release_date")
            or card.select_one(".item-date")
            or card.select_one(".date")
        )
        if date_el:
            d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", date_el.get_text())
            if d_match:
                rel_date = d_match.group(1).replace("-", "/")

        if not rel_date:
            date_node = card.find(lambda el: el.name in ["span", "td", "p"] and "Release Date" in el.get_text())
            if date_node:
                d_match = re.search(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})", date_node.get_text())
                if d_match:
                    rel_date = d_match.group(1).replace("-", "/")

        if not rel_date:
            d_match = re.search(r"(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})", card_text)
            if d_match:
                y, m, d = d_match.group(1), d_match.group(2).zfill(2), d_match.group(3).zfill(2)
                rel_date = f"{y}/{m}/{d}"

        if not rel_date:
            d_match = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", card_text)
            if d_match:
                y, m, d = d_match.group(1), d_match.group(2).zfill(2), d_match.group(3).zfill(2)
                rel_date = f"{y}/{m}/{d}"

        if not rel_date:
            ym_match = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", card_text)
            if ym_match:
                y, m = ym_match.group(1), ym_match.group(2).zfill(2)
                rel_date = f"{y}/{m}/01"

        if not rel_date:
            year_match = re.search(r"\b(19\d\d|20\d\d)\b", raw_title)
            if year_match:
                rel_date = f"{year_match.group(1)}/01/01"

        if not rel_date:
            rel_date = "Available Now"

        searchable_card_text = f"{raw_title} {raw_artist} {clean_text(card_text)}"
        if not is_relevant_product(searchable_card_text, canonical_artist, keywords, prod_key):
            continue

        items_dict[prod_key] = {
            "id": prod_key,
            "title": raw_title,
            "artist": canonical_artist,
            "category": category,
            "price": price_str,
            "price_num": price_num,
            "release_date": rel_date,
            "image": img_url,
            "affiliate_url": make_affiliate_link(prod_key),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        }

    return list(items_dict.values())


def dismiss_popups(page):
    try:
        close_btn = page.locator("button.modal-close, .modal-close, button:has-text('Close'), button:has-text('Save'), .popup-close").first
        if close_btn.is_visible(timeout=250):
            close_btn.click(force=True)
            time.sleep(0.2)
    except Exception:
        pass


def execute_search_in_session(page, category, canonical_artist, query, keywords, max_pages):
    results = []
    print(f"\n-> In-Session Search Query for: {canonical_artist} ('{query}')")

    encoded_q = urllib.parse.quote_plus(query)

    for p_num in range(1, max_pages + 1):
        target_url = f"https://www.cdjapan.co.jp/searchuni?q={encoded_q}&page={p_num}"
        success = False

        for attempt in range(1, 3):
            try:
                # Direct navigation under the existing authenticated browser session with internal Referer
                page.set_extra_http_headers({
                    "Referer": "https://www.cdjapan.co.jp/",
                    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8"
                })

                page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                dismiss_popups(page)

                # Wait for product grid container to ensure hydration
                try:
                    page.wait_for_selector(".item-detail, .n-item, .item, .search-result-item, div[class*='item-']", timeout=5000)
                except Exception:
                    pass

                # Scroll to load any lazy elements
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.5)
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.8)

                html = page.content()
                verified = extract_verified_products(html, category, canonical_artist, keywords)
                print(f"   [Page {p_num}] Extracted {len(verified)} verified products")
                results.extend(verified)
                success = True
                break

            except Exception as e:
                print(f"   Attempt {attempt} notice on Page {p_num} for {canonical_artist}: {e}")
                time.sleep(2.0)

        if not success or (p_num == 1 and len(results) == 0):
            break

        time.sleep(random.uniform(1.8, 3.0))

    return results


def main():
    catalog = load_catalog()
    initial_count = len(catalog)
    print(f"Starting Catalog Sync. Current active items: {initial_count}")

    batch = random.sample(TARGET_GROUPS, min(BATCH_SIZE, len(TARGET_GROUPS)))

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled"
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                " (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
        )

        # 1. Warm up CDJapan cookies and security tokens
        warmup_page = context.new_page()
        try:
            warmup_page.goto("https://www.cdjapan.co.jp/", wait_until="domcontentloaded", timeout=25000)
            dismiss_popups(warmup_page)
            time.sleep(1.5)
        except Exception as e_warm:
            print(f"Warmup notice: {e_warm}")
        finally:
            warmup_page.close()

        new_total = 0

        # 2. Iterate through target batch using isolated tabs with session persistence
        for idx, (cat, artist, query, keywords) in enumerate(batch, 1):
            print(f"\n[{idx}/{len(batch)}] Scraping Target: {artist}")
            page = context.new_page()
            try:
                items = execute_search_in_session(
                    page, cat, artist, query, keywords, max_pages=PAGES_PER_TARGET
                )
                added_for_artist = 0

                for it in items:
                    pid = it["id"]
                    if pid not in catalog:
                        added_for_artist += 1
                        new_total += 1
                    catalog[pid] = it

                print(
                    f"   => {artist}: Found {len(items)} items"
                    f" ({added_for_artist} new to database)"
                )
            except Exception as e_artist:
                print(f"   => Error scraping {artist}: {e_artist}")
            finally:
                page.close()

            time.sleep(random.uniform(2.5, 4.0))

        browser.close()

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    final_count = len(catalog)
    print(f"\n==========================================")
    print(f"Sync Complete! Added {new_total} new releases.")
    print(f"Total live catalog items: {final_count}")
    print(f"==========================================")


if __name__ == "__main__":
    main()
