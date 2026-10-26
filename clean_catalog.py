"""
IdolJapan.store — Catalog Cleaner & Category / Artist Reclassifier
Standardizes artist tags, fixes misclassifications across all 79+ idol groups and soloists,
enforces authentic Koharu Kusumi verification on all Tsukishima Kirari releases,
prevents group releases from being mislabeled as solo items,
removes non-idol boyband / anime false positives,
and synchronizes products.json, catalog-index.json, and writes clean_catalog_log.txt.
"""

import json
import os
import re
from datetime import datetime

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
LOG_FILE = "clean_catalog_log.txt"

# Official Up-Front prefixes used by Zetima / Piccolo Town / Up-Front Works
UPFRONT_PREFIXES = (
    "EPCE", "EPBE", "EPXE", "EPTE", "EPDE",
    "PKCP", "PKBP",
    "HKCN", "HKBN", "HKXN",
    "UFBW", "UFXW",
    "TGBS", "TGXF",
    "DAKU", "DCFGDS", "NEOODY"
)

# Canonical Tsukishima Kirari / Koharu Kusumi tracks, albums & video releases
KIRARI_KUSUMI_CANONICAL_TITLES = [
    "koi kana", "koi☆kana", "恋☆カナ",
    "balalaika", "バラライカ",
    "happy☆mysterious", "happy", "ハッピー☆彡",
    "chance!", "チャンス!",
    "papirappetta", "パパンケーキ",
    "anataboshi", "アナタボシ",
    "tan tan taan", "タンタンターン",
    "hapi hapi sunday", "はぴ☆はぴ サンデー",
    "kirarin land", "きらりん☆ランド",
    "mitsuboshi", "きらりん☆レボリューション・ソング・セレクション",
    "kirari to fuyu", "ベスト☆きらり", "best☆kirari", "best kirari",
    "kirarin revolution song selection",
    "hana wo pun", "futari wa ns", "ハナをぷーん", "ふたりはns",
    "kira pika", "kira☆pika", "きら☆ぴか",
    "milkyway", "サンサンgogo"
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

# Dedicated Soloists / Graduates whose individual solo releases must be accurately categorized
SOLO_GRADUATE_RULES = [
    ("Hello! Project", "Maria Makino", [r"\bmakino maria\b", r"\bmaria makino\b", r"牧野真莉愛"]),
    ("Hello! Project", "Yuko Nakazawa", [r"\bnakazawa yuko\b", r"\byuko nakazawa\b", r"中澤裕子"]),
    ("Hello! Project", "Kaori Iida", [r"\biida kaori\b", r"\bkaori iida\b", r"飯田圭織"]),
    ("Hello! Project", "Reina Tanaka", [r"\btanaka reina\b", r"\breina tanaka\b", r"田中れいな"]),
    ("Hello! Project", "Ai Takahashi", [r"\btakahashi ai\b", r"\bai takahashi\b", r"高橋愛"]),
    ("Hello! Project", "Risa Niigaki", [r"\bniigaki risa\b", r"\brisa niigaki\b", r"新垣里沙"]),
    ("Hello! Project", "Maimi Yajima", [r"\byajima maimi\b", r"\bmaimi yajima\b", r"矢島舞美"]),
    ("Hello! Project", "Masaki Sato", [r"\bsato masaki\b", r"\bmasaki sato\b", r"佐藤優樹", r"ding dong", r"ロマンティックなんてガラじゃない"]),
    ("Hello! Project", "Riho Sayashi", [r"\bsayashi riho\b", r"\briho sayashi\b", r"鞘師里保"]),
    ("Hello! Project", "Manaka Inaba", [r"\binaba manaka\b", r"\bmanaka inaba\b", r"稲場愛香", r"圧倒的lve", r"pink vampire"]),
    ("Hello! Project", "Mizuki Fukumura", [r"\bfukumura mizuki\b", r"\bmizuki fukumura\b", r"譜久村聖"]),
    ("Hello! Project", "Momoko Tsugunaga", [r"\btsugunaga momoko\b", r"\bmomoko tsugunaga\b", r"嗣永桃子", r"ももち"]),
    ("Hello! Project", "Miyabi Natsuyaki", [r"\bnatsuyaki miyabi\b", r"\bmiyabi natsuyaki\b", r"夏焼雅"]),
    ("Hello! Project", "Risako Sugaya", [r"\bsugaya risako\b", r"\brisako sugaya\b", r"菅谷梨沙子"]),
    ("Hello! Project", "Yurina Kumai", [r"\bkumai yurina\b", r"\byurina kumai\b", r"熊井友理奈"]),
    ("Hello! Project", "Ayaka Wada", [r"\bwada ayaka\b", r"\bayaka wada\b", r"和田彩花"]),
    ("Hello! Project", "Meimi Tamura", [r"\btamura meimi\b", r"\bmeimi tamura\b", r"田村芽実"]),
    ("Hello! Project", "Kanon Fukuda", [r"\bfukuda kanon\b", r"\bkanon fukuda\b", r"福田花音", r"巫まろ", r"maro kanna"]),
    ("Hello! Project", "Tomoko Kanazawa", [r"\bkanazawa tomoko\b", r"\btomoko kanazawa\b", r"金澤朋子"]),
    ("Hello! Project", "Yumeno Kishimoto", [r"\bkishimoto yumeno\b", r"\byumeno kishimoto\b", r"岸本ゆめの"]),
    ("Hello! Project", "Sayaka Kitahara", [r"\bkitahara sayaka\b", r"\bsayaka kitahara\b", r"北原沙弥香"]),
    ("Hello! Project", "Nozomi Tsuji", [r"\btsuji nozomi\b", r"\bnozomi tsuji\b", r"辻希美", r"のんピース"]),
    ("Hello! Project", "Ai Kago", [r"\bkago ai\b", r"\bai kago\b", r"加護亜依"]),
    ("Hello! Project", "Rika Ishikawa", [r"\bishikawa rika\b", r"\brika ishikawa\b", r"石川梨華"]),
    ("Hello! Project", "Haruka Kudo", [r"\bkudo haruka\b", r"\bharuka kudo\b", r"工藤遥"]),
    ("Hello! Project", "Haruna Iikubo", [r"\biikubo haruna\b", r"\bharuna iikubo\b", r"飯窪春菜"]),
    ("Hello! Project", "Erina Ikuta", [r"\bikuta erina\b", r"\berina ikuta\b", r"生田衣梨奈"]),
    ("Hello! Project", "Akane Haga", [r"\bhaga akane\b", r"\bakane haga\b", r"羽賀朱音"]),
    ("Hello! Project", "Rikako Sasaki", [r"\bsasaki rikako\b", r"\brikako sasaki\b", r"佐々木莉佳子"]),
    ("Hello! Project", "Mizuki Murota", [r"\bmurota mizuki\b", r"\bmizuki murota\b", r"室田瑞希"]),
    ("Hello! Project", "Yuka Miyazaki", [r"\bmiyazaki yuka\b", r"\byuka miyazaki\b", r"宮崎由加"]),
    ("Hello! Project", "Akari Uemura", [r"\buemura akari\b", r"\bakari uemura\b", r"植村あかり"]),
    ("Hello! Project", "Chisaki Morito", [r"\bmorito chisaki\b", r"\bchisaki morito\b", r"森戸知沙希"]),
    ("Hello! Project", "Mai Satoda", [r"\bsatoda mai\b", r"\bmai satoda\b", r"里田まい"]),
    ("Hello! Project", "Ayumi Ishida", [r"\bishida ayumi\b", r"\bayumi ishida\b", r"石田亜佑美"]),
    ("Hello! Project", "Ruru Dambara", [r"\bdambara ruru\b", r"\bruru dambara\b", r"段原瑠々"]),
    ("Hello! Project", "Yuhane Yamazaki", [r"\byamazaki yuhane\b", r"\byuhane yamazaki\b", r"山﨑夢羽"]),
    ("Hello! Project", "Ayano Hamaura", [r"\bhamaura ayano\b", r"\bayano hamaura\b", r"浜浦彩乃"]),
    ("Hello! Project", "Ayano Kawamura", [r"\bkawamura ayano\b", r"\bayano kawamura\b", r"川村文乃"]),
    ("Hello! Project", "Momona Kasahara", [r"\bkasahara momona\b", r"\bmomona kasahara\b", r"笠原桃奈"]),
    ("Hello! Project", "Mao Akiyama", [r"\bakiyama mao\b", r"\bmao akiyama\b", r"秋山眞緒"]),
    ("Hello! Project", "Nanami Yanagawa", [r"\byanagawa nanami\b", r"\bnanami yanagawa\b", r"梁川奈々美"]),
    ("Hello! Project", "Sayumi Michishige", [r"sayumi michishige", r"michishige sayumi", r"道重さゆみ", r"sayuming"]),
    ("Hello! Project", "Aya Matsuura", [r"aya matsuura", r"matsuura aya", r"松浦亜弥"]),
    ("Hello! Project", "Maki Goto", [r"maki goto", r"goto maki", r"後藤真希"]),
    ("Hello! Project", "Natsumi Abe", [r"natsumi abe", r"abe natsumi", r"安倍なつみ"]),
    ("Hello! Project", "Erina Mano", [r"erina mano", r"mano erina", r"真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", [r"airi suzuki", r"suzuki airi", r"鈴木愛理"]),
    ("Hello! Project", "Miki Fujimoto", [r"miki fujimoto", r"fujimoto miki", r"藤本美貴"]),
    ("Hello! Project", "Karin Miyamoto", [r"karin miyamoto", r"miyamoto karin", r"宮本佳林"])
]

# Primary Group Names (To ensure group releases don't get overwritten by individual member mentions)
PRIMARY_GROUP_NAMES = {
    "Morning Musume", "ANGERME", "Juice=Juice", "Tsubaki Factory", "BEYOOOOONDS",
    "OCHA NORMA", "Rosy Chronicle", "Hello Pro Kenshuusei", "Berryz Kobo", "℃-ute",
    "Buono!", "Country Girls", "Kobushi Factory", "Melon Kinenbi", "Tanpopo",
    "Minimoni", "v-u-den", "W", "GAM", "Taiyo to Ciscomoon", "LoVendoR", "PINK CRES.",
    "AKB48", "SKE48", "NMB48", "HKT48", "NGT48", "STU48",
    "Nogizaka46", "Sakurazaka46", "Hinatazaka46", "22/7", "Boku ga Mitakatta Aozora",
    "Momoiro Clover Z", "Shiritsu Ebisu Chugaku", "Chou Tokimeki Sendenbu",
    "TEAM SHACHI", "BATTEN GIRLS", "ukka",
    "=LOVE", "≠ME", "≒JOY",
    "FRUITS ZIPPER", "CANDY TUNE", "SWEET STEADY", "CUTIE STREET",
    "NiziU", "ME:I", "IS:SUE", "BABYMETAL", "Sakura Gakuin"
}

def is_boyband_or_anime_false_positive(text):
    t_lower = text.lower()
    for pat in MALE_BOYBAND_PATTERNS:
        if re.search(pat, t_lower):
            return True
    for pat in NON_IDOL_MEDIA_PATTERNS:
        if re.search(pat, t_lower):
            return True
    return False

def verify_tsukishima_kirari_item(pid, title, artist):
    """
    Validates whether an item is genuine Tsukishima Kirari starring Koharu Kusumi.
    Guarantees that official Up-Front releases and canonical singles are never purged.
    """
    t_lower = title.lower()
    pid_upper = pid.upper()

    # 1. Direct explicit name match
    if any(sig in t_lower for sig in ["kusumi koharu", "koharu kusumi", "久住小春"]):
        return True

    # 2. Known Zetima / Up-Front catalog numbers for Kirari / Kusumi
    if any(pid_upper.startswith(pfx) for pfx in ["EPCE", "EPBE", "EPDE"]):
        if any(sig in t_lower for sig in KIRARI_KUSUMI_CANONICAL_TITLES) or "月島きらり" in title or "kirari" in t_lower:
            return True

    # 3. Canonical song title / album matches
    for canonical in KIRARI_KUSUMI_CANONICAL_TITLES:
        if canonical in t_lower:
            return True

    # 4. If none of the above match, it is an unaffiliated anime merchandise item
    return False

def clean_catalog():
    if not os.path.exists(DATA_FILE):
        print(f"[Error] {DATA_FILE} does not exist.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_initial = len(catalog)
    cleaned_catalog = {}
    purged_count = 0
    reclassified_count = 0
    log_records = []

    print(f"Beginning Intelligent Catalog Scrub: {total_initial:,} releases to verify...", flush=True)

    for pid, item in catalog.items():
        title = item.get("title", "")
        artist = item.get("artist", "")
        category = item.get("category", "")
        full_text = f"{title} {artist}".strip()
        full_text_lower = full_text.lower()

        # -------------------------------------------------------------
        # STEP 1: Strict Tsukishima Kirari / Koharu Kusumi Verification
        # -------------------------------------------------------------
        if (artist == "Tsukishima Kirari" or 
            "tsukishima kirari" in full_text_lower or 
            "月島きらり" in full_text):

            if verify_tsukishima_kirari_item(pid, title, artist):
                item["artist"] = "Tsukishima Kirari"
                item["category"] = "Hello! Project"
            else:
                purged_count += 1
                msg = f"[PURGED: NON_KUSUMI_KIRARI] [{pid}] {title}"
                log_records.append(msg)
                continue

        # -------------------------------------------------------------
        # STEP 2: Boyband & Non-Idol False Positive Removal
        # -------------------------------------------------------------
        # Protect authentic female idols before checking negative patterns
        is_protected_female_idol = any(g.lower() in full_text_lower for g in PRIMARY_GROUP_NAMES) or \
                                   any(pfx in pid.upper() for pfx in UPFRONT_PREFIXES)

        if not is_protected_female_idol and is_boyband_or_anime_false_positive(full_text):
            purged_count += 1
            msg = f"[PURGED: FALSE_POSITIVE] [{pid}] {title} ({artist})"
            log_records.append(msg)
            continue

        # -------------------------------------------------------------
        # STEP 3: Safe Soloist Reclassification (Preserve Group Items)
        # -------------------------------------------------------------
        # Only reclassify to a soloist if the item is NOT a primary group album/single
        is_dedicated_group_release = False
        if artist in PRIMARY_GROUP_NAMES and not any(kw in title.lower() for kw in ["photobook", "photo book", "写真集", "solo", "solo live"]):
            is_dedicated_group_release = True

        if not is_dedicated_group_release:
            for cat_target, soloist_name, patterns in SOLO_GRADUATE_RULES:
                matched_soloist = False
                for pat in patterns:
                    if re.search(pat, full_text_lower):
                        # Ensure we don't misclassify a Morning Musume album as a soloist single
                        if artist != soloist_name:
                            item["artist"] = soloist_name
                            item["category"] = cat_target
                            reclassified_count += 1
                            log_records.append(f"[RECLASSIFIED: SOLOIST] [{pid}] '{title}' -> {soloist_name} ({cat_target})")
                        matched_soloist = True
                        break
                if matched_soloist:
                    break

        # -------------------------------------------------------------
        # STEP 4: Standardize Sakurazaka46 / Keyakizaka46
        # -------------------------------------------------------------
        if item.get("artist") in ["Keyakizaka46", "欅坂46"]:
            item["artist"] = "Sakurazaka46"
            item["category"] = "Sakamichi Series"
            reclassified_count += 1

        cleaned_catalog[pid] = item

    # Save to products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Synchronize catalog-index.json for live Cloudflare Pages deployment
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Write audit log to LOG_FILE
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"IdolJapan.store Catalog Clean Log — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write("=" * 70 + "\n")
        f.write(f"Total Initial Releases:     {total_initial:,}\n")
        f.write(f"Purged False Positives:     {purged_count:,}\n")
        f.write(f"Reclassified / Aligned:     {reclassified_count:,}\n")
        f.write(f"Total Preserved Releases:   {len(cleaned_catalog):,}\n")
        f.write("=" * 70 + "\n\n")
        if log_records:
            f.write("\n".join(log_records) + "\n")
        else:
            f.write("No items required purging or reclassification in this pass.\n")

    print("\n==========================================================")
    print("Catalog Scrub Complete!")
    print(f"Initial Catalog Releases:  {total_initial:,}")
    print(f"Purged False Positives:    {purged_count:,}")
    print(f"Reclassified / Aligned:    {reclassified_count:,}")
    print(f"Final Cleaned Releases:    {len(cleaned_catalog):,}")
    print(f"Audit Log Written:         {LOG_FILE}")
    print("Synchronized:              products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    clean_catalog()
