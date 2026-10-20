import numpy as np
from sklearn.model_selection import GroupKFold


def test_groupkfold_by_domain_never_splits_same_domain():
    """The same safeguard pipeline.evaluate.cross_validate relies on:
    GroupKFold grouped by domain must never put the same domain in both
    the train and test fold.
    """
    rng = np.random.default_rng(0)
    n_domains = 20
    rows_per_domain = 5
    domains = np.repeat(np.arange(n_domains), rows_per_domain)
    X = rng.normal(size=(len(domains), 3))
    y = rng.integers(0, 2, size=len(domains))

    gkf = GroupKFold(n_splits=5)
    for train_idx, test_idx in gkf.split(X, y, domains):
        train_domains = set(domains[train_idx])
        test_domains = set(domains[test_idx])
        assert train_domains.isdisjoint(test_domains), (
            "A domain appeared in both train and test folds — this is exactly "
            "the leakage GroupKFold-by-domain is meant to prevent."
        )
