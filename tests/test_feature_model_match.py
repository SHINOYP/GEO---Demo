"""
Guards against train/serve mismatch: every column the model was trained on
must actually be produced by the live feature extractor, and vice versa.
"""
from bs4 import BeautifulSoup
from features.extractor import extract_features
from models.model_loader import FEATURE_COLUMNS

SAMPLE_HTML = """
<!DOCTYPE html><html><head>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"LocalBusiness","name":"Test Biz"}
</script>
</head><body>
<h1>Welcome</h1><h2>Services</h2>
<p>Some descriptive paragraph text about the business and its offerings.</p>
<ul><li>Item one</li></ul>
</body></html>
"""


def test_every_feature_column_is_produced_by_extractor():
    soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
    mf = extract_features(soup, "https://example.com/")["model_features"]
    missing = [c for c in FEATURE_COLUMNS if c not in mf]
    assert not missing, f"FEATURE_COLUMNS references features the extractor never produces: {missing}"


def test_app_feeds_model_the_exact_trained_columns_in_order():
    """Mirrors streamlit_app.py's row = pd.DataFrame([{col: mf.get(col, 0) for col in feat_cols}])."""
    soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
    mf = extract_features(soup, "https://example.com/")["model_features"]
    row = {col: mf.get(col, 0) for col in FEATURE_COLUMNS}
    assert list(row.keys()) == FEATURE_COLUMNS
