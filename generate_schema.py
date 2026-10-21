import os
import json
import re

DATA_FILE = "products.json"
SCHEMA_OUTPUT_FILE = "schema-catalog.json"
BASE_URL = "https://idoljapan.store"

def generate_schema():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    print(f"Generating Schema.org JSON-LD microdata for {len(catalog)} releases...")

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": []
    }

    for pid, item in catalog.items():
        title = item.get("title", "")
        artist = item.get("artist", "")
        price_num = item.get("price_num", 0)
        image = item.get("image", "")
        availability = item.get("availability", "instock")

        # Map to Schema.org ItemAvailability standard
        schema_avail = "https://schema.org/InStock"
        if availability == "preorder":
            schema_avail = "https://schema.org/PreOrder"
        elif availability == "oop":
            schema_avail = "https://schema.org/Discontinued"

        product_schema = {
            "@type": "Product",
            "@id": f"{BASE_URL}/?id={pid}#product",
            "name": f"{title} - {artist}",
            "image": image,
            "description": f"Official CDJapan Japanese release: {title} by {artist} ({pid}).",
            "sku": pid,
            "brand": {
                "@type": "Brand",
                "name": artist
            },
            "offers": {
                "@type": "Offer",
                "url": f"{BASE_URL}/?id={pid}",
                "priceCurrency": "JPY",
                "price": str(price_num) if price_num > 0 else "0",
                "availability": schema_avail,
                "itemCondition": "https://schema.org/NewCondition",
                "seller": {
                    "@type": "Organization",
                    "name": "CDJapan (Tokyo)"
                }
            }
        }

        schema_graph["@graph"].append(product_schema)

    with open(SCHEMA_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(schema_graph, f, ensure_ascii=False, separators=(',', ':'))

    print(f"✅ Generated {SCHEMA_OUTPUT_FILE} with {len(schema_graph['@graph'])} structured Product schemas.")

if __name__ == "__main__":
    generate_schema()
