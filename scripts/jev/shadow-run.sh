#!/bin/bash
# Jev triage shadow run. Observes; changes nothing.
#
# Runs AFTER the live weekly scan (cron 01:30 UTC vs the scan's 00:30 — the scan
# takes ~25 min) and independently collects the same Tier-2 sources, triages
# them, and stores the verdicts. Nothing here touches the repo working tree, git,
# or the dispatch. Compare afterwards with compare-shadow.py.
#
# Safe to run by hand at any time.

set -euo pipefail

REPO_ROOT="/home/sanjayegupta/projects/elite-research-pipeline"
VENV="$REPO_ROOT/.venv-jev/bin/python"
DATE=$(date +%F)
OUT_DIR="$REPO_ROOT/logs/jev-shadow"
LOG="$OUT_DIR/$DATE.log"
CANDIDATES="$OUT_DIR/$DATE-candidates.json"
VERDICTS="$OUT_DIR/$DATE-verdicts.json"

mkdir -p "$OUT_DIR"
exec > >(tee -a "$LOG") 2>&1

echo "==========================================="
echo "Jev shadow run: $(date -u) UTC"
echo "==========================================="

if [[ ! -x "$VENV" ]]; then
  echo "ERROR: venv missing at $VENV - run: python3 -m venv .venv-jev && .venv-jev/bin/pip install typesafe-sdk" >&2
  exit 1
fi

# Its own lock: must never queue behind or block the live scan.
exec 9>"/tmp/jev-shadow.lock"
if ! flock -n 9; then
  echo "another shadow run is active - exiting" >&2
  exit 0
fi

# Read-only against the repo. Deliberately no git operations at all: the live
# scan owns the working tree, and a shadow run must never be able to disturb it.
cd "$REPO_ROOT"

echo "--- collecting candidates (7-day window) ---"
"$VENV" scripts/jev/fetch_candidates.py --days 7 --out "$CANDIDATES"

echo
echo "--- triaging ---"
"$VENV" scripts/jev/run_triage.py "$CANDIDATES" --json "$VERDICTS"

echo
echo "--- comparing against what the live scan logged ---"
# Non-fatal: the live scan's PR may not be merged yet, which is normal.
"$VENV" scripts/jev/compare-shadow.py "$VERDICTS" || \
  echo "(comparison unavailable - live scan for $DATE not merged yet; rerun compare-shadow.py later)"

echo
echo "shadow run complete: $(date -u) UTC"
echo "  candidates: $CANDIDATES"
echo "  verdicts  : $VERDICTS"
