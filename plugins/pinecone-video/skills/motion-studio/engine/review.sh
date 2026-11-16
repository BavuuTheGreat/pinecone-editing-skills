#!/usr/bin/env bash
# Turn a render into images Claude can look at and critique.
# Usage: review.sh <video.mp4> [fast_moment_seconds]
# Writes out/review_contact.png (2 fps), out/review_phone.png (1 fps at 360 px),
# out/review_strip.png (12 frames around the fast moment), out/review_loop.mp4 (seam check).
set -euo pipefail
V="${1:?video}"; T="${2:-}"
mkdir -p out
DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")"
grid() { python3 -c "import math; n=max(1,math.ceil($DUR*$1)); c=min($2,n); print(f'{c}x{math.ceil(n/c)}')"; }
ffmpeg -hide_banner -loglevel error -y -i "$V" -vf "fps=2,scale=216:-2,tile=$(grid 2 8):padding=4" -frames:v 1 out/review_contact.png
ffmpeg -hide_banner -loglevel error -y -i "$V" -vf "fps=1,scale=360:-2,tile=$(grid 1 6):padding=4" -frames:v 1 out/review_phone.png
if [ -n "$T" ]; then
  S="$(python3 -c "print(max(0, $T - 0.2))")"
  ffmpeg -hide_banner -loglevel error -y -ss "$S" -i "$V" -vf "scale=240:-2,tile=12x1:padding=2" -frames:v 1 out/review_strip.png
fi
ffmpeg -hide_banner -loglevel error -y -stream_loop 1 -i "$V" -c copy out/review_loop.mp4
ls -1 out/review_*
