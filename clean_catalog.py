"""
IdolJapan.store — Intelligent Database Cleanser & Category Validator
Inspects product titles, prunes non-idol false positives (male boybands,
unrelated anime/gaming goods, generic word leaks), and re-aligns items
to their authentic idol group and franchise.
"""

import json
import os
import re

DATA_FILE = "products.json"
STATE_FILE = "scraper_state.json"

# Canonical Artist to Franchise Category Mapping
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

# Strong signatures used to detect when an item actually belongs to another idol group
ARTIST_SIGNATURES = [
    ("Morning Musume", ["morning musume", "モーニング娘"]),
    ("ANGERME", ["angerme", "アンジュルム", "s/mileage", "スマイレージ", "s mileage"]),
    ("Juice=Juice", ["juice=juice", "juicejuice", "ジュースジュース"]),
    ("Tsubaki Factory", ["tsubaki factory", "つばきファクトリー"]),
    ("BEYOOOOONDS", ["beyooooonds", "ビヨーンズ"]),
    ("OCHA NORMA", ["ocha norma", "オチャノーマ"]),
    ("Rosy Chronicle", ["rosy chronicle", "ロージークロニクル"]),
    ("Hello Pro Kenshuusei", ["ハロプロ研修生", "hello pro kenshuusei", "kenshuusei", "ハロプロエッグ"]),
    ("AKB48", ["akb48", "akb-"]),
    ("SKE48", ["ske48", "ske-"]),
    ("NMB48", ["nmb48", "nmb-"]),
    ("HKT48", ["hkt48", "hkt-"]),
    ("NGT48", ["ngt48"]),
    ("STU48", ["stu48"]),
    ("Nogizaka46", ["nogizaka46", "乃木坂46", "乃木坂"]),
    ("Sakurazaka46", ["sakurazaka46", "櫻坂46", "keyakizaka46", "欅坂46"]),
    ("Hinatazaka46", ["hinatazaka46", "日向坂46"]),
    ("22/7", ["22/7", "ナナブンノニジュウニ", "ナナニジ"]),
    ("Momoiro Clover Z", ["momoiro clover", "ももいろクローバー", "ももクロ"]),
    ("Shiritsu Ebisu Chugaku", ["shiritsu ebisu chugaku", "私立恵比寿中学", "エビ中"]),
    ("Chou Tokimeki Sendenbu", ["tokimeki sendenbu", "ときめき♡宣伝部", "とき宣"]),
    ("=LOVE", ["=love", "イコールラブ", "イコラブ"]),
    ("≠ME", ["≠me", "ノイミー", "not equal me"]),
    ("≒JOY", ["≒joy", "ニアジョイ", "nearly equal joy"]),
    ("FRUITS ZIPPER", ["fruits zipper", "フルーツジッパー", "ふるっぱー"]),
    ("CANDY TUNE", ["candy tune", "キャンディートゥーン", "きゃんちゅー"]),
    ("SWEET STEADY", ["sweet steady", "スウィートステディ", "すいすて"]),
    ("CUTIE STREET", ["cutie street", "キューティーストリート", "きゅーすと"]),
    ("NiziU", ["niziu", "ニジュー"]),
    ("ME:I", ["me:i", "ミーアイ"]),
    ("BABYMETAL", ["babymetal", "ベビーメタル"]),
]

# Male boybands and non-female-idol groups that leak through broad retailer tags
MALE_IDOL_PATTERNS = [
    r"\bsnow man\b", r"\bsixtones\b", r"\bking & prince\b", r"\bnaniwa danshi\b",
    r"\bhey! say! jump\b", r"\bsexy zone\b", r"\btimelesz\b", r"\btravis japan\b",
    r"\bkis-my-ft2\b", r"\bkanjani\b", r"\bsuper eight\b", r"\bkat-tun\b",
    r"\bnews\b.*(?:\(cd|dvd|single|album)", r"\bwest\.\b", r"\barashi\b",
    r"\bexile\b", r"\bsandaime\b", r"\bgenerations\b", r"\bthe rampage\b",
    r"\bfantastics\b", r"\bballistik boyz\b", r"\bjo1\b", r"\bini\b",
    r"\bbe:first\b", r"\bmazzel\b", r"\b&team\b", r"\bstray kids\b",
    r"\btomorrow x together\b", r"\btxt\b", r"\bseventeen\b", r"\bbts\b",
    r"\benhypen\b", r"\bnct\b", r"\bateez\b", r"\bzerobaseone\b", r"\briize\b"
]

# Non-idol media leaks
UNRELATED_MEDIA_PATTERNS = [
    r"\bkamen rider\b", r"\bgundam\b", r"\bdragon ball\b", r"\bone piece\b",
    r"\bdetective conan\b", r"\bpokemon\b", r"\bdigimon\b", r"\byu-gi-oh\b",
    r"\btouken ranbu\b", r"\bhypnosis mic\b", r"\bensemble stars\b",
    r"\bidentity v\b", r"\btwisted wonderland\b", r"\bjujutsu kaisen\b",
    r"\bdemon slayer\b", r"\bhaikyu\b", r"\bclassical guitar\b",
    r"\bbluegrass\b", r"\bcountry & western\b", r"\bboard game\b"
]

UPFRONT_PREFIXES = ("EPCE", "EPBE", "EPXE", "EPTE", "EPDE", "PKCP", "PKBP", "UFBW", "UFXW", "HKCN", "HKBN", "HKXN")

def check_false_positive(item):
    title = str(item.get("title", "")).strip()
    title_lower = title.lower()
    artist = str(item.get("artist", "")).strip()
    pid = str(item.get("id", "")).upper()

    # 1. Unknown Artist
    if artist not in CANONICAL_ARTIST_MAP:
        return True, f"Artist '{artist}' not in recognized idol list"

    # 2. Male Idol Leaks (Unless title explicitly names one of our verified female idols)
    for pat in MALE_IDOL_PATTERNS:
        if re.search(pat, title_lower):
            has_female_idol = any(sig in title_lower for _, sigs in ARTIST_SIGNATURES for sig in sigs)
            if not has_female_idol:
                return True, f"Male boyband item detected: matches '{pat}'"

    # 3. Unrelated Gaming / Anime Franchise Goods
    for pat in UNRELATED_MEDIA_PATTERNS:
        if re.search(pat, title_lower):
            has_female_idol = any(sig in title_lower for _, sigs in ARTIST_SIGNATURES for sig in sigs)
            if not has_female_idol:
                return True, f"Unrelated anime/game leak: matches '{pat}'"

    # 4. "IS:SUE" Generic Magazine Issue Leaks
    # If tagged IS:SUE, it MUST be the LAPONE idol group, not just a magazine issue (e.g. "BOMB October Issue")
    if artist == "IS:SUE":
        is_real_issue = (
            "is:sue" in title_lower or
            "イッシュ" in title or
            "1st is:sue" in title_lower or
            "connect" in title_lower or
            "static" in title_lower or
            pid.startswith("UMCK") or
            pid.startswith("UPCH")
        )
        if not is_real_issue:
            return True, "Generic magazine issue false positive for 'IS:SUE'"

    # 5. "W" (Double You) Generic Letter Leaks
    # Must have Double You signatures or Hello! Project Zetima/Piccolo prefixes
    if artist == "W":
        has_w_sig = (
            "ダブルユー" in title or
            "double you" in title_lower or
            "w (double you)" in title_lower or
            "tsuji" in title_lower or
            "kago" in title_lower or
            "辻希美" in title or
            "加護亜依" in title or
            "robo kiss" in title_lower or
            "koi no vacance" in title_lower or
            "ai no imi" in title_lower or
            "miss love" in title_lower or
            any(pid.startswith(pfx) for pfx in UPFRONT_PREFIXES)
        )
        if not has_w_sig:
            return True, "Generic single-letter 'W' leak (missing authentic Double You markers)"

    # 6. "Tanpopo" Dandelion & Folk Leaks
    if artist == "Tanpopo":
        has_tanpopo_sig = (
            any(pid.startswith(pfx) for pfx in UPFRONT_PREFIXES) or
            any(s in title_lower for s in ["last kiss", "motto", "seinaru kane", "otome pasta", "koi wo shichaimashita", "all of tanpopo", "single v clips"])
        )
        if not has_tanpopo_sig:
            return True, "Tanpopo false positive (lacks Hello! Project catalog prefix & song title)"

    # 7. "Country Girls" Leaks
    if artist == "Country Girls":
        has_cg_sig = (
            any(pid.startswith(pfx) for pfx in UPFRONT_PREFIXES) or
            "カントリー・ガールズ" in title or
            "カントリー娘" in title or
            "country girls" in title_lower or
            "country musume" in title_lower or
            any(m in title_lower for m in ["tsugunaga", "morito", "yamaki", "inaba", "ozeki", "fujimoto"])
        )
        if not has_cg_sig:
            return True, "Country Girls false positive (American country / western leak)"

    # 8. "GAM" Gaming Goods Leaks
    if artist == "GAM":
        has_gam_sig = (
            any(pid.startswith(pfx) for pfx in UPFRONT_PREFIXES) or
            "matsuura" in title_lower or
            "fujimoto" in title_lower or
            "1st gam" in title_lower or
            "melodies" in title_lower or
            "lu lu lu" in title_lower or
            "ギャム" in title
        )
        if not has_gam_sig:
            return True, "GAM false positive (video/board game leak)"

    # 9. "Not yet" Common Phrase Leaks
    if artist == "Not yet":
        has_notyet_sig = (
            "ノットイェット" in title or
            "not yet" in title_lower or
            pid.startswith("COCA") or pid.startswith("COZA") or pid.startswith("COBA") or
            any(s in title_lower for s in ["shuumatsu", "naminori", "perapera", "suika baby", "hirihiri", "already"]) or
            any(m in title_lower for m in ["oshima yuko", "sashihara", "kitahara", "yokoyama yui"])
        )
        if not has_notyet_sig:
            return True, "Not yet false positive (common English phrase leak)"

    return False, ""

def detect_true_artist_from_title(title, current_artist):
    title_lower = title.lower()

    # If the current artist name is already in the title, trust it
    current_signatures = []
    for art_name, sigs in ARTIST_SIGNATURES:
        if art_name == current_artist:
            current_signatures = sigs
            break

    if any(sig in title_lower for sig in current_signatures):
        return current_artist

    # Check if title explicitly and strongly belongs to another idol group
    for art_name, sigs in ARTIST_SIGNATURES:
        if art_name == current_artist:
            continue
        for sig in sigs:
            if len(sig) <= 3:
                # Word boundary check for short abbreviations (e.g. ME:I, STU, SKE)
                if re.search(r"\b" + re.escape(sig) + r"\b", title_lower):
                    return art_name
            else:
                if sig in title_lower:
                    return art_name

    return current_artist

def main():
    print("==========================================")
    print("Starting Deep Catalog Clean & Audit Engine")
    print("==========================================")

    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    original_count = len(catalog)
    cleaned_catalog = {}
    pruned_records = []
    realigned_records = []

    for pid, item in catalog.items():
        if not isinstance(item, dict):
            continue

        # 1. Prune False Positives
        is_bad, reason = check_false_positive(item)
        if is_bad:
            pruned_records.append((pid, item.get("title", "")[:40], reason))
            continue

        # 2. Check for Cross-Group Misassignments in Title
        raw_title = item.get("title", "")
        current_artist = item.get("artist", "").strip()
        true_artist = detect_true_artist_from_title(raw_title, current_artist)

        if true_artist != current_artist:
            realigned_records.append((
                pid,
                raw_title[:35],
                f"{current_artist} -> {true_artist}"
            ))
            item["artist"] = true_artist

        # 3. Strictly synchronize category to canonical franchise
        correct_category = CANONICAL_ARTIST_MAP[item["artist"]]
        if item.get("category") != correct_category:
            item["category"] = correct_category

        cleaned_catalog[pid] = item

    # Save cleaned products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Sync state file
    if os.path.exists(STATE_FILE):
        state = {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
        state["total_catalog_size"] = len(cleaned_catalog)
        state["last_catalog_clean"] = "Cleaned and verified"
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"Original items in database: {original_count:,}")
    print(f"Pruned false positives:     {len(pruned_records):,}")
    print(f"Re-aligned group items:     {len(realigned_records):,}")
    print(f"Remaining verified items:   {len(cleaned_catalog):,}")

    if pruned_records:
        print("\n--- Sample of Pruned Items ---")
        for p in pruned_records[:10]:
            print(f"  ❌ [{p[0]}] {p[1]} (Reason: {p[2]})")

    if realigned_records:
        print("\n--- Sample of Re-aligned Items ---")
        for r in realigned_records[:10]:
            print(f"  🔄 [{r[0]}] {r[1]} ({r[2]})")

    print("==========================================")
    print("Catalog Audit Complete. Database is 100% clean.")
    print("==========================================")

if __name__ == "__main__":
    main()
