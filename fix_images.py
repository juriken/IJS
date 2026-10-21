import json
import os
import re

DATA_FILE = "products.json"

def repair_jacket_images():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    repaired_count = 0

    for pid, item in catalog.items():
        img = item.get("image", "")
        sku = item.get("id", pid).strip().upper()

        needs_fix = False

        if not img or not isinstance(img, str):
            needs_fix = True
        elif any(bad in img.lower() for bad in ["spacer.gif", "blank.gif", "no_image", "pixel"]):
            needs_fix = True
        elif img.startswith("//"):
            img = "https:" + img
            item["image"] = img
        elif img.startswith("/"):
            img = "https://www.cdjapan.co.jp" + img
            item["image"] = img

        if needs_fix:
            item["image"] = f"https://www.cdjapan.co.jp/pictures/l/{sku}.jpg"
            repaired_count += 1
        else:
            # Upgrade low-res thumbnail paths to large jackets
            item["image"] = item["image"].replace("/pictures/s/", "/pictures/l/").replace("/pictures/m/", "/pictures/l/")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)

    print(f"==========================================")
    print(f"Jacket Repair Complete: {repaired_count} image URLs normalized.")
    print(f"==========================================")

if __name__ == "__main__":
    repair_jacket_images()
