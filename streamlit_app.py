# -*- coding: utf-8 -*-
"""
元盾資安 報價單產生器 - Streamlit 版
========================================
可直接部署到 Streamlit Community Cloud (https://share.streamlit.io)。

本機執行：
    pip install -r requirements_streamlit.txt
    streamlit run streamlit_app.py
"""

import datetime
import pandas as pd
import streamlit as st

from quotation_generator import generate_quotation

# ---------------------------------------------------------------------------
DEFAULT_ISSUER = {
    "name_zh": "元盾資安股份有限公司",
    "name_en": "Meta Shield Security Co., Ltd.",
    "phone": "02-55625888",
    "email": "service@mss.com.tw",
    "address": "新北市中和區連城路268號4樓",
}

DEFAULT_NOTES = (
    "1、以上報價七天內有效。\n"
    "2、本報價金額為專案優惠價，切勿透露報價之價格與相關內容予第三方與公開。\n"
    "3、以上報價不含安裝設定、備品與到府服務。\n"
    "4、付款方式：現金、匯款，交貨後開立發票後30天內付款。\n"
    "5、本報價單如經貴單位加蓋公司章或發票章為後傳真回傳 即視為正式報價單。\n"
    "6、以上專案金額總計費用為含稅價。"
)

ITEM_COLUMNS = ["產品名稱", "內容描述", "單位", "數量", "原價(單價)", "折數(幾折)"]
DEFAULT_ITEMS = pd.DataFrame(
    [
        {
            "產品名稱": "M-Standard\n資安託管偵測回應服務",
            "內容描述": (
                "FMDR-M-Standard 提供的一年訂閱服務：\n"
                "1. 7x24 監控與警報處理\n2. MDR中文平台介面\n3. 分析系統警報\n"
                "4. 主動排除誤報\n5. 協助判斷可疑程式與處理建議\n"
                "6. 主動式威脅獵捕(Threat Hunting)提供事件響應服務\n"
                "7. 遠程IR服務\n8. 提供月度報表與報告\n9. 一年顧問服務協助排除問題\n使用期間:一年"
            ),
            "單位": "式",
            "數量": 60,
            "原價(單價)": 2000,
            "折數(幾折)": 9,
        }
    ],
    columns=ITEM_COLUMNS,
)


def build_items(df: pd.DataFrame):
    items = []
    for _, row in df.iterrows():
        name = str(row.get("產品名稱", "") or "")
        desc = str(row.get("內容描述", "") or "")
        if not name.strip() and not desc.strip():
            continue
        try:
            qty = int(float(row.get("數量", 0) or 0))
            unit_price = float(row.get("原價(單價)", 0) or 0)
            discount_10 = float(row.get("折數(幾折)", 10) or 10)
        except (TypeError, ValueError):
            continue
        items.append({
            "name": name,
            "description": desc,
            "unit": str(row.get("單位", "式") or "式"),
            "qty": qty,
            "unit_price": unit_price,
            "discount": discount_10 / 10.0,  # 只用來計算，不會印在報價單上
        })
    return items


st.set_page_config(page_title="報價單產生器", page_icon="📄", layout="centered")
st.title("📄 元盾資安 報價單產生器")
st.caption("折數欄位只用來計算專案價格，不會印在最後的報價單 PDF 上。")

with st.expander("① 發文公司資訊（通常不用改）"):
    c1, c2 = st.columns(2)
    issuer_name_zh = c1.text_input("公司名稱(中)", DEFAULT_ISSUER["name_zh"])
    issuer_name_en = c2.text_input("公司名稱(英)", DEFAULT_ISSUER["name_en"])
    c3, c4, c5 = st.columns(3)
    issuer_phone = c3.text_input("服務電話", DEFAULT_ISSUER["phone"])
    issuer_email = c4.text_input("服務信箱", DEFAULT_ISSUER["email"])
    issuer_address = c5.text_input("服務地址", DEFAULT_ISSUER["address"])

st.subheader("② 報價單資訊")
c1, c2, c3 = st.columns(3)
quote_date = c1.text_input("報價日期", datetime.date.today().strftime("%Y/%m/%d"))
today = datetime.date.today()
quote_no = c2.text_input("報價單號", f"Q{today.year}/{today.month}/{today.day}-01")
project_name = c3.text_input("專案名稱")

c1, c2, c3 = st.columns(3)
sales_rep = c1.text_input("業務代表")
sales_phone = c2.text_input("業務電話")
sales_email = c3.text_input("業務Email")

st.subheader("③ 客戶資訊")
c1, c2 = st.columns(2)
client_company = c1.text_input("客戶公司名稱")
client_contact = c2.text_input("聯絡人")
client_address = st.text_input("聯絡地址")
c1, c2, c3 = st.columns(3)
client_phone = c1.text_input("聯絡電話")
client_mobile = c2.text_input("行動電話")
client_email = c3.text_input("客戶Email")

st.subheader("④ 產品項目")
st.caption("「折數(幾折)」：輸入 10 代表不打折，9 代表 9 折，8.5 代表 85 折…")
items_df = st.data_editor(
    DEFAULT_ITEMS,
    num_rows="dynamic",
    use_container_width=True,
    key="items_editor",
)
tax_rate_pct = st.number_input("營業稅率 (%)", value=5.0, step=1.0)

st.subheader("⑤ 備註（每行一條）")
notes_text = st.text_area("備註", DEFAULT_NOTES, height=150)

st.subheader("⑥ 收款帳戶資訊")
c1, c2 = st.columns(2)
bank = c1.text_input("銀行", "第一銀行")
branch = c2.text_input("分行", "連城分行 0072366")
c1, c2 = st.columns(2)
account_no = c1.text_input("帳號", "236-10-025671")
account_name = c2.text_input("戶名", "元盾資安股份有限公司")

if st.button("🚀 產生報價單 PDF", type="primary"):
    items = build_items(items_df)
    if not items:
        st.error("請至少填寫一筆產品項目（產品名稱 / 數量 / 原價）")
    else:
        data = {
            "issuer": {
                "name_zh": issuer_name_zh, "name_en": issuer_name_en,
                "phone": issuer_phone, "email": issuer_email, "address": issuer_address,
            },
            "quote_date": quote_date,
            "quote_no": quote_no,
            "sales_rep": sales_rep,
            "sales_phone": sales_phone,
            "sales_email": sales_email,
            "project_name": project_name,
            "client": {
                "company": client_company, "contact": client_contact,
                "address": client_address, "phone": client_phone,
                "mobile": client_mobile, "email": client_email,
            },
            "items": items,
            "tax_rate": tax_rate_pct / 100.0,
            "notes": [line for line in notes_text.split("\n") if line.strip()],
            "payment_account": {
                "bank": bank, "branch": branch,
                "account_no": account_no, "account_name": account_name,
            },
        }
        safe_no = (quote_no or "quotation").replace("/", "-")
        output_path = f"/tmp/{safe_no}.pdf"
        generate_quotation(data, output_path)
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
        st.success("報價單已產生！")
        st.download_button(
            "⬇️ 下載報價單 PDF",
            data=pdf_bytes,
            file_name=f"{safe_no}.pdf",
            mime="application/pdf",
        )
