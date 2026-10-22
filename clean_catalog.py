"""
IdolJapan.store — Database Cleanser & Category Validator
Prunes non-idol false positives, re-aligns categories to authentic franchises,
and validates all 77 supported Japanese idol groups and soloists.
"""

import json
import os
import re

DATA_FILE = "products.json"

CANONICAL_ARTIST_MAP = {
    # Hello! Project
    "Morning Musume": "Hello! Project",
    "ANGERME": "Hello! Project",
    "Juice=Juice": "Hello! Project",
    "Tsubaki Factory": "Hello! Project",
    "BEYOOOOONDS": "Hello! Project",
    "OCHA NORMA": "Hello! Project",
    "Rosy Chronicle": "Hello! Project",
    "Hello Pro Kenshuusei": "Hello! Project",
    "Minimoni": "Hello! Project",
    "Berryz Kobo": "Hello! Project",
    "℃-ute": "Hello! Project",
    "Buono!": "Hello! Project",
    "Country Girls": "Hello! Project",
    "Kobushi Factory": "Hello! Project",
    "Melon Kinenbi": "Hello! Project",
    "Tanpopo": "Hello! Project",
    "v-u-den": "Hello! Project",
    "W": "Hello! Project",
    "GAM": "Hello! Project",
    "Taiyo to Ciscomoon": "Hello! Project",
    "LoVendoR": "Hello! Project",
    "PINK CRES.": "Hello! Project",
    "Sayumi Michishige": "Hello! Project",
    "Aya Matsuura": "Hello! Project",
    "Maki Goto": "Hello! Project",
    "Natsumi Abe": "Hello! Project",
    "Erina Mano": "Hello! Project",
    "Airi Suzuki": "Hello! Project",
    "Miki Fujimoto": "Hello! Project",
    "Tsukishima Kirari": "Hello! Project",

    # Up-Front Alumni
    "You Kikkawa": "Up-Front Alumni",
    "Up Up Girls (Kari)": "Up-Front Alumni",
    "Up Up Girls (2)": "Up-Front Alumni",

    # AKB48 Group
    "AKB48": "AKB48 Group",
    "SKE48": "AKB48 Group",
    "NMB48": "AKB48 Group",
    "HKT48": "AKB48 Group",
    "NGT48": "AKB48 Group",
    "STU48": "AKB48 Group",
    "Not yet": "AKB48 Group",
    "no3b": "AKB48 Group",
    "French Kiss": "AKB48 Group",
    "Watarirouka Hashiritai": "AKB48 Group",
    "Sayaka Yamamoto": "AKB48 Group",
    "Atsuko Maeda": "AKB48 Group",
    "Yuko Oshima": "AKB48 Group",
    "Mayu Watanabe": "AKB48 Group",
    "Yuki Kashiwagi": "AKB48 Group",
    "Rino Sashihara": "AKB48 Group",
    "Tomomi Itano": "AKB48 Group",

    # Sakamichi Series & Rivals
    "Nogizaka46": "Sakamichi Series",
    "Sakurazaka46": "Sakamichi Series",
    "Hinatazaka46": "Sakamichi Series",
    "22/7": "Sakamichi Series",
    "Boku ga Mitakatta Aozora": "Sakamichi Series",
    "Mai Shiraishi": "Sakamichi Series",
    "Nanase Nishino": "Sakamichi Series",
    "Erika Ikuta": "Sakamichi Series",
    "Asuka Saito": "Sakamichi Series",
    "Yurina Hirate": "Sakamichi Series",

    # Stardust Planet
    "Momoiro Clover Z": "Stardust Planet",
    "Shiritsu Ebisu Chugaku": "Stardust Planet",
    "Chou Tokimeki Sendenbu": "Stardust Planet",
    "TEAM SHACHI": "Stardust Planet",
    "BATTEN GIRLS": "Stardust Planet",
    "ukka": "Stardust Planet",

    # =LOVE / Sister Groups
    "=LOVE": "=LOVE / Sister Groups",
    "≠ME": "=LOVE / Sister Groups",
    "≒JOY": "=LOVE / Sister Groups",

    # KAWAII LAB.
    "FRUITS ZIPPER": "KAWAII LAB.",
    "CANDY TUNE": "KAWAII LAB.",
    "SWEET STEADY": "KAWAII LAB.",
    "CUTIE STREET": "KAWAII LAB.",

    # Modern Idols
    "NiziU": "Modern Idols",
    "ME:I": "Modern Idols",
    "IS:SUE": "Modern Idols",

    # Babymetal & Amuse Roots
    "BABYMETAL": "Babymetal",
    "Sakura Gakuin": "Babymetal",
    "@onefive": "Babymetal",
}

# Known Non-Idol False Positive Keywords & Signatures
DISALLOWED_TITLE_REGEXES = [
    r"kamen rider w\b",
    r"gundam w\b",
    r"weiss schwarz.*w\b",
    r"d\.c\.\s*~da capo~",
    r"country & western",
    r"bluegrass favorites",
    r"classical guitar.*dandelion",
    r"dandelion tea",
    r"cute anime girls figure",
]

def is_false_positive(item):
    title = str(item.get("title", "")).lower()
    artist = str(item.get("artist", "")).strip()
    pid = str(item.get("id", "")).upper()

    # 1. Unrecognized artist not in our 77 idol roster
    if artist not in CANONICAL_ARTIST_MAP:
        return True, f"Unrecognized artist: {artist}"

    # 2. Strict Tanpopo validation (must have legitimate Hello! Project prefix)
    if artist == "Tanpopo":
        valid_prefixes = ("EPCE", "EPBE", "EPTE", "EPDE", "PKCP", "PKBP", "UFBW", "UFXW")
        if not any(pid.startswith(pfx) for pfx in valid_prefixes):
            has_authentic_kw = any(sig in title for sig in ["last kiss", "motto", "seinaru kane", "otome pasta", "koi wo shichaimashita", "all of tanpopo"])
            if not has_authentic_kw:
                return True, "Tanpopo false positive (non-H!P catalog prefix & missing song title)"

    # 3. Disallowed false positive titles
    for pattern in DISALLOWED_TITLE_REGEXES:
        if re.search(pattern, title):
            return True, f"Matches disallowed pattern: {pattern}"

    return False, ""

def clean_database():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    original_count = len(catalog)
    cleaned_catalog = {}
    pruned_count = 0
    recategorized_count = 0

    for pid, item in catalog.items():
        if not isinstance(item, dict):
            pruned_count += 1
            continue

        # Check for false positives
        is_bad, reason = is_false_positive(item)
        if is_bad:
            pruned_count += 1
            continue

        artist = item.get("artist", "").strip()
        correct_category = CANONICAL_ARTIST_MAP[artist]

        # Re-align category if it was wrong or outdated
        if item.get("category") != correct_category:
            item["category"] = correct_category
            recategorized_count += 1

        cleaned_catalog[pid] = item

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    print("==========================================")
    print("Catalog Clean & Audit Complete:")
    print(f"Original items in database: {original_count}")
    print(f"Pruned invalid / non-idol items: {pruned_count}")
    print(f"Re-aligned wrong categories: {recategorized_count}")
    print(f"Remaining verified items: {len(cleaned_catalog)}")
    print("==========================================")

if __name__ == "__main__":
    clean_database()
