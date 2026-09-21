# Jev triage stage

TypeSafe/Jev judgments for the weekly scan. Jev is a System One model: it returns
typed answers and calibrated probabilities, not prose. Code keeps the workflow;
Jev supplies the judgment where code needs semantic understanding.

## Why

The weekly scan hands ~40 articles to Claude, which reads every one and decides
Strong / Weak / Noise in prose. That judgment is high-volume, repetitive, and
drifts between runs. Here it becomes four typed questions per article, asked in
one parallel request, with the framework's hard rules applied afterwards in code.

Claude then reads only the survivors and writes the dispatch — the part that is
genuinely generative.

## Layout

| file | role |
|---|---|
| `triage.py` | the four per-article questions + state shaping |
| `policy.py` | framework rules that are policy, not judgment |
| `rubric.py` | the five profile dimensions (phase two — not yet wired in) |
| `run_triage.py` | CLI over a JSON list of articles |
| `benchmark.py` | scores the rubric against already-logged human profiles |
| `test_policy.py` | pins the policy rules; no network |

## Division of labour

Judgments go to Jev. Rules stay in code:

- *"Vendor announcements without independent verification cap at 2."*
- *"Signals rated Peak hype are excluded from the shortlist regardless of other
  dimension scores."*

The second is an absolute exclusion, not a heavy negative weight. Folding it into
a weighted score would let a strong showing elsewhere buy past a rule the
framework states as unconditional.

Because judgments are stored, changing a threshold re-reads them rather than
re-asking the model.

## Hype moved before the filter

The framework's Peak-hype exclusion was being applied *after* the noise filter,
where it had nothing left to exclude — every signal logged since April is
`Grounded`. Hype is now scored on every candidate, which is where the rule was
meant to bite. On the first real-text run the dimension showed actual variance
(Grounded / Ahead of itself / Post-hype).

## What is validated, and what is not

**Triage separates signal from noise.** On 7 real articles with full text — 4 the
2026-09-21 scan logged, 3 it discarded as noise — the classes separated cleanly:

| class | structural probability |
|---|---|
| signal | 0.34 – 0.80 |
| noise  | 0.07 – 0.15 |

Gap of +0.19; any threshold in 0.16–0.34 scores 100%. `STRUCTURAL_THRESHOLD` is
set to 0.25, mid-band. **n=7, and the threshold was tuned on this same set** —
that is evidence of separability, not an independently validated number.

**Corroboration is not calibrated.** Every article scored 0.10–0.39, so at the
0.55 threshold everything lands WEAK. That may be right — single-author
commentary genuinely is weakly corroborated — or the threshold may be too high.
No labelled data exists to tell the two apart, so it is deliberately untuned.

**The five-dimension profile is not wired in.** `benchmark.py` scored it against
149 already-logged human profiles and found evidence strength systematically
*low* — errors of `{0: 5, −1: 4, −2: 3}`, never high. The likely cause is state:
that benchmark fed three-line summaries, and evidence the model cannot see is
evidence it cannot credit. Re-run with full article text before trusting it.

**Confidence does not track correctness** on evidence (0.70 when right, 0.74 when
wrong), hype, or trajectory. Only horizon behaved (0.59 vs 0.27). So
confidence-gating is used for *review flags only* and never overrides an answer.

## Running it

```bash
.venv-jev/bin/python scripts/jev/test_policy.py                    # rules, offline
.venv-jev/bin/python scripts/jev/run_triage.py articles.json       # triage
.venv-jev/bin/python scripts/jev/benchmark.py 25                   # rubric vs human labels
```

Needs `TYPESAFE_API_KEY`; `run_triage.py` and `benchmark.py` read it from `~/.env`.

## Shadow run

Scheduled by the systemd user timer `jev-shadow.timer`, **Mondays 01:30 UTC** —
an hour after the live scan starts, which takes ~25 minutes. `Persistent=true`,
so a week missed while the host was off still runs. `jev-shadow.service` is
ordered `After=weekly-scan.service`, which matters on a catch-up boot when both
timers fire at once: the shadow run compares itself against what the scan
logged, so it must not overtake it.

It observes and changes nothing: no git operations at all, no repo writes, no
dispatch. Its own non-blocking lock, so it can never queue behind or delay the
live scan. Output lands in `logs/jev-shadow/` (gitignored, host-local).

    fetch_candidates.py   12 Tier-2 feeds -> candidates in a 7-day window, full text
    run_triage.py         judgments + policy -> verdicts
    compare-shadow.py     verdicts vs what the live scan actually logged

`sources.py` holds the feed map. Four of the 16 scan sources have no
discoverable feed — The Batch, Every, Anthropic News, Analytics India — and are
listed as `BLIND_SPOTS`, excluded from both accuracy figures. The shadow run
cannot reach them, so their signals are not triage's to miss.

Articles under 500 characters of extracted text are marked UNREADABLE and never
judged: Stratechery is paywalled and OpenAI's newsroom is JS-rendered, so
scoring them would be scoring a headline.

### First full run, 2026-09-21

44 candidates: 26 kept, 9 filtered, 9 unreadable.

| metric | result |
|---|---|
| recall | 5/5 — every article the live scan cited was kept |
| precision | 5/26 — 21 extra articles would reach Claude |

**Recall is the gate.** A false drop loses a signal silently; over-keeping only
costs reading time. Zero false drops across two runs at different scales.

Precision is poor, and honestly the filter is barely earning its place yet — 26
of 35 readable articles kept is not much of a reduction. That is the expected
cost of a threshold deliberately tuned for recall on n=7. Weekly shadow data is
what will justify raising it; do not raise it on a hunch.

## Next

1. Accumulate shadow weeks. Raise `STRUCTURAL_THRESHOLD` only when the data
   shows headroom above the highest false-drop risk.
2. Re-benchmark the profile with full article text.
3. Novelty check against the 149 logged signals; the pipeline has no dedup today.
4. Fetch fallback for paywalled and JS-rendered sources, or accept them as
   permanently human-judged.
