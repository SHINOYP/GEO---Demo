import json
import os


def _load_json_or_none(path):
    """Mirrors streamlit_app.load_json_or_none without importing streamlit_app
    itself (which executes top-level Streamlit page code on import)."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_missing_metrics_file_returns_none(tmp_path):
    missing = tmp_path / "metrics.json"
    assert _load_json_or_none(str(missing)) is None


def test_existing_metrics_file_loads(tmp_path):
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps({"roc_auc_display": "0.70 ± 0.05", "underpowered": True}))
    data = _load_json_or_none(str(p))
    assert data["underpowered"] is True
    assert "roc_auc_display" in data
