import os
import json
import re
from datetime import datetime
from xml.sax.saxutils import escape

BASE_URL = "https://idoljapan.store"
CATALOG_INDEX_FILE = "catalog-index.json"
PRODUCTS_FILE = "products.json"
FEED_OUTPUT_FILE = "feed.xml"
MAX_FEED_ITEMS = 50

def load_catalog_data():
    if os.path.exists(CATALOG_INDEX_FILE):
        try:
            with open(CATALOG_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {}

def parse_date_for_sorting(item):
    d_str = str(item.get("release_date", "")).strip()
    if not d_str or d_str.lower() == "available now":
        return 0
    m = re.search(r'\b(19\d\d|20\d\d)[./-](\d{1,2})[./-](\d{1,2})\b', d_str)
    if m:
        return (int(m.group(1)) * 10000) + (int(m.group(2)) * 100) + int(m.group(3))
    return 0

def format_rfc822_date(date_num):
    if date_num > 0:
        try:
            y = date_num // 10000
            m = (date_num % 10000) // 100
            d = date_num % 100
            dt = datetime(y, m, d, 9, 0, 0)
            return dt.strftime("%a, %d %b %Y %H:%M:%S +0900")
        except Exception:
            pass
    return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

def generate_rss_feed():
    catalog = load_catalog_data()
    if not catalog:
        print("Notice: No catalog items found to generate RSS feed.")
        return

    items = list(catalog.values())
    items.sort(key=parse_date_for_sorting, reverse=True)
    feed_items = items[:MAX_FEED_ITEMS]

    now_rfc822 = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    rss_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
        '  <channel>',
        f'    <title>IdolJapan.store — Latest Japanese Idol Discography &amp; Releases</title>',
        f'    <link>{BASE_URL}/</link>',
        f'    <description>Official discography, pre-orders, and release updates for Japanese female idols fulfilled by CDJapan (Tokyo).</description>',
        f'    <language>en</language>',
        f'    <lastBuildDate>{now_rfc822}</lastBuildDate>',
        f'    <atom:link href="{BASE_URL}/{FEED_OUTPUT_FILE}" rel="self" type="application/rss+xml" />',
        f'    <generator>IdolJapan RSS Generator</generator>'
    ]

    for it in feed_items:
        sku = str(it.get("id", "")).strip()
        if not sku:
            continue

        title = str(it.get("title", "Untitled")).strip()
        artist = str(it.get("artist", "Idol Artist")).strip()
        category = str(it.get("category", "Japanese Idol")).strip()
        price = str(it.get("price", "Check CDJapan")).strip()
        rel_date = str(it.get("release_date", "Available Now")).strip()
        image_url = str(it.get("image", "")).strip()
        link_url = f"{BASE_URL}/?id={sku}"
        
        date_val = parse_date_for_sorting(it)
        pub_date = format_rfc822_date(date_val)

        description = (
            f"&lt;p&gt;&lt;strong&gt;Artist:&lt;/strong&gt; {escape(artist)}&lt;br/&gt;"
            f"&lt;strong&gt;Franchise:&lt;/strong&gt; {escape(category)}&lt;br/&gt;"
            f"&lt;strong&gt;Catalog ID:&lt;/strong&gt; {escape(sku)}&lt;br/&gt;"
            f"&lt;strong&gt;Price:&lt;/strong&gt; {escape(price)}&lt;br/&gt;"
            f"&lt;strong&gt;Street Date:&lt;/strong&gt; {escape(rel_date)}&lt;/p&gt;"
        )
        if image_url:
            description = f'&lt;p&gt;&lt;img src="{escape(image_url)}" alt="{escape(title)}" width="240" /&gt;&lt;/p&gt;' + description

        rss_lines.append('    <item>')
        rss_lines.append(f'      <title>{escape(f"[{artist}] {title}")}</title>')
        rss_lines.append(f'      <link>{escape(link_url)}</link>')
        rss_lines.append(f'      <guid isPermaLink="true">{escape(link_url)}</guid>')
        rss_lines.append(f'      <pubDate>{pub_date}</pubDate>')
        rss_lines.append(f'      <category>{escape(category)}</category>')
        rss_lines.append(f'      <description>{description}</description>')
        rss_lines.append('    </item>')

    rss_lines.append('  </channel>')
    rss_lines.append('</rss>')

    with open(FEED_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(rss_lines))

    print(f"Generated {FEED_OUTPUT_FILE} with {len(feed_items)} syndication items.")

if __name__ == "__main__":
    generate_rss_feed()
