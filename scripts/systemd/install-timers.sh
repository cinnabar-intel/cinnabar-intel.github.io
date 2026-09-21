#!/bin/bash
# Install and enable the pipeline's systemd user timers.
#
# These replace cron, which has no catch-up: a host asleep at 00:30 UTC on a
# Monday silently skipped the week (2026-05-18, and again 2026-09-14). The
# timers carry Persistent=true, so a missed run fires on next start.
#
# Idempotent. Safe to re-run after editing any unit file.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.config/systemd/user"
UNITS=(weekly-scan monthly-scan jev-shadow)

mkdir -p "$DEST"
for u in "${UNITS[@]}"; do
  cp "$SRC/$u.service" "$SRC/$u.timer" "$DEST/"
done
systemctl --user daemon-reload

for u in "${UNITS[@]}"; do
  systemctl --user enable --now "$u.timer"
done

# Without lingering, user units only run while a login session is open.
loginctl enable-linger "$USER" || \
  echo "WARNING: could not enable linger - timers will only run while you are logged in" >&2

# Cron and the timers must never both be armed, or every scan runs twice.
if crontab -l 2>/dev/null | grep -qE 'run-(weekly|monthly)-scan\.sh|jev/shadow-run\.sh'; then
  echo
  echo "WARNING: cron still has scan entries. Remove them or every scan fires twice:" >&2
  crontab -l | grep -E 'run-(weekly|monthly)-scan\.sh|jev/shadow-run\.sh' >&2
  exit 1
fi

echo
systemctl --user list-timers "${UNITS[@]/%/.timer}" --all --no-pager
