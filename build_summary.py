import json
import os
import sys

DATA_FILE = "products.json"
INDEX_FILE = "catalog-index.json"

def generate_index():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: Cannot find {DATA_FILE}")
        sys.exit(1)

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {DATA_FILE}: {e}")
        sys.exit(1)

    print(f"Building compact index from {len(catalog)} products...")

    summary_index = {}
    for pid, it in catalog.items():
        if not isinstance(it, dict):
            continue

        clean_pid = str(it.get("id", pid)).strip()
        summary_index[clean_pid] = {
            "id": clean_pid,
            "title": str(it.get("title", "")).strip(),
            "artist": str(it.get("artist", "")).strip(),
            "category": str(it.get("category", "")).strip(),
            "price_num": int(it.get("price_num", 0)),
            "price": str(it.get("price", "Check CDJapan")).strip(),
            "release_date": str(it.get("release_date", "Available Now")).strip(),
            "availability": str(it.get("availability", "instock")).strip(),
            "image": str(it.get("image", "")).strip(),
            "sample_audio": it.get("sample_audio")
        }

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(summary_index, f, ensure_ascii=False, separators=(',', ':'))

    print(f"✅ Generated {INDEX_FILE} successfully with {len(summary_index)} records.")

if __name__ == "__main__":
    generate_index()
