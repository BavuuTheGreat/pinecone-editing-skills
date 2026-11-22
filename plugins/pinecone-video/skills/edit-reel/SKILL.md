---
name: edit-reel
description: The Content Factory Editing station - turn raw footage into a finished Pinecone reel of any type. The member picks a reel theme (testimonial, podcast clip, event recap, presenter promo, creator collab, office trend, motion teaser, brand film), and Claude edits in that theme's house style, built from the audit of Pinecone's own reels. Use when asked to "edit a reel", "make a reel from this footage", "what kind of reels can we make", "show the reel themes", "set up the editing station", or given a folder of raw footage without a named type. Also refreshes the themes from a new reel audit.
argument-hint: "<folder of footage> [theme] | themes | refresh themes"
allowed-tools: Bash, Read, Write, Edit, AskUserQuestion
---

# edit-reel — Editing station (Content Factory 5)

One entry point for every reel type. A **theme** is a reel type plus its editing style: structure,
length, pace, captions, graphics, music and ending. Each theme was measured from Pinecone's published
reels (`reel-audit`, 100 reels, 25 May - 5 Nov 2026), so the output looks like what the account
already posts.

## Themes

| Theme | Card (in `references/`) | Made by | Status |
|---|---|---|---|
| Testimonial / seated interview | `themes/testimonial.md` | `interview-reel` skill | **Ready** (review-approved) |
| PineQuest impression (participant / judge) | `themes/pinequest-testimonial.md` | `interview-reel/engine/pinequest.py` | **Ready** (review-approved) |
| Engineers matter more with AI (series) | `themes/engineers-matter-ai.md` | `interview-reel/engine/engineers.py` | **Beta** (episode 1 awaiting review) |
| Podcast clip | `themes/podcast-clip.md` | `podcast-clipper` skill | **Ready** |
| Motion teaser | `themes/motion-teaser.md` | `motion-studio` skill | **Ready** |
| Event recap | `themes/event-recap.md` | `scripts/assemble.py` + `brand-templates` | Beta |
| Presenter / program promo | `themes/presenter-promo.md` | `scripts/assemble.py` + `brand-templates` | Beta |
| Creator collab | `themes/creator-collab.md` | `scripts/assemble.py` | Beta |
| Office trend | `themes/office-trend.md` | `scripts/assemble.py` | Beta |
| Cinematic brand film | `themes/brand-film.md` | `reel-planner` + `motion-studio` | Plan only |

**Ready** = renders the approved style unattended. **Beta** = Claude follows the card with the general
assembler; the first reels of each beta theme go through review before the card is called Ready.
**Plan only** = needs a shoot or AI generation; Claude writes the shot plan, not a finished edit.

## 0. Setup (once per computer)

```bash
python3 "<interview-reel skill dir>/scripts/setup.py"     # Windows: py
```

It checks python, numpy, node and ffmpeg (prints the install command for this OS) and installs the
render engine. Continue only after **Ready**.
If it reports **brand pack** missing (caption font, logo, end cards are not in the public repo), ask the member
for `pinecone-brand-pack.zip` from the Editing manager and run `setup.py --brand <path to zip or folder>`.

## 1. Pick the theme

1. Look at the footage first: `ffprobe` each file (orientation, length, audio), then
   `bash ../reel-audit/scripts/contact_sheet.sh <folder> <sheets dir>` (9 frames per file). Read the sheets.
2. Suggest the theme whose **signals** (in each card) match, and say why in one line.
3. Ask with `AskUserQuestion`: your suggestion first, marked (Recommended), plus the 2-3 next closest
   themes. Show each theme's status in its description. Never pick silently.
4. If the member asked "what themes are there", show the table above with each card's one-line summary
   and audit median views, then stop.

## 2. Intake

Read the chosen card fully. Ask in **one** message for every field its "Need from you" list marks
required and the footage doesn't answer (names spelled exactly, event name, CTA…). Never guess a name.

## 3. Make it

- **Ready themes:** hand off to the named skill and follow it exactly. Its rules beat this file.
  PineQuest impression: follow the card's recipe (job file + `pinequest.py`).
  Engineers matter more with AI: follow the card's recipe (job file + `engineers.py`); it has its own smooth-transition rules.
- **Beta themes:** follow the card's recipe:
  1. Transcribe if the card has speech captions (`../interview-reel/references/transcription.md`).
  2. Write `edl.json` (format in `scripts/assemble.py`), picking clips by the card's structure.
  3. `python3 -I scripts/assemble.py cut edl.json`. Check cuts/min against the card's pace range.
  4. Graphics and captions with `brand-templates` (`WordCaptions` with `videoSrc` = `cut.mp4`, plus
     `ListCard` / `KineticTitle` / `Counter10K` where the card calls for them). Set `"captioned"` in
     `edl.json` to that render.
  5. `python3 -I scripts/assemble.py finish edl.json`.
- **Plan only:** run `reel-planner` steps 1-2 and hand back the shot list.

Everything follows `references/house-style.md` (format, loudness, captions, end card, file names).

## 4. Check and deliver

Per reel: one still per section and the last frame before the end card, stacked in one image. Read it.
Check the card's checklist and the house-style checklist. Deliver to `~/Desktop/ai edited reels/`
(testimonials keep their own folders), then tell the member to upload to Marketing Planner → Video review.

Reviewer comments: `../interview-reel/references/review-round.md` applies to every theme.

## 5. Refresh themes (Editing manager)

When asked to "refresh themes" or after a new audit: `references/audit-loop.md`.
