# -*- coding: utf-8 -*-
"""
元盾資安 報價單產生器 - Gradio App
======================================
可直接部署到 Hugging Face Spaces（SDK 選 Gradio）。

執行方式：
    python app.py
會在本機開一個網頁介面 (預設 http://127.0.0.1:7860)。

檔案結構：
    app.py                  <- 這支檔案，Gradio 介面
    quotation_generator.py  <- PDF 產生邏輯 (reportlab)
    requirements.txt        <- 部署到 Hugging Face 用
"""

import datetime
import gradio as gr

from quotation_generator import generate_quotation

# ---------------------------------------------------------------------------
# 預設值（可依需求修改成別家公司資訊）
# ---------------------------------------------------------------------------
DEFAULT_ISSUER = {
    "name_zh": "元盾資安股份有限公司",
    "name_en": "Meta Shield Security Co., Ltd.",
    "phone": "02-55625888",
    "email": "service@mss.com.tw",
    "address": "新北市中和區連城路268號4樓",
}

# 業務代表資訊（固定預設值，欄位仍可修改）
DEFAULT_SALES = {
    "rep": "莊雅慧 Debbie",
    "phone": "0928057298",
    "email": "debbie@mss.com.tw",
}

# 收款帳戶資訊（固定不開放填寫，因為匯款資訊都是同一組）
FIXED_PAYMENT = {
    "bank": "第一銀行",
    "branch": "連城分行 0072366",
    "account_no": "236-10-025671",
    "account_name": "元盾資安股份有限公司",
}

DEFAULT_NOTES = (
    "1、以上報價七天內有效。\n"
    "2、本報價金額為專案優惠價，切勿透露報價之價格與相關內容予第三方與公開。\n"
    "3、以上報價不含安裝設定、備品與到府服務。\n"
    "4、付款方式：現金、匯款，交貨後開立發票後30天內付款。\n"
    "5、本報價單如經貴單位加蓋公司章或發票章為後傳真回傳 即視為正式報價單。\n"
    "6、以上專案金額總計費用為含稅價。"
)

# 產品項目表格欄位：折數以「幾折」輸入 (10 = 不打折, 9 = 9折, 8.5 = 85折 ...)
ITEM_COLUMNS = ["產品名稱", "內容描述", "單位", "數量", "原價(單價)", "折數(幾折)"]
ITEM_DTYPES = ["str", "str", "str", "number", "number", "number"]
DEFAULT_ITEMS = [
    ["M-Standard\n資安託管偵測回應服務",
     "FMDR-M-Standard 提供的一年訂閱服務：\n"
     "1. 7x24 監控與警報處理\n2. MDR中文平台介面\n3. 分析系統警報\n"
     "4. 主動排除誤報\n5. 協助判斷可疑程式與處理建議\n"
     "6. 主動式威脅獵捕(Threat Hunting)提供事件響應服務\n"
     "7. 遠程IR服務\n8. 提供月度報表與報告\n9. 一年顧問服務協助排除問題\n使用期間:一年",
     "式", 60, 2000, 9],
]


def _next_quote_no():
    today = datetime.date.today()
    return f"Q{today.year}/{today.month}/{today.day}-01"


def build_items_from_table(table):
    """把 Gradio Dataframe 的內容轉成 quotation_generator 需要的 items list"""
    items = []
    if table is None:
        return items
    # gradio 可能回傳 pandas.DataFrame 或 list-of-list，統一處理
    rows = table.values.tolist() if hasattr(table, "values") else table

    for row in rows:
        if row is None:
            continue
        name, desc, unit, qty, unit_price, discount_10 = (list(row) + [None] * 6)[:6]
        if not name and not desc:
            continue  # 略過空白列
        try:
            qty = float(qty) if qty not in (None, "") else 0
            unit_price = float(unit_price) if unit_price not in (None, "") else 0
            discount_10 = float(discount_10) if discount_10 not in (None, "") else 10
        except (TypeError, ValueError):
            continue
        items.append({
            "name": name or "",
            "description": desc or "",
            "unit": unit or "式",
            "qty": int(qty),
            "unit_price": unit_price,
            "discount": discount_10 / 10.0,   # 「幾折」轉成 0~1 的小數，內部計算用，不會印在報價單上
        })
    return items


def create_quotation(
    issuer_name_zh, issuer_name_en, issuer_phone, issuer_email, issuer_address,
    quote_date, quote_no, sales_rep, sales_phone, sales_email, project_name,
    client_company, client_contact, client_address, client_phone, client_mobile, client_email,
    items_table, tax_rate_pct,
    notes_text,
):
    items = build_items_from_table(items_table)
    if not items:
        raise gr.Error("請至少填寫一筆產品項目（產品名稱 / 數量 / 原價）")

    data = {
        "issuer": {
            "name_zh": issuer_name_zh,
            "name_en": issuer_name_en,
            "phone": issuer_phone,
            "email": issuer_email,
            "address": issuer_address,
        },
        "quote_date": quote_date,
        "quote_no": quote_no,
        "sales_rep": sales_rep,
        "sales_phone": sales_phone,
        "sales_email": sales_email,
        "project_name": project_name,
        "client": {
            "company": client_company,
            "contact": client_contact,
            "address": client_address,
            "phone": client_phone,
            "mobile": client_mobile,
            "email": client_email,
        },
        "items": items,
        "tax_rate": (tax_rate_pct or 0) / 100.0,
        "notes": [line for line in (notes_text or "").split("\n") if line.strip()],
        "payment_account": FIXED_PAYMENT,
    }

    safe_no = (quote_no or "quotation").replace("/", "-")
    output_path = f"/tmp/{safe_no}.pdf"
    generate_quotation(data, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Gradio 介面
# ---------------------------------------------------------------------------
with gr.Blocks(title="報價單產生器") as demo:
    gr.Markdown("# 📄 元盾資安 報價單產生器\n填好下方欄位後按「產生報價單 PDF」，"
                "**折數欄位只用來計算專案價格，不會印在最後的報價單上**。")

    with gr.Accordion("① 發文公司資訊（通常不用改）", open=False):
        with gr.Row():
            issuer_name_zh = gr.Textbox(label="公司名稱(中)", value=DEFAULT_ISSUER["name_zh"])
            issuer_name_en = gr.Textbox(label="公司名稱(英)", value=DEFAULT_ISSUER["name_en"])
        with gr.Row():
            issuer_phone = gr.Textbox(label="服務電話", value=DEFAULT_ISSUER["phone"])
            issuer_email = gr.Textbox(label="服務信箱", value=DEFAULT_ISSUER["email"])
            issuer_address = gr.Textbox(label="服務地址", value=DEFAULT_ISSUER["address"])

    gr.Markdown("### ② 報價單資訊")
    with gr.Row():
        quote_date = gr.Textbox(label="報價日期", value=datetime.date.today().strftime("%Y/%m/%d"))
        quote_no = gr.Textbox(label="報價單號", value=_next_quote_no())
        project_name = gr.Textbox(label="專案名稱")
    with gr.Row():
        sales_rep = gr.Textbox(label="業務代表", value=DEFAULT_SALES["rep"])
        sales_phone = gr.Textbox(label="業務電話", value=DEFAULT_SALES["phone"])
        sales_email = gr.Textbox(label="業務Email", value=DEFAULT_SALES["email"])

    gr.Markdown("### ③ 客戶資訊")
    with gr.Row():
        client_company = gr.Textbox(label="客戶公司名稱")
        client_contact = gr.Textbox(label="聯絡人")
    with gr.Row():
        client_address = gr.Textbox(label="聯絡地址")
    with gr.Row():
        client_phone = gr.Textbox(label="聯絡電話")
        client_mobile = gr.Textbox(label="行動電話")
        client_email = gr.Textbox(label="客戶Email")

    gr.Markdown("### ④ 產品項目\n"
                "「折數(幾折)」：輸入 10 代表不打折，9 代表 9 折，8.5 代表 85 折…"
                "程式會自動用「原價 × 折數」算出專案價格，此欄位**不會出現在產出的報價單上**。")
    items_table = gr.Dataframe(
        headers=ITEM_COLUMNS,
        datatype=ITEM_DTYPES,
        value=DEFAULT_ITEMS,
        row_count=(1, "dynamic"),
        column_count=(6, "fixed"),
        wrap=True,
        label="產品項目（可新增多列）",
    )
    tax_rate_pct = gr.Number(label="營業稅率 (%)", value=5)

    gr.Markdown("### ⑤ 備註（每行一條）")
    notes_text = gr.Textbox(label="備註", value=DEFAULT_NOTES, lines=6)

    gr.Markdown(
        "### ⑥ 收款帳戶資訊（固定，不開放修改）\n"
        f"銀行：{FIXED_PAYMENT['bank']}　分行：{FIXED_PAYMENT['branch']}　"
        f"帳號：{FIXED_PAYMENT['account_no']}　戶名：{FIXED_PAYMENT['account_name']}"
    )

    generate_btn = gr.Button("🚀 產生報價單 PDF", variant="primary")
    output_file = gr.File(label="下載報價單 PDF")

    generate_btn.click(
        fn=create_quotation,
        inputs=[
            issuer_name_zh, issuer_name_en, issuer_phone, issuer_email, issuer_address,
            quote_date, quote_no, sales_rep, sales_phone, sales_email, project_name,
            client_company, client_contact, client_address, client_phone, client_mobile, client_email,
            items_table, tax_rate_pct,
            notes_text,
        ],
        outputs=output_file,
    )

if __name__ == "__main__":
    demo.launch()
