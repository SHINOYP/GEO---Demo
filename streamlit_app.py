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
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Theme adjustments & modern cards)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4338CA 100%);
        padding: 1.8rem 2.2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(49, 46, 129, 0.3);
    }
    .badge-pill {
        display: inline-block;
        background: rgba(255, 255, 255, 0.15);
        color: #E0E7FF;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }
    .metric-card {
        background: #0F172A;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .prob-badge-high {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }
    .prob-badge-med {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }
    .prob-badge-low {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 0.4rem 1rem;
        border-radius: 8px;
        font-weight: 700;
    }
    .rec-card {
        padding: 1rem 1.2rem;
        border-radius: 10px;
        margin-bottom: 0.75rem;
        border-left: 4px solid;
    }
    .rec-high {
        background: rgba(239, 68, 68, 0.08);
        border-left-color: #EF4444;
    }
    .rec-medium {
        background: rgba(245, 158, 11, 0.08);
        border-left-color: #F59E0B;
    }
    .rec-low {
        background: rgba(59, 130, 246, 0.08);
        border-left-color: #3B82F6;
    }
</style>
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
    "Select a pre-configured sample...": "",
    "🏥 Apex Dental Clinic (High Quality Local Business)": "https://sample-dental-clinic.example.com",
    "🍕 Luigi's Trattoria (Italian Restaurant)": "https://sample-italian-bistro.example.com",
    "💼 Apex Cloud Solutions (B2B SaaS / Services)": "https://sample-cloud-tech.example.com",
    "📝 Thin Local Contractor Blog (Low Optimization)": "https://sample-basic-contractor.example.com"
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
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=64)
    st.title("Citelytics")
    st.caption("AI Citation Likelihood Prediction System")
    st.markdown("---")

    nav_choice = st.radio(
        "Navigation",
        [
            "🔍 Analyze Webpage",
            "📈 Model Architecture & XAI",
            "📋 Model Card / Limitations",
            "🎓 College Project Overview",
        ],
        index=0
    )

    st.markdown("---")
    st.markdown("### 👤 Author Information")
    st.markdown("**Stephin Arnold**")
    st.markdown("College Final Year Capstone Project")
    st.markdown("[🔗 GitHub Repository](https://github.com/StephinArnold/GEO---Demo)")
    st.caption("XGBoost 2.0 • SHAP 0.45 • Streamlit Cloud")

# ─────────────────────────────────────────────────────────────
# PAGE 1: ANALYZE WEBPAGE
# ─────────────────────────────────────────────────────────────
if nav_choice == "🔍 Analyze Webpage":
    st.markdown("""
    <div class="main-header">
        <span class="badge-pill">Explainable GEO / AEO Intelligence</span>
        <h1 style="margin: 0; font-size: 2rem; font-weight: 800;">Citation Likelihood Prediction</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.85; font-size: 1rem;">
            Predict how likely a webpage is to be cited by Generative AI Answer Engines (Perplexity, ChatGPT Search, Claude).
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_input, col_preset = st.columns([3, 2])
    with col_preset:
        preset_choice = st.selectbox("Quick-load Demo Example:", list(SAMPLE_PRESETS.keys()))
        selected_preset_url = SAMPLE_PRESETS[preset_choice]

    with col_input:
        default_url = selected_preset_url if selected_preset_url else "https://en.wikipedia.org/wiki/Artificial_intelligence"
        input_url = st.text_input("Enter Target Webpage URL:", value=default_url, placeholder="https://example.com/page")

    analyze_btn = st.button("⚡ Analyze Citation Likelihood", type="primary", use_container_width=True)
    st.caption("⚠️ Estimated likelihood from observed correlations, not a guarantee. See Model Card / Limitations for details.")

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
            st.warning("🧪 **DEMO FIXTURE** — this result is for a hand-written sample page, not a live fetch of a real URL.")
        st.caption("Estimated likelihood from observed correlations, not a guarantee.")
        score_pct = int(prob * 100)

        # Main Score Header
        kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
        with kpi_col1:
            st.metric(
                label="Citation Probability",
                value=f"{score_pct}%",
                delta=f"{'+' if score_pct >= 50 else ''}{score_pct - 50}% vs baseline",
                delta_color="normal" if score_pct >= 50 else "inverse"
            )
        with kpi_col2:
            st.metric(
                label="Citation Tier",
                value=get_label(prob).split()[0] + " Likelihood",
            )
        with kpi_col3:
            macro_val = float(features.get("derived", {}).get("macro_score", mf.get("macro_structure_score", 0.5)))
            macro_s = int(macro_val * 100)
            st.metric(label="Structural Quality", value=f"{macro_s}/100")
        with kpi_col4:
            has_schema = "Active (JSON-LD)" if features["schema"]["schema_present"] else "Missing"
            st.metric(label="Schema Markup", value=has_schema)

        st.markdown(f"**Predicted Verdict:** {get_tier_badge(prob)}", unsafe_allow_html=True)
        st.markdown("")

        # ── TABS FOR DEEP-DIVE ──
        tab_shap, tab_struct, tab_recs, tab_pdf = st.tabs([
            "🔍 Explainable AI (SHAP Impact)",
            "📐 Content & Structure Breakdown",
            "💡 Actionable Optimization Roadmap",
            "📄 Export Official PDF Report"
        ])

        # TAB 1: SHAP
        with tab_shap:
            st.subheader("Feature Impact on AI Citation (SHAP TreeExplainer)")
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
                st.markdown("##### 🟢 Top Positive Drivers (Strengths)")
                if top_pos:
                    for p in top_pos:
                        st.success(f"**{p['feature']}** = `{p['value']}` (SHAP +{p['shap_value']:.4f})")
                else:
                    st.info("No strong positive drivers detected.")

            with col_sp2:
                st.markdown("##### 🔴 Top Dragging Factors (Weaknesses)")
                if top_neg:
                    for n in top_neg:
                        st.error(f"**{n['feature']}** = `{n['value']}` (SHAP {n['shap_value']:.4f})")
                else:
                    st.info("No major negative dragging factors detected.")

        # TAB 2: STRUCTURE BREAKDOWN
        with tab_struct:
            st.subheader("Granular Webpage Quality Metrics")
            macro_val = min(max(float(features.get("derived", {}).get("macro_score", mf.get("macro_structure_score", 0.5))), 0.0), 1.0)
            meso_val = min(max(float(features.get("derived", {}).get("meso_score", mf.get("meso_structure_score", 0.5))), 0.0), 1.0)
            micro_val = min(max(float(features.get("derived", {}).get("micro_score", mf.get("micro_structure_score", 0.5))), 0.0), 1.0)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("#### 🏢 Macro-Structure")
                st.progress(macro_val)
                st.caption(f"Score: {int(macro_val * 100)}%")
                st.write(f"- **Word Count:** {features['content']['word_count']}")
                st.write(f"- **Total Headings:** {features['structure']['heading_count']}")
                st.write(f"- **H1 Headings:** {features['structure']['h1_count']}")
                st.write(f"- **Heading Hierarchy Score:** {features['structure']['heading_hierarchy_score']:.2f}")

            with c2:
                st.markdown("#### 📑 Meso-Structure")
                st.progress(meso_val)
                st.caption(f"Score: {int(meso_val * 100)}%")
                st.write(f"- **Paragraphs:** {features['content']['paragraph_count']}")
                st.write(f"- **Lists Count:** {features['content']['list_count']}")
                st.write(f"- **Tables Count:** {features['content']['table_count']}")
                st.write(f"- **Avg Paragraph Length:** {features['content']['avg_paragraph_length']:.1f} words")

            with c3:
                st.markdown("#### 🔬 Micro-Structure & Signals")
                st.progress(micro_val)
                st.caption(f"Score: {int(micro_val * 100)}%")
                st.write(f"- **Factual Density:** {features['content']['factual_density']:.3f}")
                st.write(f"- **Numerical Claims:** {features['content']['number_count']}")
                st.write(f"- **Phone Detected:** {'✅ Yes' if features['local_business']['has_phone'] else '❌ No'}")
                st.write(f"- **Address Detected:** {'✅ Yes' if features['local_business']['has_address'] else '❌ No'}")

        # TAB 3: RECOMMENDATIONS
        with tab_recs:
            st.subheader("Actionable Optimization Roadmap")
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
            st.subheader("Generate & Download Audit PDF")
            st.write("Export a clean, multi-page executive summary PDF report including all SHAP feature explanations and recommendations.")
            try:
                pdf_bytes = generate_pdf(full_analysis)
                st.download_button(
                    label="📥 Download Citelytics Audit PDF",
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
elif nav_choice == "📈 Model Architecture & XAI":
    st.title("Machine Learning Architecture & Explainability")
    st.markdown("How Citelytics models and explains Generative Answer Engine citations.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. The Research Shift: SEO vs. GEO")
        st.info("""
        - **Traditional Search (SEO):** Ranks 10 blue links based on backlinks, keywords, and domain authority.
        - **Generative Engines (GEO / AEO):** Synthesizes a direct synthesized paragraph answer and cites **only 1–3 definitive sources**.
        - **Core Hypothesis:** Citation likelihood depends strongly on **factual density, structured schemas, hierarchical content chunks, and local business verification signals**.
        """)

        st.subheader("2. Machine Learning Pipeline")
        st.markdown("""
        1. **Webpage Ingestion:** SSRF-safe scraper extracts DOM structure, text, and metadata.
        2. **Feature Engineering:** Extracts 45+ distinct numerical, categorical, and ratio features across Macro, Meso, and Micro layers.
        3. **XGBoost Binary Classifier:** Tuned gradient boosted trees predict `P(Cited=1)`.
        4. **SHAP TreeExplainer:** Deconstructs the model's non-linear decision tree paths to reveal individual feature contributions for each URL.
        """)

    with col2:
        st.subheader("3. Model Validation & Benchmark Metrics")
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
                    "⚠️ The pilot dataset is marked **underpowered** — these "
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

        st.subheader("4. Extracted Feature Dimensions (45 Total)")
        st.markdown("""
        - **Macro-Structure:** Heading depth, H1-H3 counts, hierarchy coherence, total word counts.
        - **Meso-Structure:** Paragraph counts, list frequency, data tables, visual elements.
        - **Micro-Structure:** Factual density, numbers, statistics, percentages, dates, quotes.
        - **Schema Markup:** LocalBusiness, Organization, FAQPage, Article, Review JSON-LD.
        - **Local Authority:** Contact phone, address, operating hours, review count.
        """)

# ─────────────────────────────────────────────────────────────
# PAGE: MODEL CARD / LIMITATIONS
# ─────────────────────────────────────────────────────────────
elif nav_choice == "📋 Model Card / Limitations":
    st.title("Model Card & Limitations")
    st.caption("Estimated likelihood from observed correlations, not a guarantee.")

    pilot_stats = load_pilot_stats()
    metrics = load_metrics()

    st.subheader("Dataset")
    if pilot_stats is None:
        st.warning("**Not yet measured.** No `data/pilot_stats.json` found — the real-data pilot pipeline (`pipeline/run_all.py`) has not been run yet.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Queries", pilot_stats.get("num_queries", "not yet measured"))
        c2.metric("Usable rows", pilot_stats.get("usable_rows", "not yet measured"))
        c3.metric("Class balance (positive %)", pilot_stats.get("positive_rate_display", "not yet measured"))
        st.json(pilot_stats, expanded=False)

    st.subheader("How labels were made")
    st.markdown("""
    A page is labeled **1 (cited)** if its canonical URL (or domain, in a
    secondary analysis) appears among the citations returned by the
    Perplexity `sonar` API for a given local-business query; otherwise **0**.
    The candidate pool is the union of cited URLs and the top organic
    search results for that query. See `docs/DATA_CARD.md` for the full rule.
    """)

    st.subheader("Cross-validated results (with uncertainty)")
    if metrics is None:
        st.warning("**Not yet evaluated.** Run `python -m pipeline.evaluate` to produce `artifacts/metrics.json`.")
    else:
        if metrics.get("underpowered"):
            st.error("This dataset is flagged **underpowered** for strong conclusions — treat all numbers below as preliminary.")
        st.json(metrics, expanded=False)

    st.subheader("Baseline comparison")
    st.markdown("Compare against a simple rule-based GEO checklist baseline (schema present, FAQ present, etc.) — see `artifacts/metrics.json` → `models.rule_based` once evaluation has run.")

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

# ─────────────────────────────────────────────────────────────
# PAGE 3: COLLEGE PROJECT OVERVIEW
# ─────────────────────────────────────────────────────────────
elif nav_choice == "🎓 College Project Overview":
    st.title("College Project Submission Details")
    st.markdown("### Citation Likelihood Prediction in Generative Answer Engines")
    st.caption("Explainable Machine Learning Approach for Local Business Content")

    st.markdown("""
    #### 📌 Project Summary
    - **Student / Author:** Stephin Arnold
    - **Focus Area:** Generative Engine Optimization (GEO), Artificial Intelligence, Applied Machine Learning, Explainable AI (XAI).
    - **Core Tech Stack:** Python, Streamlit, FastAPI, React, Vite, XGBoost, SHAP, BeautifulSoup4, ReportLab.

    #### 🎯 Key Contributions
    1. **Formulation of Citation Prediction as a Machine Learning Task:** Moved beyond generic SEO checklists into quantifiable probability scoring.
    2. **Multi-level Feature Engineering:** Developed 45+ domain-specific features capturing document hierarchy (Macro), readability and structure (Meso), and information density (Micro).
    3. **Model Interpretability (XAI):** Integrated SHAP (SHapley Additive exPlanations) to turn black-box predictions into transparent, actionable optimization advice for website owners.
    4. **Dual-Deployment Architecture:**
       - Full-stack interactive platform (FastAPI + React Vite UI).
       - Lightweight, zero-config cloud deployment on Streamlit Cloud.
    """)

    st.markdown("---")
    st.markdown("Project Code & Models Repository: [https://github.com/StephinArnold/GEO---Demo](https://github.com/StephinArnold/GEO---Demo)")
