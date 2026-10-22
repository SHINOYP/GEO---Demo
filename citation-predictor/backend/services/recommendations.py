"""
Rule-based recommendation engine.

Generates actionable, feature-driven recommendations from
detected feature values and SHAP results.
"""


def generate_recommendations(features: dict, shap_data: dict) -> list[dict]:
    """
    Returns a list of recommendation dicts:
      {priority, category, title, description, impact}
    """
    mf   = features.get("model_features", {})
    sc   = features.get("schema", {})
    cf   = features.get("content", {})
    sf   = features.get("structure", {})
    lb   = features.get("local_business", {})
    der  = features.get("derived", {})
    recs = []

    # ── Schema ────────────────────────────────────────────────
    if not mf.get("schema_present"):
        recs.append({
            "priority": "high", "category": "Schema",
            "title": "Add Schema.org Structured Data",
            "description": (
                "No structured data (JSON-LD or Microdata) was detected. "
                "Adding Schema.org markup — such as LocalBusiness, Article, or FAQPage — "
                "helps generative AI engines understand your page's context and improves "
                "machine-readable structure."
            ),
            "impact": "high",
        })
    elif not mf.get("local_business_schema") and lb.get("has_phone"):
        recs.append({
            "priority": "medium", "category": "Schema",
            "title": "Add LocalBusiness Schema",
            "description": (
                "Phone or address details were detected but no LocalBusiness schema is present. "
                "Add LocalBusiness (or a specific subtype like Restaurant, MedicalClinic) "
                "to help AI engines identify and cite your business details correctly."
            ),
            "impact": "medium",
        })

    if not mf.get("faq_schema") and cf.get("list_count", 0) > 2:
        recs.append({
            "priority": "medium", "category": "Schema",
            "title": "Consider Adding FAQPage Schema",
            "description": (
                "Lists and Q&A-like content were detected without FAQPage structured data. "
                "FAQPage schema allows AI answer engines to directly cite your questions and answers."
            ),
            "impact": "medium",
        })

    # ── Content quality ────────────────────────────────────────
    if cf.get("word_count", 0) < 300:
        recs.append({
            "priority": "high", "category": "Content",
            "title": "Increase Content Depth",
            "description": (
                f"The page contains only ~{cf.get('word_count', 0)} words. "
                "Generative AI engines tend to prefer comprehensive, informative pages. "
                "Consider expanding content with relevant facts, details, and context."
            ),
            "impact": "high",
        })

    if mf.get("factual_density", 0) < 0.05:
        recs.append({
            "priority": "high", "category": "Content",
            "title": "Improve Factual Density",
            "description": (
                "The estimated factual density is low. "
                "Include specific data points, statistics, dates, measurements, or verifiable facts. "
                "AI engines prioritise pages that provide concrete, citable information."
            ),
            "impact": "high",
        })

    if cf.get("avg_paragraph_length", 0) > 120:
        recs.append({
            "priority": "medium", "category": "Content",
            "title": "Break Up Long Paragraphs",
            "description": (
                f"Average paragraph length is ~{int(cf.get('avg_paragraph_length', 0))} words. "
                "Break long paragraphs into shorter, focused units (ideally 40–80 words each) "
                "to improve readability and AI content parsing."
            ),
            "impact": "medium",
        })

    if cf.get("external_link_count", 0) < 2:
        recs.append({
            "priority": "medium", "category": "Content",
            "title": "Add Credible External References",
            "description": (
                "Few or no external links were found. "
                "Linking to authoritative sources (studies, official sites) "
                "signals credibility and supports factual density."
            ),
            "impact": "medium",
        })

    if cf.get("citation_ref_count", 0) == 0 and cf.get("word_count", 0) > 500:
        recs.append({
            "priority": "low", "category": "Content",
            "title": "Add Citations or References",
            "description": (
                "No in-text citations or references were detected. "
                "Academic-style citations or footnotes can significantly improve citation likelihood."
            ),
            "impact": "medium",
        })

    # ── Structure ─────────────────────────────────────────────
    if sf.get("h1_count", 0) != 1:
        recs.append({
            "priority": "high", "category": "Structure",
            "title": "Fix H1 Tag Usage",
            "description": (
                f"{sf.get('h1_count', 0)} H1 tag(s) detected. "
                "Use exactly one H1 that clearly describes the page topic. "
                "This is a fundamental structural signal for AI content parsers."
            ),
            "impact": "high",
        })

    if sf.get("h2_count", 0) < 2:
        recs.append({
            "priority": "medium", "category": "Structure",
            "title": "Improve Section Structure with H2 Headings",
            "description": (
                "Few H2 headings were found. "
                "Use H2 headings to divide content into clear, labelled sections. "
                "This improves navigability and AI comprehension."
            ),
            "impact": "medium",
        })

    if mf.get("format_diversity", 0) < 0.4:
        recs.append({
            "priority": "low", "category": "Structure",
            "title": "Diversify Content Format",
            "description": (
                "The page uses few content types (lists, tables, images, quotes). "
                "Adding varied formats makes content easier to parse and more citable."
            ),
            "impact": "low",
        })

    # ── Local Business ─────────────────────────────────────────
    if not lb.get("has_phone"):
        recs.append({
            "priority": "medium", "category": "Local Business",
            "title": "Add Contact Phone Number",
            "description": (
                "No phone number was detected. "
                "For local business pages, including a phone number improves "
                "trustworthiness and local relevance signals."
            ),
            "impact": "medium",
        })

    if not lb.get("has_address"):
        recs.append({
            "priority": "medium", "category": "Local Business",
            "title": "Add a Physical Address",
            "description": (
                "No street address was detected. "
                "A clearly stated address is important for local business citation "
                "and improves geographic relevance signals."
            ),
            "impact": "medium",
        })

    if not lb.get("has_opening_hours"):
        recs.append({
            "priority": "low", "category": "Local Business",
            "title": "Add Opening Hours",
            "description": (
                "No opening hours were detected. "
                "Including business hours helps AI engines provide complete "
                "and citable business information."
            ),
            "impact": "low",
        })

    # Deduplicate & sort
    seen = set()
    unique_recs = []
    for r in recs:
        key = r["title"]
        if key not in seen:
            seen.add(key)
            unique_recs.append(r)

    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique_recs.sort(key=lambda r: priority_order.get(r["priority"], 3))

    return unique_recs
