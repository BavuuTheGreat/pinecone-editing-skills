"""Slice Whisper word timestamps to one clip and rebase them to 0 ms.

Usage: python3 clip_captions.py transcript.json <start_s> <end_s> captions.json
Output matches brand-templates's WordCaptions `words` prop.
"""
import json
import sys

src, start, end, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
words = json.load(open(src)).get("words", [])
clip = [
    {
        "text": w["word"].strip(),
        "startMs": round((w["start"] - start) * 1000),
        "endMs": round((w["end"] - start) * 1000),
    }
    for w in words
    if w["start"] >= start and w["end"] <= end and w["word"].strip()
]
json.dump({"words": clip, "wordsPerLine": 3}, open(out, "w"), ensure_ascii=False, indent=1)
print(f"{len(clip)} words -> {out}")
