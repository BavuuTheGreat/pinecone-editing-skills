# Office trend

Staff doing a trending format (dance, photo frame, "who is the impostor"), filmed on a phone. #lifeatpinecone.

**Status:** Beta · **Made by:** `assemble.py` · **Audit:** 5 reels, median 9.0K organic, 0.79%, 15-115 s, ~2 cuts/min
**Examples:** add on the next refresh (`audit-loop.md`)

## Signals
- Phone footage, staff in the office, the same trend audio or pose repeated

## Need from you
- ★ Which trend (link to the original) · ★ the trend audio file, if licensed · ★ names if shown on screen

## Style
| Part | Rule |
|---|---|
| Length | Match the trend: usually 10-30 s |
| Structure | The trend's own beats; hook is the first person / reveal at 0 s |
| Pace | Cut on the beat of the trend audio |
| Captions | One line of on-screen text (the trend's prompt), no speech captions unless people talk |
| Music | The trend audio, music lead (`"music_lead": true`) |
| End | No end card (keep it native) unless asked; `"end_card": null` |

## Recipe
1. Get the beat grid: `python3 ../motion-studio/engine/beats.py <audio>` (or count BPM).
2. `edl.json` with one clip per beat group, `"audio": false`, `"music": "<trend audio>"`.
3. `assemble.py cut` → optional text overlay → `assemble.py finish`.

## Check
- [ ] Cuts land on the beat · [ ] audio is licensed for the account
