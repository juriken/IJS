"""
IdolJapan.store — Pre-rendered Group Landing Page Generator
Builds static SEO-optimized landing pages with Schema.org MusicGroup markup for every idol unit.
"""

import os
import json
import re
import urllib.parse
from xml.sax.saxutils import escape

DATA_FILE = "products.json"
GROUPS_DIR = "groups"
BASE_URL = "https://idoljapan.store"

def slugify(name):
    clean = name.lower()
    clean = clean.replace("≠", "not-equal-").replace("≒", "nearly-equal-").replace("=", "equal-")
    clean = re.sub(r'[^a-z0-9\-]+', '-', clean).strip('-')
    return clean

def generate_static_group_pages():
    if not os.path.exists(DATA_FILE):
        print(f"Error: {DATA_FILE} not found.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    os.makedirs(GROUPS_DIR, exist_ok=True)

    grouped_catalog = {}
    for pid, item in catalog.items():
        artist = item.get("artist", "Other")
        # Canonicalize Keyakizaka46 into Sakurazaka46
        if artist in ["Keyakizaka46", "欅坂46"]:
            artist = "Sakurazaka46"
            item["artist"] = "Sakurazaka46"

        if artist not in grouped_catalog:
            grouped_catalog[artist] = []
        grouped_catalog[artist].append(item)

    print(f"Building pre-rendered landing pages for {len(grouped_catalog)} idol groups...")

    for artist, items in grouped_catalog.items():
        slug = slugify(artist)
        file_path = os.path.join(GROUPS_DIR, f"{slug}.html")
        category = items[0].get("category", "Japanese Idol")

        items.sort(key=lambda x: str(x.get("release_date", "")), reverse=True)
        sample_image = items[0].get("image") or f"{BASE_URL}/favicon.ico"

        schema_data = {
            "@context": "https://schema.org",
            "@type": "MusicGroup",
            "name": artist,
            "genre": "J-Pop / Idol",
            "image": sample_image,
            "url": f"{BASE_URL}/groups/{slug}.html",
            "album": [
                {
                    "@type": "MusicAlbum",
                    "name": it.get("title", ""),
                    "image": it.get("image", ""),
                    "url": f"{BASE_URL}/?id={it.get('id')}",
                    "datePublished": it.get("release_date", "")
                } for it in items[:20]
            ]
        }

        cards_html = []
        for it in items:
            title = escape(it.get("title", "Untitled"))
            pid = escape(it.get("id", ""))
            price = escape(it.get("price", "Check CDJapan"))
            rel_date = escape(it.get("release_date", "Available Now"))
            image = escape(it.get("image", ""))
            aff_url = escape(it.get("affiliate_url", f"https://www.cdjapan.co.jp/product/{pid}?affi=A033398"))

            cards_html.append(f"""
            <div class="bg-white dark:bg-slate-900 border border-stone-200 dark:border-slate-800 rounded-2xl overflow-hidden shadow-xs hover:shadow-md transition flex flex-col justify-between">
              <div class="aspect-square bg-stone-100 dark:bg-slate-800 overflow-hidden relative">
                <img src="{image}" alt="{title}" loading="lazy" class="w-full h-full object-cover" />
                <span class="absolute bottom-2 left-2 bg-stone-900/80 backdrop-blur-md text-white text-[10px] font-bold px-2 py-0.5 rounded shadow">{pid}</span>
              </div>
              <div class="p-4 flex-1 flex flex-col justify-between space-y-3">
                <div>
                  <h3 class="text-xs font-bold text-stone-900 dark:text-white line-clamp-2 leading-snug">{title}</h3>
                  <p class="text-[11px] text-stone-500 dark:text-slate-400 mt-1 flex items-center gap-1">
                    <i class="fa-regular fa-calendar text-[10px]"></i> {rel_date}
                  </p>
                </div>
                <div class="pt-2 border-t border-stone-100 dark:border-slate-800 flex items-center justify-between">
                  <div>
                    <span class="text-xs font-black text-rose-600 dark:text-rose-400">{price}</span>
                    <span class="block text-[9px] text-stone-400 dark:text-slate-500">Tokyo Price</span>
                  </div>
                  <a href="{aff_url}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg text-xs transition shadow-xs flex items-center gap-1">
                    <span>Order</span> <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                  </a>
                </div>
              </div>
            </div>
            """)

        page_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(artist)} Official Discography & CDJapan Release Directory — IdolJapan.store</title>
  <meta name="description" content="Browse official singles, albums, and concert Blu-rays for {escape(artist)} ({escape(category)}). Fulfilled directly from Tokyo with chart registration.">
  <link rel="canonical" href="{BASE_URL}/groups/{slug}.html">
  <meta property="og:title" content="{escape(artist)} Discography — IdolJapan.store">
  <meta property="og:description" content="Official releases for {escape(artist)}. International shipping by authorized retailer CDJapan.">
  <meta property="og:image" content="{sample_image}">
  <meta name="theme-color" content="#e11d48">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.2/css/all.min.css">
  <script type="application/ld+json">
  {json.dumps(schema_data, ensure_ascii=False, indent=2)}
  </script>
</head>
<body class="bg-stone-50 dark:bg-slate-950 text-stone-800 dark:text-stone-100 min-h-screen flex flex-col font-sans antialiased">
  <header class="sticky top-0 z-40 bg-rose-600 dark:bg-slate-900 text-white border-b border-rose-500/30 dark:border-slate-800 py-3.5 px-4 shadow-sm">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <a href="/" class="text-xl font-black tracking-tight flex items-center gap-2 text-white">
        <i class="fa-solid fa-compact-disc text-amber-200 text-2xl"></i>
        <span>IdolJapan<span class="text-rose-200">.store</span></span>
      </a>
      <div class="flex items-center gap-3">
        <a href="/?cat={urllib.parse.quote_plus(category)}&artist={urllib.parse.quote_plus(artist)}" class="px-3 py-1.5 bg-rose-700 dark:bg-slate-800 hover:bg-rose-800 text-white font-bold text-xs rounded-full border border-rose-400/30 shadow-xs transition">
          Launch Interactive Filter →
        </a>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 py-8 flex-1 w-full space-y-6">
    <div class="bg-white dark:bg-slate-900 border border-stone-200 dark:border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xs flex flex-col md:flex-row items-center justify-between gap-6">
      <div class="space-y-2 text-center md:text-left">
        <span class="text-xs font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider">{escape(category)}</span>
        <h1 class="text-2xl sm:text-4xl font-black text-stone-900 dark:text-white">{escape(artist)} Discography</h1>
        <p class="text-xs sm:text-sm text-stone-500 dark:text-slate-400 max-w-2xl leading-relaxed">
          Complete verified release archive for {escape(artist)}. All purchases qualify for official Japanese music chart counting (Oricon &amp; Billboard Japan) and ship directly from CDJapan's Tokyo fulfillment warehouse.
        </p>
      </div>
      <div class="bg-stone-50 dark:bg-slate-800 px-5 py-3 rounded-2xl border border-stone-200 dark:border-slate-700 text-center shrink-0">
        <span class="text-2xl font-black text-rose-600 dark:text-rose-400 block">{len(items)}</span>
        <span class="text-[11px] font-bold text-stone-500 dark:text-slate-400">Verified Releases</span>
      </div>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {"".join(cards_html)}
    </div>
  </main>

  <footer class="bg-white dark:bg-slate-900 border-t border-stone-200 dark:border-slate-800 py-8 text-center text-xs text-stone-500 dark:text-slate-400">
    <div class="max-w-5xl mx-auto px-4 space-y-2">
      <p>© 2019 – 2026 IdolJapan.store. Official CDJapan Affiliate Partner (ID: A033398).</p>
      <div class="flex justify-center gap-4 text-[11px] font-semibold pt-1">
        <a href="/" class="hover:underline">Home Catalog</a>
        <a href="/about.html" class="hover:underline">About &amp; Verification</a>
        <a href="/affiliate-disclosure.html" class="hover:underline">Disclosure</a>
        <a href="/sitemap.xml" class="hover:underline">Sitemap</a>
      </div>
    </div>
  </footer>
</body>
</html>"""

        with open(file_path, "w", encoding="utf-8") as out_f:
            out_f.write(page_content)

    print(f"Generated {len(grouped_catalog)} static group landing pages in /{GROUPS_DIR}/.")

if __name__ == "__main__":
    generate_static_group_pages()
