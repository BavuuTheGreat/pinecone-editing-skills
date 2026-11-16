# Presenter / program promo

A staff host on camera explains a program, deadline or offer, with list cards and a CTA.

**Status:** Beta · **Made by:** `assemble.py` + `brand-motion` · **Audit:** 17 reels, median 8.9K organic, 0.25% (lowest like rate), 30-205 s, ~8 cuts/min
**Examples:** instagram.com/reel/DdYiEQok8oS (listicle), /reel/DdCpl1jTswR

## Signals
- One staff member talking to camera in the office; screen recordings; program names, dates, prices

## Need from you
- ★ Program name · ★ the CTA (link, deadline) · ★ host name if shown · optional: the list items

## Style
| Part | Rule |
|---|---|
| Length | 30-45 s (longer ones performed worst) |
| Structure | Hook claim (0-3 s) → 3-5 points, one per cut → CTA |
| Pace | Cut out every pause and retake; a jump cut every 3-6 s; punch-in (crop) on emphasis |
| Captions | `WordCaptions` throughout |
| Graphics | `ListCard` for the points, screen-record inserts, `EndCard` with the CTA |
| Music | Funkorama bed 16.5 dB under speech |
| End | Program `EndCard` (CTA) → Pinecone end card |

## Recipe
1. Transcribe; drop retakes, fillers and false starts; keep sentences that end cleanly.
2. `edl.json` with every kept sentence as a clip; alternate `crop_x` / tighter source crop for punch-ins.
3. `assemble.py cut` → `WordCaptions` + `ListCard` + `EndCard` → `assemble.py finish`.

## Check
- [ ] Under 45 s · [ ] no retake left · [ ] CTA readable for 2+ s
