"""Compare a shadow triage run against what the live scan actually logged.

    python scripts/jev/compare-shadow.py logs/jev-shadow/<date>-verdicts.json

The question that matters is RECALL: did triage drop anything the live scan
thought worth logging? A false drop loses a signal silently. Over-keeping only
costs Claude some reading, so precision is reported but is not the gate.

Sources with no feed (see sources.py BLIND_SPOTS) are excluded from both
figures — the shadow run cannot reach them, so their signals are not triage's
to miss.
"""

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from sources import BLIND_SPOTS

REPO = pathlib.Path(__file__).resolve().parents[2]
WATCH = REPO / "knowledge-system/baseline/zone2-futures-intelligence/06-weak-signal-watch.md"


def norm(url: str) -> str:
    """Domain + path, lowercased, no scheme/query/trailing slash."""
    u = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
    return re.sub(r"[?#].*$", "", u).rstrip("/")


def logged_urls(date: str) -> set[str] | None:
    """URLs cited by the live scan's section for this date, or None if absent."""
    if not WATCH.exists():
        return None
    text = WATCH.read_text()
    marker = f"### Added {date}"
    if marker not in text:
        return None
    section = text.split(marker, 1)[1].split("\n### Added ", 1)[0]
    return {norm(u) for u in re.findall(r"\((https?://[^)\s]+)\)", section)}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = pathlib.Path(sys.argv[1])
    records = json.loads(path.read_text())
    date = re.search(r"(\d{4}-\d{2}-\d{2})", path.name).group(1)

    live = logged_urls(date)
    if live is None:
        print(f"no '### Added {date}' section in the watch log yet "
              f"(live scan unmerged?) - nothing to compare")
        return 1

    kept, dropped, unread = [], [], []
    for r in records:
        if r.get("source") in BLIND_SPOTS:
            continue
        (kept if r.get("keep") is True else unread if r.get("keep") is None else dropped).append(r)

    def cited(r):
        return norm(r.get("url", "")) in live

    false_drops = [r for r in dropped if cited(r)]
    true_keeps = [r for r in kept if cited(r)]
    extra_keeps = [r for r in kept if not cited(r)]
    missed_unread = [r for r in unread if cited(r)]

    print(f"live scan {date} cited {len(live)} distinct URLs")
    print(f"shadow triaged {len(kept)} keep / {len(dropped)} drop / {len(unread)} unreadable "
          f"(blind-spot sources excluded)\n")

    denom = len(true_keeps) + len(false_drops)
    if denom:
        print(f"RECALL   {len(true_keeps)}/{denom} of the scan's cited articles were kept")
    if kept:
        print(f"PRECISION {len(true_keeps)}/{len(kept)} of kept articles were cited by the scan "
              f"({len(extra_keeps)} extra sent to Claude)")

    if false_drops:
        print(f"\nFALSE DROPS - triage discarded what the scan logged ({len(false_drops)}):")
        for r in false_drops:
            p = r.get("raw", {}).get("structural")
            print(f"  structural={p}  {r.get('source','?')}: {str(r.get('title'))[:58]}")
        print("  -> lower STRUCTURAL_THRESHOLD in policy.py, or fix the question")
    else:
        print("\nno false drops: triage kept everything the live scan cited")

    if missed_unread:
        print(f"\nUNREADABLE but cited by the scan ({len(missed_unread)}) - "
              f"fetcher problem, not a judgment problem:")
        for r in missed_unread:
            print(f"  {r.get('source','?')}: {str(r.get('title'))[:58]}")

    out = path.with_name(path.name.replace("-verdicts", "-comparison"))
    out.write_text(json.dumps({
        "date": date,
        "live_cited_urls": len(live),
        "kept": len(kept), "dropped": len(dropped), "unreadable": len(unread),
        "true_keeps": len(true_keeps), "false_drops": len(false_drops),
        "extra_keeps": len(extra_keeps), "unreadable_but_cited": len(missed_unread),
        "false_drop_titles": [r.get("title") for r in false_drops],
    }, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
