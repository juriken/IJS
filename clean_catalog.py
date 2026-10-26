"""
IdolJapan.store — Intelligent Catalog Sanitizer & Classification Engine
Standardizes artist tags, enforces accurate group vs. soloist boundaries,
verifies genuine Tsukishima Kirari (Koharu Kusumi) releases,
prevents concert and compilation overwrites, eliminates false-positive boyband/anime purges,
and synchronizes products.json, catalog-index.json, and clean_catalog_log.txt.
"""

import json
import os
import re
from datetime import datetime

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"
LOG_FILE = "clean_catalog_log.txt"

# Official Up-Front catalog prefixes used by Zetima / Piccolo Town / Up-Front Works
UPFRONT_PREFIXES = (
    "EPCE", "EPBE", "EPXE", "EPTE", "EPDE",
    "PKCP", "PKBP",
    "HKCN", "HKBN", "HKXN",
    "UFBW", "UFXW",
    "TGBS", "TGXF",
    "DAKU", "DCFGDS", "NEOODY"
)

# Canonical Tsukishima Kirari / Koharu Kusumi tracks, albums, anime singles & video works
KIRARI_KUSUMI_CANONICAL_SIGNATURES = [
    "koi kana", "koi☆kana", "恋☆カナ",
    "balalaika", "バラライカ",
    "happy☆mysterious", "happy", "ハッピー☆彡", "ハッピー",
    "chance!", "チャンス!", "チャンス！",
    "papirappetta", "パパンケーキ",
    "anataboshi", "アナタボシ",
    "tan tan taan", "タンタンターン",
    "hapi hapi sunday", "はぴ☆はぴ サンデー", "はぴはぴサンデー",
    "kirarin land", "きらりん☆ランド", "きらりんランド",
    "mitsuboshi", "きらりん☆レボリューション・ソング・セレクション",
    "kirari to fuyu", "ベスト☆きらり", "best☆kirari", "best kirari",
    "kirarin revolution", "きらりん☆レボリューション", "きらりんレボリューション",
    "hana wo pun", "futari wa ns", "ハナをぷーん", "ふたりはns",
    "kira pika", "kira☆pika", "きら☆ぴか", "きらぴか",
    "milkyway", "サンサンgogo", "sunsun gogo",
    "kusumi koharu", "koharu kusumi", "久住小春"
]

# Strict boyband patterns with strict word boundaries to prevent substring collisions
MALE_BOYBAND_PATTERNS = [
    r"\b(snow\s*man)\b", r"\b(sixtones)\b", r"\b(king\s*&\s*prince)\b", r"\b(naniwa\s*danshi)\b",
    r"\b(hey!\s*say!\s*jump)\b", r"\b(sexy\s*zone)\b", r"\b(timelesz)\b", r"\b(travis\s*japan)\b",
    r"\b(kis-my-ft2)\b", r"\b(kanjani8?|super\s*eight)\b", r"\b(kat-tun)\b",
    r"\b(johnnys|johnny's|starto)\b", r"\b(west\.)\b", r"\b(arashi)\b",
    r"\b(exile(?:\s+tribe)?)\b", r"\b(sandaime\s*j\s*soul\s*brothers)\b", r"\b(generations\s+from\s+exile)\b",
    r"\b(the\s*rampage\s+from\s+exile)\b", r"\b(fantastics\s+from\s+exile)\b", r"\b(ballistik\s*boyz)\b",
    r"(?<![a-z0-9])jo1(?![a-z0-9])", r"(?<![a-z0-9])ini(?![a-z0-9])",
    r"\b(be:first)\b", r"\b(mazzel)\b", r"\b(&team)\b", r"\b(stray\s*kids)\b",
    r"\b(tomorrow\s*x\s*together|txt)\b", r"\b(seventeen)\b", r"\b(bts)\b",
    r"\b(enhypen)\b", r"\b(nct(?:\s*127|\s*dream)?)\b", r"\b(ateez)\b",
    r"\b(zerobaseone|zb1)\b", r"\b(riize)\b", r"\b(boys\s*and\s*men)\b", r"\b(bullet\s*train|超特急)\b"
]

NON_IDOL_MEDIA_PATTERNS = [
    r"\b(kamen\s*rider|仮面ライダー)\b", r"\b(gundam|ガンダム)\b", r"\b(dragon\s*ball|ドラゴンボール)\b",
    r"\b(one\s*piece|ワンピース)\b", r"\b(detective\s*conan|名探偵コナン)\b", r"\b(pokemon|ポケットモンスター)\b",
    r"\b(digimon|デジモン)\b", r"\b(yu-gi-oh|遊戯王)\b", r"\b(touken\s*ranbu|刀剣乱舞)\b",
    r"\b(hypnosis\s*mic|ヒプノシスマイク)\b", r"\b(ensemble\s*stars|あんさんぶるスターズ)\b",
    r"\b(twisted\s*wonderland|ツイステッドワンダーランド)\b", r"\b(jujutsu\s*kaisen|呪術廻戦)\b",
    r"\b(demon\s*slayer|鬼滅の刃)\b", r"\b(classical\s*guitar)\b", r"\b(bluegrass)\b"
]

# Primary Group Names (To prevent group concert/album releases from being collapsed into a single member)
PRIMARY_GROUP_NAMES = {
    "Morning Musume", "ANGERME", "Juice=Juice", "Tsubaki Factory", "BEYOOOOONDS",
    "OCHA NORMA", "Rosy Chronicle", "Hello Pro Kenshuusei", "Berryz Kobo", "℃-ute",
    "Buono!", "Country Girls", "Kobushi Factory", "Melon Kinenbi", "Tanpopo",
    "Minimoni", "v-u-den", "W", "GAM", "Taiyo to Ciscomoon", "LoVendoR", "PINK CRES.",
    "AKB48", "SKE48", "NMB48", "HKT48", "NGT48", "STU48",
    "Not yet", "no3b", "French Kiss", "Watarirouka Hashiritai",
    "Nogizaka46", "Sakurazaka46", "Hinatazaka46", "22/7", "Boku ga Mitakatta Aozora",
    "Momoiro Clover Z", "Shiritsu Ebisu Chugaku", "Chou Tokimeki Sendenbu",
    "TEAM SHACHI", "BATTEN GIRLS", "ukka",
    "=LOVE", "≠ME", "≒JOY",
    "FRUITS ZIPPER", "CANDY TUNE", "SWEET STEADY", "CUTIE STREET",
    "NiziU", "ME:I", "IS:SUE", "BABYMETAL", "Sakura Gakuin"
}

# Dedicated Soloists / Graduates whose individual solo releases must be accurately categorized
SOLO_GRADUATE_RULES = [
    ("Hello! Project", "Maria Makino", [r"\bmakino\s+maria\b", r"\bmaria\s+makino\b", r"牧野真莉愛"]),
    ("Hello! Project", "Yuko Nakazawa", [r"\bnakazawa\s+yuko\b", r"\byuko\s+nakazawa\b", r"中澤裕子"]),
    ("Hello! Project", "Kaori Iida", [r"\biida\s+kaori\b", r"\bkaori\s+iida\b", r"飯田圭織"]),
    ("Hello! Project", "Reina Tanaka", [r"\btanaka\s+reina\b", r"\breina\s+tanaka\b", r"田中れいな"]),
    ("Hello! Project", "Ai Takahashi", [r"\btakahashi\s+ai\b", r"\bai\s+takahashi\b", r"高橋愛"]),
    ("Hello! Project", "Risa Niigaki", [r"\bniigaki\s+risa\b", r"\brisa\s+niigaki\b", r"新垣里沙"]),
    ("Hello! Project", "Maimi Yajima", [r"\byajima\s+maimi\b", r"\bmaimi\s+yajima\b", r"矢島舞美"]),
    ("Hello! Project", "Masaki Sato", [r"\bsato\s+masaki\b", r"\bmasaki\s+sato\b", r"佐藤優樹", r"ding\s+dong", r"ロマンティックなんてガラじゃない"]),
    ("Hello! Project", "Riho Sayashi", [r"\bsayashi\s+riho\b", r"\briho\s+sayashi\b", r"鞘師里保"]),
    ("Hello! Project", "Manaka Inaba", [r"\binaba\s+manaka\b", r"\bmanaka\s+inaba\b", r"稲場愛香", r"圧倒的lve", r"pink\s+vampire"]),
    ("Hello! Project", "Mizuki Fukumura", [r"\bfukumura\s+mizuki\b", r"\bmizuki\s+fukumura\b", r"譜久村聖"]),
    ("Hello! Project", "Momoko Tsugunaga", [r"\btsugunaga\s+momoko\b", r"\bmomoko\s+tsugunaga\b", r"嗣永桃子", r"ももち"]),
    ("Hello! Project", "Miyabi Natsuyaki", [r"\bnatsuyaki\s+miyabi\b", r"\bmiyabi\s+natsuyaki\b", r"夏焼雅"]),
    ("Hello! Project", "Risako Sugaya", [r"\bsugaya\s+risako\b", r"\brisako\s+sugaya\b", r"菅谷梨沙子"]),
    ("Hello! Project", "Yurina Kumai", [r"\bkumai\s+yurina\b", r"\byurina\s+kumai\b", r"熊井友理奈"]),
    ("Hello! Project", "Ayaka Wada", [r"\bwada\s+ayaka\b", r"\bayaka\s+wada\b", r"和田彩花"]),
    ("Hello! Project", "Meimi Tamura", [r"\btamura\s+meimi\b", r"\bmeimi\s+tamura\b", r"田村芽実"]),
    ("Hello! Project", "Kanon Fukuda", [r"\bfukuda\s+kanon\b", r"\bkanon\s+fukuda\b", r"福田花音", r"巫まろ", r"maro\s+kanna"]),
    ("Hello! Project", "Tomoko Kanazawa", [r"\bkanazawa\s+tomoko\b", r"\btomoko\s+kanazawa\b", r"金澤朋子"]),
    ("Hello! Project", "Yumeno Kishimoto", [r"\bkishimoto\s+yumeno\b", r"\byumeno\s+kishimoto\b", r"岸本ゆめの"]),
    ("Hello! Project", "Sayaka Kitahara", [r"\bkitahara\s+sayaka\b", r"\bsayaka\s+kitahara\b", r"北原沙弥香"]),
    ("Hello! Project", "Nozomi Tsuji", [r"\btsuji\s+nozomi\b", r"\bnozomi\s+tsuji\b", r"辻希美", r"のんピース"]),
    ("Hello! Project", "Ai Kago", [r"\bkago\s+ai\b", r"\bai\s+kago\b", r"加護亜依"]),
    ("Hello! Project", "Rika Ishikawa", [r"\bishikawa\s+rika\b", r"\brika\s+ishikawa\b", r"石川梨華"]),
    ("Hello! Project", "Haruka Kudo", [r"\bkudo\s+haruka\b", r"\bharuka\s+kudo\b", r"工藤遥"]),
    ("Hello! Project", "Haruna Iikubo", [r"\biikubo\s+haruna\b", r"\bharuna\s+iikubo\b", r"飯窪春菜"]),
    ("Hello! Project", "Erina Ikuta", [r"\bikuta\s+erina\b", r"\berina\s+ikuta\b", r"生田衣梨奈"]),
    ("Hello! Project", "Akane Haga", [r"\bhaga\s+akane\b", r"\bakane\s+haga\b", r"羽賀朱音"]),
    ("Hello! Project", "Rikako Sasaki", [r"\bsasaki\s+rikako\b", r"\brikako\s+sasaki\b", r"佐々木莉佳子"]),
    ("Hello! Project", "Mizuki Murota", [r"\bmurota\s+mizuki\b", r"\bmizuki\s+murota\b", r"室田瑞希"]),
    ("Hello! Project", "Yuka Miyazaki", [r"\bmiyazaki\s+yuka\b", r"\byuka\s+miyazaki\b", r"宮崎由加"]),
    ("Hello! Project", "Akari Uemura", [r"\buemura\s+akari\b", r"\bakari\s+uemura\b", r"植村あかり"]),
    ("Hello! Project", "Chisaki Morito", [r"\bmorito\s+chisaki\b", r"\bchisaki\s+morito\b", r"森戸知沙希"]),
    ("Hello! Project", "Mai Satoda", [r"\bsatoda\s+mai\b", r"\bmai\s+satoda\b", r"里田まい"]),
    ("Hello! Project", "Ayumi Ishida", [r"\bishida\s+ayumi\b", r"\bayumi\s+ishida\b", r"石田亜佑美"]),
    ("Hello! Project", "Ruru Dambara", [r"\bdambara\s+ruru\b", r"\bruru\s+dambara\b", r"段原瑠々"]),
    ("Hello! Project", "Yuhane Yamazaki", [r"\byamazaki\s+yuhane\b", r"\byuhane\s+yamazaki\b", r"山﨑夢羽"]),
    ("Hello! Project", "Ayano Hamaura", [r"\bhamaura\s+ayano\b", r"\bayano\s+hamaura\b", r"浜浦彩乃"]),
    ("Hello! Project", "Ayano Kawamura", [r"\bkawamura\s+ayano\b", r"\bayano\s+kawamura\b", r"川村文乃"]),
    ("Hello! Project", "Momona Kasahara", [r"\bkasahara\s+momona\b", r"\bmomona\s+kasahara\b", r"笠原桃奈"]),
    ("Hello! Project", "Mao Akiyama", [r"\bakiyama\s+mao\b", r"\bmao\s+akiyama\b", r"秋山眞緒"]),
    ("Hello! Project", "Nanami Yanagawa", [r"\byanagawa\s+nanami\b", r"\bnanami\s+yanagawa\b", r"梁川奈々美"]),
    ("Hello! Project", "Sayumi Michishige", [r"\bsayumi\s+michishige\b", r"\bmichishige\s+sayumi\b", r"道重さゆみ", r"\bsayuming\b"]),
    ("Hello! Project", "Aya Matsuura", [r"\baya\s+matsuura\b", r"\bmatsuura\s+aya\b", r"松浦亜弥"]),
    ("Hello! Project", "Maki Goto", [r"\bmaki\s+goto\b", r"\bgoto\s+maki\b", r"後藤真希"]),
    ("Hello! Project", "Natsumi Abe", [r"\bnatsumi\s+abe\b", r"\babe\s+natsumi\b", r"安倍なつみ"]),
    ("Hello! Project", "Erina Mano", [r"\berina\s+mano\b", r"\bmano\s+erina\b", r"真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", [r"\bairi\s+suzuki\b", r"\bsuzuki\s+airi\b", r"鈴木愛理"]),
    ("Hello! Project", "Miki Fujimoto", [r"\bmiki\s+fujimoto\b", r"\bfujimoto\s+miki\b", r"藤本美貴", r"\bmikitty\b"]),
    ("Hello! Project", "Karin Miyamoto", [r"\bkarin\s+miyamoto\b", r"\bmiyamoto\s+karin\b", r"宮本佳林"])
]

def is_boyband_or_anime_false_positive(text):
    t_lower = text.lower()
    for pat in MALE_BOYBAND_PATTERNS:
        if re.search(pat, t_lower):
            return True, pat
    for pat in NON_IDOL_MEDIA_PATTERNS:
        if re.search(pat, t_lower):
            return True, pat
    return False, ""

def verify_tsukishima_kirari_item(pid, title, artist):
    """
    Validates genuine Tsukishima Kirari starring Koharu Kusumi releases.
    Returns True for authentic Up-Front / Zetima releases, canonical singles, and Kusumi mentions.
    Returns False for third-party non-Kusumi anime merchandise.
    """
    t_lower = title.lower()
    pid_upper = pid.upper()

    # 1. Direct Koharu Kusumi mention
    if any(sig in t_lower for sig in ["kusumi koharu", "koharu kusumi", "久住小春"]):
        return True, "Direct Koharu Kusumi Mention"

    # 2. Authentic Up-Front Zetima prefixes (EPCE, EPBE, EPDE)
    if any(pid_upper.startswith(pfx) for pfx in ["EPCE", "EPBE", "EPDE"]):
        if any(sig in t_lower for sig in KIRARI_KUSUMI_CANONICAL_SIGNATURES) or "月島きらり" in title or "kirari" in t_lower:
            return True, "Up-Front Catalog ID Match"

    # 3. Canonical singles/albums sung by Koharu Kusumi as Kirari
    for sig in KIRARI_KUSUMI_CANONICAL_SIGNATURES:
        if sig in t_lower:
            return True, f"Canonical Signature Match: '{sig}'"

    # 4. If none match, it is an unaffiliated anime merchandise product
    return False, "No Kusumi Koharu signature or Up-Front catalog match"

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
    preserved_kirari_count = 0
    log_records = []

    print(f"Beginning Intelligent Catalog Scrub: {total_initial:,} releases to verify...", flush=True)

    for pid, item in catalog.items():
        title = item.get("title", "")
        artist = item.get("artist", "")
        category = item.get("category", "")
        full_text = f"{title} {artist}".strip()
        full_text_lower = full_text.lower()
        pid_upper = pid.upper()

        # -------------------------------------------------------------
        # STEP 1: Accurate Tsukishima Kirari / Koharu Kusumi Filter
        # -------------------------------------------------------------
        is_kirari_candidate = (
            artist == "Tsukishima Kirari" or 
            "tsukishima kirari" in full_text_lower or 
            "月島きらり" in full_text or
            "きらりん☆レボリューション" in full_text or
            "kirarin revolution" in full_text_lower
        )

        if is_kirari_candidate:
            is_valid_kirari, reason = verify_tsukishima_kirari_item(pid, title, artist)
            if is_valid_kirari:
                item["artist"] = "Tsukishima Kirari"
                item["category"] = "Hello! Project"
                preserved_kirari_count += 1
            else:
                purged_count += 1
                msg = f"[PURGED: NON_KUSUMI_KIRARI] [{pid}] {title} (Reason: {reason})"
                log_records.append(msg)
                continue

        # -------------------------------------------------------------
        # STEP 2: Boyband & Non-Idol False Positive Removal
        # -------------------------------------------------------------
        # Protect known female idol groups and authentic Up-Front prefixes
        is_protected_female_idol = any(g.lower() in full_text_lower for g in PRIMARY_GROUP_NAMES) or \
                                   any(pid_upper.startswith(pfx) for pfx in UPFRONT_PREFIXES)

        if not is_protected_female_idol:
            is_bad, pattern_matched = is_boyband_or_anime_false_positive(full_text)
            if is_bad:
                purged_count += 1
                msg = f"[PURGED: FALSE_POSITIVE] [{pid}] {title} (Pattern: {pattern_matched})"
                log_records.append(msg)
                continue

        # -------------------------------------------------------------
        # STEP 3: Protected Group Concert vs. Soloist Classification
        # -------------------------------------------------------------
        # Never reclassify full group concert tours or albums to a single member
        /* File: clean_catalog.py | Approx. Lines: 180-210 | Block/Target: Protected Group Concert Tour Logic */
        # Fix mislabeled HKT48 concert tour
        if pid == "HKT-D0026" or "hkt48 natsu no hall tour" in full_text_lower:
            item["artist"] = "HKT48"
            item["category"] = "AKB48 Group"

        # Detect canonical group concert tours in the title and lock to the primary group
        is_primary_group_concert = False
        for group in PRIMARY_GROUP_NAMES:
            if group.lower() in full_text_lower and any(kw in full_text_lower for kw in [
                "concert tour", "live tour", "anniversary live", "final live", "sotsugyo special", "graduation ceremony"
            ]) and not any(kw in full_text_lower for kw in ["photobook", "photo book", "写真集", "visual book"]):
                item["artist"] = group
                is_primary_group_concert = True
                break

        if is_primary_group_concert:
            cleaned_catalog[pid] = item
            continue

        is_group_concert_or_album = (
            item.get("artist") in PRIMARY_GROUP_NAMES and
            not any(kw in full_text_lower for kw in [
                "photobook", "photo book", "写真集", "solo live", "solo album",
                "solo single", "solo tour", "visual book"
            ])
        )
        
        # Do not reclassify joint Hello! Project seasonal tours (Hina Fes, Countdown, Kenshuusei recital)
        is_joint_hp_event = any(kw in full_text_lower for kw in [
            "hina fes", "ひなフェス", "countdown japan", "hello! project 20",
            "hello! project 19", "hello! project 202", "recital", "定期公演"
        ])

        if not is_group_concert_or_album and not is_joint_hp_event:
            for cat_target, soloist_name, patterns in SOLO_GRADUATE_RULES:
                matched_soloist = False
                for pat in patterns:
                    if re.search(pat, full_text_lower):
                        if artist != soloist_name:
                            old_artist = artist
                            item["artist"] = soloist_name
                            item["category"] = cat_target
                            reclassified_count += 1
                            log_records.append(f"[RECLASSIFIED: SOLOIST] [{pid}] '{title}' ({old_artist} -> {soloist_name})")
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

    # 1. Save to products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # 2. Synchronize catalog-index.json for immediate deployment
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # 3. Write structured audit log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"IdolJapan.store Catalog Clean Log — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Initial Releases:         {total_initial:,}\n")
        f.write(f"Purged False Positives:         {purged_count:,}\n")
        f.write(f"Reclassified / Aligned:         {reclassified_count:,}\n")
        f.write(f"Verified Tsukishima Kirari:     {preserved_kirari_count:,}\n")
        f.write(f"Total Cleaned Releases Saved:   {len(cleaned_catalog):,}\n")
        f.write("=" * 80 + "\n\n")
        if log_records:
            f.write("\n".join(log_records) + "\n")
        else:
            f.write("Catalog verified clean. No records required purging or reclassification.\n")

    print("\n==========================================================")
    print("Catalog Scrub Complete!")
    print(f"Initial Releases:              {total_initial:,}")
    print(f"Purged False Positives:        {purged_count:,}")
    print(f"Reclassified / Aligned:        {reclassified_count:,}")
    print(f"Verified Tsukishima Kirari:    {preserved_kirari_count:,}")
    print(f"Total Cleaned Releases:        {len(cleaned_catalog):,}")
    print(f"Audit Log Generated:           {LOG_FILE}")
    print("Synchronized:                  products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    clean_catalog()
