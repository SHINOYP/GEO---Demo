"""
Citelytics — Citation Likelihood Prediction in Generative Answer Engines
Explainable ML Approach for Local Business Content
Author: Stephin Arnold
GitHub: https://github.com/StephinArnold/GEO---Demo
"""

import os
import sys
import time
import io
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Ensure local backend modules can be imported
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "citation-predictor", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from scraping.scraper import scrape, ScrapingError
from features.extractor import extract_features
from models.model_loader import get_model, FEATURE_COLUMNS, load_or_train_model
from explainability.shap_explainer import explain
from services.recommendations import generate_recommendations
from services.pdf_report import generate_pdf

# ─────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Citelytics — AI Citation Predictor",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# DESIGN SYSTEM
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --c-bg: #0B1120;
        --c-surface: #131B2E;
        --c-surface-2: #1B2538;
        --c-border: rgba(255,255,255,0.08);
        --c-text: #E2E8F0;
        --c-text-muted: #94A3B8;
        --c-primary: #6366F1;
        --c-primary-dark: #4338CA;
        --c-success: #10B981;
        --c-warning: #F59E0B;
        --c-danger: #EF4444;
        --radius-lg: 18px;
        --radius-md: 12px;
    }

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* tighten default top padding so our topbar sits flush */
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1100px; }

    /* ---- Topbar (shown on every page) ---- */
    .topbar {
        display: flex; align-items: center; gap: 0.5rem;
        padding: 0.2rem 0 1.3rem 0; margin-bottom: 1.4rem;
        border-bottom: 1px solid var(--c-border);
    }
    .brand-mark {
        width: 28px; height: 28px; border-radius: 7px; display: flex;
        align-items: center; justify-content: center; font-size: 0.85rem;
        font-weight: 800; color: white; background: var(--c-primary);
    }
    .brand-text { font-weight: 700; font-size: 0.95rem; color: var(--c-text); letter-spacing: -0.01em; }
    .crumb { color: var(--c-text-muted); font-size: 0.9rem; }

    /* ---- Page header (flat, no box) ---- */
    .page-eyebrow {
        color: var(--c-text-muted); font-size: 0.78rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.3rem;
    }
    .page-title { font-size: 1.8rem; font-weight: 800; color: var(--c-text); margin: 0 0 0.4rem 0; letter-spacing: -0.01em; }
    .page-sub { color: var(--c-text-muted); font-size: 0.95rem; margin: 0 0 1.4rem 0; max-width: 640px; }

    /* ---- Sidebar nav ---- */
    section[data-testid="stSidebar"] {
        background: var(--c-surface);
        border-right: 1px solid var(--c-border);
    }
    .sidebar-brand { display: flex; align-items: center; gap: 0.55rem; margin-bottom: 1.4rem; }
    .st-key-nav div[role="radiogroup"] { gap: 0.2rem; }
    .st-key-nav div[role="radiogroup"] label {
        background: transparent;
        border: 1px solid transparent;
        border-radius: var(--radius-md);
        padding: 0.5rem 0.75rem !important;
        transition: background 0.15s ease, border-color 0.15s ease;
        width: 100%;
    }
    .st-key-nav div[role="radiogroup"] label:hover {
        background: var(--c-surface-2);
        border-color: var(--c-border);
    }
    .st-key-nav div[role="radiogroup"] label[data-checked="true"] {
        background: rgba(99,102,241,0.14);
        border-color: rgba(99,102,241,0.4);
    }
    .sidebar-footer {
        border-top: 1px solid var(--c-border);
        padding-top: 0.9rem;
        margin-top: 0.5rem;
        color: var(--c-text-muted);
        font-size: 0.78rem;
        line-height: 1.6;
    }

    /* ---- Bordered containers (st.container(border=True)) as real cards ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius-lg) !important;
        border-color: var(--c-border) !important;
        background: var(--c-surface);
    }

    /* ---- KPI tiles ---- */
    .kpi-label { color: var(--c-text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
    .kpi-value { font-size: 1.8rem; font-weight: 800; color: var(--c-text); margin-top: 0.2rem; line-height: 1.1; }
    .kpi-sub { color: var(--c-text-muted); font-size: 0.76rem; margin-top: 0.25rem; }

    /* ---- Verdict / probability badges ---- */
    .prob-badge-high, .prob-badge-med, .prob-badge-low {
        display: inline-block; padding: 0.45rem 1rem; border-radius: var(--radius-md); font-weight: 700; font-size: 0.95rem;
    }
    .prob-badge-high { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .prob-badge-med  { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .prob-badge-low  { background: rgba(239, 68, 68, 0.15);  color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }

    /* ---- Recommendation cards ---- */
    .rec-card {
        padding: 1rem 1.2rem;
        border-radius: var(--radius-md);
        margin-bottom: 0.75rem;
        border-left: 4px solid;
        background: var(--c-surface-2);
    }
    .rec-high   { border-left-color: var(--c-danger); }
    .rec-medium { border-left-color: var(--c-warning); }
    .rec-low    { border-left-color: #3B82F6; }

    /* ---- Footer ---- */
    .app-footer {
        margin-top: 2.5rem; padding-top: 1.2rem; border-top: 1px solid var(--c-border);
        color: var(--c-text-muted); font-size: 0.78rem;
    }
    .app-footer a { color: var(--c-text-muted); }

    /* ---- Buttons ---- */
    .stButton > button {
        border-radius: var(--radius-md);
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def render_topbar(crumb: str):
    st.markdown(f"""
    <div class="topbar">
        <div class="brand-mark">C</div>
        <span class="brand-text">Citelytics</span>
        <span class="crumb">/ {crumb}</span>
    </div>
    """, unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-eyebrow">{eyebrow}</div>
    <div class="page-title">{title}</div>
    {f'<div class="page-sub">{subtitle}</div>' if subtitle else ''}
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div class="app-footer">
        <a href="https://github.com/StephinArnold/GEO---Demo">Source on GitHub</a>
    </div>
    """, unsafe_allow_html=True)


def kpi_tile(label: str, value: str, sub: str = ""):
    with st.container(border=True):
        st.markdown(f"""
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LOAD MODEL & INITIALIZE
# ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Initializing XGBoost Citation Model...")
def init_system():
    model = load_or_train_model()
    return model

try:
    init_system()
except Exception as e:
    st.error(f"Error loading model: {e}")

ARTIFACTS_DIR = os.path.join(CURRENT_DIR, "artifacts")
DATA_DIR = os.path.join(CURRENT_DIR, "data")


def load_json_or_none(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_metrics():
    """Read real evaluation metrics from artifacts/metrics.json.

    Returns None if the file doesn't exist yet (e.g. the real-data pilot
    pipeline hasn't been run), so the UI can show "not yet evaluated"
    instead of a fabricated number.
    """
    return load_json_or_none(os.path.join(ARTIFACTS_DIR, "metrics.json"))


def load_pilot_stats():
    return load_json_or_none(os.path.join(DATA_DIR, "pilot_stats.json"))

# Helper interpret functions
def get_label(prob: float) -> str:
    score = int(prob * 100)
    if score >= 61:
        return "Likely to be Cited"
    if score >= 31:
        return "Moderately Likely to be Cited"
    return "Less Likely to be Cited"

def get_tier_badge(prob: float) -> str:
    score = int(prob * 100)
    if score >= 61:
        return f'<span class="prob-badge-high">High Likelihood ({score}%)</span>'
    if score >= 31:
        return f'<span class="prob-badge-med">Moderate Likelihood ({score}%)</span>'
    return f'<span class="prob-badge-low">Low Likelihood ({score}%)</span>'

# Mock Fallbacks for testing demo pages
SAMPLE_PRESETS = {
    "Select a sample page...": "",
    "Apex Dental Clinic (high-quality local business)": "https://sample-dental-clinic.example.com",
    "Luigi's Trattoria (Italian restaurant)": "https://sample-italian-bistro.example.com",
    "Apex Cloud Solutions (B2B SaaS)": "https://sample-cloud-tech.example.com",
    "Thin Local Contractor Blog (low optimization)": "https://sample-basic-contractor.example.com"
}

SAMPLE_HTML_FIXTURES = {
    "https://sample-dental-clinic.example.com": """
    <!DOCTYPE html><html><head><title>Apex Dental Clinic - Advanced Cosmetic & Family Dentistry</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Dentist","name":"Apex Dental Clinic",
     "telephone":"+1-555-234-5678","openingHours":"Mo-Fr 08:00-18:00",
     "address":{"@type":"PostalAddress","streetAddress":"123 Main St","addressLocality":"Austin","addressRegion":"TX","postalCode":"78701"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.9","reviewCount":"340"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"How much does teeth whitening cost?","acceptedAnswer":{"@type":"Answer","text":"Professional in-office whitening starts at $350."}},
      {"@type":"Question","name":"Do you accept dental insurance?","acceptedAnswer":{"@type":"Answer","text":"We accept all major PPO insurance plans including Delta Dental and Cigna."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/services">Services</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Apex Dental Clinic - Expert Oral Care in Austin, TX</h1>
      <p>Apex Dental Clinic provides comprehensive dental care with over 15 years of clinical experience. Our clinic has treated over 12,000 patients with a 98% satisfaction rate.</p>
      <h2>Comprehensive Dental Services</h2>
      <p>From routine cleanings to restorative implants, our board-certified dentists use state-of-the-art 3D imaging.</p>
      <h3>Pricing & Treatment Timeline</h3>
      <table>
        <tr><th>Treatment</th><th>Duration</th><th>Average Cost</th></tr>
        <tr><td>Checkup & Cleaning</td><td>45 minutes</td><td>$120</td></tr>
        <tr><td>Dental Implants</td><td>2 visits</td><td>$1,800</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Emergency visits:</strong> Same-day emergency appointments are available daily.</li>
        <li><strong>Financing:</strong> 0% APR financing is available via CareCredit.</li>
      </ul>
      <h2>Contact & Operating Hours</h2>
      <p>Call us at <strong>(555) 234-5678</strong> or visit our office at 123 Main St, Austin, TX 78701.</p>
      <p>Hours: Monday to Friday, 8:00 AM - 6:00 PM; Saturday 9:00 AM - 2:00 PM.</p>
    </main></body></html>
    """,
    "https://sample-basic-contractor.example.com": """
    <!DOCTYPE html><html><head><title>Best Handyman Services</title></head><body>
    <h1>Welcome to our Handyman Website</h1>
    <p>We do great work. Call us today for the best prices in town. We do painting, plumbing, and fixing things around your house.</p>
    <p>No job is too big or too small! Contact us today.</p>
    </body></html>
    """
}

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-mark" style="width:30px;height:30px;font-size:0.95rem;">C</div>
        <span class="brand-text" style="font-size:1.1rem;">Citelytics</span>
    </div>
    """, unsafe_allow_html=True)

    with st.container(key="nav"):
        nav_choice = st.radio(
            "Navigation",
            [
                "Analyze",
                "Explainability",
                "Model Card",
            ],
            index=0,
            label_visibility="collapsed",
        )

    st.markdown("""
    <div class="sidebar-footer">
        Stephin Arnold &middot; CSD 415<br/>
        <a href="https://github.com/StephinArnold/GEO---Demo">GitHub</a>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE 1: ANALYZE WEBPAGE
# ─────────────────────────────────────────────────────────────
if nav_choice == "Analyze":
    render_topbar("Analyze")
    page_header(
        "Explainable GEO / AEO intelligence",
        "Citation likelihood prediction",
        "Predict how likely a webpage is to be cited by generative AI answer engines (Perplexity, ChatGPT Search, Claude).",
    )

    with st.container(border=True):
        col_input, col_preset = st.columns([3, 2])
        with col_preset:
            preset_choice = st.selectbox("Try a sample page", list(SAMPLE_PRESETS.keys()))
            selected_preset_url = SAMPLE_PRESETS[preset_choice]

        with col_input:
            default_url = selected_preset_url if selected_preset_url else "https://en.wikipedia.org/wiki/Artificial_intelligence"
            input_url = st.text_input("Webpage URL", value=default_url, placeholder="https://example.com/page")

        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)
        st.caption("Estimated likelihood from observed correlations, not a guarantee. See Model Card for details.")

    if analyze_btn and input_url:
        target_url = input_url.strip()
        progress_bar = st.progress(10, text="Scraping webpage content...")

        # 1. Scraping / Fetching
        # A fixture is only ever used when the user explicitly picked it from
        # the "Quick-load Demo Example" dropdown above. A live scrape failure
        # is reported as an error, never silently replaced by fixture data —
        # swapping in someone else's page and still showing a confident score
        # would be misleading.
        soup = None
        mock_used = target_url in SAMPLE_HTML_FIXTURES and target_url == selected_preset_url
        if mock_used:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(SAMPLE_HTML_FIXTURES[target_url], "html.parser")
        else:
            try:
                scrape_res = scrape(target_url)
                soup = scrape_res["soup"]
            except ScrapingError as e:
                progress_bar.empty()
                st.error(f"Could not analyze this page: {e}")
                st.stop()
            except Exception as e:
                progress_bar.empty()
                st.error(f"Could not analyze this page: {type(e).__name__}: {e}")
                st.stop()

        progress_bar.progress(40, text="Extracting 45+ content, structural, and schema features...")
        features = extract_features(soup, target_url)
        mf = features["model_features"]

        progress_bar.progress(70, text="Running XGBoost Classifier & SHAP TreeExplainer...")
        model, feat_cols = get_model()
        row = pd.DataFrame([{col: mf.get(col, 0) for col in feat_cols}])
        prob = float(model.predict_proba(row)[0, 1])

        # SHAP calculation
        try:
            shap_data = explain(model, feat_cols, mf)
        except Exception as e:
            shap_data = {"shap_values": {}, "top_positive": [], "top_negative": [], "base_value": 0.5}

        # Recommendations
        recommendations = generate_recommendations(features, shap_data)

        # PDF Preparation
        full_analysis = {
            "url": target_url,
            "created_at": datetime.now().isoformat(),
            "prob": prob,
            "tier": get_label(prob),
            "features": features,
            "shap": shap_data,
            "recommendations": recommendations,
        }

        progress_bar.progress(100, text="Analysis Complete!")
        time.sleep(0.3)
        progress_bar.empty()

        # ── RESULTS DASHBOARD ──
        st.markdown("---")
        if mock_used:
            st.warning("**Demo fixture** — this result is for a hand-written sample page, not a live fetch of a real URL.")
        st.caption("Estimated likelihood from observed correlations, not a guarantee.")
        score_pct = int(prob * 100)

        # Main Score Header
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        delta_sign = "+" if score_pct >= 50 else ""
        with kpi_col1:
            kpi_tile("Citation probability", f"{score_pct}%", f"{delta_sign}{score_pct - 50}% vs. 50% baseline")
        with kpi_col2:
            kpi_tile("Citation tier", get_label(prob).split()[0] + " likelihood")
        with kpi_col3:
            macro_val = float(features.get("derived", {}).get("macro_score", mf.get("macro_structure_score", 0.5)))
            macro_s = int(macro_val * 100)
            kpi_tile("Structural quality", f"{macro_s}/100")
        with kpi_col4:
            has_schema = "Active (JSON-LD)" if features["schema"]["schema_present"] else "Missing"
            kpi_tile("Schema markup", has_schema)

        st.markdown(f"**Verdict:** {get_tier_badge(prob)}", unsafe_allow_html=True)
        st.markdown("")

        # ── TABS FOR DEEP-DIVE ──
        tab_shap, tab_struct, tab_recs, tab_pdf = st.tabs([
            "Why this score",
            "Structure",
            "Recommendations",
            "Export PDF",
        ])

        # TAB 1: SHAP
        with tab_shap:
            st.subheader("Feature impact (SHAP)")
            st.write(
                "Why did this page receive this score? SHAP calculates the exact marginal contribution of each webpage feature "
                "towards pushing the citation probability **higher** (green) or **lower** (red)."
            )

            # Prepare SHAP chart
            top_pos = shap_data.get("top_positive", [])[:6]
            top_neg = shap_data.get("top_negative", [])[:6]
            all_top = top_pos + top_neg

            if all_top:
                chart_data = []
                for item in all_top:
                    feat_name = item["feature"].replace("_", " ").title()
                    chart_data.append({
                        "Feature": feat_name,
                        "SHAP Impact": item["shap_value"],
                        "Type": "Positive (Boosts Citation)" if item["shap_value"] > 0 else "Negative (Hampers Citation)",
                        "Measured Value": item["value"]
                    })
                df_chart = pd.DataFrame(chart_data)

                chart = alt.Chart(df_chart).mark_bar().encode(
                    x=alt.X('SHAP Impact:Q', title="SHAP Value (Contribution to Log-Odds)"),
                    y=alt.Y('Feature:N', sort='-x', title="Webpage Feature"),
                    color=alt.Color('Type:N', scale=alt.Scale(
                        domain=['Positive (Boosts Citation)', 'Negative (Hampers Citation)'],
                        range=['#10B981', '#EF4444']
                    )),
                    tooltip=['Feature', 'SHAP Impact', 'Measured Value', 'Type']
                ).properties(height=340)

                st.altair_chart(chart, use_container_width=True)

            col_sp1, col_sp2 = st.columns(2)
            with col_sp1:
                st.markdown("##### Positive drivers")
                if top_pos:
                    for p in top_pos:
                        st.success(f"**{p['feature']}** = `{p['value']}` (SHAP +{p['shap_value']:.4f})")
                else:
                    st.info("No strong positive drivers detected.")

            with col_sp2:
                st.markdown("##### Negative drivers")
                if top_neg:
                    for n in top_neg:
                        st.error(f"**{n['feature']}** = `{n['value']}` (SHAP {n['shap_value']:.4f})")
                else:
                    st.info("No major negative dragging factors detected.")

        # TAB 2: STRUCTURE BREAKDOWN
        with tab_struct:
            st.subheader("Webpage quality metrics")
            macro_val = min(max(float(features.get("derived", {}).get("macro_score", mf.get("macro_structure_score", 0.5))), 0.0), 1.0)
            meso_val = min(max(float(features.get("derived", {}).get("meso_score", mf.get("meso_structure_score", 0.5))), 0.0), 1.0)
            micro_val = min(max(float(features.get("derived", {}).get("micro_score", mf.get("micro_structure_score", 0.5))), 0.0), 1.0)
            c1, c2, c3 = st.columns(3)
            with c1, st.container(border=True):
                st.markdown("#### Macro-structure")
                st.progress(macro_val)
                st.caption(f"Score: {int(macro_val * 100)}%")
                st.write(f"- **Word count:** {features['content']['word_count']}")
                st.write(f"- **Total headings:** {features['structure']['heading_count']}")
                st.write(f"- **H1 headings:** {features['structure']['h1_count']}")
                st.write(f"- **Heading hierarchy score:** {features['structure']['heading_hierarchy_score']:.2f}")

            with c2, st.container(border=True):
                st.markdown("#### Meso-structure")
                st.progress(meso_val)
                st.caption(f"Score: {int(meso_val * 100)}%")
                st.write(f"- **Paragraphs:** {features['content']['paragraph_count']}")
                st.write(f"- **Lists:** {features['content']['list_count']}")
                st.write(f"- **Tables:** {features['content']['table_count']}")
                st.write(f"- **Avg paragraph length:** {features['content']['avg_paragraph_length']:.1f} words")

            with c3, st.container(border=True):
                st.markdown("#### Micro-structure & signals")
                st.progress(micro_val)
                st.caption(f"Score: {int(micro_val * 100)}%")
                st.write(f"- **Factual density:** {mf['factual_density']:.3f}")
                st.write(f"- **Numerical claims:** {features['content']['number_count']}")
                st.write(f"- **Phone detected:** {'Yes' if features['local_business']['has_phone'] else 'No'}")
                st.write(f"- **Address detected:** {'Yes' if features['local_business']['has_address'] else 'No'}")

        # TAB 3: RECOMMENDATIONS
        with tab_recs:
            st.subheader("Recommendations")
            if not recommendations:
                st.success("Great job! No urgent optimization steps found.")
            else:
                for rec in recommendations:
                    prio = rec.get("priority", "medium").lower()
                    css_class = f"rec-{prio}"
                    st.markdown(f"""
                    <div class="rec-card {css_class}">
                        <div style="font-weight: 700; font-size: 1.05rem;">
                            [{rec.get('priority', 'MED').upper()}] {rec.get('title')}
                        </div>
                        <div style="color: #94A3B8; font-size: 0.85rem; margin-top: 2px;">
                            Category: {rec.get('category')} • Potential Impact: {rec.get('impact', 'medium').capitalize()}
                        </div>
                        <div style="margin-top: 6px; font-size: 0.95rem;">
                            {rec.get('description')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # TAB 4: PDF REPORT
        with tab_pdf:
            st.subheader("Export PDF")
            st.write("A multi-page report including the SHAP feature explanations and recommendations.")
            try:
                pdf_bytes = generate_pdf(full_analysis)
                st.download_button(
                    label="Download PDF report",
                    data=pdf_bytes,
                    file_name=f"citelytics_report_{int(time.time())}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Could not generate PDF: {e}")

    render_footer()

# ─────────────────────────────────────────────────────────────
# PAGE 2: MODEL ARCHITECTURE & XAI
# ─────────────────────────────────────────────────────────────
elif nav_choice == "Explainability":
    render_topbar("Explainability")
    page_header("How it works", "Model architecture & explainability")

    col1, col2 = st.columns([1, 1])

    with col1, st.container(border=True):
        st.subheader("SEO vs. GEO")
        st.info("""
        - **Traditional search (SEO):** ranks 10 blue links based on backlinks, keywords, and domain authority.
        - **Generative engines (GEO / AEO):** synthesize a direct answer and cite only 1–3 sources.
        - **Core hypothesis:** citation likelihood depends on factual density, structured schemas, hierarchical content, and local business verification signals.
        """)

        st.subheader("Pipeline")
        st.markdown("""
        1. **Ingestion:** SSRF-safe scraper extracts DOM structure, text, and metadata.
        2. **Feature engineering:** 45 numerical, categorical, and ratio features across macro, meso, and micro layers.
        3. **Classifier:** gradient-boosted trees (XGBoost) predict `P(cited=1)`.
        4. **Explainability:** SHAP decomposes the model's decision into per-feature contributions for each URL.
        """)

    with col2, st.container(border=True):
        st.subheader("Validation metrics")
        metrics = load_metrics()
        if metrics is None:
            st.warning(
                "**Not yet evaluated.** No `artifacts/metrics.json` was found. "
                "Run `python -m pipeline.evaluate` to produce real, reproducible "
                "metrics from the pilot dataset before any number is shown here."
            )
        else:
            if metrics.get("underpowered"):
                st.warning(
                    "The pilot dataset is marked **underpowered** — these "
                    "metrics are reported for transparency but should not be "
                    "read as strong evidence. See the Model Card page."
                )
            m_c1, m_c2 = st.columns(2)
            m_c1.metric("ROC-AUC", metrics.get("roc_auc_display", "not yet evaluated"))
            m_c2.metric("F1", metrics.get("f1_display", "not yet evaluated"))
            m_c3, m_c4 = st.columns(2)
            m_c3.metric("Accuracy", metrics.get("accuracy_display", "not yet evaluated"))
            m_c4.metric("Precision / Recall", metrics.get("precision_recall_display", "not yet evaluated"))
            st.caption(f"Source: artifacts/metrics.json (generated {metrics.get('generated_at', 'unknown date')})")

        st.subheader("Feature groups (45 total)")
        st.markdown("""
        - **Macro-structure:** heading depth, H1-H3 counts, hierarchy coherence, word count.
        - **Meso-structure:** paragraph counts, list frequency, tables, visual elements.
        - **Micro-structure:** factual density, numbers, statistics, percentages, dates, quotes.
        - **Schema:** LocalBusiness, Organization, FAQPage, Article, Review JSON-LD.
        - **Local authority:** contact phone, address, operating hours, review count.
        """)

    render_footer()

# ─────────────────────────────────────────────────────────────
# PAGE: MODEL CARD / LIMITATIONS
# ─────────────────────────────────────────────────────────────
elif nav_choice == "Model Card":
    render_topbar("Model Card")
    page_header("Transparency", "Model card & limitations", "Estimated likelihood from observed correlations, not a guarantee.")

    pilot_stats = load_pilot_stats()
    metrics = load_metrics()

    with st.container(border=True):
        st.subheader("Dataset")
        if pilot_stats is None:
            st.warning("**Not yet measured.** No `data/pilot_stats.json` found — the real-data pilot pipeline (`pipeline/run_all.py`) has not been run yet.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Queries", pilot_stats.get("num_queries", "not yet measured"))
            c2.metric("Usable rows", pilot_stats.get("usable_rows", "not yet measured"))
            c3.metric("Class balance (positive %)", pilot_stats.get("positive_rate_display", "not yet measured"))
            with st.expander("Raw pilot_stats.json"):
                st.json(pilot_stats, expanded=False)

    with st.container(border=True):
        st.subheader("How labels were made")
        st.markdown("""
        A page is labeled **1 (cited)** if its canonical URL (or domain, in a
        secondary analysis) appears among the citations returned by the
        Perplexity `sonar` API for a given local-business query; otherwise **0**.
        The candidate pool is the union of cited URLs and the top organic
        search results for that query. See `docs/DATA_CARD.md` for the full rule.
        """)

    with st.container(border=True):
        st.subheader("Cross-validated results (with uncertainty)")
        if metrics is None:
            st.warning("**Not yet evaluated.** Run `python -m pipeline.evaluate` to produce `artifacts/metrics.json`.")
        else:
            if metrics.get("underpowered"):
                st.error("This dataset is flagged **underpowered** for strong conclusions — treat all numbers below as preliminary.")
            with st.expander("Raw metrics.json"):
                st.json(metrics, expanded=False)

    with st.container(border=True):
        st.subheader("Baseline comparison")
        st.markdown("Compare against a simple rule-based GEO checklist baseline (schema present, FAQ present, etc.) — see `artifacts/metrics.json` → `models.rule_based` once evaluation has run.")

    with st.container(border=True):
        st.subheader("Known limitations")
        st.markdown("""
        - **Small sample size.** The pilot dataset covers a handful of query
          categories and cities; results may not generalize.
        - **Negatives are biased.** Non-cited pages are drawn only from pages
          that already rank organically for the query — true negatives from the
          wider web are not sampled, so the model may not generalize to
          completely unranked pages.
        - **Citation non-determinism.** Repeating the same query against the
          answer engine does not always return the same citations; a single
          observation per query is a noisy label.
        - **Correlational, not mechanistic.** This model learns which page
          features *co-occur* with citation in the pilot sample. It does not
          reveal how the underlying LLM actually decides what to cite, and SHAP
          explains *this classifier*, not the LLM.
        - **Engine behavior drifts over time.** Answer engines are updated
          frequently; this model would need periodic retraining on fresh data
          to stay relevant.
        """)

    render_footer()
