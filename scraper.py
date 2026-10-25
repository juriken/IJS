"""
IdolJapan.store — Official Japanese Idol CDJapan Catalog Scraper
Combines Playwright session warmup, lazy-scroll rendering, authentic group signatures,
direct Person ID routing, calendar-verified date parsing, and multi-query aliasing.
Deep pagination support with exponential jitter backoff, resilient retry ladders,
and negative boyband/media filters.
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

DEFAULT_PAGES_ALL = 10
DEFAULT_PAGES_TARGETED = 200

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12
}

ALL_UPFRONT_PREFIXES = (
    "EPCE", "EPBE", "EPXE", "EPTE", "EPDE",
    "PKCP", "PKBP",
    "HKCN", "HKBN", "HKXN",
    "UFBW", "UFXW",
    "TGBS", "TGXF",
    "DAKU", "DCFGDS", "NEOODY"
)

TANPOPO_AUTHENTIC_SIGNATURES = [
    "last kiss", "motto", "seinaru kane", "otome pasta",
    "koi wo shichaimashita", "ouji-sama", "oujisama", "kousaten",
    "tanpopo 1", "all of tanpopo", "single v clips"
]

COUNTRY_GIRLS_SIGNATURES = [
    "country girls", "country musume", "カントリー・ガールズ", "カントリー娘",
    "tsugunaga", "嗣永桃子", "yamaki", "山木梨沙", "inaba", "稲場愛香",
    "morito", "森戸知沙希", "ozeki", "小関舞", "shimamura", "島村嬉唄",
    "yanagawa", "梁川奈々美", "funaki", "船木結", "satoda", "里田まい",
    "engeki joshi bu", "engeki jyoshi bu", "演劇女子部", "kizetsu suru", "気絶するほど"
]

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

MALE_BOYBAND_PATTERNS = [
    r"\bsnow man\b", r"\bsixtones\b", r"\bking & prince\b", r"\bnaniwa danshi\b",
    r"\bhey! say! jump\b", r"\bsexy zone\b", r"\btimelesz\b", r"\btravis japan\b",
    r"\bkis-my-ft2\b", r"\bkanjani\b", r"\bsuper eight\b", r"\bkat-tun\b",
    r"\bwest\.\b", r"\barashi\b", r"\bexile\b", r"\bsandaime\b", r"\bgenerations\b",
    r"\bthe rampage\b", r"\bfantastics\b", r"\bballistik boyz\b", r"\bjo1\b", r"\bini\b",
    r"\bbe:first\b", r"\bmazzel\b", r"\b&team\b", r"\bstray kids\b",
    r"\btomorrow x together\b", r"\btxt\b", r"\bseventeen\b", r"\bbts\b",
    r"\benhypen\b", r"\bnct\b", r"\bateez\b", r"\bzerobaseone\b", r"\briize\b"
]

NON_IDOL_MEDIA_PATTERNS = [
    r"\bkamen rider\b", r"\bgundam\b", r"\bdragon ball\b", r"\bone piece\b",
    r"\bdetective conan\b", r"\bpokemon\b", r"\bdigimon\b", r"\byu-gi-oh\b",
    r"\btouken ranbu\b", r"\bhypnosis mic\b", r"\bensemble stars\b",
    r"\btwisted wonderland\b", r"\bjujutsu kaisen\b", r"\bdemon slayer\b",
    r"\bclassical guitar\b", r"\bbluegrass\b", r"\bboard game\b"
]

PROTECTED_SUBUNITS = {
    "Tanpopo", "Minimoni", "W", "v-u-den", "GAM",
    "Tsukishima Kirari", "Taiyo to Ciscomoon", "You Kikkawa",
    "Maki Goto", "Aya Matsuura", "Natsumi Abe", "Miki Fujimoto",
    "Erina Mano", "Airi Suzuki", "Sayumi Michishige", "Buono!",
    "Karin Miyamoto"
}

LEGACY_ROSTER_GROUPS = {
    "Tanpopo", "Minimoni", "W", "v-u-den", "GAM", "Taiyo to Ciscomoon",
    "Melon Kinenbi", "Berryz Kobo", "℃-ute", "Buono!", "Country Girls",
    "Kobushi Factory", "LoVendoR", "PINK CRES.", "Tsukishima Kirari",
    "Not yet", "no3b", "French Kiss", "Watarirouka Hashiritai"
}

TARGET_GROUPS = [
    # Hello! Project — Active Groups & Units
    ("Hello! Project", "Morning Musume", [
        "Morning Musume", "モーニング娘", "モーニング娘。"
    ], [
        "Morning Musume", "Morning Musume.", "モーニング娘", "モーニング娘。",
        "Petitmoni", "Pucchimoni", "プッチモニ", "Chokotto Love", "Baby! Koi ni Knock Out"
    ]),
    ("Hello! Project", "ANGERME", [
        "ANGERME", "アンジュルム", "S mileage", "スマイレージ", "Smileage"
    ], [
        "ANGERME", "アンジュルム", "Smileage", "S/mileage", "S mileage", "スマイレージ", "s / mileage", "s・mileage"
    ]),
    ("Hello! Project", "Juice=Juice", ["Juice=Juice", "ジュースジュース"], ["Juice=Juice", "ジュースジュース"]),
    ("Hello! Project", "Tsubaki Factory", ["Tsubaki Factory", "つばきファクトリー"], ["Tsubaki Factory", "つばきファクトリー"]),
    ("Hello! Project", "BEYOOOOONDS", ["BEYOOOOONDS", "ビヨーンズ"], ["BEYOOOOONDS", "ビヨーンズ"]),
    ("Hello! Project", "OCHA NORMA", ["OCHA NORMA", "オチャノーマ"], ["OCHA NORMA", "オチャノーマ", "OCHA"]),
    ("Hello! Project", "Rosy Chronicle", ["Rosy Chronicle", "ロージークロニクル"], ["Rosy Chronicle", "ロージークロニクル", "Rosy"]),

    # Hello Pro Kenshuusei
    ("Hello! Project", "Hello Pro Kenshuusei", [
        "Hello Pro Kenshusei", "ハロプロ研修生", "Hello Pro Kenshuusei"
    ], [
        "Hello Pro Kenshuusei", "Hello Pro Kenshusei", "Hello! Pro Kenshuusei",
        "ハロプロ研修生", "Kenshuusei", "Kenshusei", "Hello Pro Egg", "ハロプロエッグ"
    ]),

    # Hello! Project — Past Groups & Subunits
    ("Hello! Project", "Minimoni", ["Minimoni", "ミニモニ", "ミニモニ。"], ["Minimoni", "Mini Moni", "Mini-Moni", "ミニモニ", "ミニモニ。"]),
    ("Hello! Project", "Berryz Kobo", ["Berryz Kobo", "Berryz工房"], ["Berryz Kobo", "Berryz", "Berryz工房"]),
    ("Hello! Project", "℃-ute", ["C-ute", "℃-ute"], ["℃-ute", "C-ute", "Cute"]),
    ("Hello! Project", "Buono!", ["Buono!"], ["Buono!"]),
    ("Hello! Project", "Country Girls", ["Country Girls", "カントリー・ガールズ"], COUNTRY_GIRLS_SIGNATURES),
    ("Hello! Project", "Kobushi Factory", [
        "Kobushi-Factory", "Kobushi Factory", "こぶしファクトリー"
    ], [
        "Kobushi Factory", "Kobushi-Factory", "こぶしファクトリー", "こぶし"
    ]),
    ("Hello! Project", "Melon Kinenbi", ["Melon Kinenbi", "メロン記念日"], ["Melon Kinenbi", "メロン記念日", "メロン"]),
    ("Hello! Project", "Tanpopo", ["Tanpopo", "タンポポ"], TANPOPO_AUTHENTIC_SIGNATURES),
    ("Hello! Project", "v-u-den", ["Biyuden", "v-u-den", "美勇伝"], ["Biyuden", "v-u-den", "V-u-den", "美勇伝", "ajisai ai ai", "koi no nukegara"]),
    ("Hello! Project", "W", ["W (Double You)", "ダブルユー", "W [Double You]"], ["W (Double You)", "ダブルユー", "Nozomi Tsuji", "Ai Kago", "w [double you]"]),
    ("Hello! Project", "GAM", ["GAM", "ギャム"], ["GAM", "ギャム", "Aya Matsuura", "Miki Fujimoto"]),
    ("Hello! Project", "Taiyo to Ciscomoon", ["太陽とシスコムーン", "Taiyo to Ciscomoon"], ["太陽とシスコムーン", "Taiyo to Ciscomoon", "T&Cボンバー", "T&C Bomber"]),

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
    ("Hello! Project", "Miki Fujimoto", ["Miki Fujimoto", "藤本美貴"], ["Miki Fujimoto", "Fujimoto Miki", "藤本美貴", "Mikitty"]),
    ("Hello! Project", "Tsukishima Kirari", ["月島きらり", "Tsukishima Kirari", "きらりん☆レボリューション"], ["月島きらり", "Tsukishima Kirari", "久住小春", "Koharu Kusumi", "きらりん"]),
    ("Hello! Project", "Karin Miyamoto", ["Karin Miyamoto", "宮本佳林"], ["Karin Miyamoto", "Miyamoto Karin", "宮本佳林"]),

    # Up-Front / H!P Alumni
    ("Up-Front Alumni", "You Kikkawa", ["You Kikkawa", "吉川友"], [
        "You Kikkawa", "Kikkawa You", "Kikkawa Yu", "吉川友", "Kikkawa"
    ]),
    ("Up-Front Alumni", "Up Up Girls (Kari)", ["Up Up Girls (Kari)", "アップアップガールズ(仮)"], [
        "Up Up Girls (Kari)", "Up Up Girls (kari)", "アップアップガールズ(仮)", "アプガ(仮)",
        "アップアップガールズ（仮）", "UpUpGirls(Kari)"
    ]),
    ("Up-Front Alumni", "Up Up Girls (2)", [
        "アップアップガールズ(2)", "Up Up Girls 2", "アップアップガールズ（2）"
    ], [
        "Up Up Girls (2)", "アップアップガールズ(2)", "アプガ2", "アップアップガールズ（2）",
        "UpUpGirls(2)", "Up Up Girls 2"
    ]),

    # AKB48 Group — Main Groups & Subunits
    ("AKB48 Group", "AKB48", ["AKB48"], ["AKB48"]),
    ("AKB48 Group", "SKE48", ["SKE48"], ["SKE48"]),
    ("AKB48 Group", "NMB48", ["NMB48"], ["NMB48"]),
    ("AKB48 Group", "HKT48", ["HKT48"], ["HKT48"]),
    ("AKB48 Group", "NGT48", ["NGT48"], ["NGT48"]),
    ("AKB48 Group", "STU48", ["STU48"], ["STU48"]),
    ("AKB48 Group", "Not yet", ["Not yet", "ノットイェット"], ["Not yet", "ノットイェット", "Oshima Yuko", "Sashihara Rino"]),
    ("AKB48 Group", "no3b", ["no3b", "ノースリーブス"], ["no3b", "No Sleeves", "ノースリーブス"]),
    ("AKB48 Group", "French Kiss", ["French Kiss", "フレンチ・キス"], ["French Kiss", "フレンチ・キス", "Kashiwagi Yuki"]),
    ("AKB48 Group", "Watarirouka Hashiritai", ["渡り廊下走り隊", "Watarirouka Hashiritai"], ["渡り廊下走り隊", "Watarirouka Hashiritai", "Watarirouka Hashiritai 7", "Watanabe Mayu"]),

    # AKB48 Group — Legendary Soloists & Graduates
    ("AKB48 Group", "Sayaka Yamamoto", ["Sayaka Yamamoto", "山本彩"], ["Sayaka Yamamoto", "Yamamoto Sayaka", "山本彩", "Sayanee"]),
    ("AKB48 Group", "Atsuko Maeda", ["Atsuko Maeda", "前田敦子"], ["Atsuko Maeda", "Maeda Atsuko", "前田敦子"]),
    ("AKB48 Group", "Yuko Oshima", ["Yuko Oshima", "大島優子"], ["Yuko Oshima", "Oshima Yuko", "大島優子"]),
    ("AKB48 Group", "Mayu Watanabe", ["Mayu Watanabe", "渡辺麻友"], ["Mayu Watanabe", "Watanabe Mayu", "渡辺麻友", "Mayuyu"]),
    ("AKB48 Group", "Yuki Kashiwagi", ["Yuki Kashiwagi", "柏木由紀"], ["Yuki Kashiwagi", "Kashiwagi Yuki", "柏木由紀", "Yukirin"]),
    ("AKB48 Group", "Rino Sashihara", ["Rino Sashihara", "指原莉乃"], ["Rino Sashihara", "Sashihara Rino", "指原莉乃", "Sashiko"]),
    ("AKB48 Group", "Tomomi Itano", ["Tomomi Itano", "板野友美"], ["Tomomi Itano", "Itano Tomomi", "板野友美", "Tomochin"]),

    # Sakamichi Series & Rivals
    ("Sakamichi Series", "Nogizaka46", ["Nogizaka46", "乃木坂46"], ["Nogizaka46", "Nogizaka", "乃木坂"]),
    ("Sakamichi Series", "Sakurazaka46", [
        "Sakurazaka46", "櫻坂46", "Keyakizaka46", "欅坂46"
    ], [
        "Sakurazaka46", "Sakurazaka", "櫻坂46", "櫻坂",
        "Keyakizaka46", "Keyakizaka", "欅坂46", "欅坂"
    ]),
    ("Sakamichi Series", "Hinatazaka46", ["Hinatazaka46", "日向坂46"], ["Hinatazaka46", "Hinatazaka", "日向坂"]),
    ("Sakamichi Series", "22/7", ["22/7", "ナナブンノニジュウニ"], ["22/7", "Nanabun no Nijuuni", "ナナブンノニジュウニ", "ナナニジ"]),
    ("Sakamichi Series", "Boku ga Mitakatta Aozora", ["僕が見たかった青空", "Boku ga Mitakatta Aozora"], ["僕が見たかった青空", "Boku ga Mitakatta Aozora", "僕青"]),

    # Sakamichi Series — Solo Graduates
    ("Sakamichi Series", "Mai Shiraishi", ["Mai Shiraishi", "白石麻衣"], ["Mai Shiraishi", "Shiraishi Mai", "白石麻衣", "Passport"]),
    ("Sakamichi Series", "Nanase Nishino", ["Nanase Nishino", "西野七瀬"], ["Nanase Nishino", "Nishino Nanase", "西野七瀬"]),
    ("Sakamichi Series", "Erika Ikuta", ["Erika Ikuta", "生田絵梨花"], ["Erika Ikuta", "Ikuta Erika", "生田絵梨花"]),
    ("Sakamichi Series", "Asuka Saito", ["Asuka Saito", "齋藤飛鳥"], ["Asuka Saito", "Saito Asuka", "齋藤飛鳥"]),
    ("Sakamichi Series", "Yurina Hirate", ["Yurina Hirate", "平手友梨奈"], ["Yurina Hirate", "Hirate Yurina", "平手友梨奈"]),

    # Stardust Planet
    ("Stardust Planet", "Momoiro Clover Z", ["Momoiro Clover Z", "ももいろクローバーZ"], ["Momoiro Clover", "Momoclo", "ももいろクローバーZ", "ももクロ"]),
    ("Stardust Planet", "Shiritsu Ebisu Chugaku", ["Shiritsu Ebisu Chugaku", "私立恵比寿中学"], ["Shiritsu Ebisu Chugaku", "Ebichu", "私立恵比寿中学", "エビ中"]),
    ("Stardust Planet", "Chou Tokimeki Sendenbu", ["Cho Tokimeki Sendenbu", "超ときめき♡宣伝部"], [
        "Cho Tokimeki Sendenbu", "Chou Tokimeki Sendenbu", "Tokimeki Sendenbu", "Tokisen", "超ときめき♡宣伝部", "ときめき♡宣伝部", "とき宣"
    ]),
    ("Stardust Planet", "TEAM SHACHI", ["TEAM SHACHI", "チームしゃちほこ"], ["TEAM SHACHI", "Team Syachihoko", "チームしゃちほこ", "しゃち"]),
    ("Stardust Planet", "BATTEN GIRLS", ["BATTEN GIRLS", "ばってん少女隊"], ["BATTEN GIRLS", "Batten Showtai", "ばってん少女隊", "ばっしょー"]),
    ("Stardust Planet", "ukka", ["ukka", "桜エビ〜ず"], ["ukka", "Sakura Ebis", "桜エビ〜ず"]),

    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", ["=LOVE", "イコールラブ"], ["=LOVE", "Equal Love", "イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", ["ノイミー", "≠ME"], NOIME_AUTHENTIC_SIGNATURES),
    ("=LOVE / Sister Groups", "≒JOY", ["Nearly Equal Joy", "≒JOY"], NIAGO_AUTHENTIC_SIGNATURES),

    # KAWAII LAB. — Complete 4 Sister Groups
    ("KAWAII LAB.", "FRUITS ZIPPER", ["FRUITS ZIPPER", "フルーツジッパー"], ["FRUITS ZIPPER", "Fruits Zipper", "ふるっぱー", "KAWAII LAB."]),
    ("KAWAII LAB.", "CANDY TUNE", ["CANDY TUNE", "キャンディートゥーン"], ["CANDY TUNE", "Candy Tune", "きゃんちゅー", "KAWAII LAB."]),
    ("KAWAII LAB.", "SWEET STEADY", ["SWEET STEADY", "スウィートステディ"], ["SWEET STEADY", "Sweet Steady", "すいすて", "KAWAII LAB."]),
    ("KAWAII LAB.", "CUTIE STREET", ["CUTIE STREET", "キューティーストリート"], ["CUTIE STREET", "Cutie Street", "きゅーすと", "KAWAII LAB."]),

    # Modern Idols — NiziU & LAPONE Sisters
    ("Modern Idols", "NiziU", ["NiziU", "ニジュー"], ["NiziU", "ニジュー"]),
    ("Modern Idols", "ME:I", ["ME:I", "ミーアイ"], ["ME:I", "ミーアイ", "Produce 101"]),
    ("Modern Idols", "IS:SUE", ["IS:SUE", "イッシュ"], ["IS:SUE", "イッシュ", "1st IS:SUE"]),

    # Babymetal & Amuse Roots
    ("Babymetal", "BABYMETAL", ["BABYMETAL"], ["BABYMETAL"]),
    ("Babymetal", "Sakura Gakuin", ["Sakura Gakuin", "さくら学院"], ["Sakura Gakuin", "さくら学院", "BABYMETAL"]),
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

def is_calendar_valid(year, month, day):
    try:
        datetime(year, month, day)
        return True
    except (ValueError, OverflowError):
        return False

def parse_normalized_date(date_raw_str):
    if not date_raw_str:
        return ""
    text = clean_text(date_raw_str)

    m1 = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})[/-](\d{1,2})\b", text)
    if m1:
        y, m, d = int(m1.group(1)), int(m1.group(2)), int(m1.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    match_jp = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if match_jp:
        y, m, d = int(match_jp.group(1)), int(match_jp.group(2)), int(match_jp.group(3))
        if is_calendar_valid(y, m, d):
            return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    match_en = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(19\d\d|20\d\d)\b", text)
    if match_en:
        mon_str = match_en.group(1).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(match_en.group(3)), MONTH_MAP[mon_str], int(match_en.group(2))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    match_en_rev = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(19\d\d|20\d\d)\b", text)
    if match_en_rev:
        mon_str = match_en_rev.group(2).lower()
        if mon_str in MONTH_MAP:
            y, m, d = int(match_en_rev.group(3)), MONTH_MAP[mon_str], int(match_en_rev.group(1))
            if is_calendar_valid(y, m, d):
                return f"{y}/{str(m).zfill(2)}/{str(d).zfill(2)}"

    match_ym = re.search(r"\b(19\d\d|20\d\d)[/-](\d{1,2})\b", text)
    if match_ym:
        y, m = int(match_ym.group(1)), int(match_ym.group(2))
        if 1 <= m <= 12:
            return f"{y}/{str(m).zfill(2)}/01"

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

def is_upfront_affiliated(pid, title_lower):
    pid_upper = pid.upper()
    if any(pid_upper.startswith(pfx) for pfx in ALL_UPFRONT_PREFIXES):
        return True
    if any(h in title_lower for h in ["hello! project", "ハロー!プロジェクト", "ハロプロ", "e-lineup", "up-front", "アップフロント", "演劇女子部"]):
        return True
    return False

def is_relevant_product(card_text, canonical_artist, keywords, prod_key, is_direct_person=False):
    if is_direct_person:
        return True

    lower_text = card_text.lower()
    pid_upper = str(prod_key).upper()

    for pat in MALE_BOYBAND_PATTERNS:
        if re.search(pat, lower_text):
            has_female_artist = any(sig.lower() in lower_text for _, art, _, _ in TARGET_GROUPS for sig in [art])
            if not has_female_artist:
                return False

    for pat in NON_IDOL_MEDIA_PATTERNS:
        if re.search(pat, lower_text):
            has_female_artist = any(sig.lower() in lower_text for _, art, _, _ in TARGET_GROUPS for sig in [art])
            if not has_female_artist:
                return False

    if canonical_artist == "Country Girls":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        if any(sig in lower_text for sig in COUNTRY_GIRLS_SIGNATURES):
            return True
        if any(w in lower_text for w in ["nashville", "bluegrass", "country & western", "country gold", "best of country"]):
            return False
        return False

    if canonical_artist == "W":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        has_w_sig = any(w in lower_text for w in [
            "ダブルユー", "double you", "w (double you)", "w [double you]", "tsuji", "kago",
            "辻希美", "加護亜依", "robo kiss", "koi no vacance", "ai no imi", "miss love"
        ])
        return has_w_sig

    if canonical_artist == "Tanpopo":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        return any(sig in lower_text for sig in TANPOPO_AUTHENTIC_SIGNATURES)

    if canonical_artist == "GAM":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        return any(s in lower_text for s in ["matsuura", "fujimoto", "1st gam", "melodies", "lu lu lu", "ギャム"])

    if canonical_artist == "Minimoni":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        return any(s in lower_text for s in ["minimoni", "mini moni", "ミニモニ", "mini-moni"])

    if canonical_artist == "v-u-den":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        return any(s in lower_text for s in ["v-u-den", "biyuden", "美勇伝", "ishikawa rika", "ajisai ai ai"])

    if canonical_artist == "Tsukishima Kirari":
        return any(s in lower_text for s in ["tsukishima kirari", "月島きらり", "kusumi koharu", "久住小春", "kirarin", "きらりん"])

    if canonical_artist == "Karin Miyamoto":
        return any(s in lower_text for s in ["karin miyamoto", "miyamoto karin", "宮本佳林", "hitorijime", "hyouon"])

    if canonical_artist == "Taiyo to Ciscomoon":
        if is_upfront_affiliated(prod_key, lower_text):
            return True
        return any(s in lower_text for s in ["taiyo to ciscomoon", "太陽とシスコムーン", "t&c bomber", "t&cボンバー"])

    if canonical_artist == "You Kikkawa":
        return any(s in lower_text for s in ["kikkawa you", "you kikkawa", "kikkawa yu", "吉川友"])

    if canonical_artist == "IS:SUE":
        is_real_issue = (
            "is:sue" in lower_text or
            "イッシュ" in card_text or
            "1st is:sue" in lower_text or
            "connect" in lower_text or
            "static" in lower_text or
            pid_upper.startswith("UMCK") or
            pid_upper.startswith("UPCH") or
            any(m in lower_text for m in ["rin", "nanami", "yuuki", "rino"])
        )
        if not is_real_issue and ("issue" in lower_text or "february" in lower_text or "october" in lower_text):
            return False
        return is_real_issue

    if canonical_artist == "Up Up Girls (Kari)":
        if "(2)" in lower_text or "（2）" in card_text or "アプガ2" in card_text:
            return False

    if canonical_artist == "Up Up Girls (2)":
        if "(2)" in lower_text or "（2）" in card_text or "アプガ2" in card_text or "up up girls 2" in lower_text:
            return True

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
        if (
            "out of print" in card_text_lower or
            "sold out" in card_text_lower or
            "no longer available" in card_text_lower or
            "archive" in card_text_lower or
            "廃盤" in card_text_lower or
            "取扱終了" in card_text_lower
        ):
            availability = "oop"
        elif is_date_upcoming(rel_date) or "pre-order" in card_text_lower or "予約" in card_text_lower:
            availability = "preorder"
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
        if close_btn.is_visible(timeout=200):
            close_btn.click(force=True)
            time.sleep(0.1)
    except Exception:
        pass

def sanitize_query_for_cdjapan(query_str):
    return query_str.replace("/", " ").strip()

def execute_artist_search(page, category, canonical_artist, target_query_or_url, keywords, max_pages):
    results = []
    seen_query_pids = set()
    consecutive_empty_pages = 0
    is_direct_person = target_query_or_url.startswith("http://") or target_query_or_url.startswith("https://")
    sanitized_target = target_query_or_url if is_direct_person else sanitize_query_for_cdjapan(target_query_or_url)
    
    print(f"\n-> Querying: {canonical_artist} ('{sanitized_target}') [Max Depth: {max_pages} pages]", flush=True)

    target_kws = [k.lower() for k in keywords]
    if len(sanitized_target) > 2:
        target_kws.extend([target_query_or_url.lower(), sanitized_target.lower()])
    effective_keywords = list(set(target_kws))

    for p_num in range(1, max_pages + 1):
        if is_direct_person:
            sep = "&" if "?" in target_query_or_url else "?"
            target_url = f"{target_query_or_url}{sep}page={p_num}&order=reldate_desc"
        else:
            encoded_q = urllib.parse.quote_plus(sanitized_target)
            target_url = f"https://www.cdjapan.co.jp/searchuni?q={encoded_q}&opt.include_eoa=1&order=reldate_desc&page={p_num}"

        extracted_on_page = []
        page_successful = False

        # Enhanced Retry Ladder with Exponential Jitter Backoff (5 attempts)
        for attempt in range(1, 6):
            try:
                page.set_extra_http_headers({
                    "Referer": "https://www.cdjapan.co.jp/",
                    "Accept-Language": "en-US,en;q=0.9,ja;q=0.8"
                })

                response = page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                dismiss_popups(page)

                current_title = page.title().strip()
                status_code = response.status if response else 0

                # Check if rate-limited or blocked
                if not current_title or status_code in [429, 403, 500, 502, 503, 504]:
                    sleep_time = (attempt * 4) + random.uniform(1.0, 3.5)
                    print(f"   [Notice] Rate-limit / HTTP {status_code} on Page {p_num}. Backing off {sleep_time:.1f}s (attempt {attempt}/5)...", flush=True)
                    time.sleep(sleep_time)
                    continue

                page_text_quick = page.locator("body").inner_text(timeout=4000).lower()
                if "no item found" in page_text_quick or "見つかりませんでした" in page_text_quick:
                    extracted_on_page = []
                    page_successful = True
                    break

                try:
                    page.wait_for_selector(
                        ".item-detail, .n-item, div.item, tr.item, div.search-result-item, .item_list",
                        timeout=6000
                    )
                except Exception:
                    pass

                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.3)
                page.evaluate("window.scrollBy(0, 900)")
                time.sleep(0.3)

                html = page.content()
                extracted_on_page = extract_verified_products(
                    html, category, canonical_artist, effective_keywords, is_direct_person=is_direct_person
                )

                if len(extracted_on_page) == 0 and attempt < 3:
                    time.sleep(2.0)
                    continue

                page_successful = True
                break

            except Exception as e:
                sleep_time = (attempt * 3) + random.uniform(1.0, 2.5)
                print(f"   Attempt {attempt}/5 notice on Page {p_num}: {e}. Retrying in {sleep_time:.1f}s...", flush=True)
                time.sleep(sleep_time)

        # Do not quit the entire search on a single temporary page failure
        if not page_successful:
            print(f"   [Warning] Page {p_num} could not be retrieved after 5 attempts. Skipping to page {p_num + 1}...", flush=True)
            continue

        if len(extracted_on_page) == 0:
            consecutive_empty_pages += 1
            if consecutive_empty_pages >= 2:
                print(f"   [Notice] Reached verified end of catalog results at page {p_num}.", flush=True)
                break
            else:
                continue
        else:
            consecutive_empty_pages = 0

        current_pids = set(it["id"] for it in extracted_on_page)
        if current_pids.issubset(seen_query_pids):
            print(f"   [Notice] Page {p_num} contains duplicate results. Stopping query.", flush=True)
            break

        seen_query_pids.update(current_pids)
        print(f"   [Page {p_num}] Extracted {len(extracted_on_page)} verified items", flush=True)
        results.extend(extracted_on_page)

        # Safe rate-limiting delay between pages
        time.sleep(random.uniform(1.5, 2.8))

    return results

def get_active_targets(is_targeted_run):
    raw_filter = os.environ.get("TARGET_ARTIST", "").strip()

    if raw_filter and raw_filter.lower() != "all groups":
        if "updated 3 groups" in raw_filter.lower():
            target_names = ["Up Up Girls (2)", "Hello Pro Kenshuusei", "Kobushi Factory"]
            return [g for g in TARGET_GROUPS if g[1] in target_names]

        if "angerme" in raw_filter.lower() or "s/mileage" in raw_filter.lower():
            return [g for g in TARGET_GROUPS if g[1] == "ANGERME"]

        if "sakurazaka" in raw_filter.lower() or "keyakizaka" in raw_filter.lower():
            return [g for g in TARGET_GROUPS if g[1] == "Sakurazaka46"]

        matched = [g for g in TARGET_GROUPS if g[1].lower() == raw_filter.lower()]
        return matched if matched else TARGET_GROUPS

    if not is_targeted_run:
        return [g for g in TARGET_GROUPS if g[1] not in LEGACY_ROSTER_GROUPS]

    return TARGET_GROUPS

def get_target_page_depth(is_targeted_run):
    env_depth = os.environ.get("PAGES_PER_TARGET", "").strip()
    if env_depth.isdigit() and int(env_depth) > 0:
        return int(env_depth)
    return DEFAULT_PAGES_TARGETED if is_targeted_run else DEFAULT_PAGES_ALL

def main():
    catalog = load_catalog()
    initial_count = len(catalog)
    print(f"Starting Catalog Sync. Current active items: {initial_count}", flush=True)

    raw_filter = os.environ.get("TARGET_ARTIST", "").strip()
    is_targeted = bool(raw_filter and raw_filter.lower() != "all groups")
    active_groups = get_active_targets(is_targeted)
    page_depth = get_target_page_depth(is_targeted)

    run_mode = "Targeted Manual Deep Scrape" if is_targeted else "Automated Exhaustive Sweep"
    print(f"Run Mode: [{run_mode}] | Groups: {len(active_groups)} | Max Depth: {page_depth} pages/query", flush=True)

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
            warmup_page.goto("https://www.cdjapan.co.jp/", wait_until="domcontentloaded", timeout=20000)
            dismiss_popups(warmup_page)
            time.sleep(1.0)
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
                        target_page, cat, artist, target_q, keywords, max_pages=page_depth
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
                    else:
                        existing_artist = str(catalog[pid].get("artist", "")).strip()
                        if existing_artist in PROTECTED_SUBUNITS and it["artist"] not in PROTECTED_SUBUNITS:
                            it["artist"] = existing_artist

                        existing_date = str(catalog[pid].get("release_date", "")).strip()
                        new_date = str(it.get("release_date", "")).strip()
                        if existing_date and existing_date != "Available Now" and (not new_date or new_date == "Available Now"):
                            it["release_date"] = existing_date

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

            time.sleep(random.uniform(1.2, 2.2))

        browser.close()

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    state_data = {
        "last_sync": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_catalog_size": len(catalog),
        "items_added_this_pass": new_total,
        "active_groups": [g[1] for g in active_groups],
        "depth_setting": page_depth
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
