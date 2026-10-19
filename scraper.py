import os
import sys
import json
import logging
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

PRODUCTS_FILE = "products.json"
SITEMAP_FILE = "sitemap.xml"
BASE_URL = "https://idoljapan.store"

# Required keys for each product record
REQUIRED_FIELDS = {"id", "title", "url", "image", "price"}

def get_resilient_session(retries: int = 4, backoff_factor: float = 1.5) -> requests.Session:
    """Configures a requests session with retries and realistic headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    })
    
    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def load_existing_products(filepath: str) -> list[dict]:
    """Loads current products. Returns empty list if file is absent or invalid."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logging.warning(f"Could not parse existing {filepath}: {e}")
        return []

def validate_product(item: dict) -> bool:
    """Ensures product dictionary satisfies schema requirements."""
    if not isinstance(item, dict):
        return False
    return REQUIRED_FIELDS.issubset(item.keys()) and bool(item.get("id"))

def fetch_catalog_items(session: requests.Session) -> list[dict]:
    """
    Main catalog fetcher logic.
    Adjust endpoints, selectors, or affiliate parameters as needed for your target.
    """
    items = []
    
    # Example logic: replace or wrap your actual scraping loop here
    # try:
    #     response = session.get("TARGET_URL", timeout=15)
    #     response.raise_for_status()
    #     ... parsing logic ...
    # except requests.RequestException as e:
    #     logging.error(f"Network error during fetch: {e}")
    #     raise
    
    return items

def atomic_save_json(filepath: str, data: list[dict], min_expected_count: int = 1):
    """
    Validates items and writes atomically via a temporary file.
    Prevents corrupting or emptying existing products on scraping failures.
    """
    valid_items = [item for item in data if validate_product(item)]
    
    if len(valid_items) < min_expected_count:
        raise ValueError(
            f"Validation failed: parsed {len(valid_items)} valid items. "
            f"Threshold is {min_expected_count}. Aborting file overwrite."
        )

    temp_filepath = f"{filepath}.tmp"
    with open(temp_filepath, "w", encoding="utf-8") as f:
        json.dump(valid_items, f, ensure_ascii=False, indent=2)

    # Atomic rename (POSIX atomic; on Windows replaces atomically in modern Python)
    os.replace(temp_filepath, filepath)
    logging.info(f"Successfully saved {len(valid_items)} products to {filepath}")

def generate_sitemap(sitemap_path: str, products: list[dict]):
    """Generates a valid sitemap.xml including core pages and indexed products."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # Static pages
    static_pages = [
        {"loc": f"{BASE_URL}/", "priority": "1.0", "changefreq": "daily"},
        {"loc": f"{BASE_URL}/about.html", "priority": "0.3", "changefreq": "monthly"},
        {"loc": f"{BASE_URL}/privacy.html", "priority": "0.2", "changefreq": "monthly"},
        {"loc": f"{BASE_URL}/terms.html", "priority": "0.2", "changefreq": "monthly"},
        {"loc": f"{BASE_URL}/affiliate-disclosure.html", "priority": "0.2", "changefreq": "monthly"},
    ]

    for page in static_pages:
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = page["loc"]
        ET.SubElement(url_elem, "lastmod").text = now_iso
        ET.SubElement(url_elem, "changefreq").text = page["changefreq"]
        ET.SubElement(url_elem, "priority").text = page["priority"]

    # Product entries (deep-link anchors or individual item views)
    for prod in products:
        prod_id = prod.get("id")
        if not prod_id:
            continue
        url_elem = ET.SubElement(urlset, "url")
        ET.SubElement(url_elem, "loc").text = f"{BASE_URL}/#product-{prod_id}"
        ET.SubElement(url_elem, "lastmod").text = prod.get("updated_at", now_iso)
        ET.SubElement(url_elem, "changefreq").text = "weekly"
        ET.SubElement(url_elem, "priority").text = "0.7"

    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ", level=0)
    
    temp_sitemap = f"{sitemap_path}.tmp"
    with open(temp_sitemap, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="utf-8", xml_declaration=False)
        
    os.replace(temp_sitemap, sitemap_path)
    logging.info(f"Updated {sitemap_path} with {len(static_pages) + len(products)} URLs.")

def main():
    existing_products = load_existing_products(PRODUCTS_FILE)
    logging.info(f"Loaded {len(existing_products)} existing records.")

    session = get_resilient_session()

    try:
        new_items = fetch_catalog_items(session)
        
        # Merge logic: if your scraper returns all active items, use new_items directly;
        # otherwise, deduplicate against existing_products by "id".
        products_to_store = new_items if new_items else existing_products

        # Set minimum threshold: require at least 50% of previous catalog size if not empty
        min_threshold = max(1, int(len(existing_products) * 0.5)) if existing_products else 1
        
        atomic_save_json(PRODUCTS_FILE, products_to_store, min_expected_count=min_threshold)
        generate_sitemap(SITEMAP_FILE, products_to_store)

    except Exception as e:
        logging.error(f"Scraper execution failed: {e}")
        # Exit with non-zero code to fail GitHub Actions step and avoid bad commits
        sys.exit(1)

if __name__ == "__main__":
    main()
