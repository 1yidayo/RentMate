import os
import re
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()


def _parse_json_response(raw: str) -> dict:
    """
    Robustly extract and parse JSON from an LLM response.
    Handles: plain JSON, ```json ... ```, ``` ... ```, extra whitespace/newlines.
    """
    raw = raw.strip()

    # Try extracting from markdown code block first
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Find the first { ... } block as fallback
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"無法從 AI 回應中解析 JSON。原始回應：\n{raw[:300]}")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.6-flash"

EXTRACT_PROMPT = """你是一個租屋資訊擷取助理。請從以下租屋貼文或網頁文字中，擷取房屋資訊並以 JSON 格式回傳。

【重要規則】
1. 只能擷取原文中**明確提到**的資訊，不可自行推測或補充。
2. 原文未提到的欄位，一律填入 null，不可填入猜測值。
3. 布林值欄位（設備類）：原文明確提到有才填 true，未提到填 false。
4. confidence 欄位記錄你對每個欄位的信心程度（high/medium/low/not_mentioned）。

【回傳 JSON 格式】
{
  "title": "物件標題或簡短描述（如無則從內容推斷）",
  "rent": 月租金數字（純數字，單位：元，無則 null）,
  "size_ping": 坪數（純數字，無則 null）,
  "location": "完整地址或地區描述",
  "district": "行政區（如：大安區、新店區）",
  "floor": "樓層描述（如：3樓/5樓、頂樓加蓋）",
  "building_type": "建物類型（如：公寓、大樓、電梯大樓、透天）",
  "bedrooms": 房間數（純數字，無則 null）,
  "bathrooms": 衛浴數（純數字，無則 null）,
  "has_ac": true/false（有冷氣）,
  "has_washing_machine": true/false（有洗衣機）,
  "has_fridge": true/false（有冰箱）,
  "has_internet": true/false（有網路）,
  "has_parking": true/false（有停車位）,
  "pet_friendly": true/false（可養寵物）,
  "gender_restriction": "性別限制（男/女/不限，無明確說明填 null）",
  "deposit": "押金描述（如：兩個月）",
  "utilities": "水電費說明",
  "near_mrt": "附近捷運站（原文有提到才填）",
  "near_school": "附近學校（原文有提到才填）",
  "contact": "聯絡方式",
  "notes": "其他重要備註",
  "confidence": {
    "rent": "high/medium/low/not_mentioned",
    "size_ping": "high/medium/low/not_mentioned",
    "location": "high/medium/low/not_mentioned",
    "bedrooms": "high/medium/low/not_mentioned",
    "deposit": "high/medium/low/not_mentioned"
  }
}

【待分析的租屋文字】
{text}

請直接回傳 JSON，不要有任何說明文字或 markdown 格式。"""


COMPARE_PROMPT = """你是一個租屋比較分析助理。請根據以下房源資料，回答使用者的問題。

【房源資料】
{listings_json}

【使用者問題】
{question}

請用繁體中文回答，條列說明，並在分析中清楚指出是哪一筆物件（用標題或 ID 區分）。
如果問題涉及比較，請給出明確推薦並說明理由。"""


def extract_listing(text: str) -> dict:
    """
    Call Gemini to extract structured listing info from raw text.
    Returns parsed dict or raises exception.
    """
    prompt = EXTRACT_PROMPT.replace("{text}", text[:5000])

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    raw = response.text
    try:
        return _parse_json_response(raw)
    except Exception as e:
        # Re-raise with the actual raw response so we can debug
        raise ValueError(
            f"JSON 解析失敗。\n\n"
            f"【Gemini 原始回傳（前500字）】\n{raw[:500]}\n\n"
            f"【錯誤訊息】{e}"
        ) from e



def answer_question(listings: list[dict], question: str) -> str:
    """
    Answer rental questions.
    Simple rent comparisons are handled locally.
    Other questions continue to use Gemini.
    """

    q = question.strip().replace(" ", "")

    # 1. Find the cheapest listing without calling Gemini
    if any(word in q for word in ["最便宜", "最低租金", "租金最低", "月租最低"]):

        valid_listings = []

        for listing in listings:
            try:
                rent = float(listing.get("rent"))
                if rent > 0:
                    valid_listings.append((listing, rent))
            except (TypeError, ValueError):
                continue

        if not valid_listings:
            return "目前沒有足夠的租金資料可以比較。"

        lowest_rent = min(rent for _, rent in valid_listings)

        cheapest = [
            listing for listing, rent in valid_listings
            if rent == lowest_rent
        ]

        results = ["目前租金最低的房源："]

        for listing in cheapest:
            title = listing.get("title") or "未命名物件"
            location = listing.get("location") or "未提供"
            listing_id = listing.get("id", "—")

            results.append(
                f"- **{title}**（ID：{listing_id}）\n"
                f"  - 月租：{lowest_rent:,.0f} 元\n"
                f"  - 地點：{location}"
            )

        results.append(
            "\n以上結果依照已儲存的房源租金計算。"
        )

        return "\n".join(results)

    # 寵物友善房源：直接由 Python 篩選
    if any(word in q for word in ["寵物", "養寵物"]):
        pet_listings = [
            l for l in listings
            if l.get("pet_friendly") in (True, 1, "1")
        ]

        if not pet_listings:
            return "目前沒有找到明確標註可養寵物的房源。"

        results = ["目前可養寵物的房源："]

        for listing in pet_listings:
            title = listing.get("title") or "未命名物件"
            rent = listing.get("rent") or "未提供"
            location = listing.get("location") or "未提供"

            results.append(
                f"- **{title}**（ID：{listing.get('id', '—')}）\n"
                f"  - 月租：{rent} 元\n"
                f"  - 地點：{location}"
            )

        return "\n".join(results)

    # 租金上限篩選
    rent_match = re.search(
        r"(?:低於|不到|不超過|不高於|以下|以內|小於)\s*(\d[\d,]*)\s*元?",
        question
    )

    if rent_match:
        max_rent = int(rent_match.group(1).replace(",", ""))

        matched = []
        for l in listings:
            try:
                rent = float(l.get("rent"))
                if 0 < rent <= max_rent:
                    matched.append(l)
            except (TypeError, ValueError):
                continue

        if not matched:
            return f"目前沒有找到月租 {max_rent:,} 元以下的房源。"

        results = [f"月租 {max_rent:,} 元以下的房源："]

        for l in matched:
            results.append(
                f"- **{l.get('title') or '未命名物件'}** "
                f"（ID：{l.get('id', '—')}）\n"
                f"  - 月租：{l.get('rent'):,} 元\n"
                f"  - 地點：{l.get('location') or '未提供'}"
            )

        return "\n".join(results)

    # 坪數篩選
    ping_match = re.search(
        r"(?:至少|大於|超過|高於|以上|不低於|不小於|小於|低於|以下|不超過)\s*(\d+(?:\.\d+)?)\s*坪",
        question
    )

    if ping_match:
        number = float(ping_match.group(1))
        keyword = ping_match.group(0)

        is_min = any(
            word in keyword
            for word in ["至少", "大於", "超過", "高於", "以上", "不低於", "不小於"]
        )

        matched = []

        for l in listings:
            try:
                size = float(l.get("size_ping"))
                if (is_min and size >= number) or (not is_min and size <= number):
                    matched.append(l)
            except (TypeError, ValueError):
                continue

        condition = "以上" if is_min else "以下"

        if not matched:
            return f"目前沒有找到 {number:g} 坪{condition}的房源。"

        results = [f"{number:g} 坪{condition}的房源："]

        for l in matched:
            results.append(
                f"- **{l.get('title') or '未命名物件'}** "
                f"（ID：{l.get('id', '—')}）\n"
                f"  - 坪數：{l.get('size_ping') or '未提供'} 坪\n"
                f"  - 月租：{l.get('rent') or '未提供'} 元\n"
                f"  - 地點：{l.get('location') or '未提供'}"
            )

        return "\n".join(results)

    # 2. Other questions continue to use Gemini
    simplified = []

    for l in listings:
        simplified.append({
            "id": l.get("id"),
            "title": l.get("title"),
            "rent": l.get("rent"),
            "size_ping": l.get("size_ping"),
            "location": l.get("location"),
            "district": l.get("district"),
            "bedrooms": l.get("bedrooms"),
            "has_ac": bool(l.get("has_ac")),
            "has_washing_machine": bool(l.get("has_washing_machine")),
            "pet_friendly": bool(l.get("pet_friendly")),
            "near_mrt": l.get("near_mrt"),
            "deposit": l.get("deposit"),
            "notes": l.get("notes"),
        })

    prompt = COMPARE_PROMPT.format(
        listings_json=json.dumps(
            simplified,
            ensure_ascii=False,
            indent=2
        ),
        question=question,
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )

    return response.text
