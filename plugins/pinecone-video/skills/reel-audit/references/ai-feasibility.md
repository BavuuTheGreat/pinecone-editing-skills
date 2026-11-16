# Scoring AI feasibility per reel

`ai_share_pct` = share of the reel's screen time that could be produced today
by (a) image/video models (Higgsfield), or (b) code-driven motion graphics (Remotion),
WITHOUT putting a synthetic version of a real person on screen.

Score each of the 9 frames in the contact sheet, then average:

| Frame shows | Score |
|---|---|
| Real person speaking / reacting (founder, student, creator, guest) | 0 |
| Real event or venue footage | 0 |
| Live footage + overlay graphic (caption chip, sticker, title) | 10 |
| Screen recording / UI mockup | 50 |
| Generic b-roll (code on monitor, office, city) with no identifiable person | 70 |
| Surreal / metaphor / CGI scene (Earth, data globe, stone heads, 3D characters) | 100 |
| Pure motion graphics (kinetic type, counters, end cards) | 100 |

Also record `ai_scenes`: short names of the scenes that scored >= 70, with the
time of the frame (frame n is at duration * (n + 0.5) / 9).

Edit-only automation (captions, reframing, clip picking, dubbing) does not count
toward `ai_share_pct`. List it separately because it saves time on 0% reels too.

## Format -> AI role (Oct 2026)

| Format | AI-made share | AI generates | Automate in edit | Keep human |
|---|---|---|---|---|
| Motion / CGI teaser | 95% | 3D scenes, kinetic type | render variants | brand sign-off |
| Cinematic brand film | 56% | surreal/CGI shots, Earth, HUDs | grade, reframe 16:9 -> 9:16 | actors, direction |
| Presenter / promo | 24% | b-roll, list cards, end cards | English dub, captions | the host |
| Creator collab | 7% | stickers, inserts | captions | the creator |
| Event / partnership | 4% | logo stings | highlight picking, captions | the footage |
| Podcast clip | 0% | - | clip picking, captions, reframe | the founder |
