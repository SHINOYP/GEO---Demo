"""
model_loader.py must never silently serve a synthetic model: it should load
the real artifacts/model.pkl, or fail loudly with instructions if it's missing.
"""
import joblib
import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from models import model_loader


@pytest.fixture(autouse=True)
def reset_singleton():
    # Each test starts from a clean cache so one test's monkeypatched
    # MODEL_PATH can't leak a cached model into another test.
    model_loader._model = None
    model_loader._feat_cols = None
    yield
    model_loader._model = None
    model_loader._feat_cols = None


def test_load_model_raises_clear_error_when_missing(tmp_path, monkeypatch):
    missing_path = tmp_path / "does_not_exist.pkl"
    monkeypatch.setattr(model_loader, "MODEL_PATH", str(missing_path))

    with pytest.raises(RuntimeError) as exc_info:
        model_loader.load_model()

    message = str(exc_info.value)
    assert "pipeline.evaluate" in message
    assert str(missing_path) in message


def test_load_model_succeeds_with_a_real_pickled_model(tmp_path, monkeypatch):
    # A tiny stub model is enough to prove the loading mechanism works,
    # without depending on the real artifacts/model.pkl being present/fresh.
    X = pd.DataFrame(
        np.random.default_rng(0).random((10, len(model_loader.FEATURE_COLUMNS))),
        columns=model_loader.FEATURE_COLUMNS,
    )
    y = np.array([0, 1] * 5)
    stub_model = xgb.XGBClassifier(n_estimators=2, max_depth=2)
    stub_model.fit(X, y)

    model_path = tmp_path / "stub_model.pkl"
    joblib.dump(stub_model, model_path)
    monkeypatch.setattr(model_loader, "MODEL_PATH", str(model_path))

    model, feat_cols = model_loader.get_model()

    assert feat_cols == model_loader.FEATURE_COLUMNS
    assert hasattr(model, "predict_proba")


def test_get_model_caches_the_loaded_model(tmp_path, monkeypatch):
    X = pd.DataFrame(
        np.random.default_rng(1).random((10, len(model_loader.FEATURE_COLUMNS))),
        columns=model_loader.FEATURE_COLUMNS,
    )
    y = np.array([0, 1] * 5)
    stub_model = xgb.XGBClassifier(n_estimators=2, max_depth=2)
    stub_model.fit(X, y)

    model_path = tmp_path / "stub_model.pkl"
    joblib.dump(stub_model, model_path)
    monkeypatch.setattr(model_loader, "MODEL_PATH", str(model_path))

    model_a, _ = model_loader.get_model()
    # Delete the file to prove the second call can't be re-reading from disk.
    model_path.unlink()
    model_b, _ = model_loader.get_model()

    assert model_a is model_b
