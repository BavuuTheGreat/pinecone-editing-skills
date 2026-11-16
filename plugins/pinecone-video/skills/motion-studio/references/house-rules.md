# Film folder rules (Claude reads this on every run in this folder)

## Render contract
- The film is a pure function of time. `window.seek(t)` paints exactly frame t, in any order.
- Never use CSS transitions or animations, `setTimeout`, `setInterval`, `requestAnimationFrame` in
  render mode, `Date.now()`, or state carried from one frame to the next.
- Randomness only via `rng(seed)` / `noise()` from `lib/motion.js`. `Math.random` is banned.
- Motion only via `spring` / `track` / `trackVec` from `lib/motion.js`. No linear slides, no CSS easing.
- The page exposes `window.film = { duration }`, a `<canvas id="c">` sized from `?w=&h=`, and
  `window.ready` (a promise for fonts and assets).
- Numbers and text that change content step on whole frames (`Math.floor(t * fps) / fps`).

## Pinecone look
- Palette: ink #0E1220, paper #F4F5F1, Pinecone blue #2E55E0, soft blue #7C9BFF. One accent per film.
- Type: one display face and one text face, both with Cyrillic support (Inter, Manrope, Montserrat,
  Unbounded, IBM Plex Sans). Mongolian copy is proofread by a human before the final render.
- Use the real logo, real product UI and real photos from `./assets`. Never invent a UI screen.
- Avoid these defaults, which make a film look machine-made:
  - a title centered on a gradient
  - every element fading in the same way
  - decorative corner labels, frame borders or HUD clutter
  - glows on UI, random particle bursts
  - more than 4 seconds with nothing new on screen
- Safe zones for reels: keep text out of the top 220 px and bottom 380 px of a 1080x1920 frame.

## Sound
- Music is either a supplied track we have rights to, or `synth.py`. Never a downloaded song.
- Changes land on `beats.json` beats, big moments on downbeats, sound effects on hits.
- Final mix at about -14 LUFS via `finish.sh`.

## Before showing the user anything
1. Render stills or a contact sheet (`review.sh`) and look at the images.
2. Score with `docs/review.md`. Fix the three worst issues.
3. Repeat until every score is 8 or higher. Then do the full render.
