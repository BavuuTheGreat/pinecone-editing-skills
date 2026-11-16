#!/usr/bin/env bash
# Cut [start,end] from a 16:9 podcast and reframe to 1080x1920.
# Usage: cut_vertical.sh <in.mp4> <start_s> <end_s> <out.mp4> [crop_x_center 0..1, default 0.5]
# crop_x_center moves the 9:16 window toward the speaker (0.3 = left guest, 0.7 = right host).
set -euo pipefail
IN="${1:?in}"; S="${2:?start}"; E="${3:?end}"; OUT="${4:?out}"; CX="${5:-0.5}"
ffmpeg -hide_banner -loglevel error -y -ss "$S" -to "$E" -i "$IN" \
  -vf "crop=ih*9/16:ih:(iw-ih*9/16)*${CX}:0,scale=1080:1920" \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 160k "$OUT"
echo "wrote $OUT"
