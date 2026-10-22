"""
IdolJapan.store — Intelligent Database Cleanser & Multi-Tier Category Sorter
Differentiates all 79 Japanese idol groups, subunits, and soloists with strict
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

# Canonical Artist to Franchise Category Mapping (All 79 Supported Roster Items)
CANONICAL_ARTIST_MAP = {
    # Hello! Project (31 Groups, Subunits & Soloists)
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
    "Karin Miyamoto": "Hello! Project",

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
    "UPCH", "UPBH",                          # Universal Music Japan
    "POCS",                                  # Universal / P-Vine
    "TGBS", "TGXF",                          # Giga
    "DAKU", "DCFGDS", "NEOODY", "NEODAI"     # Fanclub, e-LineUP, Odyssey
)

TANPOPO_SONGS = ["last kiss", "motto", "seinaru kane", "otome pasta", "koi wo shichaimashita", "ouji-sama", "tanpopo 1", "all of tanpopo"]

def is_authentic_prefix(pid):
    pid_upper = pid.upper()
    return any(pid_upper.startswith(pfx) for pfx in AUTHENTIC_LABEL_PREFIXES)

def classify_by_title_and_id(title, pid, current_artist):
    title_lower = title.lower()
    pid_upper = pid.upper()

    # =========================================================================
    # Step 1: Detect Explicit Subunits, Soloists & Special Units in Title
    # =========================================================================
    if "宮本佳林" in title or "miyamoto karin" in title_lower or "karin miyamoto" in title_lower or "hitorijime / shoujo c" in title_lower or "hyouon" in title_lower:
        return "Karin Miyamoto"

    if "tsukishima kirari" in title_lower or "月島きらり" in title or "kusumi koharu" in title_lower or "久住小春" in title or "kirarin revolution" in title_lower or "きらりん☆レボリューション" in title or any(s in title_lower for s in ["balalaika", "koikana", "papancake", "hapi hapi sunday", "mitsuboshi", "kirari to fuyu"]):
        return "Tsukishima Kirari"

    if "minimoni" in title_lower or "mini moni" in title_lower or "ミニモニ" in title or "mini-moni" in title_lower or any(s in title_lower for s in ["crazy about you", "minimoni telephone", "rock 'n' roll kenchouszaichou", "minihamuz"]):
        return "Minimoni"

    if "ダブルユー" in title or "double you" in title_lower or "w (double you)" in title_lower or "w [double you]" in title_lower or any(s in title_lower for s in ["robo kiss", "koi no vacance", "miss love tantei", "ai no imi wo oshiete"]):
        return "W"

    if "v-u-den" in title_lower or "biyuden" in title_lower or "美勇伝" in title or any(s in title_lower for s in ["ajisai ai ai", "koi no nukegara", "kacchoii ze! japan", "ai~sweet heart~", "aisucream to my purin", "yui okada"]):
        return "v-u-den"

    if ("gam" in title_lower or "ギャム" in title) and any(m in title_lower for m in ["matsuura", "fujimoto", "1st gam", "melodies", "lu lu lu"]):
        return "GAM"

    if "buono!" in title_lower or "buono " in title_lower or any(s in title_lower for s in ["honto no jibun", "renai rider", "kiss! kiss! kiss!", "gachinko de ikou", "rottara rottara", "co-no-mi-chi", "take it easy!", "bravo☆bravo", "our songs", "we are buono!"]):
        return "Buono!"

    # Tanpopo must NOT contain other group names (prevents AKB, HKT, C-ute matches)
    if ("tanpopo" in title_lower or "タンポポ" in title or any(s in title_lower for s in TANPOPO_SONGS)) and not any(other in title_lower for other in ["akb48", "hkt48", "ske48", "nmb48", "c-ute", "℃-ute", "berryz", "kashiwagi", "angerme"]):
        return "Tanpopo"

    if "taiyo to ciscomoon" in title_lower or "太陽とシスコムーン" in title or "t&c bomber" in title_lower or "t&cボンバー" in title or "magic of love" in title_lower or "gatamekira" in title_lower:
        return "Taiyo to Ciscomoon"

    if "kikkawa you" in title_lower or "you kikkawa" in title_lower or "kikkawa yu" in title_lower or "吉川友" in title or any(s in title_lower for s in ["kikkake wa you", "hapirapi", "konna watashi de yokattara", "kokokara hajimarunda", "two you", "one for you", "best of you!"]):
        return "You Kikkawa"

    # Up Up Girls: Must have explicit "up up girls" or "アプガ" before testing for (2)
    if any(u in title_lower for u in ["up up girls", "アップアップガールズ", "アプガ", "upupgirls"]):
        if any(w in title_lower for w in ["(2)", "（2）", "2"]):
            return "Up Up Girls (2)"
        return "Up Up Girls (Kari)"

    # Soloists
    if "goto maki" in title_lower or "maki goto" in title_lower or "後藤真希" in title or "gocchin" in title_lower or any(s in title_lower for s in ["ai no bakadan", "te wo nigitte arukitai", "daite yo! please go on"]):
        return "Maki Goto"

    if "mano erina" in title_lower or "erina mano" in title_lower or "真野恵里菜" in title or any(s in title_lower for s in ["otome no inori", "hajimete no keiken", "sekai wa summer party"]):
        return "Erina Mano"

    if "matsuura aya" in title_lower or "aya matsuura" in title_lower or "松浦亜弥" in title or "ayaya" in title_lower or any(s in title_lower for s in ["dokidoki! love mail", "tropical koishiteiru", "yeah! meccha holiday", "momoiro kataomoi"]):
        return "Aya Matsuura"

    if "fujimoto miki" in title_lower or "miki fujimoto" in title_lower or "藤本美貴" in title or "mikitty" in title_lower or any(s in title_lower for s in ["aenai nagai nichiyoubi", "soba ni iru dake de", "roppongi toori", "romantic ukare mode"]):
        return "Miki Fujimoto"

    if "abe natsumi" in title_lower or "natsumi abe" in title_lower or "安倍なつみ" in title or any(s in title_lower for s in ["22sai no watashi", "datte ikitekanakya"]):
        return "Natsumi Abe"

    if "suzuki airi" in title_lower or "airi suzuki" in title_lower or "鈴木愛理" in title or "do me a favor" in title_lower or "i mi shine" in title_lower:
        return "Airi Suzuki"

    if "michishige sayumi" in title_lower or "sayumi michishige" in title_lower or "道重さゆみ" in title or "sayuminglandoll" in title_lower:
        return "Sayumi Michishige"

    if "ハロプロ研修生" in title or "hello pro kenshuusei" in title_lower or "hello pro kenshusei" in title_lower or "kenshuusei" in title_lower or "kenshusei" in title_lower or "hello pro egg" in title_lower:
        return "Hello Pro Kenshuusei"

    # AKB48 Group Soloists & Subunits
    if "kashiwagi yuki" in title_lower or "yuki kashiwagi" in title_lower or "柏木由紀" in title or "yukirin" in title_lower:
        return "Yuki Kashiwagi"

    if "maeda atsuko" in title_lower or "atsuko maeda" in title_lower or "前田敦子" in title or "time machine nante iranai" in title_lower or "kimi wa boku da" in title_lower:
        return "Atsuko Maeda"

    if "yamamoto sayaka" in title_lower or "sayaka yamamoto" in title_lower or "山本彩" in title or "sayanee" in title_lower:
        return "Sayaka Yamamoto"

    if "watanabe mayu" in title_lower or "mayu watanabe" in title_lower or "渡辺麻友" in title or "mayuyu" in title_lower or "synchro tokimeki" in title_lower or "otona jelly beans" in title_lower:
        return "Mayu Watanabe"

    if "sashihara rino" in title_lower or "rino sashihara" in title_lower or "指原莉乃" in title or "soredemo suki da yo" in title_lower:
        return "Rino Sashihara"

    if "itano tomomi" in title_lower or "tomomi itano" in title_lower or "板野友美" in title or "tomochin" in title_lower:
        return "Tomomi Itano"

    if "oshima yuko" in title_lower or "yuko oshima" in title_lower or "大島優子" in title:
        return "Yuko Oshima"

    if "not yet" in title_lower or "ノットイェット" in title or any(s in title_lower for s in ["shuumatsu not yet", "naminori kakigoori", "perapera peraoche", "suika baby"]):
        return "Not yet"

    if "no3b" in title_lower or "no sleeves" in title_lower or "ノースリーブス" in title:
        return "no3b"

    if "french kiss" in title_lower or "フレンチ・キス" in title or "フレンチキス" in title:
        return "French Kiss"

    if "watarirouka hashiritai" in title_lower or "渡り廊下走り隊" in title:
        return "Watarirouka Hashiritai"

    # Sakamichi Soloists & Rival
    if "shiraishi mai" in title_lower or "mai shiraishi" in title_lower or "白石麻衣" in title or "maiyan" in title_lower:
        return "Mai Shiraishi"

    if "nishino nanase" in title_lower or "nanase nishino" in title_lower or "西野七瀬" in title or "naachan" in title_lower:
        return "Nanase Nishino"

    if "ikuta erika" in title_lower or "erika ikuta" in title_lower or "生田絵梨花" in title or "ikuchan" in title_lower:
        return "Erika Ikuta"

    if "saito asuka" in title_lower or "asuka saito" in title_lower or "齋藤飛鳥" in title or "ashurin" in title_lower:
        return "Asuka Saito"

    if "hirate yurina" in title_lower or "yurina hirate" in title_lower or "平手友梨奈" in title or "dance no riyuu" in title_lower:
        return "Yurina Hirate"

    if "boku ga mitakatta aozora" in title_lower or "僕が見たかった青空" in title or "僕青" in title:
        return "Boku ga Mitakatta Aozora"

    # Sister Groups
    if "candy tune" in title_lower or "キャンディートゥーン" in title or "きゃんちゅー" in title:
        return "CANDY TUNE"
    if "sweet steady" in title_lower or "スウィートステディ" in title or "すいすて" in title:
        return "SWEET STEADY"
    if "cutie street" in title_lower or "キューティーストリート" in title or "きゅーすと" in title:
        return "CUTIE STREET"
    if "fruits zipper" in title_lower or "フルーツジッパー" in title or "ふるっぱー" in title:
        return "FRUITS ZIPPER"

    if "is:sue" in title_lower or "イッシュ" in title or "1st is:sue" in title_lower or (pid_upper.startswith("UMCK") and "issue" in title_lower):
        return "IS:SUE"

    if "sakura gakuin" in title_lower or "さくら学院" in title:
        return "Sakura Gakuin"
    if "team shachi" in title_lower or "team syachihoko" in title_lower or "チームしゃちほこ" in title:
        return "TEAM SHACHI"
    if "batten girls" in title_lower or "batten showtai" in title_lower or "ばってん少女隊" in title:
        return "BATTEN GIRLS"
    if "ukka" in title_lower or "sakura ebis" in title_lower or "桜エビ〜ず" in title:
        return "ukka"
    if "≠me" in title_lower or "ノイミー" in title or "not equal me" in title_lower:
        return "≠ME"
    if "≒joy" in title_lower or "ニアジョイ" in title or "nearly equal joy" in title_lower:
        return "≒JOY"
    if "=love" in title_lower or "イコールラブ" in title or "イコラブ" in title:
        return "=LOVE"

    # =========================================================================
    # Step 2: Detect Primary Parent Groups in Title
    # =========================================================================
    if "akb48" in title_lower or "akb-" in title_lower or "akb gekijo" in title_lower:
        return "AKB48"
    if "ske48" in title_lower or "ske-" in title_lower:
        return "SKE48"
    if "nmb48" in title_lower or "nmb-" in title_lower:
        return "NMB48"
    if "hkt48" in title_lower or "hkt-" in title_lower:
        return "HKT48"
    if "ngt48" in title_lower:
        return "NGT48"
    if "stu48" in title_lower:
        return "STU48"

    if "nogizaka46" in title_lower or "乃木坂46" in title or "乃木坂" in title:
        return "Nogizaka46"
    if "sakurazaka46" in title_lower or "櫻坂46" in title or "keyakizaka46" in title_lower or "欅坂46" in title:
        return "Sakurazaka46"
    if "hinatazaka46" in title_lower or "日向坂46" in title:
        return "Hinatazaka46"
    if "22/7" in title_lower or "ナナブンノニジュウニ" in title or "ナナニジ" in title:
        return "22/7"

    if "morning musume" in title_lower or "モーニング娘" in title:
        return "Morning Musume"
    if "angerme" in title_lower or "アンジュルム" in title or "s/mileage" in title_lower or "スマイレージ" in title or "s mileage" in title_lower:
        return "ANGERME"
    if "juice=juice" in title_lower or "juicejuice" in title_lower or "ジュースジュース" in title:
        return "Juice=Juice"
    if "tsubaki factory" in title_lower or "つばきファクトリー" in title:
        return "Tsubaki Factory"
    if "beyooooonds" in title_lower or "ビヨーンズ" in title:
        return "BEYOOOOONDS"
    if "ocha norma" in title_lower or "オチャノーマ" in title:
        return "OCHA NORMA"
    if "rosy chronicle" in title_lower or "ロージークロニクル" in title:
        return "Rosy Chronicle"
    if "berryz kobo" in title_lower or "berryz工房" in title or "berryz" in title_lower:
        return "Berryz Kobo"
    if "℃-ute" in title or "c-ute" in title_lower or "cute concert" in title_lower:
        return "℃-ute"
    if "country girls" in title_lower or "カントリー・ガールズ" in title or "country musume" in title_lower or "カントリー娘" in title:
        return "Country Girls"
    if "kobushi factory" in title_lower or "こぶしファクトリー" in title:
        return "Kobushi Factory"
    if "melon kinenbi" in title_lower or "メロン記念日" in title:
        return "Melon Kinenbi"

    if "momoiro clover" in title_lower or "ももいろクローバー" in title or "ももクロ" in title or "momoclo" in title_lower:
        return "Momoiro Clover Z"
    if "shiritsu ebisu chugaku" in title_lower or "私立恵比寿中学" in title or "エビ中" in title or "ebichu" in title_lower:
        return "Shiritsu Ebisu Chugaku"
    if "chou tokimeki" in title_lower or "tokimeki sendenbu" in title_lower or "ときめき♡宣伝部" in title or "とき宣" in title:
        return "Chou Tokimeki Sendenbu"

    if "niziu" in title_lower or "ニジュー" in title:
        return "NiziU"
    if "me:i" in title_lower or "ミーアイ" in title:
        return "ME:I"
    if "babymetal" in title_lower or "ベビーメタル" in title:
        return "BABYMETAL"

    # =========================================================================
    # Step 3: Fallback - If title does not name a group, trust current_artist
    # =========================================================================
    if current_artist in CANONICAL_ARTIST_MAP:
        return current_artist

    return "Morning Musume"

def check_true_false_positive(item):
    title_lower = str(item.get("title", "")).lower()
    artist = str(item.get("artist", "")).strip()
    pid_upper = str(item.get("id", "")).upper()

    if is_authentic_prefix(pid_upper):
        return False, ""

    for pat in [r"\bsnow man\b", r"\bsixtones\b", r"\bking & prince\b", r"\btimelesz\b", r"\btravis japan\b", r"\bexile\b", r"\bjo1\b", r"\bini\b", r"\bbts\b", r"\bseventeen\b"]:
        if re.search(pat, title_lower):
            has_our_idol = any(k.lower() in title_lower for k in CANONICAL_ARTIST_MAP.keys())
            if not has_our_idol:
                return True, f"Male boyband item: matches '{pat}'"

    if artist == "You Kikkawa" and pid_upper.startswith("TKCA") and "kikkawa" not in title_lower and "吉川友" not in title_lower:
        return True, "Non-Kikkawa album matching common word 'you'"

    if artist == "IS:SUE":
        is_real = ("is:sue" in title_lower or "イッシュ" in title_lower or "connect" in title_lower or "static" in title_lower or pid_upper.startswith("UMCK"))
        if not is_real and ("issue" in title_lower or "magazine" in title_lower):
            return True, "Generic magazine issue leak under 'IS:SUE'"

    return False, ""

def main():
    print("==========================================")
    print("Starting Comprehensive 79-Group Catalog Sorter")
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

        raw_title = item.get("title", "")
        orig_art = item.get("artist", "").strip()
        orig_cat = item.get("category", "").strip()

        # Step 1: Detect True Artist from Title & ID
        resolved_art = classify_by_title_and_id(raw_title, pid, orig_art)
        resolved_cat = CANONICAL_ARTIST_MAP[resolved_art]

        if resolved_art != orig_art:
            realigned_artists.append((pid, raw_title[:32], f"{orig_art} -> {resolved_art}"))
            item["artist"] = resolved_art

        if resolved_cat != orig_cat:
            realigned_categories.append((pid, raw_title[:32], f"{orig_cat} -> {resolved_cat}"))
            item["category"] = resolved_cat

        # Step 2: Prune True False Positives
        is_bad, reason = check_true_false_positive(item)
        if is_bad:
            pruned_records.append((pid, raw_title, reason))
            continue

        cleaned_catalog[pid] = item

    # Save to products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Save directly to catalog-index.json so the website updates instantly
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

    # Display live breakdown for focus groups
    focus_targets = [
        "Maki Goto", "Erina Mano", "Aya Matsuura", "Buono!",
        "Hello Pro Kenshuusei", "Up Up Girls (2)", "GAM", "W",
        "v-u-den", "Minimoni", "Tanpopo", "Tsukishima Kirari",
        "Taiyo to Ciscomoon", "You Kikkawa", "Karin Miyamoto",
        "Atsuko Maeda", "Yuki Kashiwagi", "Berryz Kobo", "℃-ute"
    ]
    print("\n--- Live Distribution Across Focus Groups ---")
    for st in focus_targets:
        c = sum(1 for it in cleaned_catalog.values() if it.get("artist") == st)
        franchise = CANONICAL_ARTIST_MAP.get(st, "Unknown")
        print(f"  ⭐ {st.ljust(22)}: {str(c).rjust(4)} items [{franchise}]")

    print("\n==========================================")
    print("Sorting Complete. products.json and catalog-index.json are 100% in sync.")
    print("==========================================")

if __name__ == "__main__":
    main()
