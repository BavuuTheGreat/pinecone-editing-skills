# Engineers matter more with AI: try the series skill

A 30-32 s vertical reel (1080x1920, 30 fps) from one presenter take plus a screen recording. Face on frame 0 with
a problem hook, a built-with-AI line with the Claude and Higgsfield brand colours, the solution demo over his
words, then a typed "Ghost Text" title as the closer. Captions in the Pinecone style, jazz bed under the talk.

## Where things live

| What | Path (under `plugins/pinecone-video/skills/`) |
|---|---|
| Skill entry point (read first): steps, checklist, history of every review round | `engineers-series/SKILL.md` |
| Theme card: the style rulebook (length, structure, captions, music, colours, checklist) | `edit-reel/references/themes/engineers-matter-ai.md` |
| Template job (every key explained) | `interview-reel/engine/batches/engineers/_example.json` |
| Renderer | `interview-reel/engine/engineers.py` (pipeline), `src/eng/*` (Remotion), `reelpipe/eng_music.py` (sound) |
| Motion catalog (curtain, scramble, split-flap) and the reviewer's reference reel analysis | `engineers-series/animations/README.md`, `engineers-series/references/reference-reel-analysis.md` |

## Try it (about 30 min the first time)

1. Install Claude Code, then inside it:
   ```
   /plugin marketplace add BavuuTheGreat/pinecone-editing-skills
   /plugin install pinecone-video@pinecone-editing-skills
   ```
2. Say `set up the editing station` and wait for **Ready** (python, numpy, node, ffmpeg, Remotion).
3. Optional but recommended for exact caption timing: `python3 interview-reel/scripts/setup.py --align`
   (about 0.5 GB venv plus a 1.2 GB model).
4. Say: `make an Engineers matter more with AI episode from <presenter take> and <screen recording>`.
   Claude asks for what it needs (presenter name and role spelled exactly, which sentence each screen belongs to)
   and builds the job from `_example.json`.

Or by hand, from `plugins/pinecone-video/skills/interview-reel/engine/`:
`python3 -I engineers.py <job.json> --plan` (shows the cut and the length) then without `--plan` to render.
Other flags: `--align` (caption timing), `--remix` (sound only), `--intro` (standalone title).

## What is NOT in this repo (and what happens without it)

| Missing | Effect | How to get it |
|---|---|---|
| Brand pack: GIP caption font, Pinecone mark, brand end card | Captions fall back to Manrope; no faded mark top-centre | Editing manager, then `setup.py --brand <zip>` |
| Claude and Higgsfield logos (`engine/assets/claude_mark.png`, `higgsfield_mark.png`) | Only the coloured wordmark shows on the brand beats | Put your own 512 px PNGs in `engine/assets/`; they are git-ignored (trademarks) |
| Music track | The synthesized jazz bed plays instead | Set `music_file` in the job; episode 1 used "Jazz Music #1" by Mogo Mogo: check its licence before posting |
| Real episode jobs, footage, captions | Template only | Jobs are git-ignored on purpose (names, audio). Bring your own take |
| Annnimate starter pack (raw) | Not needed: the motion is already ported to `src/eng/anm.tsx` | n/a |

## Known limits

- Render takes roughly 10-15 min on a 16 GB Mac (concurrency 2).
- Captions come from the reel generator (`dash.pinecone.mn/reel`) through Chrome in the main Claude session; forced alignment then fixes the timing.
- Episode 1 ships at 32 s (reviewer allowed it); the default target is 30 s (`target_seconds`).
