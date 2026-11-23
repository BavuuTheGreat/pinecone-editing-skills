# Intake

## What I do

I look at a new folder of videos and write down what is in it.

## For engineers

- Inputs: folders in `inbox/` (video files, optional `note.txt`).
- Outputs: a `reel.json` record in `state/<reel id>/` with status `new`, then `transcribing`. It holds file kind, length, width, height (from `ffprobe`) and the parsed note.
- Module: `factory/factory/inbox.py` (with `state.py` for the record).

## I must

- Skip a folder whose files changed in the last 60 seconds: it is still being copied.
- Give each folder a unique id (a second folder with the same slug gets `-2`).
- Add a need (a plain sentence) when there is no video or `name:` is missing.
- Write records atomically: temp file, then rename.

## I must never

- Move, rename or delete the manager's footage.
- Take a name from speech or from the file name. Names come from `note.txt` only.
- Stop the whole tick because one folder is broken: record the error in that reel's needs and go on.

## I hand over to

Listener.
