# Docs index

Start here if you're new to this project. Grouped by what you're trying to do.

## Understand the code

- **[UNDERSTANDING.md](UNDERSTANDING.md)** — module-by-module walkthrough, written
  for someone who has never seen this code. Start here.
- **[WHITEBOARD.md](WHITEBOARD.md)** — 8 worked exercises (SHAP math, GroupKFold,
  SSRF, etc.) each team member should be able to reproduce from memory.

## Understand the data

- **[DATA_CARD.md](DATA_CARD.md)** — how the 200 queries were chosen, how
  citations/candidates were collected, the label rule, and known limitations.
- **[PILOT_REPORT.md](PILOT_REPORT.md)** — the collection-stage numbers
  (scrape success rate, class balance), generated directly from
  `data/pilot_stats.json`.

## Honesty / what's real vs. not

- **[AUDIT.md](AUDIT.md)** — the original Phase-1 read-only audit of the
  inherited codebase. A point-in-time snapshot — intentionally never edited
  after it was written, even where later work fixed what it found.
- **[KNOWN_WEAKNESSES.md](KNOWN_WEAKNESSES.md)** — a hostile-examiner pass:
  30 hardest questions, honest answers, which are fixed vs. still real.
- **[ETHICS_AND_LIMITS.md](ETHICS_AND_LIMITS.md)** — what this project does
  and doesn't do (scraping ethics, no personal data, no manipulation).

## Preparing for the review

- **[VIVA_QA.md](VIVA_QA.md)** — likely panel questions with answers checked
  against the actual code and real metrics.
- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** — a 5-minute live-demo walkthrough.
- **[SLIDE_NUMBERS.md](SLIDE_NUMBERS.md)** — every number used in
  `slides/final_review.tex`, traced to the file that produced it.
- **[REPORT_OUTLINE.md](REPORT_OUTLINE.md)** — chapter-by-chapter outline for
  the full written report.
- **[REFERENCES_TODO.md](REFERENCES_TODO.md)** — literature references to cite.
- **[INDIVIDUAL_CONTRIBUTIONS.md](INDIVIDUAL_CONTRIBUTIONS.md)** — module
  assignment per team member.
- **[DIARY_DRAFT.md](DIARY_DRAFT.md)** — draft project diary entries (fill in
  the team-specific narrative before submitting).

## Everything else

- **[../STATUS.md](../STATUS.md)** — running session-by-session log of what's
  been done, in what order, and why — the most reliable source for "what's
  the current state of things."
- **[../README_PROJECT.md](../README_PROJECT.md)** — install/run instructions
  and what's "our work" vs. the unrelated upstream repo sharing this root.
- **[../web/README.md](../web/README.md)** — the web app's architecture and
  dev workflow.
