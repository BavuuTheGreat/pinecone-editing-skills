# Refreshing the themes from a reel audit

Themes come from what Pinecone posts and how it performs. Re-run every ~3 months or when the
Editing manager asks.

1. Run `reel-audit` on `https://www.instagram.com/pineconemongolia/reels/` into
   `audits/<yyyy-mm>-pineconemongolia/` (catalog.csv + summary.md).
2. For every theme card, update the **Audit** block: reel count, organic median views, like rate,
   median length, cuts/min, 1-3 example reel URLs (the best organic ones).
3. A format in `reel-audit/references/format-taxonomy.md` with 3+ reels and no card: write a new card
   from `themes/_template.md`, status Beta, and add it to the table in `SKILL.md`.
4. A theme whose reels changed style (length, pace, captions, end card): update the card's style table
   and note the date. Never change a Ready theme's style without the Editing manager's OK; its rules
   were approved in review.
5. Promote Beta → Ready after 3 reels of that theme pass review with no style comments.
6. Bump the plugin version and list the changes in the PR.

Use the median, not the mean, and organic numbers (boosted reels have like rates near 0.0%).
