# -*- coding: utf-8 -*-
"""
元盾資安 報價單產生器 (Quotation Generator)
=============================================

用法 (Usage)
------------
1. 準備一份 dict 資料（可參考本檔案下方 example_data()）。
2. 呼叫 generate_quotation(data, output_path) 即可產出與範例報價單相同版型的 PDF。
3. 每個產品項目可填入「折數」(discount) 欄位，程式會自動用「原價 x 折數」
   算出「力麗專案價格」與「小計」，但「折數」欄位本身 **不會** 出現在產出的報價單上，
   只作為內部試算使用。
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import reportlab.pdfbase.cidfonts as _cidfonts_module

_DEFAULT_LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")

FONT_NAME = "MSung-Light"
_cidfonts_module.defaultUnicodeEncodings[FONT_NAME] = ("cht", "UniCNS-UCS2-H")
pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))

PRIMARY_COLOR = colors.HexColor("#2E5C8A")
LIGHT_BLUE = colors.HexColor("#DCE6F1")
GREY_LINE = colors.HexColor("#666666")


def _style(name, size=9, align=TA_LEFT, color=colors.black, leading=None):
    return ParagraphStyle(
        name=name, fontName=FONT_NAME, fontSize=size,
        leading=leading or size * 1.5, alignment=align, textColor=color,
    )


STYLES = {
    "title": _style("title", size=16, align=TA_CENTER, leading=19),
    "subtitle": _style("subtitle", size=10, align=TA_CENTER, color=GREY_LINE, leading=12),
    "section_header": _style("section_header", size=10, align=TA_CENTER, color=colors.white, leading=12),
    "label": _style("label", size=9, leading=11.5),
    "value": _style("value", size=9, leading=11.5),
    "cell": _style("cell", size=8.5, leading=9),
    "cell_center": _style("cell_center", size=8.5, align=TA_CENTER, leading=9),
    "cell_right": _style("cell_right", size=8.5, align=TA_RIGHT, leading=9),
    "note": _style("note", size=8, leading=8.5),
    "note_bold": _style("note_bold", size=8, leading=8.5, color=colors.red),
    "sign_label": _style("sign_label", size=9, align=TA_CENTER),
}


def _p(text, style_key="cell"):
    text = "" if text is None else str(text)
    text = text.replace("\n", "<br/>")
    return Paragraph(text, STYLES[style_key])


def _section_header_table(text, width):
    t = Table([[_p(text, "section_header")]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PRIMARY_COLOR),
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _calc_items(items):
    """
    依照每個項目的 unit_price(原價) 與 discount(折數, 0~1之間)
    計算出 專案價格 與 小計。折數欄位只用於計算，不會輸出到最終報價單上。
    """
    processed = []
    subtotal_sum = 0
    for idx, item in enumerate(items, start=1):
        unit_price = item.get("unit_price", 0)
        discount = item.get("discount", 1)  # 1 = 不打折 (10折)
        qty = item.get("qty", 1)

        project_price = round(unit_price * discount)
        line_subtotal = project_price * qty
        subtotal_sum += line_subtotal

        processed.append({
            "no": idx,
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "unit": item.get("unit", "式"),
            "qty": qty,
            "price": unit_price,
            "project_price": project_price,
            "subtotal": line_subtotal,
        })
    return processed, subtotal_sum


def generate_quotation(data, output_path="quotation.pdf", logo_path=None):
    page_width, page_height = A4
    margin = 15 * mm
    content_width = page_width - 2 * margin

    if logo_path is None:
        logo_path = _DEFAULT_LOGO_PATH
    logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else None

    def _draw_logo(canvas_obj, doc_obj):
        if not logo_path:
            return
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            target_w = 32 * mm
            target_h = target_w * ih / iw
            x = page_width - margin - target_w
            y = page_height - 10 * mm - target_h
            canvas_obj.drawImage(
                img, x, y, width=target_w, height=target_h,
                mask="auto", preserveAspectRatio=True,
            )
        except Exception:
            pass

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=margin, rightMargin=margin,
        topMargin=10 * mm, bottomMargin=page_height / 3,
        title=data.get("quote_no", "Quotation"),
    )

    story = []

    company = data.get("issuer", {})
    story.append(Paragraph(company.get("name_zh", "元盾資安股份有限公司"), STYLES["title"]))
    story.append(Paragraph(company.get("name_en", "Meta Shield Security Co., Ltd."), STYLES["subtitle"]))
    story.append(Spacer(1, 2))
    contact_line = "服務電話：{phone} ，服務信箱：{mail} ，服務地址：{addr}".format(
        phone=company.get("phone", ""), mail=company.get("email", ""), addr=company.get("address", ""),
    )
    story.append(Paragraph(contact_line, _style("issuer_contact", size=8, align=TA_CENTER, leading=10)))
    story.append(Spacer(1, 4))
    story.append(Paragraph("報　價　單<br/>Quotation", _style("doc_title", size=12, align=TA_CENTER, leading=15)))
    story.append(Spacer(1, 4))

    story.append(_section_header_table("客 戶 基 本 資 料", content_width))

    client = data.get("client", {})
    left_w = content_width * 0.15
    val_w = content_width * 0.35
    info_rows = [
        ["公司名稱：", client.get("company", ""), "報價日期：", data.get("quote_date", "")],
        ["聯 絡 人：", client.get("contact", ""), "報價單號：", data.get("quote_no", "")],
        ["聯絡地址：", client.get("address", ""), "業務代表：", data.get("sales_rep", "")],
        ["聯絡電話：", client.get("phone", ""), "服務電話：", data.get("sales_phone", "")],
        ["行動電話：", client.get("mobile", ""), "電子郵件：", data.get("sales_email", "")],
        ["電子郵件：", client.get("email", ""), "專案名稱：", data.get("project_name", "")],
    ]
    info_table_data = [[_p(r[0], "label"), _p(r[1], "value"), _p(r[2], "label"), _p(r[3], "value")]
                        for r in info_rows]
    info_table = Table(info_table_data, colWidths=[left_w, val_w, left_w, val_w])
    info_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0))

    items, subtotal_sum = _calc_items(data.get("items", []))

    col_widths = [
        content_width * 0.05, content_width * 0.16, content_width * 0.36,
        content_width * 0.05, content_width * 0.05, content_width * 0.10,
        content_width * 0.10, content_width * 0.13,
    ]

    header_row = [
        _p("No.", "cell_center"), _p("產品名稱", "cell_center"),
        _p("內容描述", "cell_center"), _p("單位", "cell_center"),
        _p("數量", "cell_center"), _p("單 價", "cell_center"),
        _p("專案價格", "cell_center"), _p("小 計", "cell_center"),
    ]
    table_data = [header_row]
    for it in items:
        table_data.append([
            _p(it["no"], "cell_center"),
            _p(it["name"], "cell"),
            _p(it["description"], "cell"),
            _p(it["unit"], "cell_center"),
            _p(it["qty"], "cell_center"),
            _p(f"$ {it['price']:,}", "cell_right"),
            _p(f"$ {it['project_price']:,}", "cell_right"),
            _p(f"$ {it['subtotal']:,}", "cell_right"),
        ])

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_table)

    tax_rate = data.get("tax_rate", 0.05)
    tax = round(subtotal_sum * tax_rate)
    grand_total = subtotal_sum + tax

    summary_label_w = sum(col_widths[:-1])
    summary_val_w = col_widths[-1]
    summary_rows = [
        ["金額合計：", f"NT$ {subtotal_sum:,}"],
        [f"營業稅 {int(tax_rate * 100)}%：", f"NT$ {tax:,}"],
        ["專案價總計：", f"NT$ {grand_total:,}"],
    ]
    summary_data = [[_p(r[0], "cell_right"), _p(r[1], "cell_right")] for r in summary_rows]
    summary_table = Table(summary_data, colWidths=[summary_label_w, summary_val_w])
    summary_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)

    story.append(_section_header_table("備　　　　　　　註", content_width))

    notes = data.get("notes", [
        "1、以上報價七天內有效。",
        "2、本報價金額為專案價，切勿透露報價之價格與相關內容予第三方與公開。",
        "3、以上報價不含安裝設定、備品與到府服務。",
        "4、付款方式：現金、匯款，交貨後開立發票後30天內付款。",
        "5、本報價單如經貴單位加蓋公司章或發票章為後傳真回傳 即視為正式報價單。",
        "6、以上專案金額總計費用為含稅價。",
    ])
    payment = data.get("payment_account", {})
    notes_left = "<br/>".join(notes) + \
        f"<br/><br/>付款方式：<br/>銀行：{payment.get('bank', '')}　分行：{payment.get('branch', '')}" \
        f"<br/>帳號：{payment.get('account_no', '')}　戶名：{payment.get('account_name', '')}"

    notes_table = Table(
        [[Paragraph(notes_left, STYLES["note"]),
          Paragraph("客戶簽回欄<br/>(本報價單經簽回即視為正式報價單)", STYLES["sign_label"])]],
        colWidths=[content_width * 0.68, content_width * 0.32],
    )
    notes_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(notes_table)

    sign_headers = ["執行單位主管", "業務主管", "技術單位", "業務人員"]
    sign_table = Table(
        [[_p(h, "cell_center") for h in sign_headers], ["", "", "", ""]],
        colWidths=[content_width / 4] * 4,
        rowHeights=[13, 28],
    )
    sign_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.75, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
    ]))
    story.append(
        KeepTogether([
            _section_header_table(company.get("name_zh", "元盾資安股份有限公司") + " 內部人員簽核", content_width),
            sign_table,
        ])
    )

    doc.build(story, onFirstPage=_draw_logo, onLaterPages=_draw_logo)
    return output_path


def example_data():
    return {
        "issuer": {
            "name_zh": "元盾資安股份有限公司",
            "name_en": "Meta Shield Security Co., Ltd.",
            "phone": "02-55625888",
            "email": "service@mss.com.tw",
            "address": "新北市中和區連城路268號4樓",
        },
        "quote_date": "2026/7/13",
        "quote_no": "Q2026/7/13-MDR01",
        "sales_rep": "Debbie 莊雅慧",
        "sales_phone": "0928-057-298",
        "sales_email": "debbie@mss.com.tw",
        "project_name": "力麗科技(博鉅-欣葉國際餐飲)",
        "client": {
            "company": "力麗科技股份有限公司",
            "contact": "陳秉智 經理",
            "address": "台北市中山區松江路162號6樓(力麗商業大樓)",
            "phone": "02-2100-2458 Ext,8604",
            "mobile": "0919-772-288",
            "email": "bensonchen@llt.com.tw",
        },
        "items": [
            {
                "name": "M-Standard\n資安託管偵測回應服務",
                "description": (
                    "FMDR-M-Standard 提供的一年訂閱服務：\n"
                    "1. 7x24 監控與警報處理\n2. MDR中文平台介面\n3. 分析系統警報\n"
                    "4. 主動排除誤報\n5. 協助判斷可疑程式與處理建議\n"
                    "6. 主動式威脅獵捕(Threat Hunting)提供事件響應服務\n"
                    "7. 遠程IR服務\n8. 提供月度報表與報告\n9. 一年顧問服務協助排除問題\n使用期間:一年"
                ),
                "unit": "式",
                "qty": 60,
                "unit_price": 2000,
                "discount": 0.9,
            }
        ],
        "tax_rate": 0.05,
        "payment_account": {
            "bank": "第一銀行",
            "branch": "連城分行 0072366",
            "account_no": "236-10-025671",
            "account_name": "元盾資安股份有限公司",
        },
    }


if __name__ == "__main__":
    data = example_data()
    generate_quotation(data, "/mnt/user-data/outputs/quotation_sample.pdf")
    print("完成，已產出 quotation_sample.pdf")
