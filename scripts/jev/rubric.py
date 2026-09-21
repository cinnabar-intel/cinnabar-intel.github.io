"""Signal-scoring rubric as TypeSafe System One questions.

The five dimensions are defined in
knowledge-system/design/05-signal-scoring-framework.md. Level text here is taken
from that document — when the framework changes, change it there first and mirror
it here, or the profiles stop meaning what the framework says they mean.

Design notes:
  - Evidence, Unlock and Horizon are ordered ladders -> Score.
  - Trajectory and Hype are named patterns with no meaningful order
    (Post-hype is not "more hype" than Peak) -> Choice.
  - All five are independent judgments over the same state, so they go in one
    request and run in parallel.
  - The framework's hard rules (vendor-announcement cap, Peak-hype exclusion)
    are policy, not judgment. They live in policy.py, applied to these answers.
"""

from typesafe_sdk import Choice, Score

# Compact profile codes used in the Weak Signal Watch log, e.g. "E3 T-Ac U2 H-Gr Z-Now".
TRAJECTORY_CODES = {
    "Emerging": "Em",
    "Accelerating": "Ac",
    "Maturing": "Ma",
    "Shifting": "Sh",
}

HYPE_CODES = {
    "Grounded": "Gr",
    "Ahead of itself": "Ah",
    "Peak hype": "Ph",
    "Post-hype": "Poh",
}

HORIZON_CODES = {
    "Now (0-6 months)": "Now",
    "Near (6-18 months)": "Near",
    "Medium (18-36 months)": "Med",
    "Far (3-7 years)": "Far",
}

EVIDENCE_LEVELS = [
    "Theoretical. A paper or concept only, with no working implementation.",
    "Lab or demo. A working prototype under controlled conditions, published by a credible lab. Also the ceiling for a vendor announcement with no independent verification, and for a conference demo with no production evidence.",
    "Early deployment. Real users at limited scale, with published results rather than claims. Peer-reviewed research that has been reproduced starts here.",
    "Scaled deployment. Multiple organizations, measurable production outcomes, and third-party verification.",
    "Industry standard. Widespread and mature, with well-understood tradeoffs.",
]

UNLOCK_LEVELS = [
    "Incremental. Makes an existing process faster or cheaper within the same paradigm.",
    "New application. Lets a new audience do something previously restricted to experts.",
    "Category creation. Makes an entire class of workflows possible that did not exist before.",
    "Paradigm shift. Restructures how industries, roles, or institutions function.",
]

HORIZON_LEVELS = [
    "Now (0-6 months)",
    "Near (6-18 months)",
    "Medium (18-36 months)",
    "Far (3-7 years)",
]


def profile_questions() -> dict:
    """The five framework dimensions as one parallel question set."""
    return {
        "evidence": Score(
            instructions={
                "task": "Rate the strength of evidence that this signal is real, based only on what the supplied source material actually establishes.",
                "judge": "How far this has progressed from concept toward verified, deployed reality.",
                "caution": "Judge the evidence presented, not how important or exciting the development would be if true. A vendor's own announcement is not independent verification.",
            },
            criteria=EVIDENCE_LEVELS,
        ),
        "unlock": Score(
            instructions={
                "task": "Rate what this signal makes newly possible.",
                "judge": "Ask: what becomes possible only because of this, that was not possible before it existed?",
                "caution": "Assess the unlock, not the evidence. Something poorly evidenced can still be paradigm-shifting if real, and a well-proven result can still be merely incremental.",
            },
            criteria=UNLOCK_LEVELS,
        ),
        "horizon": Score(
            instructions={
                "task": "Rate when this becomes actionable — the point at which it should change a decision, not when it was announced.",
                "judge": "Time until a senior practitioner would have to act differently because of it.",
            },
            criteria=HORIZON_LEVELS,
        ),
        "trajectory": Choice(
            instructions={
                "task": "Identify where this sits on its growth curve.",
                "note": "The distinction that matters most is between a curve that is still steepening and one paradigm plateauing while a different one starts underneath it.",
            },
            criteria={
                "Emerging": "A new capability with few data points, at the start of a steep early curve. High uncertainty, high potential.",
                "Accelerating": "In the exponential phase, with each period showing large improvement in cost, capability, or adoption.",
                "Maturing": "Growth is slowing and it is approaching the practical limits of the current paradigm. Diminishing gains, consolidation, 'good enough' discourse.",
                "Shifting": "The old paradigm is plateauing while a new one emerges alongside it. New architectures appearing, incumbents pivoting, 'X is dead' discourse.",
            },
        ),
        "hype": Choice(
            instructions={
                "task": "Judge whether the attention this is receiving is proportional to its substance.",
                "note": "This measures the gap between claims and evidence, not the lifecycle stage and not the quality of the underlying technology.",
            },
            criteria={
                "Grounded": "Claims match evidence. Deployments confirm the narrative, independent benchmarks exist, and discourse is about tradeoffs rather than potential.",
                "Ahead of itself": "Real progress, but claims outpace deployment. Impressive demos, 'coming soon' outnumbering 'we deployed'.",
                "Peak hype": "Massive attention with minimal production evidence. Everyone talking, few building, vendor announcements recycled as news, no independent benchmarks.",
                "Post-hype": "Attention has dropped but real builders are still shipping. Fewer headlines, more commits; honest assessment has replaced breathless coverage.",
            },
        ),
    }
