---
name: testimonial-reel
description: Edit Pinecone student testimonial interviews into finished 9:16 reels - one video per student with the bold name title, typed question cards with keyboard sounds, hard cuts, corrected Mongolian captions, Funkorama music bed and the Pinecone end card. Use when asked to "make testimonial reels", "edit the student interviews", "edit these suragch videos", "apply the reviewer comments", or given a folder of raw seated interviews. Handles setup, transcription, answer picking, captions, rendering and review fixes.
argument-hint: "<folder of raw interviews> | fix <video> <reviewer comments>"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# testimonial-reel — Pinecone testimonial editor

Raw interview in, two videos per student out:

| Output | Contents | Default folder |
|---|---|---|
| `NN_Name.mp4` | name title, question cards, end card. No captions, no music | `~/Downloads/ai-footages-edited-version/` |
| `NN_Name-edited.mp4` | the same + captions + music | `~/Desktop/ai captioned videos/` |

The engine (`engine/`) does the cutting, assembly, loudness and mix. **You** do the judgment work the
engine can't: reading the transcript, picking answers, correcting captions, applying reviewer comments.
The house rules are in `references/rulebook.md`. Never change them on your own; they were set by the
Editing manager and approved by reviewers.

## PineQuest reels

Same engine, other look: `engine/pinequest.py <job>.json` makes PineQuest S5 participant / judge impression
reels (cold-open headline, grid cards, framed project inserts, whip/glitch transitions, original music, PineQuest
end card). Theme card and recipe: `../edit-reel/references/themes/pinequest-testimonial.md`.

## 0. Setup (once per computer)

```bash
cd "<skill dir>/scripts" && python3 setup.py      # Windows: py setup.py
python3 setup.py --brand <pinecone-brand-pack.zip>   # once: font, logo, end cards (from the Editing manager)
```

It checks python, numpy, node, ffmpeg, installs numpy and the pinned render engine, and prints the
exact install command for anything missing on this OS. Do not continue until it says **Ready**.
If ffmpeg or node are missing, show the user the printed command and ask before running it.

## 1. Intake

You need, per batch: the folder of raw videos and each student's name **spelled exactly**
(Cyrillic, hyphens as given, e.g. Бат-Эрдэнэ, Бат-Очир). Speech recognition gets names wrong,
so a name you heard is a guess: ask the user to confirm every name in one message before rendering.

```bash
cd "<skill dir>/engine"
python3 -I new_batch.py "<folder>" --name <yyyy-mm-label>
```

This writes `batches/<name>.json` (one student per video) and `batches/<name>-audio/NN.m4a`.

## 2. Transcribe the raw interviews

Follow `references/transcription.md`: upload each `NN.m4a` to `dash.pinecone.mn/reel` (Speechmatics)
and save the lines as `batches/<name>-transcripts/NN.txt` (`m:ss.cc|m:ss.cc|text`).

## 3. Pick the answers

Follow `references/answer-selection.md`. For each student, find the interviewer's questions, choose
the answer to intro / q1–q4, and write `pieces` with word times into the manifest. Rules that
reviewers enforce: every answer ends on a finished sentence, no interviewer voice, a question with no
complete answer is dropped.

## 4. First render (clean)

```bash
python3 -I run.py batches/<name>.json --clean-only
```

Check one title still per student (`references/review-round.md`, "Checking a render").

## 5. Captions

Follow `references/captions.md`: transcribe each clean video's audio again, correct the lines (names
out, Pinecone mishears fixed, punctuation, grammar), save as `batches/captions/<name>/NN.txt`.
List every word you are unsure of for the user instead of guessing silently.

## 6. Final render

```bash
python3 -I run.py batches/<name>.json            # all students; --only F G for some
```

Finals go to the folders above. Report per student: file, length, LUFS/true peak (printed), and the
open questions (uncertain words, dropped questions).

## Fix round (reviewer comments)

Comments come from the Marketing Planner "Video review" page as `time + text`. Follow
`references/review-round.md`: apply each one exactly, re-render only those students, check a still at
every comment time, replace the files, trash renamed old files (never hard-delete).

## Rules of thumb

- Render concurrency is 3. Higher crash-loops a 16 GB Mac; the engine stops a crash-looping render.
- Don't edit `assets/` or `src/` to fix one video. Per-student options live in the manifest
  (`title_scale`, `caption_dy`, `pieces`).
- Music credit for every post: `assets/music/LICENSE.txt`.
