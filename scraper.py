"""
IdolJapan.store — Official Japanese Idol CDJapan Catalog Scraper
Combines Playwright session warmup, lazy-scroll rendering, authentic group signatures,
direct Person ID routing, and multi-query aliasing.
"""

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
STATE_FILE = "scraper_state.json"
PAGES_PER_TARGET = 3

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12"
}

TANPOPO_AUTHENTIC_SIGNATURES = [
    "last kiss", "motto", "seinaru kane", "otome pasta",
    "koi wo shichaimashita", "ouji-sama", "oujisama", "kousaten",
    "tanpopo 1", "all of tanpopo", "single v clips"
]
TANPOPO_VALID_PREFIXES = ("EPCE", "EPBE", "EPTE", "EPDE", "PKCP", "PKBP", "UFBW", "UFXW")

NOIME_AUTHENTIC_SIGNATURES = [
    "≠me", "not equal me", "ノイミー", "noime",
    "kimi wa kono natsu", "mahoroba asterisk", "chocolate melancholy",
    "su kida", "hanikami short", "tenshi wa doko e", "antihime",
    "anti-confiture", "omoide champion", "last chance, last dance",
    "natsumatsuri koi shitau", "kimi no oto dattanda", "chozetsu shoujo",
    "springtime in you", "hatsukoi camouflage"
]

NIAGO_AUTHENTIC_SIGNATURES = [
    "nearly equal joy", "nearly equal", "≒joy", "ニアジョイ",
    "waratte flatte", "chou kodoku", "taiikukan disco", "shonichi",
    "kitto, aoi", "yuransen", "daisuki da", "hatsukoi sync", "kimi to watashi no uta",
    "muda de ii", "yubiwa to aribai", "watashi, idol sengen"
]

TARGET_GROUPS = [
    # Hello! Project — Active Groups & Units
    ("Hello! Project", "Morning Musume", ["Morning Musume", "モーニング娘"], [
        "Morning Musume", "Morning Musume.", "Petitmoni", "Pucchimoni", "プッチモニ",
        "Chokotto Love", "Baby! Koi ni Knock Out"
    ]),
    ("Hello! Project", "ANGERME", ["ANGERME", "アンジュルム"], ["ANGERME", "Smileage", "S/mileage"]),
    ("Hello! Project", "Juice=Juice", ["Juice=Juice"], ["Juice=Juice"]),
    ("Hello! Project", "Tsubaki Factory", ["Tsubaki Factory", "つばきファクトリー"], ["Tsubaki Factory"]),
    ("Hello! Project", "BEYOOOOONDS", ["BEYOOOOONDS", "ビヨーンズ"], ["BEYOOOOONDS"]),
    ("Hello! Project", "OCHA NORMA", ["OCHA NORMA", "オチャノーマ"], ["OCHA NORMA", "OCHA"]),
    ("Hello! Project", "Rosy Chronicle", ["Rosy Chronicle", "ロージークロニクル"], ["Rosy Chronicle", "Rosy"]),

    # Hello Pro Kenshuusei
    ("Hello! Project", "Hello Pro Kenshuusei", [
        "Hello Pro Kenshusei",
        "ハロプロ研修生",
        "Hello Pro Kenshuusei"
    ], [
        "Hello Pro Kenshuusei", "Hello Pro Kenshusei", "Hello! Pro Kenshuusei",
        "ハロプロ研修生", "Kenshuusei", "Kenshusei", "Hello Pro Egg", "ハロプロエッグ"
    ]),

    # Hello! Project — Past Groups & Subunits
    ("Hello! Project", "Minimoni", ["Minimoni", "ミニモニ"], ["Minimoni", "Mini Moni", "Mini-Moni", "ミニモニ", "ミニモニ。"]),
    ("Hello! Project", "Berryz Kobo", ["Berryz Kobo", "Berryz工房"], ["Berryz Kobo", "Berryz", "Berryz工房"]),
    ("Hello! Project", "℃-ute", ["C-ute", "℃-ute"], ["℃-ute", "C-ute", "Cute"]),
    ("Hello! Project", "Buono!", ["Buono!"], ["Buono!"]),
    ("Hello! Project", "Country Girls", ["Country Girls", "カントリー・ガールズ"], ["Country Girls", "Country Musume", "カントリー・ガールズ", "カントリー娘", "Country"]),

    # Kobushi Factory
    ("Hello! Project", "Kobushi Factory", [
        "Kobushi-Factory",
        "Kobushi Factory",
        "こぶしファクトリー"
    ], [
        "Kobushi Factory", "Kobushi-Factory", "こぶしファクトリー", "こぶし"
    ]),

    ("Hello! Project", "Melon Kinenbi", ["Melon Kinenbi", "メロン記念日"], ["Melon Kinenbi", "メロン記念日", "メロン"]),
    ("Hello! Project", "Tanpopo", ["Tanpopo", "タンポポ"], TANPOPO_AUTHENTIC_SIGNATURES),
    ("Hello! Project", "v-u-den", ["Biyuden", "美勇伝"], ["Biyuden", "v-u-den", "V-u-den", "美勇伝", "ajisai ai ai", "koi no nukegara"]),

    # Hello! Project — OG Post-Graduation Units
    ("Hello! Project", "LoVendoR", ["LoVendoR", "ラベンダー"], ["LoVendoR", "LoVendoЯ", "ラベンダー", "Reina Tanaka"]),
    ("Hello! Project", "PINK CRES.", ["PINK CRES."], ["PINK CRES.", "PINK CRES", "ピンククレス", "Miyabi Natsuyaki"]),

    # Hello! Project — Soloists & OGs
    ("Hello! Project", "Sayumi Michishige", ["Sayumi Michishige", "道重さゆみ"], [
        "Sayumi Michishige", "Michishige Sayumi", "道重さゆみ", "SAYUMINGLANDOLL", "SAYUMING"
    ]),
    ("Hello! Project", "Aya Matsuura", ["Aya Matsuura", "松浦亜弥"], ["Aya Matsuura", "Matsuura Aya", "松浦亜弥"]),
    ("Hello! Project", "Maki Goto", ["Maki Goto", "後藤真希"], ["Maki Goto", "Goto Maki", "後藤真希"]),
    ("Hello! Project", "Natsumi Abe", ["Natsumi Abe", "安倍なつみ"], ["Natsumi Abe", "Abe Natsumi", "安倍なつみ"]),
    ("Hello! Project", "Erina Mano", ["Erina Mano", "真野恵里菜"], ["Erina Mano", "Mano Erina", "真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", ["Airi Suzuki", "鈴木愛理"], ["Airi Suzuki", "Suzuki Airi", "鈴木愛理"]),

    # Up-Front / H!P Alumni
    ("Up-Front Alumni", "You Kikkawa", ["You Kikkawa", "吉川友"], [
        "You Kikkawa", "Kikkawa You", "Kikkawa Yu", "吉川友", "Kikkawa"
    ]),
    ("Up-Front Alumni", "Up Up Girls (Kari)", ["Up Up Girls (Kari)", "アップアップガールズ(仮)"], [
        "Up Up Girls (Kari)", "Up Up Girls (kari)", "アップアップガールズ(仮)", "アプガ(仮)",
        "アップアップガールズ（仮）", "UpUpGirls(Kari)"
    ]),

    # Up Up Girls (2) — Japanese Kana & Space Normalized Queries
    ("Up-Front Alumni", "Up Up Girls (2)", [
        "アップアップガールズ(2)",
        "Up Up Girls 2",
        "アップアップガールズ（2）"
    ], [
        "Up Up Girls (2)", "アップアップガールズ(2)", "アプガ2", "アップアップガールズ（2）",
        "UpUpGirls(2)", "Up Up Girls 2"
    ]),

    # AKB48 Group
    ("AKB48 Group", "AKB48", ["AKB48"], ["AKB48"]),
    ("AKB48 Group", "SKE48", ["SKE48"], ["SKE48"]),
    ("AKB48 Group", "NMB48", ["NMB48"], ["NMB48"]),
    ("AKB48 Group", "HKT48", ["HKT48"], ["HKT48"]),
    ("AKB48 Group", "NGT48", ["NGT48"], ["NGT48"]),
    ("AKB48 Group", "STU48", ["STU48"], ["STU48"]),
    ("AKB48 Group", "Sayaka Yamamoto", ["Sayaka Yamamoto", "山本彩"], ["Sayaka Yamamoto", "Yamamoto Sayaka", "山本彩", "Sayanee"]),

    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46", ["Nogizaka46", "乃木坂46"], ["Nogizaka46", "Nogizaka", "乃木坂"]),
    ("Sakamichi Series", "Sakurazaka46", ["Sakurazaka46", "櫻坂46"], ["Sakurazaka46", "Sakurazaka", "櫻坂"]),
    ("Sakamichi Series", "Hinatazaka46", ["Hinatazaka46", "日向坂46"], ["Hinatazaka46", "Hinatazaka", "日向坂"]),
    ("Sakamichi Series", "Keyakizaka46", ["Keyakizaka46", "欅坂46"], ["Keyakizaka46", "Keyakizaka", "欅坂46", "欅坂"]),
    ("Sakamichi Series", "22/7", ["22/7", "ナナブンノニジュウニ"], ["22/7", "Nanabun no Nijuuni", "ナナブンノニジュウニ", "ナナニジ"]),

    # Stardust Planet
    ("Stardust Planet", "Momoiro Clover Z", ["Momoiro Clover Z", "ももいろクローバーZ"], ["Momoiro Clover", "Momoclo", "ももいろクローバーZ", "ももクロ"]),
    ("Stardust Planet", "Shiritsu Ebisu Chugaku", ["Shiritsu Ebisu Chugaku", "私立恵比寿中学"], ["Shiritsu Ebisu Chugaku", "Ebichu", "私立恵比寿中学", "エビ中"]),
    ("Stardust Planet", "Chou Tokimeki Sendenbu", ["Cho Tokimeki Sendenbu", "超ときめき♡宣伝部"], [
        "Cho Tokimeki Sendenbu", "Chou Tokimeki Sendenbu", "Tokimeki Sendenbu", "Tokisen", "超ときめき♡宣伝部", "ときめき♡宣伝部", "とき宣"
    ]),

    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", ["=LOVE", "イコールラブ"], ["=LOVE", "Equal Love", "イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", ["ノイミー", "≠ME"], NOIME_AUTHENTIC_SIGNATURES),
    ("=LOVE / Sister Groups", "≒JOY", ["Nearly Equal Joy", "≒JOY"], NIAGO_AUTHENTIC_SIGNATURES),

    # KAWAII LAB.
    ("KAWAII LAB.", "FRUITS ZIPPER", ["FRUITS ZIPPER", "フルーツジッパー"], ["FRUITS ZIPPER", "Fruits Zipper", "ふるっぱー", "KAWAII LAB."]),
    ("KAWAII LAB.", "CUTIE STREET", ["CUTIE STREET", "キューティーストリート"], ["CUTIE STREET", "Cutie Street", "きゅーすと", "KAWAII LAB."]),

    # Modern Idols
    ("Modern Idols", "NiziU", ["NiziU", "ニジュー"], ["NiziU", "ニジュー"]),
    ("Modern Idols", "ME:I", ["ME:I", "ミーアイ"], ["ME:I", "ミーアイ", "Produce 101"]),

    # Babymetal
    ("Babymetal", "BABYMETAL", ["BABYMETAL"], ["BABYMETAL"]),
]


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


def parse_normalized_date(date_raw_str):
    if not date_raw_str:
        return ""
    text = clean_text(date_raw_str)

    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m1:
        y, m, d = m1.group(1), m1.group(2).zfill(2), m1.group(3).zfill(2)
        return f"{y}/{m}/{d}"

    match_jp = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if match_jp:
        y, m, d = match_jp.group(1), match_jp.group(2).zfill(2), match_jp.group(3).zfill(2)
        return f"{y}/{m}/{d}"

    match_en = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if match_en:
        mon_str = match_en.group(1).lower()
        if mon_str in MONTH_MAP:
            m = MONTH_MAP[mon_str]
            d = match_en.group(2).zfill(2)
            y = match_en.group(3)
            return f"{y}/{m}/{d}"

    match_en_rev = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", text)
    if match_en_rev:
        mon_str = match_en_rev.group(2).lower()
        if mon_str in MONTH_MAP:
            d = match_en_rev.group(1).zfill(2)
            m = MONTH_MAP[mon_str]
            y = match_en_rev.group(3)
            return f"{y}/{m}/{d}"

    match_ym = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", text)
    if match_ym:
        y, m = match_ym.group(1), match_ym.group(2).zfill(2)
        return f"{y}/{m}/01"

    return ""


def is_date_upcoming(date_str):
    if not date_str:
        return False
    m = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", date_str)
    if not m:
        return False
    val = (int(m.group(1)) * 10000) + (int(m.group(2)) * 100) + int(m.group(3))
    now = datetime.utcnow()
    today_val = (now.year * 10000) + (now.month * 100) + now.day
    return val > today_val


def is_relevant_product(card_text, canonical_artist, keywords, prod_key, is_direct_person=False):
    if is_direct_person:
        return True

    if not keywords:
        return True
    lower_text = card_text.lower()
    pid_upper = str(prod_key).upper()

    if canonical_artist == "Tanpopo":
        if not any(pid_upper.startswith(pfx) for pfx in TANPOPO_VALID_PREFIXES):
            return False
        has_name = "tanpopo" in lower_text or "タンポポ" in card_text or "たんぽぽ" in card_text
        if not has_name:
            return False
        return any(sig in lower_text or sig in pid_upper.lower() for sig in keywords)

    if canonical_artist == "v-u-den":
        if pid_upper.startswith("PKCP-50") or pid_upper.startswith("PKBP-50"):
            return True

    if canonical_artist == "Up Up Girls (Kari)":
        if "(2)" in lower_text or "（2）" in card_text or "アプガ2" in card_text:
            return False

    if canonical_artist == "Up Up Girls (2)":
        if "(2)" in lower_text or "（2）" in card_text or "アプガ2" in card_text or "up up girls 2" in lower_text:
            return True

    if canonical_artist == "≠ME":
        if "≠me" in lower_text or "ノイミー" in card_text or "not equal me" in lower_text or "noime" in lower_text:
            return True
        return any(sig in lower_text for sig in NOIME_AUTHENTIC_SIGNATURES)

    if canonical_artist == "≒JOY":
        if "nearly equal" in lower_text or "≒joy" in lower_text or "ニアジョイ" in card_text:
            return True
        return any(sig in lower_text for sig in NIAGO_AUTHENTIC_SIGNATURES)

    for kw in keywords:
        kw_clean = kw.strip().lower()
        if len(kw_clean) <= 2:
            if re.search(r"\b" + re.escape(kw_clean) + r"\b", lower_text):
                return True
        else:
            if kw_clean in lower_text:
                return True
    return False


def extract_verified_products(html, category, canonical_artist, keywords, is_direct_person=False):
    soup = BeautifulSoup(html, "html.parser")
    items_dict = {}

    cards = soup.select(".item-detail, .n-item, div.item, tr.item, div.search-result-item, li.item")
    if not cards:
        cards = soup.find_all(
            lambda el: el.name in ["div", "li", "tr"]
            and el.get("class")
            and any(c in ["item-detail", "n-item", "item"] for c in el.get("class"))
        )

    seen_keys = set()

    for card in cards:
        link_el = card.select_one("a[href*='/product/']")
        if not link_el:
            continue

        href = link_el.get("href", "")
        match = re.search(r"/product/([A-Za-z0-9_-]+)", href)
        if not match:
            continue

        prod_key = match.group(1).upper()
        if prod_key in seen_keys:
            continue

        if prod_key.lower() in [
            "cart", "login", "help", "contact", "about",
            "tokuten", "ranking", "app", "review", "index"
        ]:
            continue

        seen_keys.add(prod_key)

        title_el = (
            card.select_one(".title a")
            or card.select_one("a.item-title")
            or card.select_one(".title")
            or card.select_one("h3 a")
            or card.select_one("h2 a")
            or link_el
        )
        raw_title = clean_text(title_el.get_text()) if title_el else ""

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

        if not raw_title or len(raw_title) < 2:
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

        img_url = img_url.replace("/pictures/s/", "/pictures/l/").replace("/pictures/m/", "/pictures/l/")

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
                    price_str = f"¥{price_num:,}"

        rel_date = ""
        for sel in [".release_date", ".item-date", ".date", "td.date", "span.date"]:
            node = card.select_one(sel)
            if node:
                parsed = parse_normalized_date(node.get_text())
                if parsed:
                    rel_date = parsed
                    break

        if not rel_date:
            date_nodes = card.find_all(
                lambda el: el.name in ["span", "td", "p", "div", "li"]
                and ("release" in el.get_text().lower() or "発売" in el.get_text())
            )
            for d_node in date_nodes:
                parsed = parse_normalized_date(d_node.get_text())
                if parsed:
                    rel_date = parsed
                    break

        if not rel_date:
            rel_date = parse_normalized_date(card.get_text())

        if not rel_date:
            rel_date = "Available Now"

        card_text_lower = card.get_text().lower()
        if is_date_upcoming(rel_date) or "pre-order" in card_text_lower:
            availability = "preorder"
        elif "out of print" in card_text_lower or "sold out" in card_text_lower or "archive" in card_text_lower:
            availability = "oop"
        else:
            availability = "instock"

        searchable_card_text = f"{raw_title} {clean_text(card.get_text())}"
        if not is_relevant_product(searchable_card_text, canonical_artist, keywords, prod_key, is_direct_person=is_direct_person):
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
            "availability": availability,
            "affiliate_url": make_affiliate_link(prod_key),
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d"),
        }

    return list(items_dict.values())


def dismiss_popups(page):
    try:
        page.keyboard.press("Escape")
        close_btn = page.locator(
            "button.modal-close, .modal-close, button:has-text('Close'), button:has-text('Save'), .popup-close, #btn_close"
        ).first
        if close_btn.is_visible(timeout=300):
            close_btn.click(force=True)
            time.sleep(0.2)
    except Exception:
        pass


def execute_artist_search(page, category, canonical_artist, target_query_or_url, keywords, max_pages):
    results = []
    is_direct_person = target_query_or_url.startswith("http://") or target_query_or_url.startswith("https://")
    print(f"\n-> Querying: {canonical_artist} ('{target_query_or_url}')", flush=True)

    for p_num in range(1, max_pages + 1):
        if is_direct_person:
            sep = "&" if "?" in target_query_or_url else "?"
            target_url = f"{target_query_or_url}{sep}page={p_num}&order=reldate_desc"
        else:
            encoded_q = urllib.parse.quote_plus(target_query_or_url)
            target_url = f"https://www.cdjapan.co.jp/searchuni?q={encoded_q}&opt.include_eoa=1&order=reldate_desc&page={p_num}"

        extracted_on_page = []

        for attempt in range(1, 3):
            try:
                page.set_extra_http_headers({
                    "Referer": "https://www.cdjapan.co.jp/",
                    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8"
                })

                response = page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                dismiss_popups(page)

                current_title = page.title().strip()
                if not current_title or (response and response.status in [429, 403, 503]):
                    print(f"   [Notice] Backing off on attempt {attempt}...", flush=True)
                    time.sleep(3.0)
                    continue

                try:
                    page.wait_for_selector(
                        ".item-detail, .n-item, div.item, tr.item, div.search-result-item, .item_list",
                        timeout=7000
                    )
                except Exception:
                    pass

                page.evaluate("window.scrollBy(0, 750)")
                time.sleep(0.5)
                page.evaluate("window.scrollBy(0, 850)")
                time.sleep(0.8)

                html = page.content()
                extracted_on_page = extract_verified_products(
                    html, category, canonical_artist, keywords, is_direct_person=is_direct_person
                )

                if len(extracted_on_page) == 0 and attempt == 1:
                    time.sleep(2.0)
                    continue

                print(f"   [Page {p_num}] Extracted {len(extracted_on_page)} verified items", flush=True)
                results.extend(extracted_on_page)
                break

            except Exception as e:
                print(f"   Attempt {attempt} notice on Page {p_num}: {e}", flush=True)
                time.sleep(2.5)

        if p_num == 1 and len(extracted_on_page) == 0:
            break

        time.sleep(random.uniform(1.5, 2.5))

    return results


def get_active_targets():
    raw_filter = os.environ.get("TARGET_ARTIST", "").strip()
    if not raw_filter or raw_filter.lower() == "all groups":
        return TARGET_GROUPS

    if "updated 3 groups" in raw_filter.lower():
        target_names = ["Up Up Girls (2)", "Hello Pro Kenshuusei", "Kobushi Factory"]
        return [g for g in TARGET_GROUPS if g[1] in target_names]

    matched = [g for g in TARGET_GROUPS if g[1].lower() == raw_filter.lower()]
    return matched if matched else TARGET_GROUPS


def main():
    catalog = load_catalog()
    initial_count = len(catalog)
    print(f"Starting Catalog Sync. Current active items: {initial_count}", flush=True)

    active_groups = get_active_targets()
    print(f"Active Filter: Running {len(active_groups)} artist group(s): {[g[1] for g in active_groups]}", flush=True)

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

        print("Initializing session on CDJapan...", flush=True)
        warmup_page = context.new_page()
        try:
            warmup_page.goto("https://www.cdjapan.co.jp/", wait_until="domcontentloaded", timeout=25000)
            dismiss_popups(warmup_page)
            time.sleep(1.5)
        except Exception as e_warm:
            print(f"Warmup notice: {e_warm}", flush=True)
        finally:
            warmup_page.close()

        new_total = 0

        for idx, (cat, artist, targets, keywords) in enumerate(active_groups, 1):
            print(f"\n[{idx}/{len(active_groups)}] Scraping Target Group: {artist}", flush=True)
            target_page = context.new_page()
            artist_items_map = {}

            try:
                for target_q in targets:
                    items = execute_artist_search(
                        target_page, cat, artist, target_q, keywords, max_pages=PAGES_PER_TARGET
                    )
                    for it in items:
                        pid = it["id"]
                        if pid not in artist_items_map:
                            artist_items_map[pid] = it

                added_for_artist = 0
                for pid, it in artist_items_map.items():
                    if pid not in catalog:
                        added_for_artist += 1
                        new_total += 1
                    catalog[pid] = it

                print(
                    f"   => {artist}: Extracted {len(artist_items_map)} unique releases"
                    f" ({added_for_artist} new to database)",
                    flush=True
                )
            except Exception as e_artist:
                print(f"   => Error scraping {artist}: {e_artist}", flush=True)
            finally:
                target_page.close()

            time.sleep(random.uniform(2.0, 4.0))

        browser.close()

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    state_data = {
        "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_catalog_size": len(catalog),
        "items_added_this_pass": new_total,
        "active_groups": [g[1] for g in active_groups]
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, indent=2, ensure_ascii=False)

    final_count = len(catalog)
    print(f"\n==========================================", flush=True)
    print(f"Sync Complete! Added {new_total} new releases.", flush=True)
    print(f"Total live catalog items: {final_count}", flush=True)
    print(f"==========================================", flush=True)


if __name__ == "__main__":
    main()
