# VIVA_QA.md — Likely Panel Questions and Honest Answers

Grouped by topic. Every answer is checked against this repo's actual code
and `docs/AUDIT.md`; nothing here invents a capability or number the code
doesn't have.

## Problem & motivation

1. **Why does this problem matter?** Generative answer engines (Perplexity,
   ChatGPT search, etc.) synthesize a direct answer and cite only 1-3
   sources, unlike classic search's 10 blue links. A local business that
   isn't cited loses visibility entirely, even if it would have ranked on
   page 1 of Google. No tool today predicts citation likelihood *before*
   publishing — existing tools only report after the fact (trackers) or
   give generic checklists.
2. **How is this different from SEO?** Classic SEO optimizes for ranking
   position based on backlinks/keywords/domain authority. This predicts a
   binary/probabilistic outcome (cited or not) for a fundamentally
   different retrieval+generation process.
3. **Who is the target user?** Local businesses (gyms, clinics, chauffeur
   services, tour operators) who want to understand, before publishing
   content, which page properties correlate with being cited.
4. **What's the deliverable?** A trained, explainable (SHAP) classifier
   plus a web app (Streamlit + optional FastAPI/React) that scores a given
   URL and explains the score.

## SEO grounding (Bataineh et al., 2025)

5. **What did Bataineh et al. (2025, Cogent Business & Management) actually
   study?** An empirical PLS-SEM (Partial Least Squares Structural Equation
   Modeling) study showing content quality, technical SEO, backlinks, and
   mobile-friendliness predict search rankings, **mediated by user
   engagement** — i.e. these factors don't directly cause rank, they
   improve user engagement signals which search engines then reward.
6. **What is PLS-SEM, in plain terms?** A statistical technique for testing
   a network of hypothesized cause-effect relationships between latent
   (not directly observable) constructs, estimated from survey/behavioral
   data, commonly used when sample sizes are moderate and relationships
   are complex/multi-step.
7. **What does R² mean in that context?** The proportion of variance in
   the outcome (e.g. ranking/engagement) explained by the model's
   predictor constructs; a higher R² means the hypothesized factors
   explain more of the variation observed.
8. **How does this project extend that idea?** Bataineh et al. studied
   classical search ranking. We hypothesize an analogous (but distinct)
   relationship for *citation by generative answer engines* — testing
   whether on-page structural/content/schema signals correlate with being
   cited, using a learned (XGBoost) rather than structural-equation model,
   because we don't have latent-construct survey data, only observable
   page features and a binary citation outcome.
9. **Why not replicate PLS-SEM instead of using XGBoost?** PLS-SEM is built
   for theory-testing with latent constructs and survey-scale data; we
   have directly observable numeric features and a binary outcome, which
   a supervised classifier is the standard, appropriate tool for.

## GEO / RAG basics

10. **What is RAG?** Retrieval-Augmented Generation — the AI system
    retrieves relevant documents, then generates an answer grounded in
    them, typically citing sources.
11. **What is GEO/AEO?** Generative/Answer Engine Optimization — optimizing
    content so it's more likely to be retrieved and cited by such systems.
12. **Do we know exactly how Perplexity decides what to cite?** No — it's a
    closed, proprietary system. We only observe inputs (page content) and
    outputs (whether cited), and model the correlation, never the
    mechanism.

## Data and labels

13. **Is your training data real?** The model currently shipped
    (`citation-predictor/models/citation_model.pkl`) is trained on
    **synthetic** data (`model_loader.py: _generate_demo_data`), honestly
    documented in the code and `docs/AUDIT.md`. We built a separate
    real-data pipeline (`pipeline/`) to collect actual Perplexity citations;
    **as of this review, real collection has not been run yet** because it
    requires a paid `PERPLEXITY_API_KEY` we hadn't configured — see
    `STATUS.md`. This is the single most important fact to state plainly
    if asked.
14. **If it's synthetic, is the reported accuracy meaningful?** No — the
    synthetic label is a linear function of the same features the model
    sees, so any AUC/F1 from it is circular (see `docs/AUDIT.md` Q1). We
    do not claim it as evidence of real-world predictive power.
15. **How would the real label be created?** `label=1` if a page's
    canonical URL appears among Perplexity's citations for a query, else
    0 — see `docs/DATA_CARD.md`.
16. **What is the candidate pool?** Union of cited URLs and top organic
    search results (via SerpAPI, or a documented fallback to Perplexity's
    own `search_results` if no SerpAPI key is available).
17. **Why could negatives be biased?** They're drawn only from pages that
    already rank organically for the query, not a random web sample — the
    model therefore learns "cited vs. not-cited among already-competitive
    pages," not "citable vs. the entire web."
18. **How many queries/rows do you have?** NOT YET MEASURED — depends on
    the real collection run; `data/pilot_stats.json` will report the exact
    count once `pipeline/run_all.py` has been executed with real API keys.
19. **Is a single observation per query enough?** No — citation is
    non-deterministic; `--repeats N` in `collect_citations.py` exists
    specifically to measure how often the same query returns the same
    citation set across repeated calls.

## Features

20. **How many features, and what groups?** ~45, in four groups: content
    (word/sentence counts, factual-density heuristics), structure
    (headings, hierarchy score), schema (JSON-LD/microdata types), and
    local-business signals (phone/address/hours/rating detection) — see
    `docs/UNDERSTANDING.md`.
21. **What's `factual_density`, exactly?** A weighted, un-validated
    heuristic: `(numbers*1 + percentages*2 + dates*1.5 + citation_refs*3 +
    ext_links*0.5 + quotes*1.5) / word_count`, capped at 1.0 — explicitly
    documented in the code as "NOT a scientifically validated measure."
22. **Do any features risk leaking the label?** In the synthetic-data
    pipeline, yes, directly — see Q14. In the real pipeline, the main risk
    is `domain_type` (directories/aggregators might be cited for reasons
    unrelated to on-page quality), which is why `evaluate.py` runs a
    dedicated check with/without a `domain_type` flag.
23. **Why do macro/meso/micro composite scores risk double-counting?**
    They're built from the same raw features (e.g. `macro_structure_score`
    uses `h1_count`, `h2_count`, `section_count`, `word_count`,
    `heading_hierarchy_score` — all *also* separate inputs), inflating
    their collective influence beyond what 45 independent signals would
    imply.

## Model choice

24. **Why XGBoost over a neural network/transformer?** At pilot scale
    (tens to low hundreds of rows), gradient-boosted trees on tabular
    features vastly outperform deep learning, train in seconds without a
    GPU, and are natively compatible with exact SHAP TreeExplainer
    attributions — a transformer would need orders of magnitude more
    labeled data and wouldn't be more interpretable.
25. **Why a logistic regression baseline?** To establish whether the
    nonlinear XGBoost model is actually buying predictive power over a
    simple, fully-interpretable linear model — if LR performs comparably,
    that's a sign the relationships are mostly linear/simple, which is
    itself informative given our small n.
26. **Why also a rule-based checklist baseline?** Because that's what
    existing commercial/open-source GEO-audit tools effectively do
    (binary "has schema / has FAQ" checks); we need to show our learned
    model beats that bar to justify the added complexity.
27. **What hyperparameters, and why conservative?** `n_estimators=150,
    max_depth=3, min_child_weight=3, subsample=0.8, colsample_bytree=0.8`
    (`pipeline/evaluate.py`) — shallow trees and subsampling to resist
    overfitting on a small pilot dataset; `scale_pos_weight` compensates
    for class imbalance without needing to drop data.

## SHAP

28. **What does SHAP explain?** Exactly how much each of the 45 input
    features pushed *our XGBoost classifier's* prediction for one specific
    row, away from a baseline (`base_value`), in log-odds space,
    additively (`docs/WHITEBOARD.md` exercise 5).
29. **What does SHAP NOT explain?** It says nothing about Perplexity's
    internal reasoning — we have no access to that model. It explains our
    model's behavior, which is itself only an approximation of real-world
    citation patterns, learned from a small, imperfect sample.
30. **Why TreeExplainer specifically?** It computes exact (not sampled)
    Shapley values for tree ensembles in polynomial time, versus the
    model-agnostic KernelSHAP which is slower and only approximate.

## Evaluation

31. **Why GroupKFold by domain instead of plain K-fold?** Plain K-fold
    could put two pages from the same website in both train and test,
    letting the model "memorize" that domain's style rather than
    generalizing — GroupKFold-by-domain guarantees no domain appears in
    both (verified by `tests/test_split_no_leakage.py`).
32. **Why also check PR-AUC, not just ROC-AUC?** PR-AUC is far less
    sensitive to a large number of true negatives, so it doesn't get
    artificially inflated under class imbalance the way ROC-AUC can.
33. **What does the label-shuffle test show?** We retrain on the same
    features but randomly shuffled labels; if AUC collapses to ~0.5, that
    confirms the real (unshuffled) model's performance isn't an artifact
    of data leakage or evaluation bugs — it's actually learning from the
    label.
34. **What's the feature-group ablation for?** Running XGBoost on
    structural-only, content-only, and authority-only feature subsets
    separately shows which feature family actually carries predictive
    signal, rather than attributing everything to "the model."
35. **How do you compare against the original synthetic-trained model?**
    `evaluate.py`'s `compare_original_repo_model` loads the existing
    `citation_model.pkl` and scores it directly on real pilot data,
    reporting the (expected) performance gap versus its inflated synthetic
    numbers.
36. **What if the dataset is too small to draw conclusions?** We say so
    explicitly — `metrics.json["underpowered"] = true` when usable rows or
    minority-class count fall below documented thresholds, and the UI/docs
    surface that flag rather than hiding it.

## Limitations

37. **Is this causal or correlational?** Purely correlational — we never
    claim changing a feature *causes* more citations (`docs/WHITEBOARD.md`
    exercise 8).
38. **Will this model stay accurate over time?** No — answer engines update
    frequently; the model would need periodic retraining on fresh citation
    data to track behavior drift.
39. **What's the biggest unfixable weakness at this scale?** See
    `docs/KNOWN_WEAKNESSES.md` — small n and selection-biased negatives are
    structural limitations of a pilot study, not implementation bugs.

## Ethics / ToS

40. **Do you respect robots.txt and rate limits?** Yes —
    `scraper.py:_check_robots_txt` checks and caches robots.txt per host;
    every API-calling pipeline script enforces `--max-calls` and
    exponential-backoff retries; see `docs/ETHICS_AND_LIMITS.md`.
41. **Do you collect personal data?** No — only page structure/content and
    business-published contact info (phone/address of a business, not a
    private individual).
42. **Could this be used to manipulate AI systems?** No — every feature is
    a legitimate, publicly-visible content/structure property (headings,
    schema, word counts); we explicitly do not use prompt injection or
    adversarial techniques (`docs/ETHICS_AND_LIMITS.md`).

## Failure-case analysis / what-if

43. **Give a real failure case from the audit.** Before our Phase-2 fix,
    any scrape failure for *any* user-entered URL silently substituted a
    fake "Apex Dental Clinic" fixture and still returned a confident
    score — now fixed to show a clear error instead
    (`docs/AUDIT.md` ranked list item 3).
44. **What would you change with 10x the data/time?** Collect citations
    across more query categories and cities, run `--repeats 3+` on every
    query to directly measure citation non-determinism, add a second
    answer engine for cross-engine validation, and retrain on a rolling
    schedule to track drift.

## Comparison with existing tools

45. **How is this different from the upstream Getcito/Elmo-style tool this
    repo was forked from?** That tool (unrelated to our own work — see
    `README_PROJECT.md`) is a post-hoc AI-visibility *tracker*: it reports
    whether you were already cited/mentioned across AI platforms, after
    the fact. Ours is a *pre-publication predictor*: score a page before
    it's even indexed, with an explicit reason (SHAP) for the score.
46. **How is this different from a checklist-style GEO auditor?** Checklist
    tools give equal, hand-assigned weight to binary signals (schema
    present? FAQ present?). Our rule-based baseline reproduces that
    approach specifically so we can show whether a *learned* weighting
    (XGBoost) actually outperforms it on real data.
