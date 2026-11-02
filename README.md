# RentMate

AI 驅動的租屋資訊整合與比較助理

## 環境設定

### 1. 安裝 Python 3.11
https://www.python.org/downloads/release/python-3119/

### 2. 建立虛擬環境
```bash
python -m venv venv
venv\Scripts\activate      # Windows
```

### 3. 安裝套件
```bash
pip install -r requirements.txt
```

### 4. 設定 API Key
複製 `.env.example` 為 `.env`，填入你的 Gemini API Key：
```
GEMINI_API_KEY=你的key貼這裡
```

取得 Key：https://aistudio.google.com/apikey（免費，無需信用卡）

### 5. 啟動應用程式
```bash
streamlit run app.py
```

## 專案結構
```
RentMate/
├── app.py              # 主程式
├── requirements.txt
├── .env                # API Key（不進 git）
├── .env.example
├── utils/
│   ├── db.py           # SQLite 資料庫
│   ├── llm.py          # Gemini API
│   └── scraper.py      # 網頁爬蟲
└── logs/
    └── ai_verification_log.md
```

## 注意事項
- `rentmate.db` 為本機資料庫，已加入 `.gitignore`，每人各自維護
- 591 有防爬機制，建議直接貼文字使用
