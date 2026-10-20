# WHITEBOARD.md — 8 Exercises with Solutions

Each student must be able to reproduce these on a whiteboard without
slides. Solutions reference real files/line-level logic in this repo, not
invented behavior.

---

## 1. Draw the full architecture

**Prompt:** Draw the system end to end, from a user typing a URL to seeing
a result.

**Solution (describe while drawing boxes + arrows):**

```
[User] --URL--> [Streamlit UI: streamlit_app.py]
                     |
                     v
          [scraper.py: scrape()]  --(SSRF check, robots.txt check,
                     |                timeout 15s, 5MB cap)
                     v
          [BeautifulSoup HTML tree]
                     |
                     v
       [extractor.py: extract_features()]
                     |
             (45 numeric features)
                     v
     [model_loader.py: get_model() -> XGBoost pipeline]
                     |
              predict_proba()
                     v
           [citation probability 0-1]
                /            \
               v              v
   [shap_explainer.py]   [recommendations.py]
     (per-feature           (rule-based
      contribution)          suggestions)
               \              /
                v            v
          [Results dashboard in Streamlit]
                     |
                     v
          [pdf_report.py: optional PDF export]
```

Say out loud: "There's a second, parallel deployment — FastAPI backend
(`citation-predictor/backend/main.py`) + React frontend
(`citation-predictor/frontend/`) — that calls the exact same
scraper/extractor/model/SHAP modules through `/api/analyze`, so the core
ML logic isn't duplicated, only the UI layer is."

---

## 2. Trace one page from URL to score

**Prompt:** Walk through, step by step, what happens when a user submits
`https://example-gym.com`.

**Solution:**
1. `streamlit_app.py` calls `scrape("https://example-gym.com")`.
2. Inside `scrape()`: `_check_ssrf(url)` resolves the hostname via
   `socket.gethostbyname`, checks it's not localhost/private/cloud-
   metadata; `_check_robots_txt(url)` fetches/caches that host's
   `robots.txt` and checks our user-agent is allowed on that path.
3. `requests.get(..., allow_redirects=False, stream=True)` fetches the
   page; if it's a redirect, the loop re-validates SSRF+robots.txt on the
   new target URL (up to 5 hops) before following it.
4. Response is streamed and capped at 5MB; HTML is parsed with
   BeautifulSoup (`lxml` parser); `<script>/<style>/<svg>` noise tags are
   stripped.
5. `extract_features(soup, url)` runs four feature groups (content,
   structure, schema, local business) plus three derived composite
   scores, returning a dict with a `model_features` sub-dict of exactly
   45 numeric columns.
6. `get_model()` loads the pickled XGBoost pipeline (or trains one on
   synthetic data if no pickle exists — flag this honestly if asked).
7. `row = pd.DataFrame([{col: mf.get(col, 0) for col in feat_cols}])` —
   builds a single-row dataframe in the exact trained column order.
8. `model.predict_proba(row)[0, 1]` — the XGBoost ensemble sums the
   leaf outputs of all its trees for this row and applies a sigmoid to
   get a probability in [0, 1].
9. `shap_explainer.explain(model, feat_cols, mf)` runs
   `shap.TreeExplainer(model)` on the same row to get a per-feature
   contribution breakdown.
10. The Streamlit dashboard renders the probability, SHAP chart, and
    rule-based recommendations.

---

## 3. Boosting on a 6-row toy dataset (work the actual numbers)

**Prompt:** Given this toy dataset (feature = `has_schema`, label =
`cited`), build 2 shallow (depth-1) boosted trees by hand.

| row | has_schema | cited (y) |
|---|---|---|
| 1 | 1 | 1 |
| 2 | 1 | 1 |
| 3 | 1 | 0 |
| 4 | 0 | 0 |
| 5 | 0 | 0 |
| 6 | 0 | 1 |

**Solution (gradient boosting intuition, simplified to regression-on-residuals):**

- **Start:** base prediction = mean(y) = (1+1+0+0+0+1)/6 = **0.5** for every row.
- **Residuals after tree 0:** row1: 0.5, row2: 0.5, row3: -0.5, row4: -0.5, row5: -0.5, row6: 0.5.
- **Tree 1** (depth-1 split on `has_schema`):
  - `has_schema=1` group (rows 1,2,3): mean residual = (0.5+0.5-0.5)/3 = **0.1667**
  - `has_schema=0` group (rows 4,5,6): mean residual = (-0.5-0.5+0.5)/3 = **-0.1667**
  - This single split reduces the group with schema toward higher
    predictions and the group without toward lower — exactly matching
    `citation-predictor`'s hypothesis that `schema_present` is informative,
    *in this toy example*, but note rows 3 and 6 are "wrong" relative to
    this split (schema present but not cited; no schema but cited) — a
    single depth-1 tree can't separate them.
  - **Predictions after tree 1** (with a learning rate η=1 for simplicity):
    `pred = 0.5 + 0.1667` for schema=1 rows ≈ 0.667; `0.5 - 0.1667` for
    schema=0 rows ≈ 0.333.
  - **New residuals:** row1: 1-0.667=0.333, row2: 0.333, row3: 0-0.667=-0.667,
    row4: 0-0.333=-0.333, row5: -0.333, row6: 1-0.333=0.667.
- **Tree 2** would need a second feature to split on to further separate
  rows 3 and 6 from their groups (e.g. `word_count` or `faq_schema`) — this
  is the core idea of boosting: each tree fixes what the previous trees
  got wrong, and with only one feature, two depth-1 trees plateau quickly.
  Real `model_loader.py` uses 150-200 trees of depth 3-4 across 45
  features, which is how it captures interactions a single toy tree can't.

---

## 4. Compute precision/recall/F1 from a confusion matrix

**Prompt:** Given TP=12, FP=4, FN=6, TN=18, compute precision, recall,
F1, and accuracy.

**Solution:**
- Precision = TP / (TP+FP) = 12/16 = **0.75**
- Recall = TP / (TP+FN) = 12/18 = **0.667**
- F1 = 2·(P·R)/(P+R) = 2·(0.75·0.667)/(0.75+0.667) = 2·0.5/1.417 ≈ **0.706**
- Accuracy = (TP+TN)/(TP+FP+FN+TN) = 30/40 = **0.75**
- Class balance here: 18 positive (TP+FN), 22 negative (FP+TN) — fairly
  balanced, so accuracy isn't too misleading in this specific example (but
  `pipeline/evaluate.py` always reports class balance alongside accuracy
  regardless, since real pilot data is likely to be more imbalanced).

---

## 5. SHAP additive breakdown (numbers that actually sum correctly)

**Prompt:** Base value = 0.10 (log-odds). Given these SHAP values, show
the final predicted probability.

| feature | shap_value (log-odds) |
|---|---|
| schema_present | +0.80 |
| word_count | +0.50 |
| faq_schema | +0.30 |
| long_paragraph_count | -0.20 |
| has_phone | -0.10 |

**Solution:**
1. Sum of SHAP values: 0.80+0.50+0.30-0.20-0.10 = **1.30**
2. Final log-odds = base_value + Σshap = 0.10 + 1.30 = **1.40**
3. Convert log-odds to probability: `p = 1 / (1 + e^-1.40)` ≈
   `1 / (1 + 0.2466)` ≈ **0.8022** → **≈80.2% citation likelihood**.
4. This is exactly `shap_explainer.py`'s `base_value` +
   `sum(shap_values.values())` relationship — SHAP values are additive in
   log-odds space for a binary XGBoost classifier, and the sigmoid is
   applied only at the very end to get back to a probability.

---

## 6. How the label is created, and where leakage could occur

**Solution — two label mechanisms exist in this repo, and a panel will
expect you to clearly distinguish them:**

- **Synthetic label (current shipped model, `model_loader.py`):**
  `label = 1 if (factual_density*8 + schema_present*2 + format_diversity*2
  + heading_hierarchy_score*2 + macro_score*2 + meso*1.5 + micro*1.5 +
  citation_ref_count*0.15 + external_link_count*0.05 + faq_schema*1.5 +
  local_business_schema*1.0 + log1p(word_count)*0.3 -
  long_paragraph_count*0.2 + noise) > median else 0`.
  **Leakage:** this formula uses the *exact same columns* the model is
  trained and scored on — the model isn't predicting an independent
  outcome, it's reverse-engineering a known function of its own inputs.
  Any AUC/F1 from this is circular (see `docs/AUDIT.md` Q1).
- **Real pilot label (`pipeline/`, `docs/DATA_CARD.md`):** `label = 1` if
  the page's canonical URL appears in that query's Perplexity citations,
  else 0. **This does not share any term with the feature extractor** — it
  comes from an independent, external API call — so it does not have the
  same circularity problem. **Different leakage risks remain** though:
  negatives are drawn only from already-ranking pages (selection bias, not
  feature leakage), and `domain_type` could leak if directories are
  systematically more/less likely to be cited for reasons unrelated to
  on-page quality — which is exactly why `evaluate.py` runs a dedicated
  `domain_type_leakage_check`.

---

## 7. Pseudocode for the scraper + feature extractor core loop

```
function scrape(url):
    check_ssrf(url)                 # reject localhost/private/cloud-meta
    check_robots_txt(url)           # reject disallowed paths
    for hop in 0..MAX_REDIRECTS:
        response = http_get(url, allow_redirects=False, timeout=15s)
        if response.is_redirect:
            url = resolve(response.location_header)
            check_ssrf(url); check_robots_txt(url)
            continue
        response.raise_for_status()
        break
    else:
        raise ScrapingError("too many redirects")

    bytes = stream_up_to(response, MAX_BYTES=5_000_000)
    html = decode(bytes)
    soup = parse_html(html)
    strip(soup, ["script", "style", "noscript", "svg"])
    return soup

function extract_features(soup, url):
    text = get_visible_text(soup)
    content = extract_content_features(soup, text)       # word/sentence/links/etc.
    structure = extract_structural_features(soup)          # headings/sections
    schema = extract_schema_features(soup)                 # JSON-LD / microdata
    local_business = extract_local_business_signals(soup, text)

    factual_density = compute_factual_density(content, text)
    macro = compute_macro_score(structure, content)
    meso = compute_meso_score(structure, content)
    micro = compute_micro_score(content)

    return flatten_into_45_model_features(
        content, structure, schema, local_business,
        factual_density, macro, meso, micro
    )
```

---

## 8. What happens if FAQ schema is added — and why it's not causation

**Prompt:** If a page adds `faq_schema` (goes from 0 to 1), what happens
to its predicted score, and can we say FAQ schema *causes* more citations?

**Solution:**
- **Mechanically:** `faq_schema` is one of 45 input features. In the
  synthetic-label world, it's directly weighted (`+1.5`) into the label
  formula, so flipping it from 0→1 would mechanically increase the
  synthetic label's underlying score — but that's an artifact of how the
  *fake* label was constructed, not evidence about real engines.
  In the real-pilot XGBoost model (once trained), SHAP would show a
  `faq_schema` SHAP value for that row; if the trees learned a split on
  `faq_schema`, flipping it changes which leaf the row falls into and
  therefore the predicted log-odds by some amount (visible directly in a
  before/after SHAP comparison — this is literally what
  `docs/VIVA_QA.md`'s "what would you change" questions explore).
- **Why this is NOT causation:** the model only ever observed
  *correlation* between `faq_schema=1` and citation in a small, biased
  pilot sample (negatives drawn only from already-ranking pages, single
  noisy observation per query — see `docs/DATA_CARD.md`). Pages with FAQ
  schema might also systematically have more content, better overall SEO,
  or be run by more sophisticated businesses — any of which could be the
  real driver. Proving causation would require a controlled experiment
  (e.g. A/B testing the same page with/without FAQ schema and observing
  citation rates over many repeated real queries), which this project
  does not attempt.
