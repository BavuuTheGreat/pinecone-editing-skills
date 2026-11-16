# @pineconemongolia reels audit - 19 Oct 2026

Scope: all 32 reels on the Reels tab, posted 5 Aug - 19 Sep 2026. Public counts pulled 19 Oct 2026.
Data: `catalog.csv` (one row per reel, with URL). Rebuild: `python3 build_catalog.py <dir with reels/ and sheets/>`.

## Headline
- 32 reels in 46 days (about 4.9/week), 920,385 views, median 11.45K, 10,230 likes (1.11% like rate)
- Median reel 90 s, 5.1 hard cuts/min

## Formats
| Format | Reels | % reels | % views | Median views | Like rate | AI-made (runtime-weighted) |
|---|---|---|---|---|---|---|
| Creator collab | 9 | 28% | 44% | 30.4K | 1.71% | 7% |
| Cinematic brand film | 3 | 9% | 19% | 13.2K | 0.07% | 56% |
| Event / partnership film | 4 | 12% | 17% | 10.7K | 1.20% | 4% |
| Podcast clip | 10 | 31% | 13% | 8.1K | 0.90% | 0% |
| Presenter / program promo | 4 | 12% | 4% | 7.0K | 0.25% | 24% |
| Motion / CGI teaser | 2 | 6% | 3% | 12.4K | 0.52% | 95% |

## Findings
1. Creator collabs over-deliver: 28% of reels, 44% of views, best like rate.
2. Podcast clips under-deliver: 31% of reels, 13% of views, 5 of the bottom 5 (3 of them were posted in the window's last 4 days).
3. The #1 reel (Morphosis film, 155K views) has 3 likes, and the Bootcamp anthem (11.1K) also has 3. Most likely paid reach. Confirm with the ads team.
4. 11% of total screen time is AI-makeable today. It is concentrated in 9 reels, each at 30% or more.
5. 3 reels were posted at 16:9 (Morphosis film, Bootcamp anthem, alumna story) and show black bars in the feed.

## Method limits
- Audio not transcribed (no Whisper key). Formats were classified from 9 frames per reel plus captions.
- AI-made share is an expert estimate per `plugins/pinecone-video/skills/reel-audit/references/ai-feasibility.md`.
- View counts include paid boosts. Use like rate for organic resonance.
