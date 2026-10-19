python -c '
import json
with open("products.json", "r", encoding="utf-8") as f:
    d = json.load(f)
removed = []
for k in list(d.keys()):
    if d[k].get("artist") == "Tanpopo":
        pid = str(d[k].get("id", "")).upper()
        if not (pid.startswith("EP") or pid.startswith("PK") or pid.startswith("UF")):
            removed.append(k)
            del d[k]
with open("products.json", "w", encoding="utf-8") as f:
    json.dump(d, f, indent=2, ensure_ascii=False)
print(f"Purged {len(removed)} false-positive Tanpopo items:", removed)
'
