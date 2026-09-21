"""Policy tests. No network: answers are stubbed, so these pin the RULES.

Run: .venv-jev/bin/python scripts/jev/test_policy.py
"""

import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from policy import CORROBORATED_THRESHOLD, STRUCTURAL_THRESHOLD, classify


def answers(structural, corroborated, hype="Grounded", category="04 AI Governance & Ethics", cat_conf=0.8):
    return SimpleNamespace(
        nouls={"structural": SimpleNamespace(noul=structural),
               "corroborated": SimpleNamespace(noul=corroborated)},
        choices={"hype": SimpleNamespace(choice=hype, confidence=0.6),
                 "category": SimpleNamespace(choice=category, confidence=cat_conf)},
    )


def main():
    failures = []

    def check(name, cond):
        print(f"  {'PASS' if cond else 'FAIL'}  {name}")
        if not cond:
            failures.append(name)

    print("policy rules:")

    v = classify(answers(0.05, 0.9))
    check("below structural threshold -> NOISE, dropped", not v.keep and v.classification == "NOISE")

    v = classify(answers(0.80, 0.90))
    check("structural + corroborated -> STRONG, kept", v.keep and v.classification == "STRONG")

    v = classify(answers(0.80, 0.10))
    check("structural, uncorroborated -> WEAK, kept", v.keep and v.classification == "WEAK")

    v = classify(answers(0.90, 0.95, hype="Peak hype"))
    check("Peak hype -> kept but shortlist-ineligible", v.keep and not v.shortlist_eligible)

    v = classify(answers(0.99, 0.99, hype="Peak hype"))
    check("Peak hype exclusion is absolute, not outweighed", not v.shortlist_eligible)

    v = classify(answers(0.80, 0.10), is_first_party_vendor=True)
    check("first-party + uncorroborated -> flags evidence cap",
          any("caps at 2" in r for r in v.needs_review))

    v = classify(answers(0.80, 0.90), is_first_party_vendor=True)
    check("first-party but corroborated -> no cap flag",
          not any("caps at" in r for r in v.needs_review))

    v = classify(answers(0.80, 0.90, cat_conf=0.10))
    check("low category confidence -> review flag, answer kept",
          any("category confidence" in r for r in v.needs_review) and v.keep)

    # boundary behaviour
    v = classify(answers(STRUCTURAL_THRESHOLD, 0.9))
    check("exactly at structural threshold -> kept", v.keep)
    v = classify(answers(STRUCTURAL_THRESHOLD - 0.001, 0.9))
    check("just below structural threshold -> dropped", not v.keep)
    v = classify(answers(0.9, CORROBORATED_THRESHOLD))
    check("exactly at corroborated threshold -> STRONG", v.classification == "STRONG")

    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
