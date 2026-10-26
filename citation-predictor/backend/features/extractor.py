"""
Feature extraction pipeline.

Extracts macro / meso / micro structural features, content features,
schema/structured-data features, and local-business signals from a parsed webpage.

All features are numeric so they can be fed directly to the XGBoost model.
"""

import re
import json
import logging
import math
from typing import Any

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("citelytics.features")

# ─────────────────────────────────────────────────────────────
# Regex helpers
# ─────────────────────────────────────────────────────────────

_RE_NUMBER      = re.compile(r'\b\d+(?:[.,]\d+)*\b')
_RE_PERCENT     = re.compile(r'\b\d+(?:\.\d+)?%')
_RE_PHONE       = re.compile(
    r'(\+?\d[\d\s\-().]{7,}\d)'
)
_RE_HOURS       = re.compile(
    r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
    r'[\w\s\-–:,]+(?:AM|PM|am|pm|\d{1,2}:\d{2})',
    re.IGNORECASE,
)
_RE_DATE        = re.compile(
    r'\b(?:\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2}|'
    r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4})\b',
    re.IGNORECASE,
)
_RE_ADDRESS     = re.compile(
    r'\b\d{1,5}\s+[A-Za-z0-9\s,\.]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|'
    r'Lane|Ln|Drive|Dr|Way|Court|Ct|Place|Pl|Square|Sq)\b',
    re.IGNORECASE,
)
_RE_RATING      = re.compile(
    r'\b(?:\d(?:\.\d)?)\s*/\s*(?:5|10)\b|'
    r'\b\d(?:\.\d)?\s+(?:stars?|out\s+of)\b',
    re.IGNORECASE,
)
_RE_QUOTE       = re.compile(r'["""].{10,300}["""]')
_RE_CITE_REF    = re.compile(
    r'(?:\[\d+\]|\[\w+,\s*\d{4}\]|(?:ibid|et al\.|op\. cit\.))',
    re.IGNORECASE,
)


def _text(soup: BeautifulSoup) -> str:
    """Return visible text (noise tags already removed by scraper)."""
    return soup.get_text(separator=" ", strip=True)


# ─────────────────────────────────────────────────────────────
# Schema detection
# ─────────────────────────────────────────────────────────────

def _extract_schema_features(soup: BeautifulSoup) -> dict:
    schema_types: list[str] = []

    # JSON-LD
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        _collect_types(data, schema_types)

    # Microdata / RDFa type hints
    for tag in soup.find_all(attrs={"itemtype": True}):
        val = tag["itemtype"]
        if isinstance(val, list):
            schema_types.extend(val)
        else:
            schema_types.append(str(val))

    types_lower = [t.lower() for t in schema_types]

    def _has(*keywords) -> int:
        return int(any(k in t for t in types_lower for k in keywords))

    return {
        "schema_present":            int(bool(schema_types)),
        "local_business_schema":     _has("localbusiness", "restaurant", "hotel",
                                          "store", "foodestablishment", "lodgingbusiness",
                                          "medicalorganization", "dentalclinic"),
        "organization_schema":       _has("organization", "corporation", "ngo"),
        "faq_schema":                _has("faqpage"),
        "article_schema":            _has("article", "newsarticle", "blogposting"),
        "product_schema":            _has("product", "offer"),
        "breadcrumb_schema":         _has("breadcrumblist"),
        "review_schema":             _has("review", "aggregaterating"),
        "number_of_schema_types":    len(set(schema_types)),
        "schema_types_detected":     list(set(schema_types))[:10],  # informational
    }


def _collect_types(obj, out: list):
    if isinstance(obj, dict):
        if "@type" in obj:
            t = obj["@type"]
            if isinstance(t, list):
                out.extend(t)
            else:
                out.append(str(t))
        for v in obj.values():
            _collect_types(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_types(item, out)


# ─────────────────────────────────────────────────────────────
# Local business signals
# ─────────────────────────────────────────────────────────────

def _extract_local_business(soup: BeautifulSoup, text: str) -> dict:
    phones   = _RE_PHONE.findall(text)
    hours    = _RE_HOURS.findall(text)
    address  = _RE_ADDRESS.findall(text)
    ratings  = _RE_RATING.findall(text)

    # Business name heuristic — look for og:site_name or title
    og_name  = soup.find("meta", property="og:site_name")
    title    = soup.find("title")
    biz_name = (og_name["content"] if og_name and og_name.get("content") else
                title.get_text(strip=True) if title else "")

    return {
        "has_phone":         int(bool(phones)),
        "has_address":       int(bool(address)),
        "has_opening_hours": int(bool(hours)),
        "has_rating":        int(bool(ratings)),
        "phone_count":       len(phones),
        "address_count":     len(address),
        "hours_mention_count": len(hours),
        "rating_count":      len(ratings),
        # informational (not fed to model)
        "business_name":     biz_name[:120],
        "detected_phones":   list(set(phones))[:3],
        "detected_hours":    hours[:3],
        "detected_addresses":address[:3],
    }


# ─────────────────────────────────────────────────────────────
# Content features
# ─────────────────────────────────────────────────────────────

def _extract_content_features(soup: BeautifulSoup, text: str) -> dict:
    paragraphs = soup.find_all("p")
    para_texts  = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
    sentences   = re.split(r'(?<=[.!?])\s+', text)
    sentences   = [s for s in sentences if len(s.split()) > 2]
    words       = text.split()

    avg_para_len   = (sum(len(p.split()) for p in para_texts) / len(para_texts)
                      if para_texts else 0)
    avg_sent_len   = (sum(len(s.split()) for s in sentences) / len(sentences)
                      if sentences else 0)

    numbers        = _RE_NUMBER.findall(text)
    percents       = _RE_PERCENT.findall(text)
    dates          = _RE_DATE.findall(text)
    quotes         = _RE_QUOTE.findall(text)
    cite_refs      = _RE_CITE_REF.findall(text)

    ext_links = soup.find_all("a", href=re.compile(r'^https?://'))
    int_links = soup.find_all("a", href=re.compile(r'^(?!//)(?!https?://)'))
    images    = soup.find_all("img")
    lists     = soup.find_all(["ul", "ol"])
    tables    = soup.find_all("table")
    emphasis  = soup.find_all(["strong", "b", "em", "i", "mark"])

    short_paras = sum(1 for p in para_texts if len(p.split()) < 40)
    long_paras  = sum(1 for p in para_texts if len(p.split()) >= 100)

    return {
        "word_count":          len(words),
        "sentence_count":      len(sentences),
        "paragraph_count":     len(para_texts),
        "avg_sentence_length": round(avg_sent_len, 2),
        "avg_paragraph_length":round(avg_para_len, 2),
        "number_count":        len(numbers),
        "percentage_count":    len(percents),
        "date_count":          len(dates),
        "quote_count":         len(quotes),
        "citation_ref_count":  len(cite_refs),
        "external_link_count": len(ext_links),
        "internal_link_count": len(int_links),
        "image_count":         len(images),
        "list_count":          len(lists),
        "table_count":         len(tables),
        "emphasis_count":      len(emphasis),
        "short_paragraph_count": short_paras,
        "long_paragraph_count":  long_paras,
    }


# ─────────────────────────────────────────────────────────────
# Structural features
# ─────────────────────────────────────────────────────────────

def _extract_structural_features(soup: BeautifulSoup) -> dict:
    h1s = soup.find_all("h1")
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")
    h4s = soup.find_all("h4")
    h5s = soup.find_all("h5")
    h6s = soup.find_all("h6")

    heading_count = len(h1s) + len(h2s) + len(h3s) + len(h4s) + len(h5s) + len(h6s)
    heading_depth = sum([
        int(bool(h1s)), int(bool(h2s)), int(bool(h3s)),
        int(bool(h4s)), int(bool(h5s)), int(bool(h6s))
    ])

    # Heading hierarchy consistency:
    # penalise if H1 is missing, reward progressive depth
    h1_ok   = int(len(h1s) == 1)
    h2_ok   = int(bool(h2s))
    h_score = (h1_ok * 0.5 + h2_ok * 0.3 + int(bool(h3s)) * 0.2)

    # Section count: treat h2 as section boundary
    section_count = max(len(h2s), 1)

    paragraphs    = soup.find_all("p")
    para_texts    = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
    avg_para_per_section = len(para_texts) / section_count if section_count else 0

    return {
        "h1_count":                   len(h1s),
        "h2_count":                   len(h2s),
        "h3_count":                   len(h3s),
        "h4_count":                   len(h4s),
        "heading_count":              heading_count,
        "heading_depth":              heading_depth,
        "heading_hierarchy_score":    round(h_score, 3),
        "section_count":              section_count,
        "avg_paragraphs_per_section": round(avg_para_per_section, 2),
    }


# ─────────────────────────────────────────────────────────────
# Derived / computed scores
# ─────────────────────────────────────────────────────────────

def _compute_factual_density(cf: dict, text: str) -> float:
    """
    Estimated factual density — transparent heuristic.
    Signals: numbers, percentages, dates, citation refs, external links.
    Normalised by word count (capped at 1.0).
    NOT a scientifically validated measure.
    """
    wc = max(cf["word_count"], 1)
    raw_signals = (
        cf["number_count"] * 1.0
        + cf["percentage_count"] * 2.0
        + cf["date_count"] * 1.5
        + cf["citation_ref_count"] * 3.0
        + cf["external_link_count"] * 0.5
        + cf["quote_count"] * 1.5
    )
    density = min(raw_signals / wc, 1.0)
    return round(density, 4)


def _compute_format_diversity(cf: dict, sf: dict) -> float:
    """
    Format diversity: 0-1 score based on how many content types are used.
    """
    signals = [
        cf["list_count"] > 0,
        cf["table_count"] > 0,
        cf["image_count"] > 0,
        cf["quote_count"] > 0,
        cf["emphasis_count"] > 0,
        sf["h2_count"] > 0,
        sf["h3_count"] > 0,
    ]
    return round(sum(signals) / len(signals), 4)


def _compute_emphasis_density(cf: dict) -> float:
    wc = max(cf["word_count"], 1)
    return round(min(cf["emphasis_count"] / wc, 1.0), 4)


def _compute_macro_score(sf: dict, cf: dict) -> float:
    """Overall page organisation score (0-1)."""
    signals = [
        min(sf["h1_count"], 1),
        min(sf["h2_count"] / 3, 1.0),
        min(sf["section_count"] / 5, 1.0),
        min(cf["word_count"] / 500, 1.0),
        sf["heading_hierarchy_score"],
    ]
    return round(sum(signals) / len(signals), 4)


def _compute_meso_score(sf: dict, cf: dict) -> float:
    """Section-level organisation score (0-1)."""
    para_per_sec = min(sf["avg_paragraphs_per_section"] / 4, 1.0)
    list_bonus   = min(cf["list_count"] / 3, 1.0)
    table_bonus  = min(cf["table_count"] / 2, 1.0)
    h3_bonus     = min(sf["h3_count"] / 3, 1.0)
    signals = [para_per_sec, list_bonus, table_bonus, h3_bonus]
    return round(sum(signals) / len(signals), 4)


def _compute_micro_score(cf: dict) -> float:
    """Local content-level quality score (0-1)."""
    short_ratio   = cf["short_paragraph_count"] / max(cf["paragraph_count"], 1)
    num_density   = min(cf["number_count"] / max(cf["word_count"], 1) * 50, 1.0)
    emphasis_ok   = min(cf["emphasis_count"] / max(cf["word_count"], 1) * 100, 1.0)
    sent_len_ok   = max(0.0, 1.0 - abs(cf["avg_sentence_length"] - 18) / 18)
    signals = [1 - short_ratio, num_density, emphasis_ok, sent_len_ok]
    return round(sum(signals) / len(signals), 4)


# ─────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────

def extract_features(soup: BeautifulSoup, url: str = "") -> dict:
    """
    Extract all features from a parsed BeautifulSoup tree.
    Returns a flat dict of features suitable for model input plus
    nested informational dicts for the UI.
    """
    text = _text(soup)

    content_feats    = _extract_content_features(soup, text)
    structural_feats = _extract_structural_features(soup)
    schema_feats     = _extract_schema_features(soup)
    local_biz_feats  = _extract_local_business(soup, text)

    factual_density  = _compute_factual_density(content_feats, text)
    format_diversity = _compute_format_diversity(content_feats, structural_feats)
    emphasis_density = _compute_emphasis_density(content_feats)
    macro_score      = _compute_macro_score(structural_feats, content_feats)
    meso_score       = _compute_meso_score(structural_feats, content_feats)
    micro_score      = _compute_micro_score(content_feats)

    # ── flat model features (fed to XGBoost) ──────────────────
    model_features = {
        # Content
        "word_count":             content_feats["word_count"],
        "sentence_count":         content_feats["sentence_count"],
        "paragraph_count":        content_feats["paragraph_count"],
        "avg_sentence_length":    content_feats["avg_sentence_length"],
        "avg_paragraph_length":   content_feats["avg_paragraph_length"],
        "factual_density":        factual_density,
        "number_count":           content_feats["number_count"],
        "percentage_count":       content_feats["percentage_count"],
        "date_count":             content_feats["date_count"],
        "quote_count":            content_feats["quote_count"],
        "citation_ref_count":     content_feats["citation_ref_count"],
        "external_link_count":    content_feats["external_link_count"],
        "internal_link_count":    content_feats["internal_link_count"],
        "image_count":            content_feats["image_count"],
        "list_count":             content_feats["list_count"],
        "table_count":            content_feats["table_count"],
        "emphasis_count":         content_feats["emphasis_count"],
        "emphasis_density":       emphasis_density,
        "format_diversity":       format_diversity,
        "short_paragraph_count":  content_feats["short_paragraph_count"],
        "long_paragraph_count":   content_feats["long_paragraph_count"],
        # Structure
        "h1_count":               structural_feats["h1_count"],
        "h2_count":               structural_feats["h2_count"],
        "h3_count":               structural_feats["h3_count"],
        "heading_count":          structural_feats["heading_count"],
        "heading_depth":          structural_feats["heading_depth"],
        "heading_hierarchy_score":structural_feats["heading_hierarchy_score"],
        "section_count":          structural_feats["section_count"],
        "avg_paragraphs_per_section": structural_feats["avg_paragraphs_per_section"],
        # Schema
        "schema_present":         schema_feats["schema_present"],
        "local_business_schema":  schema_feats["local_business_schema"],
        "organization_schema":    schema_feats["organization_schema"],
        "faq_schema":             schema_feats["faq_schema"],
        "article_schema":         schema_feats["article_schema"],
        "product_schema":         schema_feats["product_schema"],
        "breadcrumb_schema":      schema_feats["breadcrumb_schema"],
        "review_schema":          schema_feats["review_schema"],
        "number_of_schema_types": schema_feats["number_of_schema_types"],
        # Local biz
        "has_phone":              local_biz_feats["has_phone"],
        "has_address":            local_biz_feats["has_address"],
        "has_opening_hours":      local_biz_feats["has_opening_hours"],
        "has_rating":             local_biz_feats["has_rating"],
        # Macro/meso/micro
        "macro_structure_score":  macro_score,
        "meso_structure_score":   meso_score,
        "micro_structure_score":  micro_score,
    }

    # ── "what an AI crawler sees" preview ──────────────────────
    # The exact text the model's word/sentence/paragraph counts are computed
    # from — script/style/nav noise already stripped by the scraper. Shown
    # to the user as-is (truncated for payload size) so the gap between
    # "what's on the page visually" and "what the model actually reads" is
    # concrete, not just asserted.
    CRAWLER_PREVIEW_CHARS = 4000
    crawler_view = {
        "visible_text": text[:CRAWLER_PREVIEW_CHARS],
        "truncated": len(text) > CRAWLER_PREVIEW_CHARS,
        "full_char_count": len(text),
        "word_count": content_feats["word_count"],
    }

    return {
        "model_features":   model_features,
        "content":          content_feats,
        "structure":        structural_feats,
        "schema":           schema_feats,
        "local_business":   local_biz_feats,
        "crawler_view":     crawler_view,
        "derived": {
            "factual_density":   factual_density,
            "format_diversity":  format_diversity,
            "emphasis_density":  emphasis_density,
            "macro_score":       macro_score,
            "meso_score":        meso_score,
            "micro_score":       micro_score,
        },
    }
