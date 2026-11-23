#!/usr/bin/env bash
# CLI end-to-end smoke test: a tiny generated video goes through tick -> status -> approve -> tick -> review.
# Runs in a throw-away FACTORY_HOME. Uses ffmpeg to make the video when it is installed; without ffmpeg a dummy
# .mp4 is used and the duration probe is skipped (the factory then records "duration unknown").
# Run from the factory/ folder:  bash tests/e2e_smoke.sh
set -euo pipefail

cd "$(dirname "$0")/.."
FACTORY_HOME="$(mktemp -d)"
export FACTORY_HOME
trap 'rm -rf "$FACTORY_HOME"' EXIT

mkdir -p "$FACTORY_HOME/inbox/Smoke Reel"
printf '{"settle_seconds": 0, "transcriber": "manual", "editor": "handoff", "approval": "file"}\n' > "$FACTORY_HOME/config.json"
printf 'name: Сурагч\nteam: Smoke\n' > "$FACTORY_HOME/inbox/Smoke Reel/note.txt"
if command -v ffmpeg >/dev/null 2>&1; then
  ffmpeg -v error -f lavfi -i testsrc=size=320x568:rate=10:duration=1 -f lavfi -i sine=frequency=440:duration=1 \
    -shortest -pix_fmt yuv420p "$FACTORY_HOME/inbox/Smoke Reel/clip.mp4"
else
  echo "ffmpeg not found: using a dummy clip, probing skipped"
  printf 'not a real video' > "$FACTORY_HOME/inbox/Smoke Reel/clip.mp4"
fi

fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
run() { python3 -m factory "$@"; }   # set -e makes any non-zero exit fail the script
expect() { grep -q -- "$2" <<<"$1" || fail "expected '$2' in: $1"; }

out=$(run status);           expect "$out" "no reels yet"
out=$(run tick);             expect "$out" "smoke-reel"
out=$(run tick)              # probe + note
mkdir -p "$FACTORY_HOME/state/smoke-reel"
printf 'Hello this is a short manual transcript for the smoke test.\n' > "$FACTORY_HOME/state/smoke-reel/transcript.txt"
for _ in 1 2 3; do run tick >/dev/null; done
out=$(run status);           expect "$out" "smoke-reel"; expect "$out" "proposed"
run show smoke-reel >/dev/null
out=$(run approve smoke-reel ok); expect "$out" "approved"
for _ in 1 2; do run tick >/dev/null; done
out=$(run status);           expect "$out" "editing"
[ -f "$FACTORY_HOME/state/smoke-reel/EDIT_REQUEST.md" ] || fail "EDIT_REQUEST.md missing"
run done smoke-reel "$FACTORY_HOME/inbox/Smoke Reel/clip.mp4" >/dev/null
run tick >/dev/null
out=$(run review);           expect "$out" "Smoke Reel"; expect "$out" "1 in review"
[ -n "$(ls "$FACTORY_HOME/reviews")" ] || fail "review file not written"
if run approve ../../etc >/dev/null 2>&1; then fail "path traversal id accepted"; fi
echo "SMOKE OK"
