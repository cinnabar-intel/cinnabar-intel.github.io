# Possibilities with Probabilities — Newsletter Template

**Brand:** Possibilities with Probabilities
**Cadence:** Weekly, Monday evening IST (post weekly-scan merge)
**Audience:** Senior execs, AI strategy practitioners, founders — people who read Stratechery and Import AI
**Input:** Last week's weekly-scan signals (`knowledge-system/baseline/zone2-futures-intelligence/06-weak-signal-watch.md`) + weak-signal clusters at the bottom of that file
**Length target:** 900–1,200 words. Readable in 6 minutes.

---

## Design principles

Borrowed deliberately from three newsletters that defined the genre:

| From | What we steal | What we don't |
|---|---|---|
| **Not Boring** (Packy McCormick) | Narrative arc, one hero visual, personality in the prose | Meme density, long-form tangents — we stay tight |
| **Stratechery** (Ben Thompson) | One clean thesis per issue, strategic POV over news | Paywall, daily cadence — we're weekly + free |
| **Import AI** (Jack Clark) | "Why it matters" framing, "What to watch for" close | Full paper digests — our scan already does that |

**Visual storytelling without infographics:** strong typographic hierarchy, one embedded chart or callout *only if the data genuinely demands it*, no stock hero images, no dense visual abstractions. The prose does the work.

**House voice:** Calm, specific, opinionated. Odds over adjectives. Respect the reader — they already know what GPT-5 is.

---

## Structure (fixed)

```
# Possibilities with Probabilities
## Issue #[N] | Week of [date]

> [Cold-open thesis — 2 sentences. What this week was really about.]

---

### Signal of the Week — [headline]

[~250 words. The one story that matters most. Structure:
1. What happened (1 sentence — no fluff)
2. Why it's different from what came before (2-3 sentences)
3. Probability call: odds on the next inflection (1-2 sentences)
4. What to watch for next (1 sentence)
]

*[optional inline callout box only if a chart earns its place]*

---

### Three Things That Actually Moved

**1. [Headline in sentence case]** ~80 words. Why-it-matters framing. Link to source.

**2. [Headline]** ~80 words.

**3. [Headline]** ~80 words.

---

### Weak Signals Worth Watching

- **[Topic]** — one-liner. [source link]
- **[Topic]** — one-liner. [source link]
- **[Topic]** — one-liner. [source link]

---

### The Probability Call

> *[Signature one-paragraph bet with explicit odds and reasoning. Example: "65% chance a third frontier lab adopts defender-first release by end of Q3. Under 5% that any US state passes Illinois-style liability immunity this year. Together they'd convert norm emergence into regime — watch California and New York."]*

---

### For Executives Leading AI Transformation

This newsletter is written for senior leaders learning AI while already leading teams through AI adoption. If that's the seat you're in:

- **Reply with the one signal you're tracking this week.** The sharpest responses shape future issues.
- **Forward to a peer** wrestling with the same decisions — transformation is faster with a second read.
- **Book a 30-min strategic conversation** when you need a second opinion on a transformation decision → [link TBD]

---

*Possibilities with Probabilities — Sanjay Gupta*
*Reply with a sharper take, a disagreement, or a signal I missed.*
*Methodology: scan.mkdocs link | Archive: pages.link*
```

---

## Sourcing rules

Every signal cited must be traceable to the scan log. If a claim is NOT in the scan log, it doesn't enter the newsletter. This protects the integrity of the signal-to-publication chain.

Every external URL in the issue must resolve (no `TODO` URLs, no paywalled links without `[paywall]` marker).

---

## Automation boundary (for the future skill)

The skill that auto-drafts this newsletter reads:
1. Last 7 days of `## Active Signals Log` entries (the most recent `### Added YYYY-MM-DD` block)
2. The weak-signal cluster summaries at the bottom of the file
3. This template

It proposes:
- The "Signal of the Week" pick (Claude argues ranked reasoning, human picks)
- First-draft "Three Things That Moved" selections
- A probability call stub (human writes the signature bet)

It does NOT publish. It opens a PR with `newsletter/issues/YYYY-MM-DD-issue-NN.md`. Human reviews, edits, merges, publishes via MkDocs deployment.
