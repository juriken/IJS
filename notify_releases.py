import os
import json
import urllib.request
from datetime import datetime

WEBHOOK_URL = os.environ.get("DISCORD_RELEASE_WEBHOOK", "").strip()
PRODUCTS_FILE = "products.json"

def send_discord_notification():
    if not WEBHOOK_URL:
        print("ℹ️ Notice: DISCORD_RELEASE_WEBHOOK not set in environment. Skipping broadcast.")
        return

    if not os.path.exists(PRODUCTS_FILE):
        print("❌ Error: products.json not found.")
        return

    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception as e:
        print(f"❌ Error reading products.json: {e}")
        return

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Filter items updated or added today
    todays_items = [
        it for it in catalog.values() 
        if it.get("updated_at") == today_str or it.get("availability") == "preorder"
    ]

    if not todays_items:
        print("ℹ️ No new releases to broadcast today.")
        return

    # Broadcast up to 5 priority items to avoid webhook rate limits
    sample_broadcast = todays_items[:5]
    print(f"Broadcasting {len(sample_broadcast)} new release alerts to Discord webhook...")

    for it in sample_broadcast:
        title = it.get("title", "Untitled Release")
        artist = it.get("artist", "Japanese Idol")
        price = it.get("price", "Check CDJapan")
        sku = it.get("id", "")
        img = it.get("image", "")
        rel_date = it.get("release_date", "Available Now")
        link = f"https://idoljapan.store/?id={sku}"
        cdjapan_buy = it.get("affiliate_url", link)

        embed = {
            "title": f"💿 New Release: {title}",
            "url": link,
            "color": 14753096, # Sakura Rose
            "description": f"**Artist:** {artist}\n**Price:** {price}\n**Street Date:** {rel_date}\n**Catalog SKU:** `{sku}`",
            "image": {"url": img} if img else {},
            "fields": [
                {
                    "name": "Order Direct from Tokyo",
                    "value": f"[View on CDJapan]({cdjapan_buy}) • [Browse Discography]({link})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "IdolJapan.store — Official CDJapan Affiliate Directory",
                "icon_url": "https://idoljapan.store/favicon.ico"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

        payload = {
            "username": "IdolJapan Bot",
            "avatar_url": "https://www.cdjapan.co.jp/pictures/l/EPCE-7860.jpg",
            "embeds": [embed]
        }

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "IdolJapan-Notifier/1.0"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"✅ Alert sent for: {title} ({sku})")
        except Exception as err:
            print(f"⚠️ Webhook dispatch notice on {sku}: {err}")

    print("Release notification broadcast step complete.")

if __name__ == "__main__":
    send_discord_notification()
