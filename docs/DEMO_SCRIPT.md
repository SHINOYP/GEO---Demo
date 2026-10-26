# Demo Script (5 minutes)

**Status note (keep this current):** the real-data pilot has now run to
completion (300 queries, 592 usable rows — see `STATUS.md` and
`docs/PILOT_REPORT.md`), via manual citation collection
(`collection_method="manual_web_ui"`), not the `PERPLEXITY_API_KEY` path
originally planned — the team had no budget for the paid API. The raw
scraped pages from that run sit in `data/html_cache/` as content-hashed
`.html` files with no cited/not-cited label attached to the filename, so
none of them have been picked out, verified, and wired in as curated
"one cited, one not-cited, one borderline" demo presets. Until that
curation happens, Step 3 below intentionally keeps using the two
hand-written fixtures already in `streamlit_app.py`
(`SAMPLE_HTML_FIXTURES`: "Apex Dental Clinic" and a thin "Handyman"
site), which are clearly labeled **DEMO FIXTURE** in the UI, not real
pilot pages. If someone curates 3 labeled real snapshots into
`SAMPLE_HTML_FIXTURES`, swap this script's Step 3 to use those and update
this note.

## What to click, what to say

1. **Open the app** (`streamlit run streamlit_app.py`). Say: *"This predicts
   whether a generative AI answer engine — Perplexity, ChatGPT-style search
   — is likely to cite a given webpage, and explains why using SHAP."*

2. **Analyze page.** Pick a real, fast-loading public URL you trust
   (e.g. a Wikipedia article) and click **Analyze**. Say:
   *"This is a live scrape — if it fails, the app tells you exactly why
   instead of silently making something up."* Point at the probability,
   the Citation Tier tile, and the disclaimer caption under the button.

3. **Demo preset fallback.** Select "Apex Dental Clinic" from the
   dropdown. Point at the **Demo fixture** warning banner that appears in
   the results — say: *"We only ever show this banner when a preset is
   explicitly chosen; a real URL that fails to scrape shows an error, not
   a fake result."*

4. **"Why this score" tab.** Point at the green/red bars. Say: *"SHAP explains
   this XGBoost classifier's own prediction, feature by feature — it does not
   explain how the underlying LLM decided what to cite."*

5. **Model Card page.** Point at the dataset size, the label
   rule, and the limitations list. Say: *"We're upfront that this is a
   small pilot and the result is correlational, not causal."* If
   `artifacts/metrics.json` doesn't exist yet, the page will honestly say
   "Not yet evaluated" — say that out loud rather than hiding it.

## Fallback plan for each failure

| Failure | Fallback |
|---|---|
| No internet | Use the "Apex Dental Clinic" demo preset — it's a local HTML fixture, no network needed once the app/model are loaded. |
| Target site blocks scraping / robots.txt disallows it / times out | The app now shows a clear error message (not a fake substitute). Switch to a different real URL, or to the demo preset, and explain the error message out loud as a *feature* ("notice it tells us exactly why, instead of guessing"). |
| Streamlit crashes | Have a terminal ready with `streamlit run streamlit_app.py` to restart quickly; keep a second laptop/browser tab with the app already open as backup if possible. |
| API key missing (pipeline features, not the live app) | The live analysis page and Model Card page work with zero API keys — only `pipeline/collect_citations.py` needs one, and that's a backend data-collection step, not part of the interactive demo. If asked, say so honestly. |
