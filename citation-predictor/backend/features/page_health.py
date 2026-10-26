"""
Page Health checklist — a small, secondary "site health" panel shown
alongside the citation-likelihood prediction in the web UI.

Deliberately NOT part of extract_features()/FEATURE_COLUMNS: these checks
are not fed to the XGBoost model and don't influence citation_probability
at all. They exist purely as supporting context for the user (meta tags,
image accessibility, HTTPS, mobile-friendliness) — the kind of basic
on-page checks every general SEO audit tool shows, computed for free from
the same HTML we already scraped. No new dependency, no paid API, no
Lighthouse/performance-timing engine (that would require a real browser
and timing instrumentation, out of scope for a static-HTML check).
"""

from bs4 import BeautifulSoup

TITLE_MIN_LEN = 10
TITLE_MAX_LEN = 60
DESCRIPTION_MIN_LEN = 50
DESCRIPTION_MAX_LEN = 160


def check_page_health(soup: BeautifulSoup, final_url: str) -> dict:
    """Returns a small set of pass/warn/fail checks, each with a short reason."""
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""
    title_len = len(title_text)

    desc_tag = soup.find("meta", attrs={"name": "description"})
    desc_text = (desc_tag.get("content") or "").strip() if desc_tag else ""
    desc_len = len(desc_text)

    images = soup.find_all("img")
    images_with_alt = [img for img in images if (img.get("alt") or "").strip()]
    alt_coverage = (len(images_with_alt) / len(images)) if images else None

    viewport_tag = soup.find("meta", attrs={"name": "viewport"})
    has_viewport = viewport_tag is not None

    is_https = final_url.strip().lower().startswith("https://")

    checks = [
        _title_check(title_text, title_len),
        _description_check(desc_text, desc_len),
        _alt_text_check(alt_coverage, len(images)),
        _https_check(is_https),
        _viewport_check(has_viewport),
    ]

    passed = sum(1 for c in checks if c["status"] == "pass")
    return {
        "checks": checks,
        "passed": passed,
        "total": len(checks),
    }


def _title_check(title_text: str, title_len: int) -> dict:
    if not title_text:
        return {"id": "title", "label": "Page title", "status": "fail",
                "detail": "No <title> tag found."}
    if title_len < TITLE_MIN_LEN or title_len > TITLE_MAX_LEN:
        return {"id": "title", "label": "Page title", "status": "warn",
                "detail": f"Title is {title_len} characters (ideal range: "
                          f"{TITLE_MIN_LEN}-{TITLE_MAX_LEN})."}
    return {"id": "title", "label": "Page title", "status": "pass",
            "detail": f"Present, {title_len} characters."}


def _description_check(desc_text: str, desc_len: int) -> dict:
    if not desc_text:
        return {"id": "description", "label": "Meta description", "status": "fail",
                "detail": "No meta description tag found."}
    if desc_len < DESCRIPTION_MIN_LEN or desc_len > DESCRIPTION_MAX_LEN:
        return {"id": "description", "label": "Meta description", "status": "warn",
                "detail": f"Description is {desc_len} characters (ideal range: "
                          f"{DESCRIPTION_MIN_LEN}-{DESCRIPTION_MAX_LEN})."}
    return {"id": "description", "label": "Meta description", "status": "pass",
            "detail": f"Present, {desc_len} characters."}


def _alt_text_check(alt_coverage, total_images: int) -> dict:
    if total_images == 0:
        return {"id": "alt_text", "label": "Image alt text", "status": "pass",
                "detail": "No images on this page."}
    pct = round(alt_coverage * 100)
    if pct == 100:
        status = "pass"
    elif pct >= 50:
        status = "warn"
    else:
        status = "fail"
    return {"id": "alt_text", "label": "Image alt text", "status": status,
            "detail": f"{pct}% of {total_images} images have alt text."}


def _https_check(is_https: bool) -> dict:
    if is_https:
        return {"id": "https", "label": "HTTPS", "status": "pass",
                "detail": "Page is served over HTTPS."}
    return {"id": "https", "label": "HTTPS", "status": "fail",
            "detail": "Page is not served over HTTPS."}


def _viewport_check(has_viewport: bool) -> dict:
    if has_viewport:
        return {"id": "viewport", "label": "Mobile viewport", "status": "pass",
                "detail": "Responsive viewport meta tag present."}
    return {"id": "viewport", "label": "Mobile viewport", "status": "fail",
            "detail": "No viewport meta tag — page may not be mobile-friendly."}
