"""
import_notion.py — 將 Notion CSV 匯入 RentMate SQLite 資料庫
執行方式：py -3.11 import_notion.py
"""

import csv
import re
import sys
import os

# Force UTF-8 output on Windows to handle emoji in Notion titles
sys.stdout.reconfigure(encoding="utf-8")

# 確保可以 import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db import init_db, insert_listing

CSV_PATH = r"data\為什麼沒錢D 2a611108f273800086ffe988ba63119a_all.csv"


def parse_rent(value: str) -> int | None:
    """把 '11,500' 或 '11500' 轉成整數"""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[,，\s元/月]", "", value.strip())
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_size(value: str) -> float | None:
    """把 '12' 或 '12.5坪' 轉成 float"""
    if not value or not value.strip():
        return None
    cleaned = re.sub(r"[坪\s]", "", value.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_equipment(多選: str) -> dict:
    """從多選欄位（如 '獨立套房, 透天厝, 有冷氣'）解析設備布林值"""
    text = 多選.lower()
    return {
        "has_ac":              "冷氣" in text,
        "has_washing_machine": "洗衣機" in text or "洗衣" in text,
        "has_fridge":          "冰箱" in text,
        "has_internet":        "網路" in text or "wifi" in text,
        "has_parking":         "停車" in text or "車位" in text,
        "pet_friendly":        "寵物" in text,
    }


def notion_row_to_listing(row: dict) -> dict:
    """把 Notion CSV 的一列轉換成 listing dict"""
    多選 = row.get("多選", "")
    equipment = parse_equipment(多選)

    # 建物類型：從多選中找
    building_keywords = ["獨立套房", "套房", "雅房", "整層", "透天厝", "公寓", "電梯大樓", "大樓"]
    building_type = None
    for kw in building_keywords:
        if kw in 多選:
            building_type = kw
            break

    notes_parts = []
    if row.get("備註", "").strip():
        notes_parts.append(f"備註：{row['備註'].strip()}")
    if row.get("部分敘述", "").strip():
        notes_parts.append(row["部分敘述"].strip()[:300])
    if row.get("分數", "").strip():
        notes_parts.append(f"評分：{row['分數'].strip()}")

    return {
        "title":               row.get("名稱", "").strip() or "未命名物件",
        "rent":                parse_rent(row.get("租金", "")),
        "size_ping":           parse_size(row.get("坪數", "")),
        "location":            row.get("地點", "").strip() or None,
        "district":            None,  # Notion 沒有行政區欄位，留空
        "floor":               row.get("樓層", "").strip() or None,
        "building_type":       building_type,
        "bedrooms":            None,
        "bathrooms":           None,
        **equipment,
        "gender_restriction":  None,
        "deposit":             None,
        "utilities":           None,
        "near_mrt":            None,
        "near_school":         None,
        "contact":             None,
        "notes":               "\n".join(notes_parts) if notes_parts else None,
        "raw_text":            row.get("部分敘述", "").strip(),
        "source_url":          row.get("網址", "").strip() or "",
        "confidence":          {"source": "notion_import"},
    }


def main():
    init_db()

    imported = 0
    skipped = 0

    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"讀取到 {len(rows)} 筆資料，開始匯入...")

    for i, row in enumerate(rows):
        title = row.get("名稱", "").strip()
        if not title:
            skipped += 1
            continue

        listing = notion_row_to_listing(row)
        listing_id = insert_listing(listing)
        imported += 1
        print(f"  [{i+1:>3}] OK ID={listing_id}: {listing['title'][:40]}")

    print(f"\n完成！匯入 {imported} 筆，略過 {skipped} 筆空白資料。")
    print("現在可以打開 http://localhost:8501 查看比較表格。")


if __name__ == "__main__":
    main()
