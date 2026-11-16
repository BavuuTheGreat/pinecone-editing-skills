# Event recap

Fast-cut film of a Pinecone event or partnership: stage, crowd, quick handheld interviews, co-brand.

**Status:** Beta · **Made by:** `assemble.py` + `brand-motion` · **Audit:** 10 reels, median 10.0K organic, 1.20% (Oct), 55-190 s, ~18 cuts/min (best one: 46 cuts/min, 55 s, 126K)
**Examples:** instagram.com/reel/Dc3WEeziWJ5, /reel/DciHlCSmyY4, /reel/DcS54TXCJsv

## Signals
- Stage, audience, many short handheld shots from one day; partner logos; short mic interviews

## Need from you
- ★ Event name and partner names (exact spelling) · ★ date · optional: 1-3 interview quotes to keep, CTA

## Style
| Part | Rule |
|---|---|
| Length | 45-75 s (the 55 s recap beat every longer one) |
| Structure | Hook: biggest crowd or stage moment (0-3 s) → co-brand title → 3-5 beats (arrival, stage, people, reactions, win) with 1-2 short quotes → closing wide shot |
| Pace | 20-45 cuts/min on b-roll; let a quote run 3-6 s |
| Captions | Only under quotes (`WordCaptions`) |
| Graphics | `KineticTitle` co-brand lockup (e.g. "MongolZ x Pinecone"), event name + date |
| Music | Music lead (`"music_lead": true`), quotes ducked in by keeping their clip audio |
| End | Pinecone end card |

## Recipe
1. Contact sheet of every file; list usable shots with time ranges (wide, crowd, stage, reaction, logo).
2. Transcribe only the interview clips; pick 1-2 quotes that end on a finished sentence.
3. `edl.json`: b-roll clips 0.8-2.5 s with `"audio": false`, quotes with audio. Order by the structure.
4. `assemble.py cut` → `KineticTitle` overlay + quote captions → `assemble.py finish`.
   For quotes over music: set `"music_lead": false` and `"speech_over_bed_db": 10`.

## Check
- [ ] Hook is motion or crowd, not a logo
- [ ] Partner names spelled as given
- [ ] 45-75 s
