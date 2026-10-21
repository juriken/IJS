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
INDEX_FILE = "catalog-index.json"
STATE_FILE = "scraper_state.json"

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08", "september": "09",
    "october": "10", "november": "11", "december": "12"
}

TITLE_PRICE_CLEANUP_REGEX = re.compile(
    r'(?:\s*[\(\[【]?\s*(?:¥\s*[\d,]+\vert{}[\d,]+\s*(?:yen\vert{}JPY))\s*(?:\([^)]*\)\vert{}（[^）]*）\vert{}tax\s*(?:incl\vert{}included\vert{}\.\vert{}\s*in)?\vert{}税込)?\s*[\)\]】]?)+$',
    re.IGNORECASE
)

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

RAW_TARGET_GROUPS = [
    # Hello! Project — Groups & Active Units
    ("Hello! Project", "Morning Musume", "Morning Musume", [
        "Morning Musume", "Morning Musume.", "Petitmoni", "Pucchimoni", "プッチモニ",
        "Chokotto Love", "Baby! Koi ni Knock Out"
    ]),
    ("Hello! Project", "ANGERME", "ANGERME", ["ANGERME", "Smileage", "S/mileage"]),
    ("Hello! Project", "Juice=Juice", "Juice=Juice", ["Juice=Juice"]),
    ("Hello! Project", "Tsubaki Factory", "Tsubaki Factory", ["Tsubaki Factory"]),
    ("Hello! Project", "BEYOOOOONDS", "BEYOOOOONDS", ["BEYOOOOONDS"]),
    ("Hello! Project", "OCHA NORMA", "OCHA NORMA", ["OCHA NORMA", "OCHA"]),
    ("Hello! Project", "Rosy Chronicle", "Rosy Chronicle", ["Rosy Chronicle", "Rosy"]),
    ("Hello! Project", "Hello Pro Kenshuusei", "Hello Pro Kenshuusei", [
        "Hello Pro Kenshuusei", "Hello! Pro Kenshuusei", "ハロプロ研修生", "Kenshuusei",
        "Hello Pro Egg", "ハロプロエッグ", "Rainbow×Reset"
    ]),

    # Hello! Project — Past Groups & Subunits
    ("Hello! Project", "Minimoni", "Minimoni", ["Minimoni", "Mini Moni", "Mini-Moni", "ミニモニ", "ミニモニ。"]),
    ("Hello! Project", "Berryz Kobo", "Berryz Kobo", ["Berryz Kobo", "Berryz", "Berryz工房"]),
    ("Hello! Project", "℃-ute", "C-ute", ["℃-ute", "C-ute", "Cute"]),
    ("Hello! Project", "Buono!", "Buono!", ["Buono!"]),
    ("Hello! Project", "Country Girls", "Country Girls", ["Country Girls", "Country Musume", "カントリー・ガールズ", "カントリー娘", "Country"]),
    ("Hello! Project", "Kobushi Factory", "Kobushi Factory", ["Kobushi Factory", "こぶしファクトリー", "こぶし"]),
    ("Hello! Project", "Melon Kinenbi", "Melon Kinenbi", ["Melon Kinenbi", "メロン記念日", "メロン"]),
    ("Hello! Project", "Tanpopo", "Tanpopo", TANPOPO_AUTHENTIC_SIGNATURES),
    ("Hello! Project", "v-u-den", "Biyuden", ["Biyuden", "v-u-den", "V-u-den", "美勇伝", "ajisai ai ai", "koi no nukegara"]),

    # Hello! Project — OG Post-Graduation Units
    ("Hello! Project", "LoVendoR", "LoVendoR", ["LoVendoR", "LoVendoЯ", "ラベンダー", "Reina Tanaka"]),
    ("Hello! Project", "PINK CRES.", "PINK CRES.", ["PINK CRES.", "PINK CRES", "ピンククレス", "Miyabi Natsuyaki"]),

    # Hello! Project — Soloists & OGs
    ("Hello! Project", "Sayumi Michishige", "Sayumi Michishige", [
        "Sayumi Michishige", "Michishige Sayumi", "道重さゆみ", "SAYUMINGLANDOLL", "SAYUMING"
    ]),
    ("Hello! Project", "Aya Matsuura", "Aya Matsuura", ["Aya Matsuura", "Matsuura Aya", "松浦亜弥"]),
    ("Hello! Project", "Maki Goto", "Maki Goto", ["Maki Goto", "Goto Maki", "後藤真希"]),
    ("Hello! Project", "Natsumi Abe", "Natsumi Abe", ["Natsumi Abe", "Abe Natsumi", "安倍なつみ"]),
    ("Hello! Project", "Erina Mano", "Erina Mano", ["Erina Mano", "Mano Erina", "真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", "Airi Suzuki", ["Airi Suzuki", "Suzuki Airi", "鈴木愛理"]),

    # Up-Front / H!P Alumni
    ("Up-Front Alumni", "You Kikkawa", "You Kikkawa", [
        "You Kikkawa", "Kikkawa You", "Kikkawa Yu", "吉川友", "Kikkawa"
    ]),
    ("Up-Front Alumni", "Up Up Girls (Kari)", "Up Up Girls (Kari)", [
        "Up Up Girls (Kari)", "Up Up Girls (kari)", "アップアップガールズ(仮)", "アプガ(仮)",
        "アップアップガールズ（仮）", "UpUpGirls(Kari)"
    ]),
    ("Up-Front Alumni", "Up Up Girls (2)", "Up Up Girls (2)", [
        "Up Up Girls (2)", "アップアップガールズ(2)", "アプガ2", "アップアップガールズ（2）",
        "UpUpGirls(2)", "Up Up Girls 2"
    ]),

    # AKB48 Group
    ("AKB48 Group", "AKB48", "AKB48", ["AKB48"]),
    ("AKB48 Group", "SKE48", "SKE48", ["SKE48"]),
    ("AKB48 Group", "NMB48", "NMB48", ["NMB48"]),
    ("AKB48 Group", "HKT48", "HKT48", ["HKT48"]),
    ("AKB48 Group", "NGT48", "NGT48", ["NGT48"]),
    ("AKB48 Group", "STU48", "STU48", ["STU48"]),
    ("AKB48 Group", "Sayaka Yamamoto", "Sayaka Yamamoto", ["Sayaka Yamamoto", "Yamamoto Sayaka", "山本彩", "Sayanee"]),

    # Sakamichi Series
    ("Sakamichi Series", "Nogizaka46", "Nogizaka46", ["Nogizaka46", "Nogizaka", "乃木坂"]),
    ("Sakamichi Series", "Sakurazaka46", "Sakurazaka46", ["Sakurazaka46", "Sakurazaka", "櫻坂"]),
    ("Sakamichi Series", "Hinatazaka46", "Hinatazaka46", ["Hinatazaka46", "Hinatazaka", "日向坂"]),
    ("Sakamichi Series", "Keyakizaka46", "Keyakizaka46", ["Keyakizaka46", "Keyakizaka", "欅坂46", "欅坂"]),
    ("Sakamichi Series", "22/7", "22/7", ["22/7", "Nanabun no Nijuuni", "ナナブンノニジュウニ", "ナナニジ"]),

    # Stardust Planet
    ("Stardust Planet", "Momoiro Clover Z", "Momoiro Clover Z", ["Momoiro Clover", "Momoclo", "ももいろクローバーZ", "ももクロ"]),
    ("Stardust Planet", "Shiritsu Ebisu Chugaku", "Shiritsu Ebisu Chugaku", ["Shiritsu Ebisu Chugaku", "Ebichu", "私立恵比寿中学", "エビ中"]),
    ("Stardust Planet", "Chou Tokimeki Sendenbu", "Cho Tokimeki Sendenbu", [
        "Cho Tokimeki Sendenbu", "Chou Tokimeki Sendenbu", "Tokimeki Sendenbu", "Tokisen", "超ときめき♡宣伝部", "ときめき♡宣伝部", "とき宣"
    ]),

    # =LOVE & Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", "=LOVE", ["=LOVE", "Equal Love", "イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", "ノイミー", NOIME_AUTHENTIC_SIGNATURES),
    ("=LOVE / Sister Groups", "≒JOY", "Nearly Equal Joy", NIAGO
