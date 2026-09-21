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

## Next

1. Shadow-run alongside the next weekly scan — compare triage against what Claude
   keeps, without changing output.
2. Re-benchmark the profile with full article text.
3. Novelty check against the 149 logged signals; the pipeline has no dedup today.
