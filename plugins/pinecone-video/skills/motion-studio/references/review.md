# Review loop

Run `bash review.sh out/<file>.mp4 [fast_moment_s]`, then Read every image it lists.
Review as a strict motion director, not as the author. Write each round to `docs/review_log.md`.

## Scorecard (1-10 each; ship only when every row is 8+)

| Criterion | 8 or higher means |
|---|---|
| Hook | Something striking is on screen and moving before 1.0 s; the idea is readable by 2 s |
| Phone readability | Every word reads in `review_phone.png` at 360 px wide; nothing in the reel safe-zone margins |
| Motion quality | Everything springs; nothing slides linearly or pops without an in/out |
| Rhythm | Something new every 2-4 s; changes sit on beats (check against `beats.json`) |
| Composition | Clear focal point per frame; consistent margins; no accidental overlaps |
| Brand | Real logo, palette, fonts, UI; Mongolian spelling correct |
| Sound sync | Hits land on visual events (check the frames in `review_strip.png`) |
| Loop / ending | Last frame hands off cleanly (loop seam invisible in `review_loop.mp4`, or a CTA holds 1.5 s or more) |

## What to look for in the images
- Text from the old and the new state visible at once during a swap
- Ghosted numbers (content changing between sub-frames; step on whole frames instead)
- Blurry text after a scale-up (draw text at final size, scale down instead of up)
- Frames where only a flat colour is on screen (dead beats)
- The cursor covering the content it is meant to point at
- Default AI looks from the house-rules list

## Fix efficiently
- Re-render only the affected seconds: `node render.mjs --from 3.5 --to 5 --sub 1`
- Check a single moment: `node render.mjs --still 4.2`
- Use a low-res rough cut while fixing pacing: `node render.mjs --scale 0.5 --sub 1`
- Do at least 3 review rounds on a new film before showing it.

## Troubleshooting
| Symptom | Likely cause, fix |
|---|---|
| Two renders differ | `Math.random`, `Date.now`, a timer, or state carried between frames; replace with `rng`/`track` |
| Wrong or fallback font | Font not awaited; add it to `window.ready` (`document.fonts.load(...)`) |
| Blank or black output | A page error; `render.mjs` prints `[page error]`. Check that the module paths are relative |
| Motion feels floaty | Springs too soft; use `SNAPPY` for UI and keep `HEAVY` for big type only |
| Music drifts from cuts | `beats.json` was measured on a different file; re-run `beats.py` on the final track |
| Looks generic | No reference given; start from `briefs.md` B (style from a reference) |
