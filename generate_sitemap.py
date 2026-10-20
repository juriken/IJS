import json
import os
import urllib.parse
from datetime import datetime

DATA_FILE = "products.json"
SITEMAP_FILE = "sitemap.xml"
BASE_URL = "https://idoljapan.store"

STATIC_PAGES = [
    ("", "daily", "1.0"),
    ("about.html", "monthly", "0.8"),
    ("contact.html", "monthly", "0.8"),
    ("affiliate-disclosure.html", "monthly", "0.7"),
    ("privacy.html", "yearly", "0.5"),
    ("terms.html", "yearly", "0.5"),
]

FRANCHISE_HUBS = [
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


def xml_escape(val):
    if not val:
        return ""
    return (
        str(val)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]

    # 1. Core Static Pages
    for path, changefreq, priority in STATIC_PAGES:
        loc = f"{BASE_URL}/{path}" if path else f"{BASE_URL}/"
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{xml_escape(loc)}</loc>")
        xml_lines.append(f"    <lastmod>{today}</lastmod>")
        xml_lines.append(f"    <changefreq>{changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{priority}</priority>")
        xml_lines.append("  </url>")

    # 2. Franchise Hubs
    for franchise in FRANCHISE_HUBS:
        encoded_cat = urllib.parse.quote_plus(franchise)
        loc = f"{BASE_URL}/?cat={encoded_cat}"
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{xml_escape(loc)}</loc>")
        xml_lines.append(f"    <lastmod>{today}</lastmod>")
        xml_lines.append("    <changefreq>daily</changefreq>")
        xml_lines.append("    <priority>0.8</priority>")
        xml_lines.append("  </url>")

    # 3. Individual Product Deep Links
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                catalog = json.load(f)

            for pid, item in catalog.items():
                encoded_pid = urllib.parse.quote_plus(str(pid))
                loc = f"{BASE_URL}/?id={encoded_pid}"
                item_date = item.get("updated_at") or today

                xml_lines.append("  <url>")
                xml_lines.append(f"    <loc>{xml_escape(loc)}</loc>")
                xml_lines.append(f"    <lastmod>{item_date}</lastmod>")
                xml_lines.append("    <changefreq>weekly</changefreq>")
                xml_lines.append("    <priority>0.6</priority>")
                xml_lines.append("  </url>")
        except Exception as e:
            print(f"Warning: Could not parse {DATA_FILE} for deep links: {e}")

    xml_lines.append("</urlset>")

    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(xml_lines) + "\n")

    print(f"Sitemap successfully generated at {SITEMAP_FILE} with {len(xml_lines) - 2} entries.")


if __name__ == "__main__":
    main()
