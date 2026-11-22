"""Start a batch from a folder of raw interviews: writes a manifest skeleton and caption-tool audio.

    python3 -I new_batch.py "~/Downloads/shoot-2026-11" --name 2026-12-bootcamp

Creates batches/<name>.json (one student per video, pieces empty, to be filled from the transcript)
and batches/<name>-audio/<NN>.m4a (mono 64k, well under the caption tool's 10 MB upload limit)."""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reelpipe import media  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = (".mp4", ".mov", ".m4v", ".mkv")
KEYS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DEFAULTS = os.path.join(HERE, "batches", "_house.json")


def natural(s: str) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--name", required=True, help="batch name, e.g. 2026-12-bootcamp")
    ap.add_argument("--start-num", type=int, default=1, help="number of the first video (file prefix NN_)")
    a = ap.parse_args()

    folder = os.path.expanduser(a.folder)
    vids = sorted((f for f in os.listdir(folder) if f.lower().endswith(VIDEO) and not f.startswith(".")), key=natural)
    if not vids:
        sys.exit(f"no videos in {folder}")
    out = os.path.join(HERE, "batches", f"{a.name}.json")
    if os.path.exists(out):
        sys.exit(f"{out} exists; pick another --name")

    base = json.load(open(DEFAULTS, encoding="utf8"))  # house settings: cards, music, end card, caption style
    audio_dir = os.path.join(HERE, "batches", f"{a.name}-audio")
    os.makedirs(audio_dir, exist_ok=True)
    students = []
    for i, f in enumerate(vids):
        num = a.start_num + i
        src = os.path.join(folder, f)
        m4a = os.path.join(audio_dir, f"{num:02d}.m4a")
        media.run(["-i", src, "-vn", "-ac", "1", "-c:a", "aac", "-b:a", "64k", m4a])
        students.append({"key": KEYS[i % 26] + ("" if i < 26 else str(i // 26)), "num": num, "name": "", "source": src,
                         "pieces": [], "captions": f"captions/{a.name}/{num:02d}.txt", "duration": round(media.duration(src), 2)})
        print(f"  {num:02d}  {f}  ({students[-1]['duration']} s)  audio -> {os.path.relpath(m4a, HERE)}")
    base["students"] = students
    json.dump(base, open(out, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    os.makedirs(os.path.join(HERE, "batches", "captions", a.name), exist_ok=True)
    print(f"\nmanifest -> {os.path.relpath(out, HERE)}  (fill name + pieces per student)")


if __name__ == "__main__":
    main()
