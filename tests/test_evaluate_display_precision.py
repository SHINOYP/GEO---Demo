from pipeline.evaluate import format_mean_std


def test_format_mean_std_rounds_to_2_decimals_for_display():
    """Display strings (roc_auc_display, f1_display) must use the same
    2-decimal precision the docs/slides quote (e.g. '0.69 ± 0.08'), not
    the raw 4-decimal values stored in metrics.json's per-model dicts
    ('0.6919 ± 0.0816'), which would silently disagree with the rounded
    number everyone reads and quotes."""
    assert format_mean_std({"mean": 0.6919, "std": 0.0816}) == "0.69 ± 0.08"
    assert format_mean_std({"mean": None, "std": None}) == "not yet evaluated"
