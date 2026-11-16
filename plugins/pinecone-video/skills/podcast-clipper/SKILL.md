---
name: podcast-clipper
description: Turn a long podcast episode (16:9, Mongolian or English) into vertical 9:16 reels - word-level transcript, pick the strongest 30-60 s moments, cut and reframe to the speaker, and output word-by-word captions for the brand-motion WordCaptions template. Use when asked to "clip the podcast", "make reels from this episode", or "cut shorts from a YouTube interview".
argument-hint: "<episode file or URL> [number of clips]"
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# podcast-clipper

Podcast clips were 31% of our reels but only 13% of views in the Oct 2026 audit.
They ran 100 s at the median, with 3 cuts/min, and they made up 5 of the bottom 5. This skill makes them
cheaper to produce and tighter. Default target: **30-60 s, hook in the first 3 s**.

## Pipeline

1. **Get the episode.** For a URL, use `yt-dlp -f "bv*[height<=1080]+ba/b" -o episode.%(ext)s <url>`
   in a fresh, empty folder.
2. **Transcribe with word timestamps.**
   `bash "${CLAUDE_SKILL_DIR}/scripts/transcribe.sh" episode.mp4 transcript.json mn`
   (Groq whisper-large-v3; the key is shared with /watch in `~/.config/watch/.env`.
   Episodes over ~50 min: split the audio first. Groq's upload limit is 25 MB.)
   Mongolian ASR is good enough to find moments, but **a human must proofread the caption text**.
3. **Pick clips.** Read `segments` from `transcript.json` and propose N clips as a table:
   `# | start | end | hook line (first sentence) | why it stands alone | crop_x`.
   Pick a moment when:
   - the first sentence is a claim, a number, or a question (e.g. "Teachers need $3,000 a month")
   - it makes sense without the rest of the episode
   - it is 30-60 s, cut on sentence boundaries
   Confirm the list with the user before cutting.
4. **Cut + reframe** each clip:
   `bash "${CLAUDE_SKILL_DIR}/scripts/cut_vertical.sh" episode.mp4 <start> <end> clip01.mp4 <crop_x>`
   `crop_x` 0..1 moves the 9:16 window toward the speaker. Check one frame per clip with
   `ffmpeg -ss 2 -i clip01.mp4 -frames:v 1 check.jpg`, then Read it.
   If both speakers alternate quickly, use Higgsfield `reframe` (it tracks the speaker) instead.
5. **Captions.**
   `python3 "${CLAUDE_SKILL_DIR}/scripts/clip_captions.py" transcript.json <start> <end> captions01.json`
   Copy `clip01.mp4` into the brand-motion project's `public/`, add `"videoSrc"` pointing to it,
   and render `WordCaptions` with `--props=captions01.json`.
6. **Title + end card.** Put the hook line as an on-screen title for the first 3 s, and add
   the brand-motion `EndCard` with the full-episode CTA.

## Output checklist per clip

- [ ] 1080x1920, 30-60 s, starts on the hook sentence
- [ ] Captions proofread by a Mongolian speaker
- [ ] Podcast credit (show name and episode number) kept on screen, as the originals do
- [ ] End card names the full episode and the bootcamp CTA
