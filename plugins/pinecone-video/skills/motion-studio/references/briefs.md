# Brief templates

Fill in the brackets. A detailed brief beats a clever one-liner: the brief, the
assets, and the review loop matter more than the wording of the prompt.

## A. Programme / product launch reel (15-30 s, 9:16)

```
Film: [PROGRAMME, e.g. Morphosis] launch reel, [DURATION]s, 9:16 first, then 1:1.
Audience: [e.g. engineers with 2+ years of experience in Mongolia].
Feeling at the end: [e.g. "the world market is reachable from Ulaanbaatar"].

Assets: logo + photos in ./assets. Product/site: [URL]; capture real screenshots with
Playwright into ./assets/ui and list everything before animating. Do not draw any UI from imagination.
Proof point (real, sourced): [e.g. 1,331 graduates since 2017].
CTA: [e.g. "Бүртгүүлэх · link in bio"], held for at least 1.5 s.

Beats at [BPM] BPM, one idea per beat group:
1. Hook (0-2 s): [the problem in at most 5 words, kinetic type].
2. Turn: the programme appears; its UI or visual builds itself piece by piece.
3. Three proof moments, each a real screen or photo with one action.
4. The number, counted up on a downbeat.
5. Logo lockup + CTA.

Sound: synth.py at [BPM], click/pop on UI actions, whoosh on transitions.
Gate: show docs/shotlist.md on the beat grid, then a stills contact sheet, before full animation.
```

## B. Style from a reference

```
Reference: ./refs/[file] (a video, a frame, or a folder of images).
1. Extract frames (ffmpeg, 2 per second) and study them.
2. Write docs/style_guide.md: palette hex codes, type (family, weight, tracking), average shot length,
   transition types, camera language, texture, how text enters and leaves.
3. Write docs/shotlist.md for a [DURATION]s film about [SUBJECT] in that style.
   Borrow the grammar only: no logos, characters, footage or copy from the reference.
4. Stop and show both files. Wait for approval before writing code.
```

## C. One-shape UI loop (8-12 s, loops forever)

```
One rounded container never cuts. It changes size, corner radius and fill to become each state:
[6-10 states, e.g. "Элсэх" button -> email field (typed) -> loader -> check -> schedule card
-> progress ring -> certificate -> button]. A cursor triggers every change.
Content enters after each morph starts and leaves before the next one. Springs only, tiny
overshoot on UI. 120 BPM, one state change per beat pair. The last frame equals the first,
including cursor position. Show the state list on the beat grid before writing code.
```

## D. Long-form director brief (30-120 s, multi-session)

```
You are director, animator, sound designer and render engineer for a [DURATION] code-rendered film.
Treat it as a multi-session production. Do not rush the final render.

Logline: [one line + the feeling at the end].
Inputs: ./refs ([what to take, what to ignore]); ./audio/track.wav (rights cleared; measure with
beats.py) or synth.py; keys in .env ([names]); budget [₮ / credits].
Look: [palette, type, texture, camera language] + the house-rules list of looks to avoid.
Beat sheet: 0:00-0:02 hook [image] ... a payoff every 3-5 s ... the end sets up the start.

Gates, in order, each shown to me before the next one:
  1 style_guide + shotlist   2 stills for every shot + review
  3 low-res rough cut with placeholder sound   4 full animation   5 polish + sound   6 final
For long films, write docs/ANIMATION_GUIDE.md first, so that chapters split across sub-agents
share one style.
Review every shot until all scores are 8+, logged in docs/review_log.md.
Deliver: out/final.mp4, out/final_poster.png, out/review_contact.png, clean source, README.md.
```

## Pinecone ideas that fit this skill (from the Oct 2026 reel audit)

| Idea | Template | Why |
|---|---|---|
| Hello World / Hackathon event teaser | A | The motion teaser format is 95% AI-makeable |
| "Be 1 of 10K" counter refresh | A + C | Counter and logo already exist as assets |
| Morphosis global launch (English) | A or D | Brand film format; reuse real Morphosis UI |
| Bootcamp enrollment button loop | C | Short loop works as a story ad and a reel cover |
