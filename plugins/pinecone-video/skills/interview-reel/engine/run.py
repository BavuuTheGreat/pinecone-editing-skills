"""One command for the whole edit.

    python3 -I run.py batches/<batch>.json                 # every student, every stage
    python3 -I run.py batches/<batch>.json --only F G      # some students
    python3 -I run.py batches/<batch>.json --clean-only    # skip captions + music
    python3 -I run.py batches/<batch>.json --out-dir /tmp/test   # write finals somewhere else

Per student: EDL -> cut -> props -> render clean -> finish -> (captions -> render -> finish -> music mix) -> edit spec.
Finals land in the manifest's out_clean / out_edited; everything else in build/<batch>/ (safe to delete)."""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reelpipe import media, stages  # noqa: E402

ENGINE = stages.ENGINE


def expand(p: str, base: str) -> str:
    p = os.path.expanduser(p)
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(base, p))


def prep_end_card(src: str, public: str, seconds: float) -> str:
    """Normalise the supplied end card to 1080x1920/30 with a silent stereo track."""
    dst = os.path.join(public, "end_card.mp4")
    if not os.path.exists(dst):
        media.run(["-i", src, "-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=stereo", "-filter_complex",
                   "[0:v]scale=1080:1920:flags=lanczos,fps=30,setsar=1,format=yuv420p[v]", "-map", "[v]", "-map", "1:a",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-g", "15", "-c:a", "aac", "-b:a", "256k",
                   "-t", str(seconds), dst])
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--only", nargs="*", help="student keys")
    ap.add_argument("--clean-only", action="store_true")
    ap.add_argument("--out-dir", help="override out_clean and out_edited")
    args = ap.parse_args()

    mpath = os.path.abspath(args.manifest)
    base = os.path.dirname(mpath)
    batch = json.load(open(mpath, encoding="utf8"))
    name = os.path.splitext(os.path.basename(mpath))[0]
    build = os.path.join(ENGINE, "build", name)
    public = os.path.join(build, "public")
    stages.stage_public(batch, public)

    batch["music"] = expand(batch["music"], base)
    end_src = expand(batch["end_card"], base)
    batch["end_card_seconds"] = batch.get("end_card_seconds") or round(media.duration(end_src), 3)
    batch["end_card"] = prep_end_card(end_src, public, batch["end_card_seconds"])
    out_clean = os.path.abspath(args.out_dir) if args.out_dir else expand(batch["out_clean"], base)
    out_edited = os.path.abspath(args.out_dir) if args.out_dir else expand(batch["out_edited"], base)
    os.makedirs(out_clean, exist_ok=True)
    os.makedirs(out_edited, exist_ok=True)
    conc = batch.get("concurrency", 3)

    for st in batch["students"]:
        if args.only and st["key"] not in args.only:
            continue
        if not st.get("name") or not st.get("pieces"):
            print(f"[{st['key']}] skipped: fill `name` and `pieces` first (see references/answer-selection.md)", flush=True)
            continue
        t0 = time.time()
        st["source"] = expand(st["source"], base)
        stem = f"{st['num']:02d}_{st['name']}"
        work = os.path.join(build, st["key"])
        os.makedirs(work, exist_ok=True)
        print(f"[{st['key']}] {stem}", flush=True)

        pieces = stages.resolve_pieces(st)
        json.dump({"source": st["source"], "pieces": pieces}, open(os.path.join(work, "edl.json"), "w"), ensure_ascii=False, indent=1)
        clips = stages.cut(st, pieces, public)
        p = stages.props(batch, st, clips)
        pf = os.path.join(work, "props.json")
        json.dump(p, open(pf, "w"), ensure_ascii=False, indent=1)

        stages.render(pf, os.path.join(work, "clean_render.mp4"), public, conc)
        clean = os.path.join(out_clean, stem + ".mp4")
        stages.finish(os.path.join(work, "clean_render.mp4"), p, clean)
        spec = {"clean": stages.edit_spec(batch, st, p, clean, None)}
        print(f"  clean  -> {clean}", flush=True)

        cap = st.get("captions")
        cap = cap if cap and os.path.exists(expand(cap, base)) else None
        if not args.clean_only and cap:
            cp = stages.caption_props(p, expand(cap, base), batch["caption_style"], st.get("caption_dy"))
            cpf = os.path.join(work, "props_captions.json")
            json.dump(cp, open(cpf, "w"), ensure_ascii=False, indent=1)
            stages.render(cpf, os.path.join(work, "cap_render.mp4"), public, conc)
            stages.finish(os.path.join(work, "cap_render.mp4"), cp, os.path.join(work, "cap_finished.mp4"))
            edited = os.path.join(out_edited, stem + "-edited.mp4")
            loud = stages.mix(os.path.join(work, "cap_finished.mp4"), cp, batch["music"], edited, batch["speech_over_bed_db"])
            spec["edited"] = stages.edit_spec(batch, st, cp, edited, loud)
            print(f"  edited -> {edited}  {loud['lufs']} LUFS / {loud['true_peak']} dBTP", flush=True)
        elif not cap:
            print("  no caption file yet: transcribe the clean version, correct it, set `captions`, re-run", flush=True)

        json.dump(spec, open(os.path.join(work, "edit_spec.json"), "w"), ensure_ascii=False, indent=1)
        print(f"  done in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
