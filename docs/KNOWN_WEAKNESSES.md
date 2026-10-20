# KNOWN_WEAKNESSES.md — Red-Team Pass

Written as a hostile examiner reading the actual code and `docs/AUDIT.md`.
30 hardest questions, honest answers, and which ones expose a real,
**unfixable-by-Thursday** weakness vs. ones we can mitigate in the answer.

1. **"Your headline metrics are 0.888 AUC. Prove it."**
   We can't — `docs/AUDIT.md` Q2 confirms these exact numbers appear
   nowhere else in the repo (no log/notebook/artifact) and are also
   circular even if reproduced (Q1). **UNFIXABLE for the demo model** — our
   honest answer: we removed them from the UI and replaced with "not yet
   evaluated" / real pilot numbers once collected.
2. **"So your model has never seen a single real citation?"**
   Correct, as of this review. **This is the central unresolved weakness.**
   We built the full real-data pipeline but have not yet run it against a
   live API key.
3. **"Then what, exactly, did you accomplish this semester?"** A working,
   auditable, honestly-labeled system (scraper, 45-feature extractor,
   XGBoost+SHAP pipeline, evaluation harness with leakage safeguards) that
   is *ready* to train on real data the moment it's collected, plus the
   audit that found and fixed the dishonesty in the inherited codebase.
   This is a legitimate scope statement for a Phase-1 review.
4. **"Why didn't you just get the API key weeks ago?"** Fair criticism —
   team process gap, not a technical one. Answer honestly; don't deflect.
5. **"Your negatives are pages that already rank. Doesn't that make this
   trivial / useless?"** It constrains the claim: we predict
   cited-vs-not-cited *among already-competitive pages*, not
   citable-vs-the-whole-web. **Partially fixable**: documented explicitly,
   not hidden.
6. **"A single API call per query — how do you know that citation wasn't
   random noise?"** We don't, with `--repeats 1`. `--repeats 3+` exists to
   measure this but hasn't been run. **Real limitation until repeats are run.**
7. **"20 queries. Isn't that absurdly small for 45 features?"** Yes — classic
   curse-of-dimensionality risk; `underpowered` flag in `metrics.json`
   exists specifically to surface this rather than hide it behind a single
   confident-looking number.
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
    NOT YET MEASURED — this is exactly what `domain_type_leakage_check`
    will report once real data exists; we can't claim an answer yet.
25. **"Your tests don't call a live trained model end-to-end — are they
    real tests or just smoke tests?"** They're unit/contract tests
    (feature extraction correctness, SSRF rejection, canonicalization,
    split-leakage guarantee, feature-column train/serve match) — genuinely
    useful, but they do not validate the model's real-world predictive
    accuracy, which can only come from the pilot evaluation run.
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
    what happens?"** It will correctly detect `data/dataset.csv` is
    missing and write a placeholder `metrics.json` with
    `"error": "NOT YET MEASURED..."` rather than crash or fabricate
    numbers — demonstrate this live as proof of the honesty-by-design
    approach if pressed.

## Summary: unfixable-by-Thursday weaknesses (say so plainly if asked)

- No real citation data collected yet (items 1-2, 6-7) — structural,
  depends on API access and time, not something more code can fix by the
  review.
- Small, convenience-sample query list and selection-biased negatives
  (items 5, 7, 17) — inherent to a pilot study at this scale.
- No rate limiting on the API backend (item 13) — a real gap, mitigated
  only by not exposing it publicly for the demo.
- Redundant macro/meso/micro composite features inherited from upstream
  (item 10) — known, not yet re-engineered.
