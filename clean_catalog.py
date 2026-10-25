"""
IdolJapan.store — Catalog Cleaner & Category / Artist Reclassifier
Standardizes artist tags, fixes misclassifications across all 79+ idol groups and soloists,
enforces strict Koharu Kusumi verification on all Tsukishima Kirari releases,
removes non-idol boyband / anime false positives, and synchronizes products.json and catalog-index.json.
"""

import json
import os
import re

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"

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

# Classification Rules: (Category, Canonical Artist, Regex/Substring Matchers)
RECLASSIFICATION_RULES = [
    # 43 Graduate & Soloist Hello! Project Members
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

    # Hello! Project — Active Groups & Units
    ("Hello! Project", "Morning Musume", [r"morning musume", r"モーニング娘"]),
    ("Hello! Project", "ANGERME", [r"angerme", r"アンジュルム", r"s/mileage", r"スマイレージ"]),
    ("Hello! Project", "Juice=Juice", [r"juice=juice", r"ジュースジュース"]),
    ("Hello! Project", "Tsubaki Factory", [r"tsubaki factory", r"つばきファクトリー"]),
    ("Hello! Project", "BEYOOOOONDS", [r"beyooooonds", r"ビヨーンズ"]),
    ("Hello! Project", "OCHA NORMA", [r"ocha norma", r"オチャノーマ"]),
    ("Hello! Project", "Rosy Chronicle", [r"rosy chronicle", r"ロージークロニクル"]),
    ("Hello! Project", "Hello Pro Kenshuusei", [r"hello pro kenshuusei", r"hello pro kenshusei", r"ハロプロ研修生"]),

    # Hello! Project — Subunits & Past Flagships
    ("Hello! Project", "Minimoni", [r"minimoni", r"mini moni", r"ミニモニ"]),
    ("Hello! Project", "Berryz Kobo", [r"berryz kobo", r"berryz工房", r"\bberryz\b"]),
    ("Hello! Project", "℃-ute", [r"c-ute", r"℃-ute", r"\bcute\b"]),
    ("Hello! Project", "Buono!", [r"\bbuono!\b", r"\bbuono\b"]),
    ("Hello! Project", "Country Girls", [r"country girls", r"country musume", r"カントリー・ガールズ", r"カントリー娘"]),
    ("Hello! Project", "Kobushi Factory", [r"kobushi factory", r"こぶしファクトリー"]),
    ("Hello! Project", "Melon Kinenbi", [r"melon kinenbi", r"メロン記念日"]),
    ("Hello! Project", "Tanpopo", [r"\btanpopo\b", r"タンポポ"]),
    ("Hello! Project", "v-u-den", [r"v-u-den", r"biyuden", r"美勇伝"]),
    ("Hello! Project", "W", [r"w \(double you\)", r"double you", r"ダブルユー"]),
    ("Hello! Project", "GAM", [r"\bgam\b", r"ギャム"]),
    ("Hello! Project", "Taiyo to Ciscomoon", [r"taiyo to ciscomoon", r"太陽とシスコムーン", r"t&c bomber"]),
    ("Hello! Project", "LoVendoR", [r"lovendor", r"ラベンダー"]),
    ("Hello! Project", "PINK CRES.", [r"pink cres", r"ピンククレス"]),

    # Hello! Project — Soloists & OGs
    ("Hello! Project", "Sayumi Michishige", [r"sayumi michishige", r"michishige sayumi", r"道重さゆみ", r"sayuming"]),
    ("Hello! Project", "Aya Matsuura", [r"aya matsuura", r"matsuura aya", r"松浦亜弥"]),
    ("Hello! Project", "Maki Goto", [r"maki goto", r"goto maki", r"後藤真希"]),
    ("Hello! Project", "Natsumi Abe", [r"natsumi abe", r"abe natsumi", r"安倍なつみ"]),
    ("Hello! Project", "Erina Mano", [r"erina mano", r"mano erina", r"真野恵里菜"]),
    ("Hello! Project", "Airi Suzuki", [r"airi suzuki", r"suzuki airi", r"鈴木愛理"]),
    ("Hello! Project", "Miki Fujimoto", [r"miki fujimoto", r"fujimoto miki", r"藤本美貴"]),
    ("Hello! Project", "Karin Miyamoto", [r"karin miyamoto", r"miyamoto karin", r"宮本佳林"]),

    # Up-Front Alumni
    ("Up-Front Alumni", "You Kikkawa", [r"you kikkawa", r"kikkawa you", r"吉川友"]),
    ("Up-Front Alumni", "Up Up Girls (Kari)", [r"up up girls \(kari\)", r"アップアップガールズ\(仮\)"]),
    ("Up-Front Alumni", "Up Up Girls (2)", [r"up up girls \(2\)", r"up up girls 2", r"アップアップガールズ\(2\)"]),

    # Sakamichi Series
    ("Sakamichi Series", "Sakurazaka46", [r"sakurazaka46", r"sakurazaka", r"櫻坂46", r"keyakizaka46", r"keyakizaka", r"欅坂46"]),
    ("Sakamichi Series", "Nogizaka46", [r"nogizaka46", r"nogizaka", r"乃木坂46"]),
    ("Sakamichi Series", "Hinatazaka46", [r"hinatazaka46", r"hinatazaka", r"日向坂46"]),
    ("Sakamichi Series", "22/7", [r"\b22/7\b", r"ナナブンノニジュウニ"]),
    ("Sakamichi Series", "Boku ga Mitakatta Aozora", [r"boku ga mitakatta aozora", r"僕が見たかった青空"]),
    ("Sakamichi Series", "Mai Shiraishi", [r"mai shiraishi", r"白石麻衣"]),
    ("Sakamichi Series", "Nanase Nishino", [r"nanase nishino", r"西野七瀬"]),
    ("Sakamichi Series", "Erika Ikuta", [r"erika ikuta", r"生田絵梨花"]),
    ("Sakamichi Series", "Asuka Saito", [r"asuka saito", r"齋藤飛鳥"]),
    ("Sakamichi Series", "Yurina Hirate", [r"yurina hirate", r"平手友梨奈"]),

    # AKB48 Group
    ("AKB48 Group", "AKB48", [r"\bakb48\b"]),
    ("AKB48 Group", "SKE48", [r"\bske48\b"]),
    ("AKB48 Group", "NMB48", [r"\bnmb48\b"]),
    ("AKB48 Group", "HKT48", [r"\bhkt48\b"]),
    ("AKB48 Group", "NGT48", [r"\bngt48\b"]),
    ("AKB48 Group", "STU48", [r"\bstu48\b"]),
    ("AKB48 Group", "Not yet", [r"not yet", r"ノットイェット"]),
    ("AKB48 Group", "no3b", [r"\bno3b\b", r"ノースリーブス"]),
    ("AKB48 Group", "French Kiss", [r"french kiss", r"フレンチ・キス"]),
    ("AKB48 Group", "Watarirouka Hashiritai", [r"watarirouka hashiritai", r"渡り廊下走り隊"]),
    ("AKB48 Group", "Sayaka Yamamoto", [r"sayaka yamamoto", r"山本彩"]),
    ("AKB48 Group", "Atsuko Maeda", [r"atsuko maeda", r"前田敦子"]),
    ("AKB48 Group", "Yuko Oshima", [r"yuko oshima", r"大島優子"]),
    ("AKB48 Group", "Mayu Watanabe", [r"mayu watanabe", r"渡辺麻友"]),
    ("AKB48 Group", "Yuki Kashiwagi", [r"yuki kashiwagi", r"柏木由紀"]),
    ("AKB48 Group", "Rino Sashihara", [r"rino sashihara", r"指原莉乃"]),
    ("AKB48 Group", "Tomomi Itano", [r"tomomi itano", r"板野友美"]),

    # Stardust Planet
    ("Stardust Planet", "Momoiro Clover Z", [r"momoiro clover z", r"ももいろクローバーz", r"\bmomoclo\b"]),
    ("Stardust Planet", "Shiritsu Ebisu Chugaku", [r"shiritsu ebisu chugaku", r"私立恵比寿中学", r"\bebichu\b"]),
    ("Stardust Planet", "Chou Tokimeki Sendenbu", [r"cho(?:u)? tokimeki sendenbu", r"超ときめき♡宣伝部", r"とき宣"]),
    ("Stardust Planet", "TEAM SHACHI", [r"team shachi", r"チームしゃちほこ"]),
    ("Stardust Planet", "BATTEN GIRLS", [r"batten girls", r"ばってん少女隊"]),
    ("Stardust Planet", "ukka", [r"\bukka\b", r"桜エビ〜ず"]),

    # =LOVE / Sister Groups
    ("=LOVE / Sister Groups", "=LOVE", [r"\b=love\b", r"イコールラブ", r"イコラブ"]),
    ("=LOVE / Sister Groups", "≠ME", [r"\b≠me\b", r"ノイミー", r"not equal me"]),
    ("=LOVE / Sister Groups", "≒JOY", [r"\b≒joy\b", r"ニアジョイ", r"nearly equal joy"]),

    # KAWAII LAB.
    ("KAWAII LAB.", "FRUITS ZIPPER", [r"fruits zipper", r"フルーツジッパー", r"ふるっぱー"]),
    ("KAWAII LAB.", "CANDY TUNE", [r"candy tune", r"キャンディートゥーン", r"きゃんちゅー"]),
    ("KAWAII LAB.", "SWEET STEADY", [r"sweet steady", r"スウィートステディ", r"すいすて"]),
    ("KAWAII LAB.", "CUTIE STREET", [r"cutie street", r"キューティーストリート", r"きゅーすと"]),

    # Modern & Alternative
    ("Modern & Alternative", "NiziU", [r"\bniziu\b", r"ニジュー"]),
    ("Modern & Alternative", "ME:I", [r"\bme:i\b", r"ミーアイ"]),
    ("Modern & Alternative", "IS:SUE", [r"\bis:sue\b", r"イッシュ"]),
    ("Modern & Alternative", "BABYMETAL", [r"\bbabymetal\b"]),
    ("Modern & Alternative", "Sakura Gakuin", [r"sakura gakuin", r"さくら学院"])
]

def is_boyband_or_anime_false_positive(text):
    t_lower = text.lower()
    for pat in MALE_BOYBAND_PATTERNS:
        if re.search(pat, t_lower):
            return True
    for pat in NON_IDOL_MEDIA_PATTERNS:
        if re.search(pat, t_lower):
            return True
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

    print(f"Beginning Catalog Scrub: {total_initial:,} releases to process...")

    for pid, item in catalog.items():
        title = item.get("title", "")
        artist = item.get("artist", "")
        full_text = f"{title} {artist}".strip()
        full_text_lower = full_text.lower()

        # 1. STRICT KOHARU KUSUMI ENFORCEMENT ON TSUKISHIMA KIRARI
        if artist == "Tsukishima Kirari" or "tsukishima kirari" in full_text_lower or "月島きらり" in full_text:
            has_koharu = any(sig in full_text_lower for sig in [
                "kusumi koharu", "koharu kusumi", "久住小春",
                "starring 久住小春", "starring koharu kusumi"
            ])
            if not has_koharu:
                purged_count += 1
                continue
            item["artist"] = "Tsukishima Kirari"
            item["category"] = "Hello! Project"

        # 2. Boyband & Non-Idol False Positive Scrub
        if is_boyband_or_anime_false_positive(full_text):
            purged_count += 1
            continue

        # 3. Dynamic Reclassification & Standardization
        matched = False
        for cat, canonical_artist, patterns in RECLASSIFICATION_RULES:
            for pat in patterns:
                if re.search(pat, full_text_lower):
                    if item.get("artist") != canonical_artist or item.get("category") != cat:
                        item["artist"] = canonical_artist
                        item["category"] = cat
                        reclassified_count += 1
                    matched = True
                    break
            if matched:
                break

        # Standardize Sakurazaka / Keyakizaka
        if item.get("artist") in ["Keyakizaka46", "欅坂46"]:
            item["artist"] = "Sakurazaka46"
            item["category"] = "Sakamichi Series"
            reclassified_count += 1

        cleaned_catalog[pid] = item

    # Save to products.json
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    # Synchronize catalog-index.json for immediate live frontend consistency
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    print("==========================================================")
    print("Catalog Scrub Complete!")
    print(f"Initial Catalog Releases:  {total_initial:,}")
    print(f"Purged False Positives:    {purged_count:,}")
    print(f"Reclassified / Aligned:    {reclassified_count:,}")
    print(f"Final Cleaned Releases:    {len(cleaned_catalog):,}")
    print("Synchronized: products.json & catalog-index.json")
    print("==========================================================")

if __name__ == "__main__":
    clean_catalog()
