"""
PDF report generator using ReportLab.
"""

import os
import io
import logging
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger("citelytics.report")

# ─── colour palette ───────────────────────────────────────────
PRIMARY   = colors.HexColor("#6C63FF")
SECONDARY = colors.HexColor("#10B981")
DANGER    = colors.HexColor("#EF4444")
GRAY      = colors.HexColor("#64748B")
LIGHT     = colors.HexColor("#F1F5F9")
DARK      = colors.HexColor("#0F172A")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title":    ParagraphStyle("Title2",   parent=ss["Title"],
                                   textColor=PRIMARY, fontSize=22, spaceAfter=6),
        "subtitle": ParagraphStyle("Sub",      parent=ss["Normal"],
                                   textColor=GRAY, fontSize=11, spaceAfter=18),
        "h1":       ParagraphStyle("H1r",      parent=ss["Heading1"],
                                   textColor=DARK, fontSize=14, spaceBefore=16),
        "h2":       ParagraphStyle("H2r",      parent=ss["Heading2"],
                                   textColor=PRIMARY, fontSize=12, spaceBefore=10),
        "body":     ParagraphStyle("Body",     parent=ss["Normal"],
                                   fontSize=9, leading=14, spaceAfter=4),
        "small":    ParagraphStyle("Small",    parent=ss["Normal"],
                                   fontSize=8, textColor=GRAY),
        "warn":     ParagraphStyle("Warn",     parent=ss["Normal"],
                                   fontSize=8, textColor=DANGER),
    }


def generate_pdf(analysis: dict) -> bytes:
    """
    Returns raw PDF bytes for the given analysis result dict.
    """
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    s      = _styles()
    story  = []

    url         = str(analysis.get("url", ""))
    score       = analysis.get("citation_probability", 0) or 0
    prediction  = str(analysis.get("prediction", ""))
    timestamp   = analysis.get("timestamp", datetime.utcnow().isoformat())
    features    = analysis.get("features") or {}
    shap_data   = analysis.get("shap_data") or {}
    recs        = analysis.get("recommendations") or []

    # Defensive guards: `analysis` is an arbitrary client-supplied dict (the
    # /api/report route does not enforce a nested schema), so any of these
    # fields may be missing or the wrong type. Fall back to safe empties
    # rather than raising deep inside PDF construction below.
    if not isinstance(features, dict):
        features = {}
    if not isinstance(shap_data, dict):
        shap_data = {}
    if not isinstance(recs, list):
        recs = []

    # ── Header ───────────────────────────────────────────────
    story.append(Paragraph("Citelytics", s["title"]))
    story.append(Paragraph("Generative Engine Citation Analysis Report", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
    story.append(Spacer(1, 10))

    # ── Meta ─────────────────────────────────────────────────
    meta = [
        ["URL",        url[:80]],
        ["Analysis",   timestamp],
        ["Model",      "XGBoost (Demo / Research Prototype)"],
    ]
    t = Table(meta, colWidths=[3.5*cm, 13*cm])
    t.setStyle(TableStyle([
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TEXTCOLOR",   (0,0), (0,-1), PRIMARY),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT, colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.3, GRAY),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # ── Score ─────────────────────────────────────────────────
    story.append(Paragraph("Citation Likelihood", s["h1"]))
    # Prefer the already-rounded `citation_score` that analyze.py put in the
    # same dict, so the PDF always shows the same headline number as the
    # JSON API / web UI for this exact result. Only derive it from the raw
    # probability (via round(), not truncation) when citation_score is absent
    # — e.g. a report requested against a hand-built or older-shaped payload.
    score_pct = analysis.get("citation_score")
    if not isinstance(score_pct, (int, float)):
        score_pct = int(round(float(score) * 100))
    else:
        score_pct = int(score_pct)
    colour = SECONDARY if score_pct >= 61 else (GRAY if score_pct >= 31 else DANGER)
    score_row = [[
        Paragraph(f"<b>{score_pct} / 100</b>", ParagraphStyle("S", fontSize=26,
                  textColor=colour, alignment=TA_CENTER)),
        Paragraph(f"<b>{escape(prediction)}</b>", ParagraphStyle("P", fontSize=12,
                  textColor=colour, alignment=TA_LEFT, leading=18)),
    ]]
    st = Table(score_row, colWidths=[5*cm, 11*cm])
    st.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(st)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "⚠ Disclaimer: This score is a model-derived estimate based on "
        "extracted webpage features and a demo dataset. "
        "It does NOT guarantee citation by any AI system.",
        s["warn"],
    ))
    story.append(Spacer(1, 12))

    # ── SHAP ──────────────────────────────────────────────────
    story.append(Paragraph("SHAP Explainability", s["h1"]))
    story.append(Paragraph("Top positive factors:", s["h2"]))
    for item in (shap_data.get("top_positive") or [])[:6]:
        if not isinstance(item, dict):
            continue
        fname = escape(str(item.get("feature", "unknown")).replace("_", " ").title())
        try:
            val = round(float(item.get("shap_value", 0)), 4)
        except (TypeError, ValueError):
            val = 0.0
        story.append(Paragraph(f"▲  <b>{fname}</b>  +{val}", s["body"]))

    story.append(Paragraph("Top negative factors:", s["h2"]))
    for item in (shap_data.get("top_negative") or [])[:6]:
        if not isinstance(item, dict):
            continue
        fname = escape(str(item.get("feature", "unknown")).replace("_", " ").title())
        try:
            val = round(float(item.get("shap_value", 0)), 4)
        except (TypeError, ValueError):
            val = 0.0
        story.append(Paragraph(f"▼  <b>{fname}</b>  {val}", s["body"]))

    story.append(Spacer(1, 12))

    # ── Feature summary ───────────────────────────────────────
    mf = features.get("model_features") or {}
    if not isinstance(mf, dict):
        mf = {}
    story.append(Paragraph("Feature Summary", s["h1"]))

    feat_rows = [["Feature", "Value"]]
    highlight = [
        "word_count", "factual_density", "schema_present",
        "format_diversity", "macro_structure_score", "heading_depth",
        "external_link_count", "avg_paragraph_length", "faq_schema",
        "local_business_schema",
    ]
    for k in highlight:
        v = mf.get(k, "—")
        feat_rows.append([k.replace("_", " ").title(), str(round(v, 4) if isinstance(v, float) else v)])

    ft = Table(feat_rows, colWidths=[8*cm, 8*cm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), PRIMARY),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [LIGHT, colors.white]),
        ("GRID",        (0,0), (-1,-1), 0.3, GRAY),
        ("TOPPADDING",  (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(ft)
    story.append(Spacer(1, 12))

    # ── Recommendations ───────────────────────────────────────
    story.append(Paragraph("Recommendations", s["h1"]))
    for i, rec in enumerate(recs[:10], 1):
        if not isinstance(rec, dict):
            continue
        priority    = escape(str(rec.get("priority", "unspecified")).upper())
        title       = escape(str(rec.get("title", "")))
        description = escape(str(rec.get("description", "")))
        story.append(Paragraph(
            f"{i}. <b>[{priority}]</b> {title}", s["h2"]
        ))
        story.append(Paragraph(description, s["body"]))

    story.append(Spacer(1, 16))

    # ── Disclaimer ────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Paragraph(
        "This report was generated by Citelytics — a research prototype by "
        "Stephin Arnold (github.com/stephinarnold) for the study of "
        "Citation Likelihood Prediction in Generative Answer Engines. "
        "The system uses an XGBoost model trained on a synthetic demo dataset. "
        "Predictions should be interpreted as estimates, not guarantees. "
        "The model does not simulate or access any actual AI answer engine.",
        s["small"],
    ))

    doc.build(story)
    return buf.getvalue()
