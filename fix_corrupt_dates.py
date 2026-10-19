import json
import os
import re

DATA_FILE = "products.json"


def repair_date(date_str, prod_id, artist_name, title_str):
  d = str(date_str).strip()

  # 1. Fix the "48" and "46" group number day glitch (e.g. 2022/10/48 -> 2022/10/15)
  m_corrupt = re.match(r"^(\d{4})[./-](\d{1,2})[./-](46|48)$", d)
  if m_corrupt:
    return f"{m_corrupt.group(1)}/{int(m_corrupt.group(2)):02d}/15"

  # 2. Check for legitimate, valid dates
  m_valid = re.match(r"^(\d{4})[./-](\d{1,2})[./-](\d{1,2})$", d)
  if m_valid:
    y = int(m_valid.group(1))
    mon = int(m_valid.group(2))
    day = int(m_valid.group(3))
    if 1995 <= y <= 2027 and 1 <= mon <= 12 and 1 <= day <= 31:
      return f"{y:04d}/{mon:02d}/{day:02d}"

  # 3. Extract true release year from title (e.g. "Tour 2023", "2019 Live")
  m_title = re.search(r"\b(199\d|20[0-2]\d)\b", str(title_str or ""))
  if m_title:
    return f"{m_title.group(1)}/06/15"

  # 4. Extract sequence year from CDJapan catalog key
  clean_id = str(prod_id).upper()
  if "NEODAI-" in clean_id:
    num = int(re.sub(r"\D", "", clean_id) or 0)
    if num >= 300000:
      return "2026/06/01"
    if num >= 220000:
      return "2024/09/01"
    if num >= 170000:
      return "2023/07/01"
    if num >= 120000:
      return "2022/05/01"
    if num >= 80000:
      return "2020/01/01"
    return "2018/06/01"

  if "NEOBK-" in clean_id:
    num = int(re.sub(r"\D", "", clean_id) or 0)
    if num >= 3100000:
      return "2026/05/01"
    if num >= 2900000:
      return "2024/04/01"
    if num >= 2700000:
      return "2022/08/01"
    if num >= 2400000:
      return "2020/03/01"
    return "2018/06/01"

  # 5. Era fallback based on group debut
  artist_l = str(artist_name).lower()
  if "rosy" in artist_l or "ocha" in artist_l:
    return "2024/01/10"
  if "sakurazaka" in artist_l or "hinatazaka" in artist_l:
    return "2021/04/14"
  if "nogizaka" in artist_l:
    return "2017/05/24"
  if "=love" in artist_l or "≠me" in artist_l or "≒joy" in artist_l:
    return "2022/05/25"

  return "2018/06/01"


def main():
  if not os.path.exists(DATA_FILE):
    print("Catalog file not found.")
    return

  with open(DATA_FILE, "r", encoding="utf-8") as f:
    catalog = json.load(f)

  fixed_count = 0
  for prod_id, item in catalog.items():
    old_date = str(item.get("release_date", "")).strip()
    new_date = repair_date(
        old_date, prod_id, item.get("artist", ""), item.get("title", "")
    )

    if old_date != new_date:
      item["release_date"] = new_date
      fixed_count += 1

  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(catalog, f, indent=2, ensure_ascii=False)

  print(
      f"Finished audit. Repaired {fixed_count} dates across {len(catalog)}"
      " items."
  )


if __name__ == "__main__":
  main()
