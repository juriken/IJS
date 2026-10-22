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

# Complete Hello! Project & Up-Front Catalog Code Prefixes
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

    # W (Double You) safe check
    if artist == "W":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_w_sig = any(w in title_lower for w in [
            "ダブルユー", "double you", "w (double you)", "w [double you]", "tsuji", "kago",
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
            "koi wo shichaimashita", "all of tanpopo", "single v clips", "タンポポ"
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

    # Minimoni safe check
    if artist == "Minimoni":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_mini_sig = any(s in title_lower for s in ["minimoni", "mini moni", "ミニモニ", "mini-moni"])
        if not has_mini_sig:
            return True, "Minimoni false positive"

    # v-u-den safe check
    if artist == "v-u-den":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_vuden_sig = any(s in title_lower for s in ["v-u-den", "biyuden", "美勇伝", "ishikawa rika", "ajisai ai ai"])
        if not has_vuden_sig:
            return True, "v-u-den false positive"

    # Tsukishima Kirari safe check
    if artist == "Tsukishima Kirari":
        has_kirari_sig = any(s in title_lower for s in ["tsukishima kirari", "月島きらり", "kusumi koharu", "久住小春", "kirarin", "きらりん"])
        if not has_kirari_sig:
            return True, "Tsukishima Kirari false positive"

    # Taiyo to Ciscomoon safe check
    if artist == "Taiyo to Ciscomoon":
        if is_upfront_affiliated(pid, title_lower):
            return False, ""
        has_taiyo_sig = any(s in title_lower for s in ["taiyo to ciscomoon", "太陽とシスコムーン", "t&c bomber", "t&cボンバー"])
        if not has_taiyo_sig:
            return True, "Taiyo to Ciscomoon false positive"

    # You Kikkawa safe check
    if artist == "You Kikkawa":
        has_kikka_sig = any(s in title_lower for s in ["kikkawa you", "you kikkawa", "kikkawa yu", "吉川友"])
        if not has_kikka_sig:
            return True, "You Kikkawa false positive"

    return False, ""

def realign_artist_and_category(item):
    """
    Scans the product title and ID to accurately re-route releases that were
    misassigned to parent groups (Morning Musume, Berryz Kobo, etc.).
    """
    title = str(item.get("title", "")).strip()
    title_lower = title.lower()
    current_artist = str(item.get("artist", "")).strip()
    pid_upper = str(item.get("id", "")).upper()

    new_artist = current_artist

    # 1. Tsukishima Kirari (Take precedence over Morning Musume parent tag)
    if any(s in title_lower for s in ["tsukishima kirari", "月島きらり", "kirarin revolution", "きらりん☆レボリューション", "きらりんレボリューション"]):
        new_artist = "Tsukishima Kirari"

    # 2. Minimoni (Take precedence over Morning Musume parent tag)
    elif any(s in title_lower for s in ["minimoni", "mini moni", "ミニモニ", "mini-moni"]):
        new_artist = "Minimoni"

    # 3. Tanpopo (Take precedence over Morning Musume parent tag)
    elif "tanpopo" in title_lower or "タンポポ" in title or any(s in title_lower for s in TANPOPO_AUTHENTIC_SIGNATURES):
        if is_upfront_affiliated(pid_upper, title_lower):
            new_artist = "Tanpopo"

    # 4. W (Double You)
    elif any(s in title_lower for s in ["ダブルユー", "double you", "w (double you)", "w [double you]"]) or (" w " in f" {title_lower} " and is_upfront_affiliated(pid_upper, title_lower)):
        new_artist = "W"

    # 5. v-u-den (Biyuden)
    elif any(s in title_lower for s in ["v-u-den", "biyuden", "美勇伝"]) or pid_upper.startswith("PKCP-50") or pid_upper.startswith("PKBP-50"):
        new_artist = "v-u-den"

    # 6. GAM
    elif any(s in title_lower for s in ["gam", "ギャム"]) and any(m in title_lower for m in ["matsuura", "fujimoto", "melodies", "lu lu lu", "1st gam"]):
        new_artist = "GAM"

    # 7. Taiyo to Ciscomoon / T&C Bomber
    elif any(s in title_lower for s in ["taiyo to ciscomoon", "太陽とシスコムーン", "t&c bomber", "t&cボンバー"]):
        new_artist = "Taiyo to Ciscomoon"

    # 8. You Kikkawa
    elif any(s in title_lower for s in ["kikkawa you", "you kikkawa", "kikkawa yu", "吉川友"]):
        new_artist = "You Kikkawa"

    # 9. Up Up Girls (2) (Distinguish from Kari)
    elif any(w in title_lower for w in ["(2)", "（2）", "アプガ2", "up up girls 2", "up up girls (2)"]):
        new_artist = "Up Up Girls (2)"

    # 10. Soloists Misassigned to Morning Musume
    elif current_artist in ["Morning Musume", "Hello! Project", "Other"]:
        if any(w in title_lower for w in ["goto maki", "maki goto", "後藤真希", "gocchin"]) and "morning musume" not in title_lower[:25]:
            new_artist = "Maki Goto"
        elif any(w in title_lower for w in ["mano erina", "erina mano", "真野恵里菜"]):
            new_artist = "Erina Mano"
        elif any(w in title_lower for w in ["matsuura aya", "aya matsuura", "松浦亜弥", "ayaya"]):
            new_artist = "Aya Matsuura"
        elif any(w in title_lower for w in ["michishige sayumi", "sayumi michishige", "道重さゆみ", "sayuminglandoll"]):
            new_artist = "Sayumi Michishige"
        elif any(w in title_lower for w in ["abe natsumi", "natsumi abe", "安倍なつみ"]) and "morning musume" not in title_lower[:25]:
            new_artist = "Natsumi Abe"
        elif any(w in title_lower for w in ["fujimoto miki", "miki fujimoto", "藤本美貴", "mikitty"]) and "morning musume" not in title_lower[:25]:
            new_artist = "Miki Fujimoto"
        elif any(w in title_lower for w in ["ハロプロ研修生", "kenshuusei", "kenshusei", "hello pro egg", "ハロプロエッグ"]):
            new_artist = "Hello Pro Kenshuusei"
        elif "buono!" in title_lower or "buono " in title_lower:
            new_artist = "Buono!"

    # Always enforce the canonical category for the resolved artist
    new_category = CANONICAL_ARTIST_MAP.get(new_artist, "Hello! Project")
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

        current_art = item.get("artist", "").strip()
        current_cat = item.get("category", "").strip()

        # Step 1: Detect True Artist and Franchise Category
        new_art, new_cat = realign_artist_and_category(item)

        if new_art != current_art:
            realigned_artists.append((pid, item.get("title", "")[:35], f"{current_art} -> {new_art}"))
            item["artist"] = new_art

        if new_cat != current_cat:
            realigned_categories.append((pid, item.get("title", "")[:35], f"{current_cat} -> {new_cat}"))
            item["category"] = new_cat

        # Step 2: Prune False Positives
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

    # Update state file
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

    # Summary table of the 8 focus groups
    focus_groups = ["GAM", "W", "v-u-den", "Minimoni", "Tanpopo", "Tsukishima Kirari", "Taiyo to Ciscomoon", "You Kikkawa"]
    print("\n--- Verified Counts for the 8 Target Groups ---")
    for fg in focus_groups:
        c = sum(1 for it in cleaned_catalog.values() if it.get("artist") == fg)
        print(f"  ⭐ {fg}: {c} items active")

    if realigned_artists:
        print("\n--- Sample of Corrected Artists ---")
        for r in realigned_artists[:15]:
            print(f"  🎤 [{r[0]}] {r[1]} ({r[2]})")

    print("==========================================")
    print("Catalog Audit Complete.")
    print("==========================================")

if __name__ == "__main__":
    main()
