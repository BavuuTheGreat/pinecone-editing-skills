---
name: ai-video-playbook
description: Plan and produce Pinecone Academy reels with AI - pick the format, split it into scenes, decide per scene whether it is filmed, generated (Higgsfield image/video), or templated (Remotion), write the prompts, and run the guardrails. Use when asked to "make a reel", "plan a video", "which scenes can AI make", "generate b-roll", or to remake a past reel with AI.
argument-hint: "<brief or reel URL to remake>"
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# AI video playbook - Pinecone reels

Rule of thumb from the Oct 2026 audit: **AI builds the world; real people tell the story.**
Creator and event reels earn 61% of views. Never replace those people with AI.
Use AI for the produced formats (brand films, teasers, promos) and for editing everywhere.

## Step 1 - Pick the format

Use `../reel-audit/references/format-taxonomy.md`. If the brief fits a human format
(creator, event, podcast), skip to the editing automations in Step 4. Generation adds little there.

## Step 2 - Shot list with a source per shot

Write a table: `# | seconds | what's on screen | VO / text | source`.
For source, choose one of:

| Source | Use for | Tool |
|---|---|---|
| FILM | any real person: founder, staff host, students, creators, events | camera |
| GEN-IMG | posters, backdrops, metaphor stills, CTA backgrounds | Higgsfield `generate_image` |
| GEN-VID | surreal/CGI motion: Earth, data worlds, stone-head people, 3D characters | Higgsfield `generate_video` (image -> video for control) |
| TEMPLATE | counters, list cards, kinetic titles, end cards, captions | `brand-motion` skill (Remotion) |
| SCREEN | product UI, code, student projects | screen recording, then a TEMPLATE zoom |

Hook (0-3 s) gets its own row. Every reel ends on a TEMPLATE end card with the CTA.

## Step 3 - Generate (GEN-IMG / GEN-VID)

1. If unsure which model fits, call `models_explore` with `action: "recommend"` first.
2. Generate a **still first** (`generate_image`, 9:16), get approval, then animate it
   (`generate_video` with the still as the start frame). This costs fewer credits than
   re-rolling video.
3. Batch independent shots with `generate_image_batch` / `generate_video_batch`, then
   `jobs_wait`, then one `show_generation_by_ids`.
4. Use the prompt patterns in `references/scene-prompts.md`. Always state: 9:16, the brand
   palette (near-black #0E1220, Pinecone blue #2E55E0, warm white), lighting, camera move,
   and duration.
5. Fix footage you already have, instead of reshooting:
   - 16:9 brand films go to 9:16 with `reframe`
   - English versions of Morphosis/global promos with `dubbing`
   - low-res archive clips with `upscale_video`

Always check the credit balance (`balance`) and give the user the quote before a batch.
Never call `execute_preset` or `publish_*` without explicit approval.

## Step 4 - Assemble

- Motion graphics and captions: `brand-motion` skill.
- Long podcast -> clips: `podcast-clipper` skill.
- Full voiceover explainer cut in CapCut: the `capcut-editing-automation` skill (enable it in claude.ai).
- Check pacing against the audit baseline: produced formats run at about 20 cuts/min, talk formats at 3-5.

## Step 5 - Guardrails (block shipping if any fail)

1. No synthetic face or voice of a real, identifiable person (founder, students, alumni, creators, guests).
2. Photorealistic generated scenes get Instagram's AI label.
3. Logo, colours and Mongolian spelling checked by a human.
4. Generated text inside images is re-typed as a TEMPLATE layer. Image models misspell Cyrillic.

## Remaking a past reel

Run `/watch <url>` (or read its `reel-audit` contact sheet), then write the shot list
with the original timestamps. Mark each shot FILM / GEN / TEMPLATE and estimate the
credits needed. Example: the Morphosis film (155K views) breaks down as 4 GEN-VID shots
(painting, stone heads, Earth, data globe) + actor scenes (FILM) + end card (TEMPLATE).
