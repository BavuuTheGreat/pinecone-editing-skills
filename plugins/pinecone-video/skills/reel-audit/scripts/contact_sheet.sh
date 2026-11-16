#!/usr/bin/env bash
# Build one 3x3 contact sheet + pacing metrics per video.
# Usage: contact_sheet.sh <videos_dir> <out_dir>
# Output: <out_dir>/<id>.jpg (9 evenly spaced frames, read left->right, top->bottom)
#         and <out_dir>/metrics.csv
set -euo pipefail
IN="${1:?videos dir}"; OUT="${2:?out dir}"
mkdir -p "$OUT"
echo "id,duration_s,cuts,cuts_per_min,avg_shot_s,has_audio" > "$OUT/metrics.csv"
for f in "$IN"/*.mp4; do
  id="$(basename "$f" .mp4)"
  dur="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"
  # Scene cuts (threshold 0.3 catches hard cuts, ignores most camera moves)
  cuts="$(ffmpeg -hide_banner -nostats -i "$f" -vf "select='gt(scene,0.3)',metadata=print" -an -f null - 2>&1 | grep -c pts_time || true)"
  audio="$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$f" | head -1)"
  python3 - "$id" "$dur" "$cuts" "${audio:+yes}" >> "$OUT/metrics.csv" <<'PY'
import sys
i, d, c, a = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4] or "no"
print(f"{i},{d:.1f},{c},{c / d * 60:.1f},{d / (c + 1):.1f},{a}")
PY
  tmp="$(mktemp -d)"
  for n in 0 1 2 3 4 5 6 7 8; do
    t="$(python3 -c "print(round(${dur} * (${n} + 0.5) / 9, 2))")"
    ffmpeg -hide_banner -loglevel error -ss "$t" -i "$f" -frames:v 1 \
      -vf "scale=360:-2" \
      "$tmp/$n.jpg"
  done
  ffmpeg -hide_banner -loglevel error -y -i "$tmp/%d.jpg" -vf "tile=3x3:padding=4" -frames:v 1 "$OUT/$id.jpg"
  rm -rf "$tmp"
done
echo "Wrote $(ls "$OUT"/*.jpg | wc -l | tr -d ' ') sheets + metrics.csv to $OUT"
