# KNOWN_WEAKNESSES.md — Red-Team Pass

Written as a hostile examiner reading the actual code and `docs/AUDIT.md`.
30 hardest questions, honest answers, and which ones expose a real,
**unfixable-by-Thursday** weakness vs. ones we can mitigate in the answer.

1. **"Your headline metrics are 0.888 AUC. Prove it."**
   We can't — `docs/AUDIT.md` Q2 confirms these exact numbers appear
   nowhere else in the repo (no log/notebook/artifact) and are also
   circular even if reproduced (Q1). **UNFIXABLE for that original demo
   model** — our honest answer: we removed those numbers from the UI and
   replaced them with real cross-validated metrics from an actual pilot
   (XGBoost ROC-AUC 0.64 ± 0.12 on the full 200-query dataset, pooled
   across 10 repeated GroupKFold splits — see `artifacts/metrics.json`),
   and we go further — we evaluated the *original* synthetic-trained model
   on our real data and it scores 0.49, essentially chance, which is the
   proof that its 0.888 never meant anything.
2. **"So your model has never seen a single real citation?"**
   **No longer true — we fixed this.** We collected all 200 planned
   queries (manually via perplexity.ai, since no paid API budget was
   available) and evaluated on 390 real scraped pages (118 cited / 272
   not). The dataset is not flagged underpowered. Scaling from the initial
   100-query pilot (214 rows, single-split AUC 0.65 ± 0.19) to 200 queries
   evaluated with a more rigorous repeated-split methodology (390 rows,
   AUC 0.64 ± 0.12) is consistent with a real signal that needed both more
   data and a less noise-prone evaluation to pin down.
3. **"Then what, exactly, did you accomplish this semester?"** A working,
   auditable, honestly-labeled system (scraper, 45-feature extractor,
   XGBoost+SHAP pipeline, evaluation harness with leakage safeguards),
   **plus a completed real-data pilot run at the full planned scale (200
   queries, 390 usable rows)** with real cross-validated metrics, a passed
   label-shuffle sanity check, and a concrete demonstration that the
   inherited synthetic-trained model fails on real data. This is a strong
   scope statement for a Phase-1 review.
4. **"Why didn't you just get the API key weeks ago?"** Fair criticism —
   team process gap, not a technical one. We worked around it by manually
   collecting all 200 queries' citations via the free perplexity.ai
   website instead of the paid API, which got us real data at full scale
   without the budget. Answer honestly; don't deflect.
5. **"Your negatives are pages that already rank. Doesn't that make this
   trivial / useless?"** It constrains the claim: we predict
   cited-vs-not-cited *among already-competitive pages*, not
   citable-vs-the-whole-web. **Partially fixable**: documented explicitly,
   not hidden.
6. **"A single API call per query — how do you know that citation wasn't
   random noise?"** We don't, with `--repeats 1` (and our manual
   collection method also only captured one observation per query).
   `--repeats 3+` exists in the automated path to measure this but hasn't
   been run. **Real limitation, honestly disclosed** — the label-shuffle
   control (AUC 0.51 ± 0.04, almost exactly chance) is indirect evidence
   the signal isn't pure noise, but it doesn't substitute for measuring
   citation stability directly.
7. **"200 queries. Isn't that still small for 45 features?"** Yes —
   classic curse-of-dimensionality risk, though far better than the
   original 20-query pilot. The `underpowered` flag in `metrics.json`
   exists specifically to surface this rather than hide it behind a single
   confident-looking number; at 390 usable rows it currently reads
   `false`, and the error bars have tightened as we scaled up and fixed the
   evaluation methodology (±0.19 at n=100 → ±0.12 at n=200, pooled across
   10 repeated splits), but we still present this as a strong early signal
   from a pilot study, not a production-validated model.
8. **"Walk me through SHAP — does it prove causation?"** No, and we say so
   explicitly (`docs/WHITEBOARD.md` ex. 8) — correlation only.
9. **"If I remove `factual_density` from your synthetic model, does
   performance crater? What does that tell you?"** Very likely yes, since
   it's weighted `*8` in the label formula — proving the circularity, not
   predictive power. We'd say this openly if asked to demonstrate it live.
10. **"Your macro/meso/micro scores are built from features already in the
    model. Isn't that redundant engineering?"** Yes, confirmed in
    `docs/AUDIT.md` Q3 — a genuine design flaw inherited from upstream,
    not something we introduced, but also not yet removed. **Partially
    fixable**: could drop or isolate them in the real-data retraining;
    not done yet.
11. **"Does your SSRF fix actually close every bypass?"** We close the
    redirect-DNS-rebind gap specifically identified in the audit. We do
    not claim comprehensive SSRF hardening (e.g. no protection against
    DNS rebinding *during* the single request itself, a TOCTOU window
    between `_check_ssrf`'s resolution and `requests`' own). **Honest
    answer: mitigated the known gap, not provably exhaustive.**
12. **"Why trust `urllib.robotparser` defaulting to 'allow' when robots.txt
    fails to fetch?"** Matches standard crawler convention (no robots.txt
    = no restriction), but it does mean a transient network blip during
    robots.txt fetch silently permits a scrape that a slower retry might
    have blocked. Low risk, documented trade-off.
13. **"Rate limiting — what stops someone hammering your `/api/analyze`
    endpoint?"** Nothing currently (confirmed absent in `docs/AUDIT.md`
    Q6). **Real, unfixed gap** if the FastAPI backend is ever
    internet-exposed; mitigated for the review by only running it locally/
    in a controlled demo.
14. **"Your dedup-by-template-fingerprint — does it actually catch near-
    duplicate pages, or just byte-identical ones?"** It strips text content
    and quoted strings before hashing, so it catches *structurally*
    identical templates with different text (e.g. the same site-builder
    theme), not pages that are similar but structurally different. A
    genuinely different-looking duplicate (e.g. a mirrored page with
    reordered sections) would be missed.
15. **"Explain exactly why GroupKFold-by-domain, not by URL."** Multiple
    URLs on the same domain tend to share template/boilerplate; grouping
    by URL alone wouldn't prevent the model from learning a specific
    site's structure and "cheating" on a held-out page from that same
    site.
16. **"What if a business has zero organic ranking but gets cited — does
    your candidate pool even capture that?"** No — the candidate pool is
    cited ∪ organic-ranking; a cited page with literally no organic
    presence (rare, but possible) would still appear via the cited-set
    union, so it is captured as a positive, but any *missed* citation to a
    URL outside both sets simply never enters the dataset at all — a blind
    spot, not an error, but worth naming.
17. **"Perplexity's citation set depends on the exact prompt phrasing.
    Isn't your query list arbitrary?"** Yes — 20 hand-picked queries are a
    convenience sample, not a statistically representative query
    distribution for any of the 4 business categories.
18. **"Your SerpAPI fallback uses Perplexity's own search_results as the
    candidate pool when no key is set. Doesn't that bias candidates toward
    what Perplexity already considered, defeating independence?"** Yes,
    explicitly documented as a limitation in `docs/DATA_CARD.md` — not
    hidden, but a real methodological weakness without a SerpAPI key.
19. **"Logistic regression needs standardized features — did you leak
    scaling fit across folds?"** No — `StandardScaler` is fit only on
    `X_train` inside each fold and applied to `X_test`, in
    `pipeline/evaluate.py:cross_validate`. Verified by reading the code.
20. **"Does your XGBoost hyperparameter choice count as 'tuning on the
    test set'?"** No — hyperparameters are fixed a priori (conservative,
    not searched per fold), exactly to avoid that trap; stated in
    `pipeline/evaluate.py` module design. No nested CV was implemented
    because hyperparameters are fixed, not searched.
21. **"Calibration — is a 70% score really a 70% chance?"** Only loosely,
    per the Brier score computed in `calibration_check`; with small n, we
    explicitly recommend reading the output as a *ranking* signal, not a
    literal probability (stated in the function's own docstring/comment).
22. **"If I ask you to defend the exact choice of `n_estimators=150`, what
    do you say?"** It's a reasonable, conservative default for small-data
    gradient boosting, not a value searched via grid/CV on this dataset —
    honest answer: chosen by engineering judgment, not tuned.
23. **"Why not simply use AUC alone and skip PR-AUC/calibration?"** Because
    under class imbalance, AUC alone can look good while the model is
    useless at any practical operating threshold — PR-AUC and calibration
    give a fuller picture, which matters since we expect imbalance (more
    non-cited than cited pages) in the real pilot.
24. **"Does removing `domain_type` change results meaningfully?"**
    Measured on the full 200-query dataset: AUC with the directory-
    aggregator flag is 0.71 vs. 0.64 without it — a modest lift, not a
    dominant effect. So whether a cited page is a directory (JustDial,
    MagicPin, etc.) helps a little, but the model isn't just learning "is
    this a directory," which would be a red flag. See
    `sanity_checks.domain_type_leakage_check` in `artifacts/metrics.json`.
25. **"Your tests don't call a live trained model end-to-end — are they
    real tests or just smoke tests?"** The pytest suite is unit/contract
    tests (feature extraction correctness, SSRF rejection, canonicalization,
    split-leakage guarantee, feature-column train/serve match) — genuinely
    useful, but they do not validate real-world predictive accuracy. That
    now *has* been validated separately, by the actual pilot evaluation
    run (`pipeline.evaluate` on 390 real rows from the full 200-query
    dataset) — a different kind of check (statistical, not unit-test), but
    a real one.
26. **"What happens to your whole claim if Perplexity changes its API
    response schema?"** `collect_citations.py` checks both `citations` and
    `search_results` keys and logs whichever shape is observed to
    `docs/API_NOTES.md` on first real call — a reasonable mitigation, but
    if the schema changes again later (after our collection run), old
    cached data could reflect a different schema; the extractor should be
    revisited each time a fresh collection is run.
27. **"Could you have picked a worse review week to need a paid API?"**
    Fair jab — acknowledge the scheduling risk honestly rather than
    arguing it isn't a risk.
28. **"Why 45 features and not more/fewer — is that number meaningful?"**
    No — it's simply however many the inherited extractor happens to
    compute; not a deliberately chosen feature-count target.
29. **"Does the model handle a page with literally zero text (e.g. a pure
    image landing page)?"** The scraper requires >100 chars of raw HTML
    (`scraper.py`) and most features default to 0/low values for near-empty
    pages, but a pure-image, no-text, no-schema page would score very low
    uniformly rather than erroring — reasonable degraded behavior, not
    tested with a dedicated fixture.
30. **"If the panel asks you to run `pipeline.evaluate` live right now,
    what happens?"** It will actually run successfully — `data/dataset.csv`
    exists (390 real rows from the full 200-query dataset) — and reproduce
    the exact numbers in `artifacts/metrics.json` (XGBoost ROC-AUC ≈ 0.64,
    label-shuffle ≈ 0.51, etc.) in just over a minute (the evaluation now
    repeats GroupKFold 10 times and pools the results for a more precise
    estimate, so it's a little slower than a single 5-fold split would be —
    still fast enough to run live). This is worth offering to demonstrate
    live: it proves the numbers aren't hand-typed. (Before real data
    existed, this same script would have written a placeholder
    `{"error": "NOT YET MEASURED..."}` instead of crashing or fabricating
    numbers — that honesty-by-design fallback is still there for anyone
    who clones the repo without the data files.)

## Summary: unfixable-by-Thursday weaknesses (say so plainly if asked)

- **Resolved since this pass was written:** real citation data has now
  been collected for the full planned 200 queries (390 usable rows) and
  evaluated (items 1-3 are no longer live weaknesses — see the real
  numbers in `artifacts/metrics.json`). Kept here, struck through in
  spirit, as a record of what the red-team pass originally flagged and how
  it was actually closed, not just argued around.
- **Still real:** only one observation per query, no `--repeats` run yet
  (item 6) — citation non-determinism is not directly measured.
- Small-by-ML-standards sample size and selection-biased negatives
  (items 5, 7, 17) — inherent to a pilot study at this scale; error bars
  (±0.12 on AUC, pooled across repeated splits, down from ±0.19 at n=100)
  are reported honestly rather than hidden.
- No rate limiting on the API backend (item 13) — a real gap, mitigated
  only by not exposing it publicly for the demo.
- Redundant macro/meso/micro composite features inherited from upstream
  (item 10) — known, not yet re-engineered.
