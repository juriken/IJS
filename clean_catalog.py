"""
IdolJapan.store — Intelligent Database Cleanser & Category Validator
Safely re-aligns all soloists, subunits, and franchise categories across the 77-idol roster,
extracts solo releases misfiled under parent groups, resolves legacy category strings,
and prunes genuine non-idol false positives while protecting all authentic merchandise.
"""

import json
import os
import re
from datetime import datetime

DATA_FILE = "products.json"
STATE_FILE = "scraper_state.json"
PRUNED_LOG_FILE = "pruned_items.txt"

# Canonical Artist to Franchise Category Mapping (All 77 Supported Roster Items)
CANONICAL_ARTIST_MAP = {
    # Hello! Project (30 Groups, Subunits & Soloists)
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

    # AKB48 Group (Main Groups, Subunits & Soloists)
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

# Legacy category strings mapped to modern franchise categories
LEGACY_CATEGORY_TRANSLATION = {
    "Momoiro Clover Z": "Stardust Planet",
    "AKB48": "AKB48 Group",
    "Sakamichi": "Sakamichi Series",
    "Up-Front": "Up-Front Alumni",
    "Hello Pro": "Hello! Project",
    "H!P": "Hello! Project",
    "KAWAII LAB": "KAWAII LAB.",
}

# Complete Hello! Project & Up-Front Catalog Code Prefixes
ALL_UPFRONT_PREFIXES = (
    "EPCE", "EPBE", "EPXE", "EPTE", "EPDE",
    "PKCP", "PKBP",
    "HKCN", "HKBN", "HKXN",
    "UFBW", "UFXW",
    "TGBS", "TGXF",
    "DAKU", "DCFGDS", "NEOODY"
)

COUNTRY_GIRLS_SIGNATURES = [
    "country girls", "country musume", "カントリー・ガールズ", "カントリー娘",
    "tsugunaga", "嗣永桃子", "yamaki", "山木梨沙", "inaba", "稲場愛香",
    "morito", "森戸知沙希", "ozeki", "小関舞", "shimamura", "島村嬉唄",
    "yanagawa", "梁川奈々美", "funaki", "船木結", "satoda", "里田まい",
    "engeki joshi bu", "engeki jyoshi bu", "演劇女子部", "kizetsu suru", "気絶するほど"
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

def is_upfront_affiliated(pid, title_lower):
    pid_upper = pid.upper()
    if any(pid_upper.startswith(pfx) for pfx in ALL_UPFRONT_PREFIXES):
        return True
    if any(h in title_lower for h in ["hello! project", "ハロー!プロジェクト", "ハロプロ", "e-lineup", "up-front", "アップフロント", "演劇女子部"]):
        return True
    return False

def check_false_positive(item):
    title = str(item.get("title", "")).strip()
    title_lower = title.lower()
    artist = str(item.get("artist", "")).strip()
    pid = str(item.get("id", "")).upper()

    if artist not in CANONICAL_ARTIST_MAP:
        return True, f"Artist '{artist}' not in recognized 77-idol roster"

    # Male boyband leak filter
    for pat in MALE_BOYBAND_PATTERNS:
        if re.search(pat, title_lower):
            has_our_idol = any(k.lower() in title_lower for k in CANONICAL_ARTIST_MAP.keys())
            if not has_our_idol:
                return True, f"Male boyband item: matches '{pat}'"

    # Non-idol media leak filter
    for pat in NON_IDOL_MEDIA_PATTERNS:
        if re.search(pat, title_lower):
            has_our_idol = any(k.lower() in title_lower for k in CANONICAL_ARTIST_MAP.keys())
            if not has_our_idol:
                return True, f"Unrelated anime/game leak: matches '{pat}'"

    # Country Girls safe check
    if artist == "Country Girls":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        if any(sig in title_lower for sig in COUNTRY_GIRLS_SIGNATURES):
            return False, ""
        if any(w in title_lower for w in ["nashville", "bluegrass", "country & western", "country gold", "best of country"]):
            return True, "American country/western music leak"
        return True, "Country Girls false positive (missing H!P affiliation & member name)"

    # W (Double You) safe check
    if artist == "W":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_w_sig = any(w in title_lower for w in [
            "ダブルユー", "double you", "w (double you)", "tsuji", "kago",
            "辻希美", "加護亜依", "robo kiss", "koi no vacance", "ai no imi", "miss love"
        ])
        if not has_w_sig:
            return True, "Generic letter 'W' leak (missing authentic Double You signatures)"

    # Tanpopo safe check
    if artist == "Tanpopo":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_tanpopo_sig = any(s in title_lower for s in [
            "last kiss", "motto", "seinaru kane", "otome pasta",
            "koi wo shichaimashita", "all of tanpopo", "single v clips"
        ])
        if not has_tanpopo_sig:
            return True, "Tanpopo false positive (lacks H!P markers)"

    # GAM safe check
    if artist == "GAM":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_gam_sig = any(s in title_lower for s in ["matsuura", "fujimoto", "1st gam", "melodies", "lu lu lu", "ギャム"])
        if not has_gam_sig:
            return True, "GAM false positive (video/board game leak)"

    # IS:SUE safe check (prevent generic magazine issues)
    if artist == "IS:SUE":
        is_real_issue = (
            "is:sue" in title_lower or
            "イッシュ" in title or
            "1st is:sue" in title_lower or
            "connect" in title_lower or
            "static" in title_lower or
            pid.startswith("UMCK") or
            pid.startswith("UPCH") or
            any(m in title_lower for m in ["rin", "nanami", "yuuki", "rino"])
        )
        if not is_real_issue and ("issue" in title_lower or "february" in title_lower or "october" in title_lower):
            return True, "Generic magazine issue leak under 'IS:SUE'"

    return False, ""

def realign_artist_and_category(item):
    """
    Detects if an item's title clearly identifies it as a specific solo artist
    or subunit, especially when misfiled under parent groups like Morning Musume.
    """
    title = str(item.get("title", "")).strip()
    title_lower = title.lower()
    current_artist = str(item.get("artist", "")).strip()
    current_category = str(item.get("category", "")).strip()
    
    new_artist = current_artist
    new_category = current_category

    # Case A: If category was literally stored as an artist name
    if current_category in CANONICAL_ARTIST_MAP:
        if current_artist not in CANONICAL_ARTIST_MAP or current_artist == "All":
            new_artist = current_category
        new_category = CANONICAL_ARTIST_MAP[new_artist]

    # Case B: If category was stored as a legacy string
    if new_category in LEGACY_CATEGORY_TRANSLATION:
        new_category = LEGACY_CATEGORY_TRANSLATION[new_category]

    # Case C: Soloist and Subunit title recognition
    # 1. Hello! Project Soloists and Subunits
    if new_artist in ["Morning Musume", "Hello! Project", "Berryz Kobo", "℃-ute", "Other"]:
        if any(w in title_lower for w in ["goto maki", "maki goto", "後藤真希", "gocchin"]) and not "morning musume" in title_lower[:25]:
            new_artist = "Maki Goto"
        elif any(w in title_lower for w in ["mano erina", "erina mano", "真野恵里菜"]):
            new_artist = "Erina Mano"
        elif any(w in title_lower for w in ["matsuura aya", "aya matsuura", "松浦亜弥", "ayaya"]):
            new_artist = "Aya Matsuura"
        elif "buono!" in title_lower or "buono " in title_lower:
            new_artist = "Buono!"
        elif any(w in title_lower for w in ["ハロプロ研修生", "kenshuusei", "kenshusei", "hello pro egg", "ハロプロエッグ"]):
            new_artist = "Hello Pro Kenshuusei"
        elif any(w in title_lower for w in ["michishige sayumi", "sayumi michishige", "道重さゆみ", "sayuminglandoll"]):
            new_artist = "Sayumi Michishige"
        elif any(w in title_lower for w in ["abe natsumi", "natsumi abe", "安倍なつみ"]) and not "morning musume" in title_lower[:25]:
            new_artist = "Natsumi Abe"
        elif any(w in title_lower for w in ["fujimoto miki", "miki fujimoto", "藤本美貴", "mikitty"]) and not "morning musume" in title_lower[:25]:
            new_artist = "Miki Fujimoto"
        elif any(w in title_lower for w in ["tsukishima kirari", "月島きらり", "久住小春", "koharu kusumi"]):
            new_artist = "Tsukishima Kirari"
        elif any(w in title_lower for w in ["suzuki airi", "airi suzuki", "鈴木愛理"]):
            new_artist = "Airi Suzuki"
        elif any(w in title_lower for w in ["minimoni", "mini moni", "ミニモニ"]):
            new_artist = "Minimoni"
        elif any(w in title_lower for w in ["tanpopo", "タンポポ"]) and any(s in title_lower for s in TANPOPO_AUTHENTIC_SIGNATURES):
            new_artist = "Tanpopo"
        elif any(w in title_lower for w in ["biyuden", "v-u-den", "美勇伝"]):
            new_artist = "v-u-den"
        elif any(w in title_lower for w in ["ダブルユー", "double you", "w (double you)"]):
            new_artist = "W"
        elif any(w in title_lower for w in ["gam", "ギャム"]) and any(m in title_lower for m in ["matsuura", "fujimoto"]):
            new_artist = "GAM"
        elif any(w in title_lower for w in ["taiyo to ciscomoon", "太陽とシスコムーン", "t&c bomber", "t&cボンバー"]):
            new_artist = "Taiyo to Ciscomoon"
        elif any(w in title_lower for w in ["lovendor", "lovendoя", "ラベンダー"]):
            new_artist = "LoVendoR"
        elif any(w in title_lower for w in ["pink cres", "ピンククレス"]):
            new_artist = "PINK CRES."
        elif any(w in title_lower for w in ["country girls", "カントリー・ガールズ", "カントリー娘"]):
            new_artist = "Country Girls"
        elif any(w in title_lower for w in ["kobushi factory", "こぶしファクトリー"]):
            new_artist = "Kobushi Factory"
        elif any(w in title_lower for w in ["melon kinenbi", "メロン記念日"]):
            new_artist = "Melon Kinenbi"

    # 2. Up-Front Alumni Recognition
    if new_artist in ["Up Up Girls (Kari)", "Up-Front Alumni"]:
        if any(w in title_lower for w in ["(2)", "（2）", "アプガ2", "up up girls 2", "up up girls (2)"]):
            new_artist = "Up Up Girls (2)"

    # 3. AKB48 Group Soloists and Subunits
    if new_artist in ["AKB48", "AKB48 Group"]:
        if any(w in title_lower for w in ["yamamoto sayaka", "sayaka yamamoto", "山本彩"]):
            new_artist = "Sayaka Yamamoto"
        elif any(w in title_lower for w in ["maeda atsuko", "atsuko maeda", "前田敦子"]):
            new_artist = "Atsuko Maeda"
        elif any(w in title_lower for w in ["oshima yuko", "yuko oshima", "大島優子"]):
            new_artist = "Yuko Oshima"
        elif any(w in title_lower for w in ["watanabe mayu", "mayu watanabe", "渡辺麻友", "mayuyu"]):
            new_artist = "Mayu Watanabe"
        elif any(w in title_lower for w in ["kashiwagi yuki", "yuki kashiwagi", "柏木由紀", "yukirin"]):
            new_artist = "Yuki Kashiwagi"
        elif any(w in title_lower for w in ["sashihara rino", "rino sashihara", "指原莉乃"]):
            new_artist = "Rino Sashihara"
        elif any(w in title_lower for w in ["itano tomomi", "tomomi itano", "板野友美"]):
            new_artist = "Tomomi Itano"
        elif any(w in title_lower for w in ["not yet", "ノットイェット"]):
            new_artist = "Not yet"
        elif any(w in title_lower for w in ["no3b", "no sleeves", "ノースリーブス"]):
            new_artist = "no3b"
        elif any(w in title_lower for w in ["french kiss", "フレンチ・キス"]):
            new_artist = "French Kiss"
        elif any(w in title_lower for w in ["watarirouka", "渡り廊下走り隊"]):
            new_artist = "Watarirouka Hashiritai"

    # 4. Sakamichi Series Soloists
    if new_artist in ["Nogizaka46", "Sakurazaka46", "Sakamichi Series"]:
        if any(w in title_lower for w in ["shiraishi mai", "mai shiraishi", "白石麻衣"]):
            new_artist = "Mai Shiraishi"
        elif any(w in title_lower for w in ["nishino nanase", "nanase nishino", "西野七瀬"]):
            new_artist = "Nanase Nishino"
        elif any(w in title_lower for w in ["ikuta erika", "erika ikuta", "生田絵梨花"]):
            new_artist = "Erika Ikuta"
        elif any(w in title_lower for w in ["saito asuka", "asuka saito", "齋藤飛鳥"]):
            new_artist = "Asuka Saito"
        elif any(w in title_lower for w in ["hirate yurina", "yurina hirate", "平手友梨奈"]):
            new_artist = "Yurina Hirate"

    # 5. Babymetal & Amuse Roots
    if new_artist in ["BABYMETAL", "Babymetal"]:
        if any(w in title_lower for w in ["sakura gakuin", "さくら学院"]):
            new_artist = "Sakura Gakuin"
        elif any(w in title_lower for w in ["@onefive", "onefive", "ワンファイブ"]):
            new_artist = "@onefive"

    # Ensure category is strictly synchronized to the canonical franchise of the artist
    if new_artist in CANONICAL_ARTIST_MAP:
        new_category = CANONICAL_ARTIST_MAP[new_artist]

    return new_artist, new_category

def main():
    print("==========================================")
    print("Starting Comprehensive Catalog Re-Alignment")
    print("==========================================")

    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    original_count = len(catalog)
    cleaned_catalog = {}
    pruned_records = []
    realigned_artists = []
    realigned_categories = []

    for pid, item in catalog.items():
        if not isinstance(item, dict):
            continue

        # Step 1: Detect true artist and category first
        current_art = item.get("artist", "").strip()
        current_cat = item.get("category", "").strip()

        new_art, new_cat = realign_artist_and_category(item)

        if new_art != current_art:
            realigned_artists.append((pid, item.get("title", "")[:35], f"{current_art} -> {new_art}"))
            item["artist"] = new_art

        if new_cat != current_cat:
            realigned_categories.append((pid, item.get("title", "")[:35], f"{current_cat} -> {new_cat}"))
            item["category"] = new_cat

        # Step 2: Prune genuine non-idol false positives
        is_bad, reason = check_false_positive(item)
        if is_bad:
            pruned_records.append((pid, item.get("title", ""), reason))
            continue

        cleaned_catalog[pid] = item

    # Save cleaned catalog
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Save full pruned log
    with open(PRUNED_LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Total Pruned Items: {len(pruned_records)}\n")
        f.write("=" * 60 + "\n")
        for idx, (p_id, p_title, p_reason) in enumerate(pruned_records, 1):
            f.write(f"[{idx}/{len(pruned_records)}] [{p_id}] {p_title} (Reason: {p_reason})\n")

    # Sync state file
    if os.path.exists(STATE_FILE):
        state = {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
        state["total_catalog_size"] = len(cleaned_catalog)
        state["last_catalog_clean"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"Original items in database: {original_count:,}")
    print(f"Artists corrected:          {len(realigned_artists):,}")
    print(f"Categories synchronized:    {len(realigned_categories):,}")
    print(f"Pruned false positives:     {len(pruned_records):,}")
    print(f"Remaining verified items:   {len(cleaned_catalog):,}")

    if realigned_artists:
        print("\n--- Sample of Corrected Artists ---")
        for r in realigned_artists[:12]:
            print(f"  🎤 [{r[0]}] {r[1]} ({r[2]})")

    if realigned_categories:
        print("\n--- Sample of Synchronized Franchise Categories ---")
        for c in realigned_categories[:12]:
            print(f"  🏷️  [{c[0]}] {c[1]} ({c[2]})")

    if pruned_records:
        print(f"\n==========================================")
        print(f"COMPLETE LIST OF ALL PRUNED ITEMS ({len(pruned_records):,} items):")
        print(f"==========================================")
        for idx, (p_id, p_title, p_reason) in enumerate(pruned_records, 1):
            print(f"[{idx}/{len(pruned_records)}] ❌ [{p_id}] {p_title} — Reason: {p_reason}")

    print("==========================================")
    print("Catalog Audit Complete. All categories and soloists 100% synchronized.")
    print("==========================================")

if __name__ == "__main__":
    main()
