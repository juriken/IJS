import json
import os

DATA_FILE = "products.json"

# Authentic Tanpopo singles, albums, members, and catalog numbers
AUTHENTIC_TANPOPO_SIGNATURES = [
    "last kiss", "ラストキッス",
    "motto", "もっと",
    "seinaru kane", "聖なる鐘",
    "otome pasta", "乙女 パスタ", "乙女パスタ",
    "koi wo shichaimashita", "恋をしちゃいました",
    "ouji-sama", "王子様と雪の夜", "oujisama",
    "kousaten", "交差点",
    "tanpopo 1", "all of tanpopo", "single v clips",
    "epce-5019", "epce-5066", "epce-5093", "epce-5129", "epce-5176",
    "epde-1014", "epde-1024", "epde-1037", "epde-1058", "epbe-5118"
]

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    total_before = len(catalog)
    cleaned_catalog = {}
    removed_tanpopo = 0
    reassigned_mm = 0
    kept_tanpopo = 0

    for pid, item in catalog.items():
        if item.get("artist") == "Tanpopo":
            title_lower = str(item.get("title", "")).lower()

            # Must contain the word tanpopo in title/id to be considered
            has_tanpopo_name = "tanpopo" in title_lower or "タンポポ" in title_lower or "たんぽぽ" in title_lower

            # Must match a known Tanpopo release signature
            is_real_tanpopo = has_tanpopo_name and any(sig in title_lower or sig in pid.lower() for sig in AUTHENTIC_TANPOPO_SIGNATURES)

            if is_real_tanpopo:
                cleaned_catalog[pid] = item
                kept_tanpopo += 1
            elif "morning musume" in title_lower or "モーニング娘" in title_lower:
                # Reassign Morning Musume releases to their proper artist tag
                item["artist"] = "Morning Musume"
                item["category"] = "Hello! Project"
                cleaned_catalog[pid] = item
                reassigned_mm += 1
            else:
                # Delete generic Hello Project concerts or unrelated items
                removed_tanpopo += 1
        else:
            cleaned_catalog[pid] = item

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    print(f"Catalog Cleaned Successfully!")
    print(f"* Total items before: {total_before}")
    print(f"* Deleted non-Tanpopo items: {removed_tanpopo}")
    print(f"* Reassigned to Morning Musume: {reassigned_mm}")
    print(f"* Verified Tanpopo releases kept: {kept_tanpopo}")
    print(f"* Total items now: {len(cleaned_catalog)}")

if __name__ == "__main__":
    main()
