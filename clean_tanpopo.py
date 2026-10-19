import json
import os

DATA_FILE = "products.json"

# Authentic Tanpopo H!P members and official indicators
VALID_TANPOPO_KEYWORDS = [
    "iida kaori", "kaori iida", "飯田圭織",
    "ishiguro aya", "aya ishiguro", "石黒彩",
    "yaguchi mari", "mari yaguchi", "矢口真里",
    "kago ai", "ai kago", "加護亜依",
    "ishikawa rika", "rika ishikawa", "石川梨華",
    "konno asami", "asami konno", "紺野あさ美",
    "niigaki risa", "risa niigaki", "新垣里沙",
    "hello! project", "morning musume", "up-front",
    "last kiss", "motto", "tanpopo 1", "all of tanpopo",
    "otome pasta", "koi wo shichaimashita", "seinaru kane",
    "tsunku", "つんく"
]

VALID_CATALOG_PREFIXES = ["EPCE", "EPBE", "EPTE", "PKCP", "PKBP", "UFBW", "UFXW"]

def is_authentic_tanpopo(item):
    if item.get("artist") != "Tanpopo":
        return True  # Do not touch other artists

    pid = str(item.get("id", "")).upper()
    title = str(item.get("title", "")).lower()

    # Match official Up-Front Works catalog ID prefixes
    if any(pid.startswith(pfx) for pfx in VALID_CATALOG_PREFIXES):
        return True

    # Check for known H!P members or verified singles/albums
    combined_text = f"{title} {item.get('artist', '')}".lower()
    return any(kw in combined_text for kw in VALID_TANPOPO_KEYWORDS)

def main():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    before_count = len(catalog)
    cleaned_catalog = {
        pid: item for pid, item in catalog.items()
        if is_authentic_tanpopo(item)
    }
    after_count = len(cleaned_catalog)
    removed_count = before_count - after_count

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned_catalog, f, indent=2, ensure_ascii=False)

    print(f"Tanpopo Cleanup Complete!")
    print(f"Removed: {removed_count} false-positive Tanpopo items.")
    print(f"Remaining active items: {after_count}")

if __name__ == "__main__":
    main()
