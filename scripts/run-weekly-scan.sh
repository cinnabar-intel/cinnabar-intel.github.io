#!/bin/bash
# Weekly Tier 2 source scan — Mon 00:30 UTC = 6 AM IST.
#
# SCHEDULED BY CRON, not systemd. The unit files in scripts/systemd/ exist but
# were never installed (`systemctl --user is-enabled weekly-scan.timer` reports
# not-found, and ~/.config/systemd/user/ has no weekly-scan.*). That matters:
# cron has NO catch-up, so the Persistent=true behaviour those unit files
# describe — a missed run firing on next boot — does not apply. If the host is
# asleep at 00:30 UTC on a Monday, the week is simply skipped. Installing the
# timers would restore catch-up; until then, treat a skipped week as possible.
#
# Uses Accenture Claude subscription via headless `claude --print` invocation.
# Opens a PR for human review. Never pushes to master directly.

set -euo pipefail

# Single-instance lock, shared with the monthly scan (same repo, same working
# tree). A delayed run (e.g. systemd Persistent catch-up) waits up to 2h for
# the other scan to finish instead of corrupting its checkout.
LOCK_FILE="/tmp/elite-research-scan.lock"
exec 9>"$LOCK_FILE"
if ! flock -w 7200 9; then
  echo "ERROR: could not acquire scan lock within 2h — another scan still running?" >&2
  exit 1
fi

REPO_ROOT="/home/sanjayegupta/projects/elite-research-pipeline"
DATE=$(date +%F)
BRANCH="claude/weekly-scan-$DATE"
LOG_DIR="$REPO_ROOT/logs/weekly-scans"
LOG_FILE="$LOG_DIR/$DATE.log"
PROMPT_FILE="$REPO_ROOT/scripts/weekly-scan-prompt.md"
TARGET_FILE="knowledge-system/baseline/zone2-futures-intelligence/06-weak-signal-watch.md"
DISPATCH_FILE="digest/src/pages/index.astro"
AUDIO_SCRIPT_FILE="digest/audio-scripts/${DATE}.md"
AUDIO_MP3_FILE="digest/public/audio/${DATE}.mp3"

mkdir -p "$LOG_DIR"

# Send all output to both stdout and log file
exec > >(tee -a "$LOG_FILE") 2>&1

echo "==========================================="
echo "Weekly scan starting: $(date -u) UTC"
echo "==========================================="

cd "$REPO_ROOT"

# On any failure after branch creation, restore master and delete the scan
# branch so the next run starts clean. (2026-05-11 incident: budget-exceeded
# exit left the repo on the scan branch with a dirty tree.)
SCAN_BRANCH_ACTIVE=0
cleanup() {
  local rc=$?

  # Always record the outcome. A failed scan used to leave nothing but a short
  # log nobody reads, so a lost week looked identical to a quiet week.
  if (( rc == 0 )); then
    echo "ok $DATE $(date -u +%FT%TZ)" > "$LOG_DIR/LAST-RUN-STATUS"
    rm -f "$LOG_DIR/FAILED-$DATE.txt"
  else
    echo "FAILED $DATE rc=$rc $(date -u +%FT%TZ)" > "$LOG_DIR/LAST-RUN-STATUS"
    {
      echo "Weekly scan FAILED"
      echo "  date : $DATE"
      echo "  exit : $rc"
      echo "  when : $(date -u +%FT%TZ)"
      echo "  log  : $LOG_FILE"
      echo
      echo "Last 20 log lines:"
      tail -20 "$LOG_FILE" 2>/dev/null | sed 's/^/    /'
    } > "$LOG_DIR/FAILED-$DATE.txt"
    echo "ERROR: wrote failure marker $LOG_DIR/FAILED-$DATE.txt" >&2
    # Best-effort desktop toast; never let notification failure mask the real rc.
    powershell.exe -NoProfile -Command \
      "New-BurntToastNotification -Text 'Cinnabar scan FAILED','$DATE exit $rc'" \
      >/dev/null 2>&1 || true
  fi

  if (( rc != 0 && SCAN_BRANCH_ACTIVE == 1 )); then
    echo "ERROR: scan failed (exit $rc) — restoring master, deleting $BRANCH" >&2
    git checkout --force master 2>/dev/null || true
    git clean -fd -- digest/audio-scripts digest/public/audio digest/src/pages/issues 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
  fi
}
trap cleanup EXIT

# Ensure clean state on master.
# --force: discard partial tracked-file edits left by a previously failed run.
# git clean: remove untracked scan artifacts, restricted to the paths the scan
# creates (never a blanket clean — other untracked work in the repo is kept).
git checkout --force master
git clean -fd -- digest/audio-scripts digest/public/audio digest/src/pages/issues

# Wait for network before touching the remote. (2026-09-14 incident: the timer
# fired while the host had no DNS, `git pull` failed on the first line, and the
# whole week's scan was lost silently. Persistent=true only re-fires a *missed*
# run, never a failed one.)
wait_for_network() {
  local attempt deadline=$((SECONDS + 1800))   # give a waking host up to 30 min
  for ((attempt = 1; ; attempt++)); do
    # GIT_TERMINAL_PROMPT=0 + timeout: never block on a credential prompt or a
    # stalled DNS lookup. A hung probe would be worse than the failure it guards.
    if GIT_TERMINAL_PROMPT=0 timeout 30 \
         git ls-remote --exit-code origin HEAD >/dev/null 2>&1; then
      (( attempt > 1 )) && echo "network reachable after $attempt attempts"
      return 0
    fi
    if (( SECONDS >= deadline )); then
      echo "ERROR: no network after 30 min ($attempt attempts) - giving up" >&2
      return 1
    fi
    echo "network unreachable (attempt $attempt), retrying in 60s..."
    sleep 60
  done
}
wait_for_network

git pull origin master

# Abort if branch already exists (idempotency — don't overwrite prior scan)
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "ERROR: Branch $BRANCH already exists locally. Investigate manually."
  exit 1
fi

if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  echo "ERROR: Branch $BRANCH already exists on origin. Investigate manually."
  exit 1
fi

git checkout -b "$BRANCH"
SCAN_BRANCH_ACTIVE=1

# Run Claude Code in headless mode with Sonnet 4.6
# --print: non-interactive, output to stdout
# --permission-mode bypassPermissions: auto-approve all tools (needed for non-interactive web scans)
# --allowedTools: explicit whitelist — defense-in-depth alongside bypass mode
# --model sonnet: use Sonnet 4.6 (~5x cheaper than Opus, sufficient for web research synthesis)
# --max-budget-usd: safety ceiling to prevent runaway spend
# --output-format text: simple text output
# timeout 3600: wall-clock ceiling — a hung claude process must not block the
# working tree past the next scheduled run (budget caps spend, not time).
timeout 3600 claude \
  --print \
  --permission-mode bypassPermissions \
  --allowedTools "WebSearch" "WebFetch" "Read" "Write" "Edit" "Glob" "Grep" "Bash" \
  --model sonnet \
  --max-budget-usd 10.00 \
  --output-format text \
  < "$PROMPT_FILE"

# Commit and push only if there are changes to the target file (the scan log).
# The dispatch is a downstream artifact — only included if it also changed.
if git diff --quiet -- "$TARGET_FILE"; then
  echo "No changes to $TARGET_FILE — skipping commit and PR"
  git checkout master
  git branch -D "$BRANCH"
  echo "Scan complete (no signals found): $(date -u) UTC"
  exit 0
fi

# Stage the scan log (always) and the dispatch (if Claude updated it).
# Stage only this allowlist — defensive against unrelated modifications.
git add "$TARGET_FILE"
DISPATCH_NOTE="Dispatch: not modified (scan only)"
AUDIO_NOTE="Audio: not generated"

if ! git diff --quiet -- "$DISPATCH_FILE"; then
  # Archive the prior dispatch (HEAD version, before Claude's changes) so readers
  # can browse past issues. Reads issueDate from the committed file, not the
  # working-tree version Claude just wrote.
  PRIOR_DATE=$(git show HEAD:"$DISPATCH_FILE" | grep -oP 'issueDate = "\K[^"]+' | head -1 || true)
  ARCHIVE_PAGE="digest/src/pages/issues/${PRIOR_DATE}.astro"
  ISSUES_JSON="digest/src/data/issues.json"

  if [[ -n "$PRIOR_DATE" && ! -f "$ARCHIVE_PAGE" ]]; then
    mkdir -p "$(dirname "$ARCHIVE_PAGE")"
    git show HEAD:"$DISPATCH_FILE" | sed \
      -e 's|from "\.\./layouts/|from "../../layouts/|g' \
      -e 's|from "\.\./components/|from "../../components/|g' \
      -e 's|from "\.\./data/|from "../../data/|g' \
      > "$ARCHIVE_PAGE"

    export PRIOR_DATE ISSUES_JSON
    python3 - <<'PYEOF'
import json, os
path = os.environ['ISSUES_JSON']
with open(path) as f:
    issues = json.load(f)
date = os.environ['PRIOR_DATE']
if not any(i['date'] == date for i in issues):
    issues.insert(0, {'date': date})
with open(path, 'w') as f:
    json.dump(issues, f, indent=2)
    f.write('\n')
PYEOF

    git add "$ARCHIVE_PAGE" "$ISSUES_JSON"
    echo "Archived dispatch $PRIOR_DATE → $ARCHIVE_PAGE"
  fi

  git add "$DISPATCH_FILE"
  DISPATCH_NOTE="Dispatch: updated"

  # Step 10 of the prompt should have written the audio script. If it
  # exists and is committable, generate the MP3 via gen-audio.sh.
  # F-2 graceful: TTS failure does NOT abort the scan PR. Dispatch ships
  # without audio; the AudioBrief component renders nothing if MP3 absent.
  if [[ -f "$AUDIO_SCRIPT_FILE" ]]; then
    git add "$AUDIO_SCRIPT_FILE"
    echo "─── generating dispatch audio ───"
    if "$REPO_ROOT/scripts/gen-audio.sh" dispatch "$DATE"; then
      git add "$AUDIO_MP3_FILE"
      AUDIO_NOTE="Audio: generated ($(wc -c < "$AUDIO_MP3_FILE" | tr -d ' ') bytes)"
    else
      AUDIO_NOTE="Audio: generation FAILED — dispatch shipping without audio. Investigate & retry via 'scripts/gen-audio.sh dispatch $DATE'."
      echo "WARNING: $AUDIO_NOTE" >&2
    fi
  else
    AUDIO_NOTE="Audio: script not produced by Claude — dispatch shipping without audio. Investigate prompt Step 10."
    echo "WARNING: $AUDIO_NOTE" >&2
  fi
fi

git commit -m "Weekly signal scan — $DATE

Automated Tier 2 source scan. Review before merging to master.
$DISPATCH_NOTE
$AUDIO_NOTE

Generated by scripts/run-weekly-scan.sh"

git push origin "$BRANCH"

# Create PR.
# Body is built via a quoted heredoc + envsubst into a temp file: the text
# never goes through a shell interpolation pass, so backticks/quotes in it
# cannot split arguments or execute (the 2026-05-19 failure class).
BODY_FILE=$(mktemp)
export DATE BRANCH AUDIO_NOTE LOG_FILE
envsubst '${DATE} ${BRANCH} ${AUDIO_NOTE} ${LOG_FILE}' > "$BODY_FILE" <<'PR_BODY_EOF'
Automated Tier 2 source scan from the weekly cron job.

**Files in this PR:**
- `knowledge-system/baseline/zone2-futures-intelligence/06-weak-signal-watch.md` (always — appended scan section)
- `digest/src/pages/index.astro` (if dispatch was regenerated this run — see commit message)
- `digest/audio-scripts/${DATE}.md` (TTS script — if dispatch updated)
- `digest/public/audio/${DATE}.mp3` (cloned-voice audio brief — if TTS succeeded; see status: `${AUDIO_NOTE}`)

**Listen before merging:** open the audio brief in GitHub's inline player while this PR is open:
`https://github.com/cinnabar-intel/cinnabar-intel.github.io/blob/${BRANCH}/digest/public/audio/${DATE}.mp3`

(The raw URL serves with `content-disposition: attachment` and downloads instead of playing — use the `blob/` URL above for inline preview.)

**Sources scanned (16):**
- Synthesizers: Import AI, The Batch, One Useful Thing, Zvi, Stratechery
- Specialists: SemiAnalysis, Simon Willison, Latent Space, Interconnects, Gary Marcus, Pragmatic Engineer
- Workflow: Every/Chain of Thought, Hugging Face blog
- First-party: Anthropic News, OpenAI blog
- Indian perspective: Analytics India Magazine

**Review checklist (scan):**
- [ ] Each new signal's 5-dimension profile is correctly scored
- [ ] Category mapping is accurate
- [ ] No hype or noise crept through
- [ ] Scan summary numbers match entries added

**Review checklist (dispatch, if updated):**
- [ ] `scanNumber` = prior issue + 1; `signalCount` = strong + weak; matches scan summary
- [ ] Thesis lands as the right unifier for the week
- [ ] 5 featured signals' `profile` strings match the appended scan entries verbatim
- [ ] No em-dashes in rendered copy
- [ ] CI `verify-digest` check is green (Astro builds)

**Review checklist (audio brief, if generated):**
- [ ] Audio plays from the raw URL above and sounds like Sanjay (no audible artifacts)
- [ ] Word count 220–280, opens with "Sanjay here.", closes with "Full detail in the dispatch. Until next week."
- [ ] Model identifiers spelled phonetically (e.g. "GPT five point five" not "GPT-5.5")
- [ ] If audio failed, retry locally: `scripts/gen-audio.sh dispatch ${DATE}`

Run log: `${LOG_FILE}`
PR_BODY_EOF

gh pr create \
  --title "Weekly signal scan — $DATE" \
  --body-file "$BODY_FILE" \
  --base master \
  --head "$BRANCH"
rm -f "$BODY_FILE"

# Leave the working tree on master so manual work between scans never starts
# from a stale scan branch. The pushed branch stays for the open PR.
git checkout master

echo "==========================================="
echo "Weekly scan complete: $(date -u) UTC"
echo "==========================================="
