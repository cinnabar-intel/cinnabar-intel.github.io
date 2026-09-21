"""Measure Jev's agreement with the human-assigned profiles already in the log.

The Weak Signal Watch contains months of hand-scored signals. That is a free
gold standard, so calibration is measured against it rather than assumed.

Usage: python scripts/jev/benchmark.py [N]
"""

import json
import os
import pathlib
import re
import sys

from typesafe_sdk import TypeSafeClient

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from rubric import (HORIZON_CODES, HORIZON_LEVELS, HYPE_CODES, TRAJECTORY_CODES,
                    profile_questions)

REPO = pathlib.Path(__file__).resolve().parents[2]
WATCH = REPO / "knowledge-system/baseline/zone2-futures-intelligence/06-weak-signal-watch.md"

ENTRY = re.compile(
    r"^\*\*\[(\d{4}-\d{2}-\d{2})\]\s*\|\s*(.+?)\*\*\s*\n"
    r"\*\*Source:\*\*\s*(.+?)\n"
    r"\*\*Profile:\*\*\s*(.+?)\n"
    r"\*\*Category:\*\*\s*(.+?)\n"
    r"\*\*Why it matters:\*\*\s*(.+?)\n",
    re.M | re.S,
)


def load_env(path=pathlib.Path.home() / ".env"):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("TYPESAFE_API_KEY=") and "TYPESAFE_API_KEY" not in os.environ:
            os.environ["TYPESAFE_API_KEY"] = line.split("=", 1)[1].strip().strip('"\'')


def parse_profile(raw):
    """'E3 T-Ac U2 H-Gr Z-Now' -> dict of the five codes."""
    out = {}
    if m := re.search(r"\bE\s*(\d)", raw):
        out["evidence"] = int(m.group(1))
    if m := re.search(r"\bU\s*(\d)", raw):
        out["unlock"] = int(m.group(1))
    if m := re.search(r"\bT-([A-Za-z]+)", raw):
        out["trajectory"] = m.group(1)[:2].title()
    if m := re.search(r"\bH-([A-Za-z]+)", raw):
        h = m.group(1).lower()
        out["hype"] = {"gr": "Gr", "ah": "Ah", "ph": "Ph", "po": "Poh", "peak": "Ph"}.get(h[:2])
    if m := re.search(r"\bZ-([A-Za-z]+)", raw):
        z = m.group(1).lower()
        out["horizon"] = {"now": "Now", "nea": "Near", "med": "Med", "far": "Far"}.get(z[:3])
    return out


def main():
    load_env()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rows = [
        dict(zip(["date", "name", "source", "profile", "category", "why"], m.groups()))
        for m in ENTRY.finditer(WATCH.read_text())
    ]
    rows = [r for r in rows if len(parse_profile(r["profile"])) == 5][-limit:]
    print(f"benchmarking {len(rows)} labelled signals\n")

    questions = profile_questions()
    results, failures = [], []

    with TypeSafeClient() as client:
        for i, r in enumerate(rows, 1):
            state = {
                "signal": r["name"].strip(),
                "source": r["source"].strip(),
                "why_it_matters": r["why"].strip(),
            }
            try:
                resp = client.system_one(state, questions)
            except Exception as e:  # noqa: BLE001 - surface any API failure, keep going
                failures.append((r["name"][:60], repr(e)[:120]))
                continue

            got = {
                # .score is a probability-weighted float over 0-indexed levels
                "evidence": round(resp.scores["evidence"].score) + 1,   # -> 1-5
                "unlock": round(resp.scores["unlock"].score) + 1,       # -> 1-4
                "horizon": HORIZON_CODES[
                    HORIZON_LEVELS[
                        max(0, min(len(HORIZON_LEVELS) - 1, round(resp.scores["horizon"].score)))
                    ]
                ],
                "trajectory": TRAJECTORY_CODES[resp.choices["trajectory"].choice],
                "hype": HYPE_CODES[resp.choices["hype"].choice],
            }
            results.append({"human": parse_profile(r["profile"]), "jev": got,
                            "name": r["name"].strip()[:70],
                            "raw": {k: round(v.score, 2) for k, v in resp.scores.items()},
                            "conf": {k: round(getattr(v, "confidence", 0.0), 2)
                                     for k, v in list(resp.scores.items()) + list(resp.choices.items())}})
            print(f"  [{i}/{len(rows)}] ok")

    if failures:
        print("\nAPI FAILURES:")
        for n, e in failures[:5]:
            print(" ", n, "->", e)
    if not results:
        print("\nno results - aborting")
        return 1

    print(f"\n{'dimension':<12} {'exact':>7} {'within-1':>9}")
    print("-" * 30)
    for dim in ["evidence", "unlock", "trajectory", "hype", "horizon"]:
        pairs = [(r["human"][dim], r["jev"][dim]) for r in results if r["human"].get(dim)]
        exact = sum(h == j for h, j in pairs) / len(pairs)
        if dim in ("evidence", "unlock"):
            near = sum(abs(h - j) <= 1 for h, j in pairs) / len(pairs)
            print(f"{dim:<12} {exact:>6.0%} {near:>9.0%}")
        else:
            print(f"{dim:<12} {exact:>6.0%} {'-':>9}")

    json.dump(results, open("/tmp/jev_benchmark.json", "w"), indent=1)
    print(f"\nn={len(results)}  detail -> /tmp/jev_benchmark.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
