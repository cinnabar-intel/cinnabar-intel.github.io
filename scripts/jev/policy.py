"""Framework rules that are policy, not judgment.

These are deliberately NOT asked of the model. They are stated as rules in
knowledge-system/design/05-signal-scoring-framework.md, so they belong in code
where they are auditable, testable, and changeable without re-running inference:

  - "Vendor announcements without independent verification cap at 2."
  - "Signals rated Peak hype are excluded from the shortlist regardless of
     other dimension scores."

The second is an absolute exclusion, not a heavy negative weight. Folding it
into a weighted score would let a strong showing elsewhere buy its way past a
rule the framework states as unconditional.

Thresholds below are starting points. They are the knobs to tune once real-run
data exists; changing one costs nothing, because it re-reads stored judgments
rather than re-asking the model.
"""

from dataclasses import dataclass, field

# Probability above which a Noul counts as yes.
#
# STRUCTURAL = 0.25 is measured, not guessed. On a 7-article set (4 signals the
# 2026-09-21 scan logged, 3 the same scan discarded as noise) the two classes
# separated cleanly: signals 0.34-0.80, noise 0.07-0.15. Any threshold in
# 0.16-0.34 scores 100%; 0.25 sits mid-band, ~0.09 clear of both edges.
# n=7 demonstrates separability, not a tuned value - widen the set before
# trusting the exact number, and prefer erring low so a borderline article
# reaches a human rather than being dropped silently.
STRUCTURAL_THRESHOLD = 0.25

# CORROBORATED has NOT been calibrated. On the same set every article scored
# 0.10-0.39, so at 0.55 everything classifies WEAK and the distinction stops
# doing work. That may be correct (commentary and single-author analysis really
# are weakly corroborated) or the threshold may be too high - there is no
# labelled corroboration data yet to tell the two apart. Leave it until a real
# run produces some, and do not tune it blind.
CORROBORATED_THRESHOLD = 0.55

# Choice confidence below which the category assignment is not trusted on its
# own. Benchmarking showed confidence does not track correctness on every
# dimension, so this gates review only - it never overrides the answer.
CATEGORY_CONFIDENCE_FLOOR = 0.35

VENDOR_EVIDENCE_CAP = 2


@dataclass
class Verdict:
    """What code decided, and why. Every field is explainable to a human."""

    keep: bool
    classification: str          # STRONG | WEAK | NOISE
    category: str
    shortlist_eligible: bool
    reasons: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)


def classify(answers, *, is_first_party_vendor: bool = False) -> Verdict:
    """Apply framework policy to one article's triage answers.

    `answers` is the SystemOneResult from triage_questions().
    `is_first_party_vendor` comes from the source directory, not from the model:
    whether the publisher is the party whose product the article is about.
    """
    structural = answers.nouls["structural"].noul
    corroborated = answers.nouls["corroborated"].noul
    hype = answers.choices["hype"].choice
    category = answers.choices["category"].choice
    category_conf = answers.choices["category"].confidence

    reasons: list[str] = []
    needs_review: list[str] = []

    if structural < STRUCTURAL_THRESHOLD:
        reasons.append(f"not a structural development (p={structural:.2f})")
        return Verdict(False, "NOISE", category, False, reasons, needs_review)

    # Peak hype is an absolute bar on the shortlist, never a weight.
    shortlist_eligible = hype != "Peak hype"
    if not shortlist_eligible:
        reasons.append("Peak hype - excluded from shortlist by framework rule")

    if corroborated >= CORROBORATED_THRESHOLD:
        classification = "STRONG"
        reasons.append(f"independently corroborated (p={corroborated:.2f})")
    else:
        classification = "WEAK"
        reasons.append(f"single-source or self-reported (p={corroborated:.2f})")

    if is_first_party_vendor and corroborated < CORROBORATED_THRESHOLD:
        needs_review.append(
            f"first-party vendor source without independent verification - "
            f"Evidence Strength caps at {VENDOR_EVIDENCE_CAP}"
        )

    if category_conf < CATEGORY_CONFIDENCE_FLOOR:
        needs_review.append(f"low category confidence ({category_conf:.2f}) - confirm placement")

    return Verdict(True, classification, category, shortlist_eligible, reasons, needs_review)


def evidence_ceiling(is_first_party_vendor: bool, corroborated: float) -> int | None:
    """The framework's vendor cap, for the phase-two profile scorer."""
    if is_first_party_vendor and corroborated < CORROBORATED_THRESHOLD:
        return VENDOR_EVIDENCE_CAP
    return None
