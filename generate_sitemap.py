import os
import json
import re
from datetime import datetime
from xml.sax.saxutils import escape

BASE_URL = "https://idoljapan.store"
CATALOG_FILES = ["catalog-index.json", "products.json"]
GROUPS_DIR = "groups"

STATIC_PAGES = [
    {"loc": "/", "priority": "1.0", "changefreq": "daily"},
    {"loc": "/about.html", "priority": "0.5", "changefreq": "monthly"},
    {"loc": "/affiliate-disclosure.html", "priority": "0.5", "changefreq": "monthly"},
    {"loc": "/privacy.html", "priority": "0.3", "changefreq": "monthly"},
    {"loc": "/terms.html", "priority": "0.3", "changefreq": "monthly"},
    {"loc": "/contact.html", "priority": "0.5", "changefreq": "monthly"}
]

FRANCHISE_CATEGORIES = [
    "Hello! Project",
    "Up-Front Alumni",
    "AKB48 Group",
    "Sakamichi Series",
    "Stardust Planet",
    "=LOVE / Sister Groups",
    "KAWAII LAB.",
    "Modern Idols",
    "Babymetal"
]

def load_products():
    for filename in CATALOG_FILES:
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and data:
                        return data
                    elif isinstance(data, list) and data:
                        return {item.get("id"): item for item in data if item.get("id")}
            except Exception as e:
                print(f"Warning: Could not read {filename}: {e}")
    return {}

def format_xml_date(date_str=None):
    if date_str:
        m = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', date_str)
        if m:
            y, month, day = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
            return f"{y}-{month}-{day}"
    return datetime.utcnow().strftime("%Y-%m-%d")

def generate_sitemap():
    products = load_products()
    today_iso = datetime.utcnow().strftime("%Y-%m-%d")
    
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # 1. Core static pages
    for page in STATIC_PAGES:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{escape(BASE_URL + page['loc'])}</loc>")
        xml_lines.append(f"    <lastmod>{today_iso}</lastmod>")
        xml_lines.append(f"    <changefreq>{page['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{page['priority']}</priority>")
        xml_lines.append("  </url>")

    # 2. Franchise collection links
    for cat in FRANCHISE_CATEGORIES:
        encoded_cat = cat.replace(" ", "+")
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{escape(f'{BASE_URL}/?cat={encoded_cat}')}</loc>")
        xml_lines.append(f"    <lastmod>{today_iso}</lastmod>")
        xml_lines.append("    <changefreq>daily</changefreq>")
        xml_lines.append("    <priority>0.9</priority>")
        xml_lines.append("  </url>")

    # 3. Pre-rendered Group Landing Pages
    if os.path.exists(GROUPS_DIR):
        for fname in sorted(os.listdir(GROUPS_DIR)):
            if fname.endswith(".html"):
                xml_lines.append("  <url>")
                xml_lines.append(f"    <loc>{escape(f'{BASE_URL}/groups/{fname}')}</loc>")
                xml_lines.append(f"    <lastmod>{today_iso}</lastmod>")
                xml_lines.append("    <changefreq>daily</changefreq>")
                xml_lines.append("    <priority>0.9</priority>")
                xml_lines.append("  </url>")

    # 4. Product canonical deep links
    for pid, item in products.items():
        if not pid:
            continue
        
        status = item.get("availability", "instock")
        rel_date = item.get("release_date", "")
        lastmod = format_xml_date(rel_date)
        
        if status == "preorder":
            priority = "0.8"
            changefreq = "weekly"
        elif status == "oop":
            priority = "0.4"
            changefreq = "monthly"
        else:
            priority = "0.7"
            changefreq = "weekly"

        canonical_url = f"{BASE_URL}/?id={pid}"
        
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{escape(canonical_url)}</loc>")
        xml_lines.append(f"    <lastmod>{lastmod}</lastmod>")
        xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")
    
    output_content = "\n".join(xml_lines)
    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Successfully generated sitemap.xml with {len(xml_lines) // 7} indexed URLs.")

if __name__ == "__main__":
    generate_sitemap()
