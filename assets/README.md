# assets: shared library for every member

Music, images and sound effects that any member can use in a reel. Every file has a licence you can point to.

The files themselves are not in git. `MANIFEST.json` lists them, `fetch_assets.py` downloads them from their
licensed source. This keeps the public repo small and the licences clear.

## What belongs here

- Music, images, sound effects and fonts that are free to share, with a licence that allows this use.
- Each one must have a source URL (or a licence page) and the exact credit text the licence asks for.

## What must never be here

- The Pinecone brand pack: the GIP font, the Pinecone logo, the end cards. They stay in the private brand zip that
  `setup.py --brand <zip>` installs into the engine.
- Third-party logos (trademarks).
- Real footage, student names, transcripts, captions.
- Anything without a licence you can point to. "Found online" is not a licence.

If you are not sure, do not add it. Ask the Editing manager.

## Layout

```
assets/
  MANIFEST.json     the list: id, file, source, licence, credit, mood, themes
  fetch_assets.py   downloads the files in the list
  README.md
  music/            fetched .mp3 files + CREDITS.txt (credit lines of the tracks you have)
  images/           empty for now
  sfx/              empty for now
```

`music/*.mp3`, `music/*.wav`, `images/*` and `sfx/*` are git-ignored. `MANIFEST.json`, `README.md`,
`fetch_assets.py` and `music/CREDITS.txt` are tracked.

## Fetch

```
python3 assets/fetch_assets.py                    # download every missing file
python3 assets/fetch_assets.py --list             # id, title, licence, present or missing
python3 assets/fetch_assets.py --only easy-lemon  # one entry
python3 assets/fetch_assets.py --force            # download again
```

It needs only python 3 and an internet connection. It checks that the download is audio and at least 100 KB, then
writes `music/CREDITS.txt`. If any download fails it says which one and exits with an error.

## Add an asset

1. Put the file in the right folder (`music/`, `images/` or `sfx/`). Keep a short, readable file name.
2. Add one entry to `MANIFEST.json` in the matching list. Required fields: `id` (lower-case, unique), `title`,
   `file` (path under `assets/`), `licence`, `licence_url`, `credit`. Add `source_url` if the file can be downloaded,
   so `fetch_assets.py` can fetch it. Add what you know (`artist`, `bpm`, `mood`, `themes`, `tags`, `notes`). Leave out
   what you do not know.
3. Check it: `python3 assets/fetch_assets.py --list` shows the entry. Open a pull request.

`themes` names the theme cards (in `plugins/pinecone-video/skills/edit-reel/references/themes/`) the track suits.
The factory planner reads it when it chooses music. A track with `"tags": ["default"]` is the first choice for its theme.

## Credit

Every track here is Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/). A video that uses
one must show the credit line from `music/CREDITS.txt` (also the `credit` field in `MANIFEST.json`) where it is posted.

The engine keeps its own copy of Funkorama in `plugins/pinecone-video/skills/interview-reel/engine/assets/music/`.
That copy is the one the testimonial engine reads today.
