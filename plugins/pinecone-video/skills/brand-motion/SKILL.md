---
name: brand-motion
description: Render Pinecone-branded motion graphics with Remotion - milestone counters ("N/10K"), numbered list cards, kinetic event titles, word-by-word captions with the green highlight, and programme end cards. Use when a reel needs titles, captions, counters, list overlays, teasers or end cards, or when asked to "animate", "make a motion graphic", "add captions" or "make an end card".
argument-hint: "<which template + the text/data>"
allowed-tools: Bash, Read, Write, Edit
---

# brand-motion - Pinecone motion templates (Remotion)

The `template/` folder is a ready Remotion 4 project with 5 compositions, rebuilt
from graphics that repeat across our reels:

| Composition | Rebuilds | Props |
|---|---|---|
| `Counter10K` | "Be 1 of 10K" milestone counter | `steps[{year,count,image?}]`, `goal`, `tagline` |
| `ListCard` | "5 most in-demand jobs" list overlay | `heading`, `items[{rank,title,note?}]`, `backgroundVideo?` |
| `KineticTitle` | hello_world '26 teaser | `kicker`, `title`, `name`, `place`, `date` |
| `WordCaptions` | podcast clip captions (green active word) | `words[{text,startMs,endMs}]`, `wordsPerLine`, `videoSrc?` |
| `EndCard` | Morphosis end card | `eyebrow`, `programme`, `line`, `cta`, `partners[]` |

Every composition is 1080x1920 at 30 fps. Brand tokens are in `template/src/brand.ts`.

## Use

```bash
cp -R "${CLAUDE_SKILL_DIR}/template" ./reel-motion && cd reel-motion && npm install
npx remotion studio src/index.ts                  # preview + tweak props in the browser
npx remotion render src/index.ts ListCard out/list.mp4 --props=props.json
npx remotion still  src/index.ts EndCard  out/end.png --frame=90   # quick check
```

Write `props.json` matching the props table. Duration adapts to the data:
`Counter10K` and `ListCard` grow with their steps and items, and `WordCaptions` ends at the last word.

Media (`image`, `backgroundVideo`, `videoSrc`) must be in `public/` and referenced with
`staticFile("name.mp4")`, or be a full https URL.

## Rules

- Load the `remotion-best-practices` skill before writing new Remotion code.
- Project code rules apply: TS/TSX files at most 160 lines, no `any`, no `eslint-disable`.
  Add a new composition as its own file and register it in `Root.tsx`.
- Run `npx tsc --noEmit` and render one `still` of every changed composition before handing off.
- Mongolian Cyrillic is typeset here, never inside AI-generated images (they misspell it).
- The tokens in `brand.ts` were sampled from published reels. Swap in the official brand book when the design team provides it.
