"""
Citelytics — Citation Likelihood Prediction in Generative Answer Engines
Explainable ML Approach for Local Business Content
Author: Stephin Arnold
"""

import logging
import os
import sys
import time
import json
from datetime import datetime

import streamlit as st
import pandas as pd
import altair as alt

logger = logging.getLogger(__name__)

# Ensure local backend modules can be imported
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(CURRENT_DIR, "citation-predictor", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from scraping.scraper import scrape, ScrapingError
from features.extractor import extract_features
from models.model_loader import get_model, FEATURE_COLUMNS
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg: #FFFFFF;
        --muted: #F4F4F5;
        --muted-foreground: #71717A;
        --border: #E4E4E7;
        --foreground: #18181B;
        --primary: #18181B;
        --primary-foreground: #FAFAFA;
        --accent: #2563EB;
        --success: #16A34A;
        --success-bg: #F0FDF4;
        --warning: #B45309;
        --warning-bg: #FFFBEB;
        --danger: #DC2626;
        --danger-bg: #FEF2F2;
        --radius: 8px;
    }

    html, body, [class*="css"] { font-family: 'Inter', -apple-system, sans-serif; color: var(--foreground); }
    .stApp { background: var(--bg); }

    header[data-testid="stHeader"] { background: transparent; }

    .block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 900px; }

    /* ---- Card subheadings: Streamlit's default st.subheader is sized
       for a full page section, not a small card title — scale it down. */
    div[data-testid="stVerticalBlockBorderWrapper"] h3 {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }

    /* ---- st.metric: the default truncates long text values with an
       ellipsis (it's built for short numbers). We show text like "not
       yet measured" in some metrics, so let it wrap instead of cutting
       off. ---- */
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
        font-size: 1.3rem !important;
        line-height: 1.3 !important;
    }

    /* ---- Topbar ---- */
    .topbar {
        display: flex; align-items: center;
        padding: 0 0 1rem 0; margin-bottom: 1.75rem;
        border-bottom: 1px solid var(--border);
    }
    .topbar-left { display: flex; align-items: center; gap: 0.5rem; }
    .brand-text { font-weight: 600; font-size: 0.95rem; color: var(--foreground); }
    .crumb { color: var(--muted-foreground); font-size: 0.9rem; }

    /* ---- Page header ---- */
    .page-badge {
        display: inline-block; background: var(--muted); color: var(--muted-foreground);
        font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.6rem;
        border-radius: 9999px; border: 1px solid var(--border); margin-bottom: 0.75rem;
    }
    .page-title {
        font-size: 1.6rem; font-weight: 600; color: var(--foreground);
        margin: 0 0 0.4rem 0; letter-spacing: -0.02em; line-height: 1.3;
    }
    .page-sub { color: var(--muted-foreground); font-size: 0.92rem; margin: 0 0 1.5rem 0; max-width: 620px; line-height: 1.55; }

    /* ---- Sidebar nav ---- */
    section[data-testid="stSidebar"] {
        background: var(--muted);
        border-right: 1px solid var(--border);
    }
    .sidebar-brand { margin-bottom: 1.5rem; font-weight: 600; font-size: 0.95rem; }
    .st-key-nav div[role="radiogroup"] { gap: 0.1rem; }
    .st-key-nav div[role="radiogroup"] label {
        background: transparent;
        border: 1px solid transparent;
        border-radius: var(--radius);
        padding: 0.4rem 0.65rem !important;
        transition: background 0.1s ease;
        width: 100%;
        font-size: 0.9rem;
    }
    .st-key-nav div[role="radiogroup"] label:hover { background: rgba(0,0,0,0.04); }
    .st-key-nav div[role="radiogroup"] label[data-checked="true"] {
        background: var(--bg);
        border-color: var(--border);
    }
    .sidebar-footer {
        border-top: 1px solid var(--border);
        padding-top: 0.85rem;
        margin-top: 0.5rem;
        color: var(--muted-foreground);
        font-size: 0.76rem;
        line-height: 1.7;
    }
    .sidebar-footer a { color: var(--muted-foreground); }

    /* ---- Bordered containers (st.container(border=True)) as real cards ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: var(--radius) !important;
        border-color: var(--border) !important;
        background: var(--bg);
    }

    /* ---- Inputs ---- */
    div[data-testid="stTextInput"] input, div[data-baseweb="select"] > div {
        border-color: var(--border) !important;
        border-radius: var(--radius) !important;
        background: var(--bg) !important;
    }

    /* ---- KPI tiles ---- */
    .kpi-label { color: var(--muted-foreground); font-size: 0.72rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.04em; }
    .kpi-value { font-size: 1.55rem; font-weight: 600; color: var(--foreground); margin-top: 0.3rem; line-height: 1.1; }
    .kpi-sub { color: var(--muted-foreground); font-size: 0.74rem; margin-top: 0.3rem; }

    /* ---- Verdict / probability badges ---- */
    .prob-badge-high, .prob-badge-med, .prob-badge-low {
        display: inline-block; padding: 0.3rem 0.75rem; border-radius: 9999px; font-weight: 500; font-size: 0.85rem;
    }
    .prob-badge-high { background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }
    .prob-badge-med  { background: var(--warning-bg); color: var(--warning); border: 1px solid var(--warning); }
    .prob-badge-low  { background: var(--danger-bg);  color: var(--danger);  border: 1px solid var(--danger); }

    /* ---- Recommendation cards ---- */
    .rec-card {
        padding: 0.9rem 1.1rem;
        border-radius: var(--radius);
        margin-bottom: 0.6rem;
        border: 1px solid var(--border);
        border-left: 3px solid;
        background: var(--bg);
    }
    .rec-high   { border-left-color: var(--danger); }
    .rec-medium { border-left-color: var(--warning); }
    .rec-low    { border-left-color: var(--accent); }

    /* ---- Buttons ---- */
    .stButton > button {
        border-radius: var(--radius);
        font-weight: 500;
    }
    .stButton > button[kind="primary"] {
        background: var(--primary);
        color: var(--primary-foreground);
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: #27272A;
    }
</style>
""", unsafe_allow_html=True)


def render_topbar(crumb: str):
    st.markdown(f"""
    <div class="topbar">
        <div class="topbar-left">
            <span class="brand-text">Citelytics</span>
            <span class="crumb">/ {crumb}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_header(badge: str, title: str, subtitle: str = ""):
    st.markdown(f"""
    <div class="page-badge">{badge}</div>
    <div class="page-title">{title}</div>
    {f'<div class="page-sub">{subtitle}</div>' if subtitle else ''}
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
    model, _ = get_model()
    return model

try:
    init_system()
except Exception as e:
    st.error(f"Error loading model: {e}")
    st.stop()

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
# Shared tier thresholds — a single source of truth so the label, the badge,
# and the KPI tile can never drift out of sync with each other.
TIER_HIGH_THRESHOLD = 61
TIER_MED_THRESHOLD = 31


def get_tier_name(prob: float) -> str:
    """Return the tier name ("High" / "Moderate" / "Low") for a probability.

    Rounds to the nearest whole percent (matching every displayed score)
    before comparing against the tier thresholds, so a probability that
    displays as e.g. 61% is always classified consistently with what the
    user sees on screen.
    """
    score = round(prob * 100)
    if score >= TIER_HIGH_THRESHOLD:
        return "High"
    if score >= TIER_MED_THRESHOLD:
        return "Moderate"
    return "Low"


def get_label(prob: float) -> str:
    tier = get_tier_name(prob)
    if tier == "High":
        return "Likely to be Cited"
    if tier == "Moderate":
        return "Moderately Likely to be Cited"
    return "Less Likely to be Cited"

def get_tier_badge(prob: float) -> str:
    score = round(prob * 100)
    tier = get_tier_name(prob)
    if tier == "High":
        return f'<span class="prob-badge-high">High Likelihood ({score}%)</span>'
    if tier == "Moderate":
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
    """,
    "https://sample-italian-bistro.example.com": """
    <!DOCTYPE html><html><head><title>Luigi's Trattoria - Authentic Italian Restaurant</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Restaurant","name":"Luigi's Trattoria",
     "telephone":"+1-555-312-7788","openingHours":"Tu-Su 11:00-22:00",
     "address":{"@type":"PostalAddress","streetAddress":"48 Elm Street","addressLocality":"Portland","addressRegion":"OR","postalCode":"97201"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.7","reviewCount":"512"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"Do you take reservations?","acceptedAnswer":{"@type":"Answer","text":"Yes, reservations are recommended on weekends and can be made by phone or online."}},
      {"@type":"Question","name":"Is there outdoor seating?","acceptedAnswer":{"@type":"Answer","text":"Yes, we have a heated patio open year-round with seating for 30 guests."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/menu">Menu</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Luigi's Trattoria - Family-Owned Italian Dining in Portland, OR</h1>
      <p>Luigi's Trattoria has served handmade pasta and wood-fired pizza since 1998. Our dining room seats 80 guests and our chefs import ingredients directly from Italy.</p>
      <h2>Our Menu</h2>
      <p>From classic Bolognese to seasonal risottos, every dish is prepared fresh daily using recipes passed down three generations.</p>
      <h3>Pricing & Hours</h3>
      <table>
        <tr><th>Item</th><th>Course</th><th>Price</th></tr>
        <tr><td>Spaghetti Carbonara</td><td>Entree</td><td>$18</td></tr>
        <tr><td>Margherita Pizza</td><td>Entree</td><td>$16</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Private events:</strong> Our back room can be reserved for parties of up to 40.</li>
        <li><strong>Gluten-free:</strong> Gluten-free pasta is available on request.</li>
      </ul>
      <h2>Contact & Operating Hours</h2>
      <p>Call us at <strong>(555) 312-7788</strong> or visit us at 48 Elm Street, Portland, OR 97201.</p>
      <p>Hours: Tuesday to Sunday, 11:00 AM - 10:00 PM. Closed Mondays.</p>
    </main></body></html>
    """,
    "https://sample-cloud-tech.example.com": """
    <!DOCTYPE html><html><head><title>Apex Cloud Solutions - B2B Cloud Infrastructure Platform</title>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Organization","name":"Apex Cloud Solutions",
     "telephone":"+1-555-998-4420",
     "address":{"@type":"PostalAddress","streetAddress":"900 Market Ave","addressLocality":"Denver","addressRegion":"CO","postalCode":"80202"},
     "aggregateRating":{"@type":"AggregateRating","ratingValue":"4.6","reviewCount":"128"}}
    </script>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
      {"@type":"Question","name":"What is the pricing model?","acceptedAnswer":{"@type":"Answer","text":"Plans are priced per active workload per month, starting at $499/month for teams of up to 10."}},
      {"@type":"Question","name":"Do you offer a free trial?","acceptedAnswer":{"@type":"Answer","text":"Yes, a 14-day free trial is available with no credit card required."}}
    ]}
    </script>
    </head><body>
    <header><nav><a href="/">Home</a> | <a href="/pricing">Pricing</a> | <a href="/contact">Contact</a></nav></header>
    <main>
      <h1>Apex Cloud Solutions - Enterprise-Grade Infrastructure for Growing Teams</h1>
      <p>Apex Cloud Solutions provides managed Kubernetes orchestration and CI/CD pipelines trusted by over 1,200 engineering teams worldwide, with a 99.98% uptime SLA.</p>
      <h2>Platform Capabilities</h2>
      <p>Our platform automates deployment, scaling, and observability across multi-cloud environments with built-in SOC 2 compliance.</p>
      <h3>Plans & Pricing</h3>
      <table>
        <tr><th>Plan</th><th>Workloads</th><th>Monthly Price</th></tr>
        <tr><td>Starter</td><td>Up to 10</td><td>$499</td></tr>
        <tr><td>Growth</td><td>Up to 50</td><td>$1,999</td></tr>
      </table>
      <h2>Frequently Asked Questions</h2>
      <ul>
        <li><strong>Onboarding:</strong> Dedicated solutions engineers assist with migration within the first 30 days.</li>
        <li><strong>Support:</strong> 24/7 support is included on all paid plans.</li>
      </ul>
      <h2>Contact</h2>
      <p>Call us at <strong>(555) 998-4420</strong> or visit our headquarters at 900 Market Ave, Denver, CO 80202.</p>
    </main></body></html>
    """
}

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <span class="brand-text" style="font-size:1.2rem;">Citelytics</span>
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
        Stephin Arnold &middot; CSD 415
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE 1: ANALYZE WEBPAGE
# ─────────────────────────────────────────────────────────────
if nav_choice == "Analyze":
    render_topbar("Analyze")
    page_header(
        "GEO / AEO",
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
        shap_error = None
        try:
            shap_data = explain(model, feat_cols, mf)
        except Exception as e:
            logger.warning("SHAP explanation failed for %s: %s", target_url, e)
            shap_error = str(e)
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
        score_pct = round(prob * 100)

        # Main Score Header
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        delta_sign = "+" if score_pct >= 50 else ""
        with kpi_col1:
            kpi_tile("Citation probability", f"{score_pct}%", f"{delta_sign}{score_pct - 50}% vs. 50% baseline")
        with kpi_col2:
            kpi_tile("Citation tier", f"{get_tier_name(prob)} likelihood")
        with kpi_col3:
            macro_val = float(features.get("derived", {}).get("macro_score", mf.get("macro_structure_score", 0.5)))
            macro_s = round(macro_val * 100)
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
            if shap_error:
                st.warning(
                    f"The SHAP explainer could not compute feature contributions for this page ({shap_error}). "
                    "The sections below are empty because the explanation failed, not because this page has no strong drivers."
                )
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
                st.caption(f"Score: {round(macro_val * 100)}%")
                st.write(f"- **Word count:** {features['content']['word_count']}")
                st.write(f"- **Total headings:** {features['structure']['heading_count']}")
                st.write(f"- **H1 headings:** {features['structure']['h1_count']}")
                st.write(f"- **Heading hierarchy score:** {features['structure']['heading_hierarchy_score']:.2f}")

            with c2, st.container(border=True):
                st.markdown("#### Meso-structure")
                st.progress(meso_val)
                st.caption(f"Score: {round(meso_val * 100)}%")
                st.write(f"- **Paragraphs:** {features['content']['paragraph_count']}")
                st.write(f"- **Lists:** {features['content']['list_count']}")
                st.write(f"- **Tables:** {features['content']['table_count']}")
                st.write(f"- **Avg paragraph length:** {features['content']['avg_paragraph_length']:.1f} words")

            with c3, st.container(border=True):
                st.markdown("#### Micro-structure & signals")
                st.progress(micro_val)
                st.caption(f"Score: {round(micro_val * 100)}%")
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

