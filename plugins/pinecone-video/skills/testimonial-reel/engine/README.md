# Testimonial Reel Engine

Automated editor for Pinecone student testimonial reels (Content Factory, Editing step).
Raw interview in, two finished 1080×1920 videos out per student:

- **clean**: name title, typed question cards, end card. No captions, no music.
- **edited**: clean + captions + music bed.

Rules it follows: `docs/tdd/content-factory-editing-tdd.md` (Editing Rulebook).

## Setup

```bash
cd plugins/pinecone-video/skills/testimonial-reel/engine
npm ci            # Remotion 4.0.536, pinned
# needs: node 18+, python 3.11+ with numpy, ffmpeg/ffprobe on PATH
```

## Run

```bash
python3 -I run.py batches/<batch>.json              # all students
python3 -I run.py batches/<batch>.json --only F G   # some students
python3 -I run.py batches/<batch>.json --clean-only # no captions/music
python3 -I run.py batches/<batch>.json --out-dir build/test-out
```

Per student: EDL → cut → props → render clean → loudness → captions → render → music mix → edit spec.
Finals go to the manifest's `out_clean` / `out_edited`. Scratch goes to `build/<batch>/` (delete freely; delete
`build/<batch>/public/<KEY>_*` to force a re-cut after changing a student's pieces).

## Adding a batch

`python3 -I new_batch.py <folder> --name <yyyy-mm-label>` writes `batches/<name>.json` from the house
settings in `batches/_house.json`. Fill each student (worked example: `batches/_example.json`):

```json
{
  "key": "F", "num": 6, "name": "Бат-Эрдэнэ", "source": "~/Downloads/suragch 6 .mp4",
  "pieces": [
    {"id": "h01", "answer": "intro", "start": 4.82, "end": 10.62},
    {"id": "h02", "answer": "q1", "word_start": 16.98, "word_end": 40.28, "lo": 15.7, "hi": 41.1}
  ],
  "captions": "captions/<batch>/06.txt",
  "title_scale": 0.8
}
```

- `answer`: `intro`, `q1`…`q4`. Card text per answer is in `cards`. Several pieces per answer get one card.
- A piece is either `start`/`end` (seconds in the raw file) or word times from the transcript
  (`word_start`, `word_end` plus the allowed window `lo`/`hi`): the engine snaps both cuts to the quietest 40 ms.
- `title_scale`: 0.8 for names of 9+ letters.
- `caption_dy`: `{"until": 3.45, "dy": 28}` lowers early captions when the name's letters reach down (у, д, р).

## Captions (still manual)

1. Run with `--clean-only` (or without `captions`) to get the clean video.
2. Upload its audio (m4a, under 10 MB) to `dash.pinecone.mn/reel`, transcribe (Speechmatics).
3. Save the lines as `batches/captions/NN.txt`, one per line: `m:ss.cc|m:ss.cc|text`.
4. Correct them: drop the line where the student says their name, fix misheard words ("Pinecone" is often heard
   as банканд / банкинд / ком / киноны / тоонд), add punctuation.
5. Set `captions` for the student, run again.

## Layout

| Path | What |
|---|---|
| `run.py` | CLI, one command for a batch |
| `reelpipe/stages.py` | cut, props, captions, render, loudness, music mix, edit spec |
| `reelpipe/media.py` | ffmpeg/ffprobe helpers, quiet-point search |
| `src/` | Remotion composition `StudentReel` (cards, name title, captions, end card) |
| `assets/` | fonts, logo, typing SFX, end card, music |
| `batches/` | `_house.json` (house settings), `_example.json`, `pinequest/_example.json`. Real batches, captions and audio are git-ignored: they hold student names and stay on the editing Mac. |

## Notes

- Render concurrency is 3. At 6, a 16 GB Mac crash-looped; the engine now aborts a crash-looping render.
- Music: "Funkorama" by Kevin MacLeod, CC BY 4.0. Every post needs the line in `assets/music/LICENSE.txt`.
- `edit_spec.json` per student (in `build/`) records length, cards, music and loudness for the Analytics loop.
