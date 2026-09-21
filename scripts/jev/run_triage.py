"""Run triage over candidate articles.

    python scripts/jev/run_triage.py articles.json [--json out.json]

Input is a JSON list of {title, source, url, published, text, first_party?}.
Prints one line per article and, with --json, writes the full record so a
later stage (or a threshold change) can reuse the judgments without re-asking.
"""

import argparse
import json
import os
import pathlib
import sys

from typesafe_sdk import TypeSafeClient

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from policy import classify
from triage import article_state, triage_questions


def load_env(path=pathlib.Path.home() / ".env"):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if line.strip().startswith("TYPESAFE_API_KEY=") and "TYPESAFE_API_KEY" not in os.environ:
            os.environ["TYPESAFE_API_KEY"] = line.split("=", 1)[1].strip().strip("\"'")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("articles", type=pathlib.Path)
    ap.add_argument("--json", dest="out", type=pathlib.Path)
    args = ap.parse_args()

    load_env()
    articles = json.loads(args.articles.read_text())
    questions = triage_questions()
    records = []

    with TypeSafeClient() as client:
        for art in articles:
            try:
                answers = client.system_one(article_state(art), questions)
            except Exception as e:  # noqa: BLE001 - one bad article must not kill the batch
                print(f"  ERROR  {art.get('title','?')[:58]:<58}  {e!r}"[:160])
                records.append({"title": art.get("title"), "error": repr(e)})
                continue

            v = classify(answers, is_first_party_vendor=art.get("first_party", False))
            flag = "keep" if v.keep else "drop"
            short = "" if v.shortlist_eligible else "  [no-shortlist]"
            print(f"  {flag:<4} {v.classification:<6} {art.get('title','?')[:52]:<52} "
                  f"{v.category.split()[0]}{short}")
            for r in v.reasons:
                print(f"         - {r}")
            for r in v.needs_review:
                print(f"         ! {r}")

            records.append({
                "title": art.get("title"),
                "url": art.get("url"),
                "keep": v.keep,
                "classification": v.classification,
                "category": v.category,
                "shortlist_eligible": v.shortlist_eligible,
                "reasons": v.reasons,
                "needs_review": v.needs_review,
                "raw": {
                    "structural": round(answers.nouls["structural"].noul, 3),
                    "corroborated": round(answers.nouls["corroborated"].noul, 3),
                    "hype": answers.choices["hype"].choice,
                    "hype_conf": round(answers.choices["hype"].confidence, 3),
                    "category_conf": round(answers.choices["category"].confidence, 3),
                },
            })

    kept = sum(1 for r in records if r.get("keep"))
    print(f"\n{kept}/{len(records)} kept for reading "
          f"({len(records) - kept} filtered before Claude sees them)")
    if args.out:
        args.out.write_text(json.dumps(records, indent=1))
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
