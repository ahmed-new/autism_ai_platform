# -*- coding: utf-8 -*-
"""
Build a single PDF report from research artifacts.
Independent of production code.
"""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak

BASE = os.path.dirname(__file__)
ART = os.path.join(BASE, "artifacts")
DATA = os.path.join(BASE, "data")
os.makedirs(ART, exist_ok=True)

def read_text(name):
    p = os.path.join(ART, name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return None

def try_img(name, width=15*cm):
    p = os.path.join(ART, name)
    if os.path.exists(p):
        img = Image(p, width=width, height=width*0.65)
        img.hAlign = "CENTER"
        return img
    return None

def main():
    doc = SimpleDocTemplate(
        os.path.join(ART, "ML_research_report.pdf"),
        pagesize=A4,
        rightMargin=1.7*cm, leftMargin=1.7*cm,
        topMargin=1.7*cm, bottomMargin=1.7*cm,
        title="Tamkeen ML Research Report",
        author="Research Module"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="h1", fontName="Helvetica-Bold", fontSize=18, spaceAfter=12, alignment=2))  # RTL لاحقًا لو حبيت تضيف خط عربي
    styles.add(ParagraphStyle(name="h2", fontName="Helvetica-Bold", fontSize=14, spaceAfter=8))
    styles.add(ParagraphStyle(name="p",  fontName="Helvetica", fontSize=10.5, leading=14))
    styles.add(ParagraphStyle(name="mono", fontName="Courier", fontSize=9))

    flow = []

    flow.append(Paragraph("تقرير أبحاث التعلم الآلي — منصة تمكين", styles["h1"]))
    flow.append(Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), styles["p"]))
    flow.append(Spacer(1, 8))

    # ملخص
    flow.append(Paragraph("ملخص", styles["h2"]))
    flow.append(Paragraph(
        "هذا التقرير يجمّع نواتج وحدة الأبحاث (غير متصلة بالإنتاج): "
        "نموذج انتباه أساسي (LogReg)، مؤشر SCQ (Naive Bayes)، ومحاكي اختيار المهارة التالية (LinUCB). "
        "البيانات صناعية لأغراض البحث فقط.", styles["p"]))
    flow.append(Spacer(1, 12))

    # Attention baseline
    flow.append(Paragraph("1) Attention Baseline", styles["h2"]))
    txt = read_text("attention_baseline_report.txt")
    if txt:
        flow.append(Paragraph("ملخص القياسات:", styles["p"]))
        flow.append(Spacer(1, 6))
        for line in txt.splitlines():
            flow.append(Paragraph(line.replace(" ", "&nbsp;"), styles["mono"]))
    else:
        flow.append(Paragraph("لا يوجد ملف تقرير.", styles["p"]))
    flow.append(Spacer(1, 8))
    for name in ["attention_baseline_roc.png", "attention_baseline_pr.png", "attention_baseline_cm.png"]:
        img = try_img(name)
        if img: flow.append(img); flow.append(Spacer(1, 8))

    flow.append(PageBreak())

    # SCQ screener
    flow.append(Paragraph("2) SCQ Screener (غير تشخيصي)", styles["h2"]))
    txt = read_text("scq_screener_report.txt")
    if txt:
        for line in txt.splitlines():
            flow.append(Paragraph(line.replace(" ", "&nbsp;"), styles["mono"]))
    else:
        flow.append(Paragraph("لا يوجد ملف تقرير.", styles["p"]))
    flow.append(Spacer(1, 8))
    for name in ["scq_screener_roc.png", "scq_screener_pr.png"]:
        img = try_img(name)
        if img: flow.append(img); flow.append(Spacer(1, 8))

    flow.append(PageBreak())

    # Bandit
    flow.append(Paragraph("3) محاكي اختيار المهارة التالية (LinUCB)", styles["h2"]))
    txt = read_text("bandit_summary.txt")
    if txt:
        for line in txt.splitlines():
            flow.append(Paragraph(line.replace(" ", "&nbsp;"), styles["mono"]))
    else:
        flow.append(Paragraph("لا يوجد ملخص.", styles["p"]))
    flow.append(Spacer(1, 8))
    for name in ["bandit_avg_reward.png", "bandit_regret.png"]:
        img = try_img(name)
        if img: flow.append(img); flow.append(Spacer(1, 8))

    doc.build(flow)
    print("Saved:", os.path.join(ART, "ML_research_report.pdf"))

if __name__ == "__main__":
    main()
