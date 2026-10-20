from bs4 import BeautifulSoup
from features.extractor import extract_features

SIMPLE_HTML = """
<!DOCTYPE html><html><head><title>Test</title></head><body>
<h1>Main Heading</h1>
<p>This is a short paragraph with one sentence.</p>
<h2>Sub Heading</h2>
<p>Another paragraph here. It has two sentences in it.</p>
</body></html>
"""

SCHEMA_HTML = """
<!DOCTYPE html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"LocalBusiness","name":"Test Biz",
 "telephone":"+1-555-000-1111",
 "address":{"@type":"PostalAddress","streetAddress":"1 Main St"}}
</script>
</head><body><h1>Test Biz</h1><p>Call us at (555) 000-1111.</p></body></html>
"""

NO_SCHEMA_HTML = """
<!DOCTYPE html><html><body><p>Plain text, no headings, no schema at all.</p></body></html>
"""


def test_heading_counts():
    soup = BeautifulSoup(SIMPLE_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/simple")
    mf = feats["model_features"]
    assert mf["h1_count"] == 1
    assert mf["h2_count"] == 1
    assert mf["heading_count"] == 2


def test_paragraph_count():
    soup = BeautifulSoup(SIMPLE_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/simple")
    assert feats["content"]["paragraph_count"] == 2


def test_schema_present_detects_local_business():
    soup = BeautifulSoup(SCHEMA_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/schema")
    mf = feats["model_features"]
    assert mf["schema_present"] == 1
    assert mf["local_business_schema"] == 1


def test_no_schema_page_has_schema_present_zero():
    soup = BeautifulSoup(NO_SCHEMA_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/noschema")
    assert feats["model_features"]["schema_present"] == 0
    assert feats["model_features"]["h1_count"] == 0


def test_phone_detection():
    soup = BeautifulSoup(SCHEMA_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/schema")
    assert feats["local_business"]["has_phone"] in (True, 1)


def test_all_model_features_are_numeric():
    soup = BeautifulSoup(SIMPLE_HTML, "html.parser")
    feats = extract_features(soup, "https://example.com/simple")
    for name, value in feats["model_features"].items():
        assert isinstance(value, (int, float)), f"{name} is not numeric: {type(value)}"
