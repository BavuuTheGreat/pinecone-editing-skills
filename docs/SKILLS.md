# Skills in the `pinecone-video` plugin

Ten skills. Each section says what it is for an engineer and for a five-year-old, when to use it, and which theme
cards it serves. Theme cards are in `plugins/pinecone-video/skills/edit-reel/references/themes/`.

Renamed in 0.6.0 (the old names no longer exist, say the new one):
`testimonial-reel` is now `interview-reel`, `ai-video-playbook` is now `reel-planner`, `brand-motion` is now `brand-templates`.

## Which skill do I need?

| I have / I want | Use |
|---|---|
| A folder of raw footage and I am not sure what to make | `edit-reel` |
| Seated student interviews, one reel per student | `interview-reel` |
| A PineQuest participant or judge interview | `interview-reel` (PineQuest engine) |
| Another episode of "Engineers matter more with AI" | `engineers-series` |
| A long podcast episode to cut into shorts | `podcast-clipper` |
| A launch teaser or motion ad drawn from code | `motion-studio` |
| A counter, list card, title, captions or end card in the house look | `brand-templates` |
| An idea for a reel and I need a shot list (film, generate or template per shot) | `reel-planner` |
| "What kind of reels does this account make?" | `reel-audit` |
| A big goal with many parts ("make all five reels", "fix everything") | `loop-engineer` |
| A pull request with bot comments | `ecc-triage` |

## edit-reel

- **For an engineer.** Editing station router. Input: a folder of footage and optionally a theme. It looks at the
  footage, suggests a theme, asks for missing facts (names, team, result), hands off to the right engine or assembler
  (`scripts/assemble.py` for event recap, presenter promo, creator collab, office trend), checks the result against
  `references/house-style.md` and delivers to `~/Desktop/ai edited reels/`. Output: a finished 1080x1920 reel.
  Entry: say `edit a reel from <folder>`, `show the reel themes`, `set up the editing station`. No engine of its own.
- **For a five-year-old.** You hand over a box of video clips. The helper looks inside and asks "what do you want to
  make?". Then it picks the right toy to build it with and gives you back one finished little movie.
- **Use it when** you have footage and no named type, or you want the list of themes.
- **Theme cards.** All of them (it is the router); Beta themes (event-recap, presenter-promo, creator-collab,
  office-trend) are built by its own `assemble.py`.

## interview-reel

- **For an engineer.** Renamed from `testimonial-reel`. Hosts three engines in `engine/` (Python pipeline `reelpipe/` +
  Remotion project `src/`): `run.py` (seated testimonials), `pinequest.py` (PineQuest participant and judge reels),
  `engineers.py` (Engineers series renderer, used by `engineers-series`). Inputs: raw interview video, a batch or job
  JSON (answers picked, corrected captions, names). Outputs: per student a clean reel and an edited reel (captions +
  music), loudness -14.5 LUFS. Entry: `scripts/setup.py` (one-time), then `python3 -I run.py batches/<batch>.json`,
  `python3 pinequest.py <job.json> [--plan]`. Rules: `references/rulebook.md`, `captions.md`, `answer-selection.md`,
  `review-round.md`.
- **For a five-year-old.** Someone sits and talks to a camera. The helper keeps the best sentences, adds their name
  and the questions as typed words, and puts a nice song underneath. Out comes a short movie for each person.
- **Use it when** you have seated interviews, a PineQuest interview, or reviewer comments to apply to one of those reels.
- **Theme cards.** `testimonial.md`, `pinequest-testimonial.md` (and the renderer for `engineers-matter-ai.md`).

## engineers-series

- **For an engineer.** Entry point and memory for the series "Engineers matter more with AI". Input: one presenter
  take, screen recordings, episode number. Output: an episode with the Ghost Text intro, hard cuts, GIP captions from
  the reel generator, a chill-jazz bed and a sign-off. Uses the renderer `../interview-reel/engine/engineers.py` +
  `src/eng/*`; Annnimate-style motion ports in `animations/`. Entry: `python3 -I engineers.py <job> [--plan|--intro|--align|--remix]`
  from the engine folder; guide in `docs/engineers-series/README.md`.
- **For a five-year-old.** A grown-up talks about what they built, and we show their screen while they talk. The
  helper makes it look like a robot is finishing their sentence in grey letters, then adds the words and the music.
- **Use it when** you make or tweak an episode of the series.
- **Theme card.** `engineers-matter-ai.md`.

## podcast-clipper

- **For an engineer.** Input: a long 16:9 podcast episode (file or URL). Pipeline: `scripts/transcribe.sh` (word
  timestamps) -> pick 30-60 s moments with the user -> `scripts/cut_vertical.sh` (9:16 reframe, `crop_x`) ->
  `scripts/clip_captions.py` (word captions for the `brand-templates` `WordCaptions` template). Output: vertical clips
  with captions. Humans proofread Mongolian captions.
- **For a five-year-old.** A very long talk is like a long story book. The helper finds the best page, cuts it out and
  stands it up tall, so it fits on a phone.
- **Use it when** you have a podcast or long interview to turn into shorts.
- **Theme card.** `podcast-clip.md`.

## motion-studio

- **For an engineer.** Bespoke motion films rendered from code: a page paints any frame via `window.seek(t)`, headless
  Chromium screenshots it, ffmpeg encodes, beats and music are synthesized. Input: an approved brief (intake gate asks
  for missing inputs). Output: MP4 films in one or more formats, self-reviewed from contact sheets until every score is
  8+. Entry: `scripts/new_film.sh`, then the pipeline in its SKILL.md. Different from `brand-templates`: this makes a
  new film each time.
- **For a five-year-old.** The helper draws a brand-new cartoon, frame by frame, with a computer pencil, and makes
  the pictures jump to the music beat.
- **Use it when** you want a launch teaser, event teaser, motion ad, showreel or an animated explainer.
- **Theme cards.** `motion-teaser.md`, `brand-film.md` (with `reel-planner`).

## brand-templates

- **For an engineer.** Renamed from `brand-motion`. A Remotion 4 project (`template/`) with five fixed compositions:
  `Counter10K`, `ListCard`, `KineticTitle`, `WordCaptions`, `EndCard`; props in JSON, 1080x1920 at 30 fps, brand tokens
  in `template/src/brand.ts`. Entry: copy `template/`, `npx remotion render src/index.ts <Composition> out.mp4 --props=props.json`.
- **For a five-year-old.** It is a box of stickers that always look the same: a counting sticker, a list sticker, a
  title sticker, a talking-words sticker and a goodbye sticker. You only change the words on them.
- **Use it when** a reel needs a counter, list card, kinetic title, word captions or an end card in the house look.
- **Theme cards.** `event-recap.md`, `presenter-promo.md`, `podcast-clip.md`, `motion-teaser.md` (quick option),
  `brand-film.md` (graphics).

## reel-planner

- **For an engineer.** Renamed from `ai-video-playbook`. Planning, no render. Input: a brief or a reel URL to remake.
  Output: format choice, scene split, per scene a decision (film it, generate it with Higgsfield, or template it with
  `brand-templates`), prompts (`references/scene-prompts.md`) and guardrails (no synthetic face or voice of a real
  person, Mongolian text typeset in code).
- **For a five-year-old.** Before you build a block tower you draw the plan. The helper draws the plan of the movie
  and writes who builds each part: a person with a camera, a computer drawing, or a sticker.
- **Use it when** a reel is not a plain edit of footage you already have, or you ask "which scenes can AI make?".
- **Theme card.** `brand-film.md` (plan only).

## reel-audit

- **For an engineer.** Input: an Instagram, TikTok or YouTube Shorts account. Pipeline: collect URLs and views,
  download (yt-dlp), `scripts/contact_sheet.sh` (one 3x3 sheet per reel + pacing metrics), classify every reel,
  aggregate and score AI feasibility. Output: `catalog.csv`, `metrics.csv`, `summary.md`. The theme cards came from the
  first audit (`audits/`).
- **For a five-year-old.** The helper watches a whole shelf of videos fast, makes a picture card of each one, and then
  tells you what kinds of videos are on the shelf and which are popular.
- **Use it when** you want to know what content works, benchmark a competitor, or refresh the themes.
- **Theme cards.** All of them are measured from its audit; `edit-reel` can refresh them from a new one.

## loop-engineer

- **For an engineer.** The loop for any main goal: split into units (reels, reviewer comments, factory features,
  engine changes, PR bot findings), write acceptance checks per unit type (reel: render, stills at reviewer times,
  -14.5 LUFS and -1 dBTP, whisper/energy check at every cut, captions; factory and engine: unit tests, e2e smoke,
  `--plan`; PR: CI green + `ecc-triage`), then plan -> build -> verify -> review -> fix until all pass in the same
  iteration. Three failed iterations with no new information = blocked; owner decisions are parked; checks are never weakened.
- **For a five-year-old.** If you ask for five cookies, the helper does not stop after one. It counts and tastes all
  five before saying "done", and asks you only about the things only you can decide.
- **Use it when** a request has many parts or you say "make it work" or "loop until done".
- **Theme cards.** None (a process skill).

## ecc-triage

- **For an engineer.** After a push to a PR, read the ECC Tools bot comments for the latest commit
  (`gh pr view <n> --json comments`), sort useful (security evidence, CI, manifest integrity) from noise (RAG corpora,
  harness drift), fix the useful ones with `loop-engineer`, push, read again until CI is green and only noise or
  owner-owned items remain.
- **For a five-year-old.** A robot leaves sticky notes on your drawing. The helper reads them, fixes the notes that
  are right, and ignores the silly ones.
- **Use it when** you push to a pull request, or someone says "check the bot comments".
- **Theme cards.** None (a process skill).
