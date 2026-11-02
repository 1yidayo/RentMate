import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Sites known to use JavaScript rendering — BeautifulSoup cannot read their content
JS_RENDERED_SITES = ["591.com.tw", "house.591.com.tw", "rent.591.com.tw"]


def scrape_url(url: str) -> dict:
    """
    Attempt to scrape text content from a URL.
    Returns a dict with 'success', 'text', and 'error'.
    """
    # Early check for known JS-rendered sites
    for site in JS_RENDERED_SITES:
        if site in url:
            return {
                "success": False,
                "text": "",
                "error": (
                    "⚠️ 591 使用 JavaScript 動態渲染，BeautifulSoup 無法讀取真實房源內容。\n\n"
                    "**請改用「貼文字」方式：**\n"
                    "1. 打開 591 網頁\n"
                    "2. 複製房源標題、租金、地點、設備等文字\n"
                    "3. 貼到「貼文字」頁籤即可"
                ),
            }

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script / style / boilerplate tags
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        text = text[:6000]

        # Heuristic: if text is mostly short lines it's probably JS boilerplate
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        avg_len = sum(len(l) for l in lines) / max(len(lines), 1)

        if len(text) < 100 or avg_len < 10:
            return {
                "success": False,
                "text": "",
                "error": (
                    "頁面內容疑似 JavaScript 渲染或需要登入，無法直接讀取。\n"
                    "請改為手動複製貼文內容到「貼文字」頁籤。"
                ),
            }

        return {"success": True, "text": text, "error": None}

    except requests.exceptions.Timeout:
        return {"success": False, "text": "", "error": "連線逾時（10秒），請確認網址是否正確，或改為手動貼上文字。"}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code
        return {"success": False, "text": "", "error": f"HTTP {code} 錯誤：該頁面需要登入或不允許直接存取。請改為手動貼上文字內容。"}
    except Exception as e:
        return {"success": False, "text": "", "error": f"無法讀取網頁：{str(e)}。請改為手動貼上文字內容。"}
