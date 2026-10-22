"""
IdolJapan.store — Intelligent Database Cleanser & Multi-Tier Category Sorter
Differentiates all 78 Japanese idol groups, subunits, and soloists with strict
precedence rules, resolves parent-group misallocations, and synchronizes
both products.json AND catalog-index.json simultaneously.
"""

import json
import os
import re
from datetime import datetime

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
STATE_FILE = "scraper_state.json"
PRUNED_LOG_FILE = "pruned_items.txt"

# Canonical Artist to Franchise Category Mapping (All 78 Supported Roster Items)
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

    # Up-Front Alumni (3)
    "You Kikkawa": "Up-Front Alumni",
    "Up Up Girls (Kari)": "Up-Front Alumni",
    "Up Up Girls (2)": "Up-Front Alumni",

    # AKB48 Group (17 Groups, Subunits & Soloists)
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

    # Sakamichi Series & Rivals (10)
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

    # Stardust Planet (6)
    "Momoiro Clover Z": "Stardust Planet",
    "Shiritsu Ebisu Chugaku": "Stardust Planet",
    "Chou Tokimeki Sendenbu": "Stardust Planet",
    "TEAM SHACHI": "Stardust Planet",
    "BATTEN GIRLS": "Stardust Planet",
    "ukka": "Stardust Planet",

    # =LOVE / Sister Groups (3)
    "=LOVE": "=LOVE / Sister Groups",
    "≠ME": "=LOVE / Sister Groups",
    "≒JOY": "=LOVE / Sister Groups",

    # KAWAII LAB. (4)
    "FRUITS ZIPPER": "KAWAII LAB.",
    "CANDY TUNE": "KAWAII LAB.",
    "SWEET STEADY": "KAWAII LAB.",
    "CUTIE STREET": "KAWAII LAB.",

    # Modern Idols (3)
    "NiziU": "Modern Idols",
    "ME:I": "Modern Idols",
    "IS:SUE": "Modern Idols",

    # Babymetal & Roots (2)
    "BABYMETAL": "Babymetal",
    "Sakura Gakuin": "Babymetal",
}

# Complete Whitelist of Authentic Record Label Prefixes
AUTHENTIC_LABEL_PREFIXES = (
    "EPCE", "EPBE", "EPXE", "EPTE", "EPDE",  # Zetima
    "PKCP", "PKBP",                          # Piccolo Town
    "HKCN", "HKBN", "HKXN",                  # Hachama
    "UFBW", "UFXW",                          # Up-Front Works
    "UPCH", "UPBH",                          # Universal Music Japan (Kikka, etc.)
    "POCS",                                  # Universal / P-Vine (Kikka)
    "TGBS", "TGXF",                          # Giga
    "DAKU", "DCFGDS", "NEOODY", "NEODAI"     # Fanclub, e-LineUP, Odyssey
)

# Priority 1: High-Specificity Subunits, Soloists, and Sister Groups
# Items are tested against these specific signatures FIRST before parent groups.
PRIORITY_ARTIST_RULES = [
    # Hello! Project Soloists & Subunits
    ("Tsukishima Kirari", [
        "tsukishima kirari", "月島きらり", "kusumi koharu", "久住小春",
        "kirarin revolution", "きらりん☆レボリューション", "きらりんレボリューション", "balalaika", "koikana", "papancake"
    ]),
    ("W", [
        "ダブルユー", "double you", "w (double you)", "w [double you]",
        "robo kiss", "koi no vacance", "miss love tantei", "ai no imi wo oshiete"
    ]),
    ("Minimoni", [
        "minimoni", "mini moni", "ミニモニ", "mini-moni",
        "crazy about you", "minimoni telephone", "rock 'n' roll kenchouszaichou"
    ]),
    ("Tanpopo", [
        "tanpopo", "タンポポ", "last kiss", "motto", "seinaru kane", "otome pasta", "koi wo shichaimashita"
    ]),
    ("v-u-den", [
        "v-u-den", "biyuden", "美勇伝", "ajisai ai ai", "koi no nukegara", "kacchoii ze! japan"
    ]),
    ("GAM", [
        "gam", "ギャム", "1st gam", "melodies", "lu lu lu", "daisuki rakuten eagles"
    ]),
    ("Buono!", [
        "buono!", "buono ", "honto no jibun", "renai rider", "kiss! kiss! kiss!", "co-no-mi-chi"
    ]),
    ("Maki Goto", [
        "goto maki", "maki goto", "後藤真希", "gocchin", "ai no bakadan", "te wo nigitte arukitai", "daite yo! please go on"
    ]),
    ("Erina Mano", [
        "mano erina", "erina mano", "真野恵里菜", "otome no inori", "hajimete no keiken", "sekai wa summer party"
    ]),
    ("Aya Matsuura", [
        "matsuura aya", "aya matsuura", "松浦亜弥", "ayaya", "dokidoki! love mail", "yeah! meccha holiday", "momoiro kataomoi"
    ]),
    ("Miki Fujimoto", [
        "fujimoto miki", "miki fujimoto", "藤本美貴", "mikitty", "aenai nagai nichiyoubi", "boogie train '03", "roppongi toori"
    ]),
    ("Natsumi Abe", [
        "abe natsumi", "natsumi abe", "安倍なつみ", "22sai no watashi", "datte ikitekanakya"
    ]),
    ("Airi Suzuki", [
        "suzuki airi", "airi suzuki", "鈴木愛理", "do me a favor", "i mi shine"
    ]),
    ("Sayumi Michishige", [
        "michishige sayumi", "sayumi michishige", "道重さゆみ", "sayuminglandoll"
    ]),
    ("Taiyo to Ciscomoon", [
        "taiyo to ciscomoon", "太陽とシスコムーン", "t&c bomber", "t&cボンバー", "magic of love", "gatamekira"
    ]),
    ("LoVendoR", [
        "lovendor", "lovendoя", "ラベンダー"
    ]),
    ("PINK CRES.", [
        "pink cres", "ピンククレス"
    ]),
    ("Hello Pro Kenshuusei", [
        "ハロプロ研修生", "hello pro kenshuusei", "hello pro kenshusei", "kenshuusei", "kenshusei", "hello pro egg", "ハロプロエッグ"
    ]),

    # Up-Front Alumni
    ("You Kikkawa", [
        "kikkawa you", "you kikkawa", "kikkawa yu", "吉川友", "kikkake wa you", "hapirapi", "konna watashi de yokattara"
    ]),
    ("Up Up Girls (2)", [
        "up up girls (2)", "up up girls 2", "アップアップガールズ(2)", "アップアップガールズ（2）", "アプガ2"
    ]),
    ("Up Up Girls (Kari)", [
        "up up girls (kari)", "アップアップガールズ(仮)", "アップアップガールズ（仮）", "アプガ(仮)"
    ]),

    # AKB48 Group Soloists & Subunits
    ("Not yet", ["not yet", "ノットイェット", "shuumatsu not yet", "naminori kakigoori", "perapera peraoche"]),
    ("no3b", ["no3b", "no sleeves", "ノースリーブス", "relax!", "tane", "lie"]),
    ("French Kiss", ["french kiss", "フレンチ・キス", "zutto mae kara", "if", "kakko warui i love you"]),
    ("Watarirouka Hashiritai", ["watarirouka hashiritai", "渡り廊下走り隊", "hatsukoi dash", "yaruki hanabi", "akKanbe bashi"]),
    ("Sayaka Yamamoto", ["yamamoto sayaka", "sayaka yamamoto", "山本彩", "rainbow", "identity", "alpha"]),
    ("Atsuko Maeda", ["maeda atsuko", "atsuko maeda", "前田敦子", "flower", "kimi wa boku da", "time machine nante iranai"]),
    ("Yuko Oshima", ["oshima yuko", "yuko oshima", "大島優子"]),
    ("Mayu Watanabe", ["watanabe mayu", "mayu watanabe", "渡辺麻友", "synchro tokimeki", "otona jelly beans", "hikaru monodachi"]),
    ("Yuki Kashiwagi", ["kashiwagi yuki", "yuki kashiwagi", "柏木由紀", "shortcake", "birthday wedding"]),
    ("Rino Sashihara", ["sashihara rino", "rino sashihara", "指原莉乃", "soredemo suki da yo", "ikuji nashi masquerade"]),
    ("Tomomi Itano", ["itano tomomi", "tomomi itano", "板野友美", "dear j", "fui ni", "10nen go no kimi e"]),

    # Sakamichi Series Soloists & Rival Group
    ("Boku ga Mitakatta Aozora", ["boku ga mitakatta aozora", "僕が見たかった青空", "僕青", "aozora ni tsuite kangaeru"]),
    ("Mai Shiraishi", ["shiraishi mai", "mai shiraishi", "白石麻衣", "passport"]),
    ("Nanase Nishino", ["nishino nanase", "nanase nishino", "西野七瀬", "fudangi", "kaze wo kigaete"]),
    ("Erika Ikuta", ["ikuta erika", "erika ikuta", "生田絵梨花", "tenchou", "intermission"]),
    ("Asuka Saito", ["saito asuka", "asuka saito", "齋藤飛鳥", "shiosai"]),
    ("Yurina Hirate", ["hirate yurina", "yurina平手友梨奈", "平手友梨奈", "dance no riyuu", "kakegae no nai sekai"]),

    # Modern Idols & LAPONE Sister
    ("IS:SUE", ["is:sue", "イッシュ", "1st is:sue", "connect", "static"]),

    # Babymetal & Sakura Gakuin
    ("Sakura Gakuin", ["sakura gakuin", "さくら学院"]),

    # KAWAII LAB. Sister Groups
    ("CANDY TUNE", ["candy tune", "キャンディートゥーン", "きゃんちゅー", "kiss me patissier"]),
    ("SWEET STEADY", ["sweet steady", "スウィートステディ", "すいすて"]),
    ("CUTIE STREET", ["cutie street", "キューティーストリート", "きゅーすと", "kawaii dake ja dame desu ka"]),
    ("FRUITS ZIPPER", ["fruits zipper", "フルーツジッパー", "ふるっぱー", "watashi no ichiban kawaii tokoro"]),

    # Stardust Planet Groups
    ("TEAM SHACHI", ["team shachi", "team syachihoko", "チームしゃちほこ", "しゃち"]),
    ("BATTEN GIRLS", ["batten girls", "batten showtai", "ばってん少女隊", "ばっしょー"]),
    ("ukka", ["ukka", "sakura ebis", "桜エビ〜ず"]),
    ("Chou Tokimeki Sendenbu", ["chou tokimeki sendenbu", "cho tokimeki sendenbu", "tokimeki sendenbu", "超ときめき♡宣伝部", "ときめき♡宣伝部", "とき宣", "suki!"]),
    ("Shiritsu Ebisu Chugaku", ["shiritsu ebisu chugaku", "私立恵比寿中学", "エビ中", "ebichu"]),
    ("Momoiro Clover Z", ["momoiro clover", "ももいろクローバー", "ももクロ", "momoclo"]),

    # =LOVE & Sister Groups
    ("≠ME", ["≠me", "ノイミー", "not equal me"]),
    ("≒JOY", ["≒joy", "ニアジョイ", "nearly equal joy"]),
    ("=LOVE", ["=love", "イコールラブ", "イコラブ"]),
]

# Priority 2: Primary Parent Groups (Evaluated ONLY if Priority 1 did not match)
PARENT_GROUP_RULES = [
    ("Morning Musume", ["morning musume", "モーニング娘"]),
    ("ANGERME", ["angerme", "アンジュルム", "s/mileage", "スマイレージ", "s mileage"]),
    ("Juice=Juice", ["juice=juice", "juicejuice", "ジュースジュース"]),
    ("Tsubaki Factory", ["tsubaki factory", "つばきファクトリー"]),
    ("BEYOOOOONDS", ["beyooooonds", "ビヨーンズ"]),
    ("OCHA NORMA", ["ocha norma", "オチャノーマ"]),
    ("Rosy Chronicle", ["rosy chronicle", "ロージークロニクル"]),
    ("Berryz Kobo", ["berryz kobo", "berryz工房", "berryz"]),
    ("℃-ute", ["c-ute", "cute", "℃-ute"]),
    ("Country Girls", ["country girls", "country musume", "カントリー・ガールズ", "カントリー娘"]),
    ("Kobushi Factory", ["kobushi factory", "こぶしファクトリー"]),
    ("Melon Kinenbi", ["melon kinenbi", "メロン記念日"]),
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
    ("NiziU", ["niziu", "ニジュー"]),
    ("ME:I", ["me:i", "ミーアイ"]),
    ("BABYMETAL", ["babymetal", "ベビーメタル"]),
]

def is_authentic_prefix(pid):
    pid_upper = pid.upper()
    return any(pid_upper.startswith(pfx) for pfx in AUTHENTIC_LABEL_PREFIXES)

def classify_artist_and_category(item):
    """
    Classifies every release using a strict two-stage hierarchy:
    Stage 1: Checks for specific subunits, soloists, and sister groups.
    Stage 2: Checks for primary parent groups.
    Stage 3: Strictly validates and synchronizes the franchise category.
    """
    title = str(item.get("title", "")).strip()
    title_lower = title.lower()
    current_artist = str(item.get("artist", "")).strip()
    pid_upper = str(item.get("id", "")).upper()

    searchable_text = f"{title_lower} {current_artist.lower()}"

    # Stage 1: Priority Subunits & Soloists
    for target_artist, signatures in PRIORITY_ARTIST_RULES:
        for sig in signatures:
            if len(sig) <= 3:
                if re.search(r"\b" + re.escape(sig) + r"\b", searchable_text):
                    return target_artist, CANONICAL_ARTIST_MAP[target_artist]
            else:
                if sig in searchable_text:
                    return target_artist, CANONICAL_ARTIST_MAP[target_artist]

    # Special prefix mappings for Hello! Project subunits
    if pid_upper.startswith("PKCP-50") or pid_upper.startswith("PKBP-50"):
        return "v-u-den", "Hello! Project"

    # Stage 2: Parent Groups
    for parent_artist, signatures in PARENT_GROUP_RULES:
        for sig in signatures:
            if len(sig) <= 3:
                if re.search(r"\b" + re.escape(sig) + r"\b", searchable_text):
                    return parent_artist, CANONICAL_ARTIST_MAP[parent_artist]
            else:
                if sig in searchable_text:
                    return parent_artist, CANONICAL_ARTIST_MAP[parent_artist]

    # Stage 3: If current artist is already recognized in our roster, keep it
    if current_artist in CANONICAL_ARTIST_MAP:
        return current_artist, CANONICAL_ARTIST_MAP[current_artist]

    # Fallback to current artist with Hello! Project default
    return current_artist, CANONICAL_ARTIST_MAP.get(current_artist, "Hello! Project")

def check_true_false_positive(item):
    """Prunes strictly non-idol items (boybands, anime/gaming goods, non-Kikka albums)."""
    title_lower = str(item.get("title", "")).lower()
    artist = str(item.get("artist", "")).strip()
    pid_upper = str(item.get("id", "")).upper()

    # Protected label prefixes are never false positives
    if is_authentic_prefix(pid_upper):
        return False, ""

    # Check for male boybands
    for pat in [r"\bsnow man\b", r"\bsixtones\b", r"\bking & prince\b", r"\btimelesz\b", r"\btravis japan\b", r"\bexile\b", r"\bjo1\b", r"\bini\b", r"\bbts\b", r"\bseventeen\b"]:
        if re.search(pat, title_lower):
            has_our_idol = any(k.lower() in title_lower for k in CANONICAL_ARTIST_MAP.keys())
            if not has_our_idol:
                return True, f"Male boyband item: matches '{pat}'"

    # Tokuma common word 'you' leak
    if artist == "You Kikkawa" and pid_upper.startswith("TKCA") and "kikkawa" not in title_lower and "吉川友" not in title_lower:
        return True, "Non-Kikkawa album matching common word 'you'"

    # Generic magazine issue leak under IS:SUE
    if artist == "IS:SUE":
        is_real = ("is:sue" in title_lower or "イッシュ" in title_lower or "connect" in title_lower or "static" in title_lower or pid_upper.startswith("UMCK"))
        if not is_real and ("issue" in title_lower or "magazine" in title_lower):
            return True, "Generic magazine issue leak under 'IS:SUE'"

    return False, ""

def main():
    print("==========================================")
    print("Starting Comprehensive 78-Group Catalog Sorter")
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

        orig_art = item.get("artist", "").strip()
        orig_cat = item.get("category", "").strip()

        # Step 1: Execute Hierarchical Classification
        resolved_art, resolved_cat = classify_artist_and_category(item)

        if resolved_art != orig_art:
            realigned_artists.append((pid, item.get("title", "")[:32], f"{orig_art} -> {resolved_art}"))
            item["artist"] = resolved_art

        if resolved_cat != orig_cat:
            realigned_categories.append((pid, item.get("title", "")[:32], f"{orig_cat} -> {resolved_cat}"))
            item["category"] = resolved_cat

        # Step 2: Prune False Positives
        is_bad, reason = check_true_false_positive(item)
        if is_bad:
            pruned_records.append((pid, item.get("title", ""), reason))
            continue

        cleaned_catalog[pid] = item

    # Save to products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Save directly to catalog-index.json so Cloudflare serves the exact same state
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

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
    print(f"Artists re-aligned:         {len(realigned_artists):,}")
    print(f"Categories synchronized:    {len(realigned_categories):,}")
    print(f"Pruned false positives:     {len(pruned_records):,}")
    print(f"Total live catalog items:   {len(cleaned_catalog):,}")

    # Display live breakdown for previously zero-count and solo groups
    sample_targets = [
        "Maki Goto", "Erina Mano", "Aya Matsuura", "Buono!",
        "Hello Pro Kenshuusei", "Up Up Girls (2)", "GAM", "W",
        "v-u-den", "Minimoni", "Tanpopo", "Tsukishima Kirari",
        "Taiyo to Ciscomoon", "You Kikkawa", "IS:SUE", "Sakura Gakuin",
        "CANDY TUNE", "SWEET STEADY"
    ]
    print("\n--- Live Distribution Across Focus Groups ---")
    for st in sample_targets:
        c = sum(1 for it in cleaned_catalog.values() if it.get("artist") == st)
        franchise = CANONICAL_ARTIST_MAP.get(st, "Unknown")
        print(f"  ⭐ {st.ljust(22)}: {str(c).rjust(4)} items [{franchise}]")

    print("\n==========================================")
    print("Sorting Complete. products.json and catalog-index.json are 100% in sync.")
    print("==========================================")

if __name__ == "__main__":
    main()
