---
name: motion-studio
description: Make bespoke motion-graphics films rendered from code - launch reels, event teasers, UI loops, showreels and longer director-brief films. Each frame is drawn by window.seek(t) in headless Chromium with spring physics, cut to a beat grid, scored with synthesized or supplied music, and self-reviewed from contact sheets until every score is 8+. Use when asked for a launch video, teaser, motion ad, product reel, animated explainer or "make it look like this reference". For the fixed repeating Pinecone graphics (captions, list cards, end cards, counters) use brand-templates instead.
argument-hint: "<what film> [any of: URL, duration, formats, proof point, CTA, reference, music] - missing required inputs are asked for"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# motion-studio - code-rendered motion films

You cannot output video directly. You write a page that paints any moment on request,
and `render.mjs` turns it into an MP4:

```
index.html  --window.seek(t)-->  headless Chromium  --PNG per sub-frame-->  ffmpeg (blend + H.264)
                                                                                |
beats.json <-- beats.py (track or BPM grid)      synth.py --> audio.wav --> finish.sh --> final.mp4
```

Because frames depend only on t, renders are reproducible, any second can be re-rendered
alone, and you can review your own output as images.

**Effort:** start new films at xhigh effort (or max for a big launch). Medium is fine for small fixes.

## 0. Intake (gate 0: no scaffolding or code until the brief is approved)
Every run starts here, even when the request looks complete. Follow `references/intake.md`:
1. Pick the film type (A launch · B reference · C UI loop · D long-form). Ask if it is unclear.
2. Take every field the user already gave. Find the REQUIRED fields for that type that are still missing.
3. Ask for them: choice fields with `AskUserQuestion` (at most 4 per call), free-text fields
   (URL, real metric, CTA, logline, UI states, reference path, key names, budget) in one numbered
   message. Then **stop and wait for the answers**. At most 2 rounds, then use the defaults for optional fields.
4. Never fill a required field with a guess. No metric given: drop the proof beat. No URL: use only the
   assets the user supplied.
5. Write `docs/brief.md` from `references/brief-template.md`, marking each field given, defaulted or
   not available. Show it and wait for an explicit OK.

## 1. Scaffold (after gate 0)
```bash
bash "${CLAUDE_SKILL_DIR}/scripts/new_film.sh" films/<slug>
cd films/<slug>
```
This copies the engine (`render.mjs`, `lib/motion.js`, `index.html` starter, `beats.py`,
`synth.py`, `review.sh`, `finish.sh`), writes `CLAUDE.md` from `references/house-rules.md`,
and installs Playwright Chromium. Read the starter `index.html` first: it shows the contract,
springs, the one-shape morph, frame-stepped counters, and a seamless loop.

## 2. Plan (gate 1: user approves the shot list before any animation code)
- Assets: capture real UI with Playwright into `assets/ui/`, and copy in the logo and photos. List them.
- Reference given: `references/briefs.md` B, which writes `docs/style_guide.md`.
- Beat grid: `python3 beats.py audio/track.wav > beats.json`, or `python3 beats.py --bpm 120 --dur 20 > beats.json`.
- `docs/shotlist.md`: time | beat | what's on screen | motion | sound cue. Hook before 2 s.
  Pick the closest brief in `references/briefs.md` (A launch, B reference, C UI loop, D long-form).

## 3. Build
Write `index.html` (split scenes into `scenes/*.js` modules once it passes ~300 lines).
Follow `CLAUDE.md`: pure `seek(t)`, `track()` springs, seeded randomness, frame-stepped text changes.
Preview a moment with `node render.mjs --still 1.2`, and the pacing with `node render.mjs --scale 0.5 --sub 1`.

## 4. Review loop (minimum 3 rounds; gate: every score 8+)
`node render.mjs --sub 1 --scale 0.5` then `bash review.sh out/silent.mp4 <fast moment>`.
Read the images and score with `references/review.md`. Fix the three worst issues, re-render only the
affected range (`--from/--to`), and repeat. Log every round in `docs/review_log.md`.

## 5. Sound + final
```bash
python3 synth.py --bpm 120 --dur <D> --cues cues.json --out out/audio.wav   # or use the supplied track
node render.mjs                                 # full quality: 30 fps, 4 sub-frames of motion blur
bash finish.sh out/silent.mp4 out/audio.wav <poster_t>      # about -14 LUFS, poster PNG
node render.mjs --w 1080 --h 1080 --out out/square.mp4      # extra formats from the same timeline
```
Write `cues.json` from `beats.json` (sfx on hits/downbeats).

## 6. Deliver
`out/final.mp4`, `out/final_poster.png`, `out/review_contact.png`, final scores, and the top 3
things you would improve next. Keep one folder per brand or campaign, so later films reuse its assets and sound.

## Hard rules
- Real product UI, logos and photos only. Never invent screens or fake metrics.
- Never put a synthetic likeness of a real person into a film (see reel-planner guardrails).
- API keys (e.g. ElevenLabs for voiceover) live in `.env`, never in prompts or source.
- Music only from `synth.py` or a track whose rights the team holds.
- A review image you have not actually Read does not count as reviewed.
