# Review rounds

Reviewers leave comments on the Marketing Planner "Video review" page
(ask the Editing manager for the link; PIN per member; never type a PIN, ask the user for
screenshots or text). Each comment is `time` + text. Times are in the **edited** video, which uses the
same timeline as the caption file.

## Reading comments

| Comment looks like | Means |
|---|---|
| a word or phrase ("санхүүд", "байгаа") | replace the caption line at that time with this wording |
| "X → гээд шууд өгүүлбэрийг нь дуусгачий" | the line becomes X and the sentence ends there |
| "… гэдэг 2 үгийг нь хасчих" | delete those words (or the whole line if that is all it holds) |
| a name ("Бат-Эрдэнэ") at 0:01–0:02 | the name title is wrong: fix `name` (file name changes too) |
| "өгүүлбэрээ дуусгахгүй … төгчихлөө" | the cut ends mid-sentence: extend the piece if the raw file finishes the sentence, otherwise drop that piece/question |

Count the comments: the page shows "N open"; the yellow dots under the player mark every comment. If a
screenshot shows fewer than N, ask for the rest before the final render.

## Applying

1. Back up the caption files (`build/caption_backup_<date>/`).
2. Edit with exact-match replacement: each old line must exist exactly once, or stop and look.
3. Name changes: update `name` (and `title_scale` if long) in the manifest.
4. Re-render only the affected students into a staging folder (`--out-dir build/stage-fix`).

## Checking a render

- One still at each comment time, cropped to the caption band (y 1490–1730), stacked in one image.
- Title still at 1.6 s. Last frame before the end card (duration − 10.2 s).
- Loudness line printed by `run.py`: about -14.5 LUFS, true peak ≤ -1 dBTP.

## Delivering

Move the staged files over the old ones. When a name changed, move the old-name files to the Trash
(`~/.Trash/` on macOS), never `rm`. Tell the user which comments are done and which need their call.
