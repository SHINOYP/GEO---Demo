# Final Report Outline (target: >=25 pages, >=15 journal references with impact factors)

Chapter-by-chapter outline with a suggested page budget. "Derivable now"
sections already have real content to draw from this repo; "TODO (team)"
sections need material only the team can supply (screenshots, personal
reflections, guide feedback, final numbers once the pilot runs).

| # | Chapter | Pages | Status |
|---|---|---|---|
| 1 | Abstract | 1 | TODO (team) — write last, once Results is final |
| 2 | Introduction | 2 | Derivable now |
| 3 | Literature Review | 4 | Derivable now (see below) |
| 4 | Problem Statement | 1 | Derivable now |
| 5 | Existing Methodology | 3 | Derivable now |
| 6 | Proposed Methodology | 3 | Derivable now |
| 7 | System Design | 2 | Derivable now |
| 8 | Dataset and Pipeline | 3 | Partially derivable — real numbers pending pilot run |
| 9 | Implementation | 2 | Derivable now |
| 10 | Results and Analysis | 3 | Blocked until pipeline.evaluate has run on real data |
| 11 | Limitations | 1 | Derivable now |
| 12 | Conclusion and Future Work | 1 | Derivable now |
| 13 | References | 2 | Partially derivable — 9 of ~24 references identified |
| 14 | Appendix | 2 | Derivable now (feature table, glossary) |
| | Total | ~30 | |

## 1. Abstract (1 page)
TODO (team): one paragraph each on problem, approach, and headline result —
write only once Chapter 10 has real numbers.

## 2. Introduction (2 pages)
- The shift from classical search (10 blue links, ranked by backlinks,
  keywords, domain authority) to generative answer engines that synthesize
  one paragraph and cite only 1-3 sources.
- Why this matters for local businesses specifically (visibility in AI
  answers is becoming a new acquisition channel).
- Research question: "How likely is a webpage to be cited by a generative
  AI answer engine, and why?"

## 3. Literature Review (4 pages)
- SEO empirical grounding: Bataineh et al. (2025), Cogent Business &
  Management — PLS-SEM study showing content quality, technical SEO,
  backlinks, and mobile-friendliness predict rankings via user engagement
  (mediation). Explain what PLS-SEM is, what was measured, and what an
  R-squared value means here, in plain terms for a reader with no stats
  background.
- GEO/AEO and LLM-citation literature: Xie et al. 2025 (ACM TOIS 44(2)),
  Li et al. 2025 (ACM TOIS 43(3)), Huang et al. 2025 (ACM TOIS 43(2)),
  Yang et al. 2024 (IEEE TKDE), Aggarwal et al. (KDD 2024), Bagga et al.
  (arXiv 2511.20867), Chen et al. (arXiv 2509.08919), Kalai et al. 2026
  (Nature) — see docs/REFERENCES_TODO.md for venue types and what still
  needs verifying.
- Gap this project addresses: existing GEO tools are either post-hoc
  trackers (report whether you were cited, after the fact — e.g. the
  upstream Getcito/Elmo-style tool this repo's Streamlit shell was built
  alongside) or static rule checklists (schema present? FAQ present?);
  neither is a learned, explainable, pre-publication predictor.
- TODO (team): need ~15 total journal references with verified impact
  factors; currently 9 are identified (mixed journal/conference/arXiv).

## 4. Problem Statement (1 page)
Derivable from the project proposal plus Chapter 2 framing.

## 5. Existing Methodology (3 pages)
- Post-hoc AI-visibility trackers (what Getcito/Elmo-style tools do:
  monitor after the fact whether a brand was mentioned/cited; no
  predictive or explanatory model of why).
- Static GEO/SEO checklist auditors (binary "best practice present?"
  scoring, no learning from outcomes) — this project re-implements one
  as the rule_based_checklist baseline in pipeline/evaluate.py precisely
  so it can be compared fairly against the learned model.
- Classical SEO ranking-factor studies (Bataineh et al. 2025) — correlate
  page/site factors with search-engine rank, not with LLM citation.

## 6. Proposed Methodology (3 pages)
- Formulate citation likelihood as a supervised binary classification
  problem: given a page's structural/content/schema/local-business
  features, predict P(cited=1) for a given query.
- Pipeline: query set -> citation collection (Perplexity sonar) -> candidate
  pool (cited union organic) -> scrape + feature-extract -> label by
  canonical-URL match -> train/evaluate (rule-based, logistic regression,
  XGBoost) -> SHAP explainability -> recommendations.
- Explicit scope limits: correlational, not mechanistic; SHAP explains
  this classifier, not the underlying LLM. State this plainly — it is a
  defensible, deliberate scope choice, not an oversight.

## 7. System Design (2 pages)
- Architecture diagram (see docs/UNDERSTANDING.md for a Mermaid version):
  Streamlit UI / FastAPI+React dual deployment -> scraper -> feature
  extractor -> XGBoost model -> SHAP explainer -> recommendations/PDF.
- Data flow diagram for the pipeline (pipeline/*.py).

## 8. Dataset and Pipeline (3 pages)
- pipeline/queries.csv: 100 queries, 4 categories (gyms in Kerala,
  chauffeur services in GCC cities, kayaking tours, dental clinics).
- Label rule and known limitations: see docs/DATA_CARD.md verbatim.
- Real counts (dataset size, scrape success rate, class balance,
  citations-per-query) are NOT YET MEASURED — pending a real run of
  pipeline.run_all once PERPLEXITY_API_KEY is available. Pull these
  automatically from data/pilot_stats.json once it exists; never
  hand-type them.

## 9. Implementation (2 pages)
- Key modules and why each tool was chosen (requests+BeautifulSoup for
  scraping, XGBoost for the classifier, SHAP for explainability, Streamlit
  for the demo UI) — draw directly from docs/UNDERSTANDING.md.
- Security/robustness measures actually implemented: SSRF guard with
  redirect re-validation, robots.txt compliance, timeouts, response size
  cap (citation-predictor/backend/scraping/scraper.py).

## 10. Results and Analysis (3 pages)
Blocked until python -m pipeline.evaluate has been run against real
pilot data. Once it has:
- Pull ROC-AUC/PR-AUC/F1/precision/recall (mean ± std) for all three
  models (rule-based, logistic regression, XGBoost) directly from
  artifacts/metrics.json.
- Report the label-shuffle control result (expect AUC approx 0.5 — if
  not, investigate leakage before trusting anything else).
- Report the feature-group ablation (structural/content/authority/all).
- Report the domain-type leakage check (with/without a directory flag).
- Report SHAP stability across folds and the calibration/Brier score.
- If artifacts/metrics.json["underpowered"] == true, say so explicitly
  and frame results as preliminary, not as strong evidence.

## 11. Limitations (1 page)
Pull directly from the Streamlit Model Card page and docs/DATA_CARD.md:
small n, negatives biased toward already-ranking pages, citation
non-determinism, correlational not mechanistic, engine drift requiring
periodic retraining.

## 12. Conclusion and Future Work (1 page)
- What Semester 7 (this review) delivered vs. the Semester 8 plan: scale
  to more queries/engines, --repeats runs for label stability, retraining
  cadence, more domains/categories.

## 13. References (2 pages)
See docs/REFERENCES_TODO.md. Do not invent citations or impact factors —
every new reference added must be verified on Clarivate JCR or Scimago
before inclusion.

## 14. Appendix (2 pages)
- Full 45-feature table (name, type, computation, group) — pull from
  docs/AUDIT.md Q3 table, re-verified against
  citation-predictor/backend/features/extractor.py.
- Viva-safe glossary — reuse the glossary section of docs/UNDERSTANDING.md.
