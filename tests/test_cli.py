"""
Subprocess smoke tests for citation-predictor/backend/cli.py — mirrors
exactly what web/lib/pythonBridge.ts does when it spawns this script, so a
regression here is a regression the web app would actually hit.
"""
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI_PATH = os.path.join(REPO_ROOT, "citation-predictor", "backend", "cli.py")
FIXTURE_HTML = """
<!DOCTYPE html><html><head><title>Apex Dental Clinic</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Dentist","name":"Apex Dental Clinic",
 "telephone":"+1-555-010-2020",
 "address":{"@type":"PostalAddress","streetAddress":"1 Main St","addressLocality":"Springfield"}}
</script></head><body>
<h1>Apex Dental Clinic — Family &amp; Cosmetic Dentistry</h1>
<p>We provide comprehensive dental care including cleanings, fillings, and cosmetic dentistry.</p>
<h2>Our Services</h2><p>Routine checkups, root canals, teeth whitening, and emergency care.</p>
<p>Call us at (555) 010-2020 or visit 1 Main St, Springfield.</p>
</body></html>
"""


def run_cli(args, stdin_text=None):
    return subprocess.run(
        [sys.executable, CLI_PATH] + args,
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=os.path.join(REPO_ROOT, "citation-predictor", "backend"),
        timeout=60,
    )


def _require_real_model():
    model_path = os.path.join(REPO_ROOT, "artifacts", "model.pkl")
    if not os.path.exists(model_path):
        pytest.skip("artifacts/model.pkl not present; run `python -m pipeline.evaluate` first")


def test_analyze_html_stdin_produces_valid_json_with_expected_keys():
    _require_real_model()
    result = run_cli(
        ["analyze", "https://sample-dental-clinic.example.com", "--html-stdin"],
        stdin_text=FIXTURE_HTML,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    expected_keys = {
        "url", "final_url", "timestamp", "citation_probability", "citation_score",
        "prediction", "likelihood_level", "features", "shap_data", "shap_error",
        "recommendations", "model_note",
    }
    assert expected_keys <= set(body.keys())
    assert 0.0 <= body["citation_probability"] <= 1.0
    assert isinstance(body["recommendations"], list)


def test_analyze_rejects_malformed_url_with_clean_error_json():
    result = run_cli(["analyze", "not-a-url"])
    assert result.returncode != 0
    body = json.loads(result.stdout)
    assert body["error"] is True
    assert body["kind"] == "validation"


def test_report_from_a_prior_analyze_result_produces_a_real_pdf():
    _require_real_model()
    analyze_result = run_cli(
        ["analyze", "https://sample-dental-clinic.example.com", "--html-stdin"],
        stdin_text=FIXTURE_HTML,
    )
    assert analyze_result.returncode == 0, analyze_result.stderr

    report_result = subprocess.run(
        [sys.executable, CLI_PATH, "report"],
        input=analyze_result.stdout.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.join(REPO_ROOT, "citation-predictor", "backend"),
        timeout=60,
    )
    assert report_result.returncode == 0, report_result.stderr
    assert report_result.stdout.startswith(b"%PDF-")


def test_report_rejects_malformed_json_with_clean_error():
    result = run_cli(["report"], stdin_text="not json")
    assert result.returncode != 0
    body = json.loads(result.stdout)
    assert body["error"] is True
    assert body["kind"] == "validation"
