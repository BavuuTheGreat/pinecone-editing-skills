---
name: reel-audit
description: Batch-audit an Instagram/TikTok/YouTube Shorts account - collect every reel URL, download them, build one contact sheet per reel plus pacing metrics, then classify each reel by format and score which scenes AI can produce. Use when asked to "watch our reels", "audit our content", "what kind of videos do we make", or to benchmark a competitor account.
argument-hint: "<profile-or-reels-url> [why you're auditing]"
allowed-tools: Bash, Read, Write, AskUserQuestion
---

# /reel-audit - watch a whole account, not one video

`/watch` is for one video. This skill is for 10-100 short videos at once, where
per-video Whisper + 30 frames would cost too much. Use one 3x3 contact sheet per reel
(about 1/10 of the tokens) plus the caption text and view counts.

## Pipeline

| Step | What | Output |
|---|---|---|
| 1 | Collect reel URLs + view counts | `urls.txt`, `views.tsv` |
| 2 | Download video + metadata | `<id>.mp4`, `<id>.info.json` |
| 3 | Contact sheets + pacing | `<id>.jpg`, `metrics.csv` |
| 4 | Read every sheet, classify | `catalog.csv` |
| 5 | Aggregate + AI-feasibility scoring | `summary.md` |

### 1. Collect URLs

`yt-dlp` cannot list Instagram profiles ("Unsupported URL"). Use Claude in Chrome
on `https://www.instagram.com/<handle>/reels/` (the user must be logged in), scroll
to load the full grid, then run in the page:

```js
const m = new Map();
document.querySelectorAll('a[href*="/reel/"]').forEach(a => {
  if (!m.has(a.href)) m.set(a.href, a.innerText.replace(/\n/g, ' '));
});
[...m].map(([u, v]) => `${u}\t${v}`).join('\n');
```

The grid tile text is the play count. Save it as `views.tsv` (url, views).

### 2. Download (public reels need no login)

Run downloads from a **fresh empty directory**, and keep scripts outside it:

```bash
yt-dlp -a urls.txt -o "%(id)s.%(ext)s" --write-info-json \
  -f "best[height<=720]/best" --sleep-interval 2 -q --no-warnings
```

`info.json` gives `upload_date`, `like_count`, `comment_count`, `description` (the caption).
`duration` is often null for Instagram, so read it with ffprobe (step 3 does this).

### 3. Contact sheets + pacing

```bash
bash "${CLAUDE_SKILL_DIR}/scripts/contact_sheet.sh" <videos_dir> <sheets_dir>
```

- One JPG per reel: 9 evenly spaced frames, read left to right, top to bottom.
- `metrics.csv`: duration, hard cuts (ffmpeg scene > 0.3), cuts/min, average shot length.

### 4. Classify

Read sheets in parallel batches of about 8. For each reel record in `catalog.csv`:

`id, date, views, likes, duration_s, cuts_per_min, format, people_on_screen, setting, text_overlay(Y/N), ai_share_pct, ai_scenes`

Use the format taxonomy in `references/format-taxonomy.md`. Add a new format only
if 3+ reels fit it and none of the existing ones do.

### 5. Aggregate

Report the general picture first and then the detail. Put a number on every claim:
1. Totals: reels, total views, median views, date range, posting cadence.
2. Format mix: count, % of reels, median views per format.
3. Top 5 / bottom 5 by views, with their formats.
4. AI feasibility per format (see `references/ai-feasibility.md`).
5. Scene-level list: which shots to replace or extend with AI, and which tool to use.

Use the median, not the mean. One viral reel distorts the mean.

## Gotchas

- The ffmpeg build may lack `drawtext`, so the sheets have no timestamp labels. Frame n is at `duration * (n + 0.5) / 9`.
- Do not use the user's browser cookies with yt-dlp unless they ask. Public reels download without login.
- Instagram captions are often in Mongolian (Cyrillic). Quote them and translate them in the report.
- Delete the downloaded MP4s when done. They are the account owner's media.
