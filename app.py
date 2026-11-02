"""
RentMate — Main Streamlit Application
AI-powered rental listing aggregator and comparison tool
"""

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Must be first Streamlit call
st.set_page_config(
    page_title="RentMate — AI 租屋比較助理",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.db import init_db

# Initialize DB on every cold start
init_db()

# ── Sidebar Navigation ──────────────────────────────────────────────────────
st.sidebar.title("🏠 RentMate")
st.sidebar.caption("AI 租屋資訊整合與比較助理")
st.sidebar.markdown("---")

pages = {
    "🏠 首頁": "home",
    "➕ 新增房源": "add",
    "📊 比較表格": "compare",
    "💬 AI 問答": "chat",
}

if "page" not in st.session_state:
    st.session_state.page = "home"

for label, key in pages.items():
    if st.sidebar.button(label, use_container_width=True, key=f"nav_{key}"):
        st.session_state.page = key

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**使用流程**\n\n"
    "1. 新增房源（貼網址或文字）\n"
    "2. 查看比較表格\n"
    "3. 用 AI 問答分析\n"
)

# ── Page Routing ────────────────────────────────────────────────────────────
page = st.session_state.page

if page == "home":
    st.title("🏠 RentMate")
    st.subheader("AI 驅動的租屋資訊整合與比較助理")
    st.markdown("""
    ### 你的問題
    你是否曾花大量時間在各平台找房，卻要手動建表格比較？

    **RentMate** 讓你只需貼上租屋貼文或網址，AI 自動擷取房屋條件，建立個人化比較表格。

    ---
    ### 如何使用
    | 步驟 | 說明 |
    |------|------|
    | 1️⃣ 新增房源 | 貼上 591、Dcard、Facebook 的租屋文字或網址 |
    | 2️⃣ AI 擷取 | 系統自動分析並整理：租金、坪數、設備、地點... |
    | 3️⃣ 比較表格 | 一眼看清所有物件的條件差異 |
    | 4️⃣ AI 問答 | 直接問「哪間最適合我？」、「有哪些可以養寵物？」 |

    ---
    """)

    # Quick stats
    from utils.db import get_all_listings
    listings = get_all_listings()
    col1, col2, col3 = st.columns(3)
    col1.metric("已收錄物件", f"{len(listings)} 筆")
    if listings:
        rents = [l["rent"] for l in listings if l.get("rent")]
        if rents:
            col2.metric("平均月租", f"${sum(rents)//len(rents):,}")
            col3.metric("最低月租", f"${min(rents):,}")

elif page == "add":
    st.title("➕ 新增房源")
    st.markdown("貼上租屋文字或網址，AI 自動擷取資訊。")

    tab_url, tab_text = st.tabs(["🔗 貼網址", "📝 貼文字"])

    with tab_url:
        st.markdown("""
        > ⚠️ **注意**：591 等平台需要登入才能查看完整資訊，可能無法直接爬取。
        > 若失敗，請改用「貼文字」頁籤。
        """)
        url_input = st.text_input("租屋網址", placeholder="https://...")
        if st.button("🔍 讀取並分析", key="btn_url") and url_input:
            from utils.scraper import scrape_url
            from utils.llm import extract_listing
            from utils.db import insert_listing

            with st.spinner("正在讀取網頁..."):
                result = scrape_url(url_input)

            if not result["success"]:
                st.error(f"❌ {result['error']}")
            else:
                st.success("✅ 網頁讀取成功，正在 AI 分析...")
                with st.spinner("AI 擷取中..."):
                    try:
                        data = extract_listing(result["text"])
                        data["raw_text"] = result["text"]
                        data["source_url"] = url_input
                        listing_id = insert_listing(data)
                        st.success(f"✅ 已新增物件（ID: {listing_id}）！")
                        st.json(data)
                    except Exception as e:
                        st.error(f"AI 分析失敗：{e}")

    with tab_text:
        text_input = st.text_area(
            "貼上租屋貼文或廣告文字",
            height=250,
            placeholder="例如：\n台大附近 雙人套房 月租12000\n三樓/五樓 含水電 有冷氣冰箱洗衣機\n近公館捷運站步行8分 不得養寵物..."
        )
        if st.button("🤖 AI 分析", key="btn_text") and text_input:
            from utils.llm import extract_listing
            from utils.db import insert_listing

            with st.spinner("AI 正在擷取資訊..."):
                try:
                    data = extract_listing(text_input)
                    data["raw_text"] = text_input
                    data["source_url"] = ""
                    listing_id = insert_listing(data)
                    st.success(f"✅ 已新增物件（ID: {listing_id}）！")

                    # Show extracted result with confidence indicators
                    st.markdown("### 擷取結果")
                    confidence = data.get("confidence", {})

                    def conf_badge(field):
                        level = confidence.get(field, "not_mentioned")
                        icons = {"high": "🟢", "medium": "🟡", "low": "🔴", "not_mentioned": "⚪"}
                        return icons.get(level, "⚪")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**月租金** {conf_badge('rent')}")
                        st.write(f"${data.get('rent'):,}" if data.get('rent') else "未提及")
                        st.markdown(f"**坪數** {conf_badge('size_ping')}")
                        st.write(f"{data.get('size_ping')} 坪" if data.get('size_ping') else "未提及")
                        st.markdown(f"**押金** {conf_badge('deposit')}")
                        st.write(data.get('deposit') or "未提及")
                    with col2:
                        st.markdown(f"**地點** {conf_badge('location')}")
                        st.write(data.get('location') or "未提及")
                        st.markdown(f"**行政區**")
                        st.write(data.get('district') or "未提及")
                        st.markdown(f"**樓層**")
                        st.write(data.get('floor') or "未提及")
                    with col3:
                        st.markdown("**設備**")
                        equip = []
                        if data.get('has_ac'): equip.append("❄️ 冷氣")
                        if data.get('has_washing_machine'): equip.append("🫧 洗衣機")
                        if data.get('has_fridge'): equip.append("🧊 冰箱")
                        if data.get('has_internet'): equip.append("📶 網路")
                        if data.get('has_parking'): equip.append("🚗 停車")
                        if data.get('pet_friendly'): equip.append("🐾 寵物")
                        st.write("、".join(equip) if equip else "未提及")
                        st.markdown("**捷運**")
                        st.write(data.get('near_mrt') or "未提及")

                    st.markdown("---")
                    st.caption("🟢 高信心  🟡 中信心  🔴 低信心  ⚪ 原文未提及（AI 未填入）")

                except Exception as e:
                    st.error(f"AI 分析失敗：{e}")

elif page == "compare":
    st.title("📊 房源比較表格")

    from utils.db import get_all_listings, delete_listing
    import pandas as pd

    listings = get_all_listings()

    if not listings:
        st.info("還沒有任何房源。請先到「新增房源」頁面新增物件。")
    else:
        # Build display dataframe
        rows = []
        for l in listings:
            rows.append({
                "ID": l["id"],
                "標題": l.get("title") or "—",
                "月租(元)": l.get("rent"),
                "坪數": l.get("size_ping"),
                "地點": l.get("location") or "—",
                "行政區": l.get("district") or "—",
                "樓層": l.get("floor") or "—",
                "建物型態": l.get("building_type") or "—",
                "冷氣": "✅" if l.get("has_ac") else "❌",
                "洗衣機": "✅" if l.get("has_washing_machine") else "❌",
                "冰箱": "✅" if l.get("has_fridge") else "❌",
                "網路": "✅" if l.get("has_internet") else "❌",
                "寵物": "✅" if l.get("pet_friendly") else "❌",
                "押金": l.get("deposit") or "—",
                "捷運": l.get("near_mrt") or "—",
            })

        df = pd.DataFrame(rows)

        # Filters
        with st.expander("🔍 篩選條件", expanded=False):
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                max_rent = st.number_input("最高月租 (0=不限)", min_value=0, value=0, step=1000)
            with f_col2:
                need_ac = st.checkbox("需要冷氣")
                need_pet = st.checkbox("可養寵物")
            with f_col3:
                need_washer = st.checkbox("需要洗衣機")
                need_internet = st.checkbox("需要網路")

            filtered = listings
            if max_rent > 0:
                filtered = [l for l in filtered if l.get("rent") and l["rent"] <= max_rent]
            if need_ac:
                filtered = [l for l in filtered if l.get("has_ac")]
            if need_pet:
                filtered = [l for l in filtered if l.get("pet_friendly")]
            if need_washer:
                filtered = [l for l in filtered if l.get("has_washing_machine")]
            if need_internet:
                filtered = [l for l in filtered if l.get("has_internet")]

            st.caption(f"符合條件：{len(filtered)} / {len(listings)} 筆")
            display_ids = {l["id"] for l in filtered}
            df = df[df["ID"].isin(display_ids)]

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Delete listing
        st.markdown("---")
        st.markdown("### 刪除物件")
        del_id = st.number_input("輸入要刪除的物件 ID", min_value=1, step=1)
        if st.button("🗑️ 刪除", key="btn_delete"):
            delete_listing(int(del_id))
            st.success(f"已刪除 ID {del_id}")
            st.rerun()

elif page == "chat":
    st.title("💬 AI 問答分析")
    st.markdown("直接用自然語言詢問你的房源，AI 幫你分析比較。")

    from utils.db import get_all_listings
    from utils.llm import answer_question

    listings = get_all_listings()

    if not listings:
        st.info("還沒有任何房源。請先到「新增房源」頁面新增物件。")
    else:
        st.caption(f"目前共有 {len(listings)} 筆房源供 AI 分析。")

        # Chat history
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # Display history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input
        question = st.chat_input("例如：哪間最便宜？有哪些可以養寵物？推薦租哪一間？")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("AI 分析中..."):
                    try:
                        answer = answer_question(listings, question)
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    except Exception as e:
                        err_msg = f"❌ 分析失敗：{e}"
                        st.error(err_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": err_msg})

        if st.button("🗑️ 清除對話紀錄"):
            st.session_state.chat_history = []
            st.rerun()
