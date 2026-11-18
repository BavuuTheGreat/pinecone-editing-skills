# Animation library for the series (Annnimate starter pack)

The reviewer gave us the **Annnimate starter pack** (19 free web components, "yours to use in any project, no attribution",
https://annnimate.com) to make clips look more professional "but keep it simple". The raw pack is saved here
(`annnimate-starter-pack/`, git-ignored: third-party download, keep it out of the public repo; the original is in
`~/Downloads/annnimate-starter-pack`, and a copy is in the series kit folder next to the footage).

## What the pack is, and why it is ported rather than pasted
Each component is **GSAP + ScrollTrigger for a web page** (React, Vue and plain HTML versions, plus a `preview.mp4`). A video render needs
every frame to be a pure function of time, so the video engine does not run the components; it re-implements their **motion** (durations,
staggers, easing curves, layering, read from each component's source) as `time -> pixels` in Remotion:
`../../testimonial-reel/engine/src/eng/anm.tsx`. Same look, deterministic, no GSAP at render time.

## Ported and used in the series (episode 1)
| Component | Port | Where it is used | Why |
|---|---|---|---|
| curtain-slider | `CurtainOut`, `curtainPath`, `curtainIncoming` | between the layers of the wide window: map -> office-guide scenes, scene -> scene (12 columns wipe away, 0.7 s, the next image zoom-settles in beneath) | replaces hard cuts inside the window with one clean, professional move |
| dual-scramble | `DualScramble` | chapter label (resolves out of Pinecone-green noise), the map's "Pinecone Academy" | fits the "Ghost Text" idea: text being generated |
| split-flap-board | `SplitFlapTile` | the "50 m" tag on the map (two tiles riffle up from 00, rebound on landing) | a mechanical counter that tells "50 metres" at a glance |
| process-rail | `ChapterRail` | optional chapter indicator: job `"chapter_style": "rail"` (default stays the pill) | a bead travels along a line, each step lights as it arrives |
| text-reveal | `TextReveal` | available (words rise out of a mask, staggered, expo.out); not used in episode 1 | for headlines/titles in later episodes |
Easing curves from the pack: `ANM = bezier(0.3, 0.9, 0.1, 1)`, `ANM_IO = bezier(0.7, 0, 0.16, 1)`.

## The other 14 and what they would be good for in a video
accordion (reveal list rows line by line: FAQ-style lower thirds), ascii-overlay (data characters over a photo: tech-flavoured establishing shot),
diagonal-gallery (stepping photo queue: a "meet the team" or event recap), echo-headline (one-word headline with a 3D trail of echoes: a bold
single-word title card), elastic-divider (a line that rings like a string: a section divider between chapters), feature-dialog (tile that expands
into a dialog: product feature callout), floating-navbar (header folding into a pill: UI mock-ups), image-fly-in (images flying out of depth: a
montage of screenshots), magnetic-tag-cloud (tags knocked apart and pulled back: skills/tools cloud), multi-level-drawer-menu (UI demo),
pricing (digit-by-digit price roll: a counter/number reveal), rotating-words (a wheel of words landing on the last: "AI can ... build / debug / ship"),
scale-slider (photos shrinking toward an edge: a carousel of project shots), stacking-cards (cards covering each other with a counter: step-by-step cards).
Keep it simple: one or two of these per episode at most, only where they explain something.

## How to port another one (about 30 minutes)
1. Read the component's `.js` for: `duration`, `stagger`, the `ease`, what moves (`x/y/yPercent/rotateX/clip`), and the order of the tweens.
2. Write it as a React component taking `t` (seconds since it started) in `anm.tsx`; compute each tween with `interpolate(t, [start, start + duration], [from, to], { easing })` (the pack's GSAP eases map to `Easing.bezier` / `Easing.out(Easing.exp)` / power2 = `x*x`).
3. Randomness only through a seeded hash of (index, frame bucket), never `Math.random`.
4. Check with `remotion still` at three frames (start, middle, end) before a full render.
Shortcut for heavy ones: drive the real GSAP timeline by frame (`tl.seek(frame / fps)` inside `useLayoutEffect`, `gsap.ticker.lagSmoothing(0)`; no ScrollTrigger) and render the DOM; test in a still first.

## Licence note
README of the pack: free components, "yours to use in any project", no attribution, no expiry. The library has 130+ more components (paid). Do not republish the pack itself.
