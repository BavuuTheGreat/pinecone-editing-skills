#!/usr/bin/env bash
# Mux picture + sound at -14 LUFS (Instagram/TikTok target) and export a poster frame.
# Usage: finish.sh <silent.mp4> <audio.wav> [poster_seconds=1] [out=out/final.mp4]
set -euo pipefail
V="${1:?silent video}"; A="${2:?audio wav}"; P="${3:-1}"; O="${4:-out/final.mp4}"
ffmpeg -hide_banner -loglevel error -y -i "$V" -i "$A" -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1:LRA=11" -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$O"
ffmpeg -hide_banner -loglevel error -y -ss "$P" -i "$O" -frames:v 1 "${O%.*}_poster.png"
ffmpeg -hide_banner -nostats -i "$O" -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | sed 's/^ */integrated loudness: /'
echo "wrote $O and ${O%.*}_poster.png"
