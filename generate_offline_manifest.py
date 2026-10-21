import os
import re
from datetime import datetime

SW_FILE = "sw.js"

def stamp_service_worker():
    if not os.path.exists(SW_FILE):
        print(f"❌ Error: {SW_FILE} does not exist.")
        return

    with open(SW_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # Generate distinct build version timestamp
    build_version = datetime.utcnow().strftime("v%Y%m%d%H%M%S")
    updated_content = re.sub(
        r"const CACHE_NAME = ['\"]idoljapan-cache-[^'\"]+['\"];",
        f"const CACHE_NAME = 'idoljapan-cache-{build_version}';",
        content
    )

    with open(SW_FILE, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print(f"✅ Service Worker stamped with fresh cache key: idoljapan-cache-{build_version}")

if __name__ == "__main__":
    stamp_service_worker()
