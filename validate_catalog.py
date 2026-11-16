import os
import sys
import json
import re

REQUIRED_FIELDS = ["id", "title", "artist", "category", "price", "release_date"]
MIN_CATALOG_ITEMS = 3000
EXPECTED_AFFILIATE_ID = "A033398"

def validate_json_file(file_path, is_summary=False):
    if not os.path.exists(file_path):
        print(f"❌ Error: Required file '{file_path}' does not exist.")
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Failed to parse JSON in '{file_path}': {e}")
        return False

    if not isinstance(data, dict):
        print(f"❌ Error: Root element in '{file_path}' must be a JSON object.")
        return False

    total_items = len(data)
    print(f"ℹ️ Checking '{file_path}': {total_items} items found.")

    if total_items < MIN_CATALOG_ITEMS:
        print(f"❌ Error: Catalog item count ({total_items}) is below minimum threshold ({MIN_CATALOG_ITEMS}). Aborting to prevent empty deploy.")
        return None

    for pid, item in data.items():
        if not isinstance(item, dict):
            print(f"❌ Error: Item '{pid}' in '{file_path}' is not a valid object.")
            return None

        # Verify essential fields are present and non-empty
        for field in REQUIRED_FIELDS:
            if field not in item or item[field] is None or not str(item[field]).strip():
                print(f"❌ Error: Item '{pid}' missing or empty required field '{field}'.")
                return None

        # Validate SKU format (no spaces or control characters)
        if re.search(r"\s", str(item["id"])):
            print(f"❌ Error: SKU '{item['id']}' contains illegal whitespace characters.")
            return None

        # Validate affiliate links on full payload
        if not is_summary and "affiliate_url" in item:
            aff_url = item.get("affiliate_url", "")
            if EXPECTED_AFFILIATE_ID not in aff_url:
                print(f"❌ Error: Item '{pid}' missing affiliate parameter '{EXPECTED_AFFILIATE_ID}' in URL: {aff_url}")
                return None

    print(f"✅ '{file_path}' passed structural integrity checks across all {total_items:,} items.")
    return data

def main():
    print("==========================================")
    print("Starting Catalog CI Integrity Validation")
    print("==========================================")

    from path_helper import get_target_path

    full_data = validate_json_file(get_target_path("products.json"), is_summary=False)
    index_data = validate_json_file(get_target_path("catalog-index.json"), is_summary=True)

    if full_data is None or index_data is None:
        print("❌ Catalog validation failed. Exiting with non-zero code to block deploy.")
        sys.exit(1)

    if set(full_data.keys()) != set(index_data.keys()):
        print(f"❌ Error: Dual-file parity mismatch (products.json: {len(full_data):,}, catalog-index.json: {len(index_data):,}).")
        sys.exit(1)

    print("==========================================")
    print("🎉 All catalog data checks passed successfully!")
    print("==========================================")
    sys.exit(0)

if __name__ == "__main__":
    main()
