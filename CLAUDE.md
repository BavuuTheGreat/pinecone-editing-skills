# CLAUDE.md - pinecone-editing-skills

Any agent working in this repo reads this first. The repo is PUBLIC on GitHub (BavuuTheGreat/pinecone-editing-skills).

## What this repo is

Pinecone Academy's editing station for Claude Code: raw footage in, finished 9:16 Pinecone reels out. It ships as one
Claude Code plugin (`pinecone-video`) plus a local "editing factory" that watches an inbox folder, proposes a reel,
waits for a human yes, edits, and queues the result for review.

## Map

```
.claude-plugin/marketplace.json            makes the repo a plugin marketplace
plugins/pinecone-video/
  .claude-plugin/plugin.json               plugin manifest (version must equal marketplace.json)
  skills/<skill>/SKILL.md                  one folder per skill; frontmatter `name` == folder name
  skills/interview-reel/engine/            python + Remotion engine: run.py, pinequest.py, engineers.py, reelpipe/, src/
factory/                                   the editing factory (python stdlib): factory/, tests/, agents/, themes.json, ui/
docs/SKILLS.md                             every skill explained for an engineer and a five-year-old
docs/content-factory/, docs/tdd/           member guide, editing rulebook, checklist
docs/engineers-series/README.md            Engineers series guide
assets/                                    fetch_assets.py + MANIFEST.json (openly licensed music and images)
scripts/check_manifests.py                 install-manifest integrity check (+ test_check_manifests.py)
.github/workflows/ci.yml                   engine, factory, manifests, security jobs
```

## Skills (`plugins/pinecone-video/skills/`)

| Skill | Job | Old name |
|---|---|---|
| `edit-reel` | Editing station entry point: footage in, picks the theme, hands off, checks, delivers | |
| `interview-reel` | Interview / testimonial reels; hosts the testimonial, PineQuest and Engineers engines | `testimonial-reel` |
| `engineers-series` | Episodes of "Engineers matter more with AI" | |
| `podcast-clipper` | Long podcast to 30-60 s vertical clips | |
| `motion-studio` | Bespoke code-rendered motion films | |
| `brand-templates` | Fixed Pinecone graphics (counter, list card, title, captions, end card) | `brand-motion` |
| `reel-planner` | Plan a reel: format, shot list, film / generate / template per shot | `ai-video-playbook` |
| `reel-audit` | Audit an account's reels | |
| `loop-engineer` | The loop for any main goal | |
| `ecc-triage` | Handle the ECC Tools bot comments on a PR | |

Theme cards live in `plugins/pinecone-video/skills/edit-reel/references/themes/`. A review lesson goes into the theme
card, not into one job. Per-video fixes go into the job file, never into `engine/src` or `engine/assets`.

## How to run every check

```bash
python3 scripts/check_manifests.py                  # manifests, skill folders, README, docs/SKILLS.md
python3 -m unittest discover -s scripts -q          # tests of the manifest check
cd plugins/pinecone-video/skills/interview-reel/engine && python3 -m unittest discover -s tests          # engine
cd factory && python3 -m unittest discover -s tests -q                                                   # factory
cd factory && bash tests/e2e_smoke.sh                                                                    # CLI end to end
cd plugins/pinecone-video/skills/interview-reel/engine && npm ci && npx tsc --noEmit                      # TS types
python3 pinequest.py <job.json> --plan              # (from the engine folder) prints the timeline without rendering
```

CI (`.github/workflows/ci.yml`) runs the engine, factory, manifests and security (bandit, gitleaks) jobs. All must be green.

## Rules for a main goal and for PRs

- A main goal (several reels, a feature, "fix everything") runs under the `loop-engineer` skill: split into units, an
  acceptance check per unit with real evidence, all units pass in the same iteration, 3 failed iterations with no new
  information = blocked, park items the owner must decide, never weaken a check.
- Every push to a PR is followed by the `ecc-triage` skill: wait 1-2 minutes, read the ECC Tools comments for the
  latest commit, fix the useful findings, loop until CI is green. Do not comment on the PR on your own.
- Test first: watch a test fail, then pass. Keep diffs minimal.
- Changing a skill name: rename the folder, the `name:` in SKILL.md, every path that mentions it, README, `docs/SKILLS.md`,
  both manifests (bump `version` in both), and run `scripts/check_manifests.py`.

## Public-repo privacy rules

This repo is public. Never commit:

- real student names, transcripts, captions or audio: use placeholders such as "Сурагч" in examples, tests and docs
- footage, renders, `build/` output, job folders (real jobs stay on the editing Mac and are git-ignored)
- brand pack files (GIP font, Pinecone logo, end cards) or anything the licence keeps private
- credentials, tokens, cookies, `.env` files
- internal review URLs (links into the Marketing Planner video review) or private channel names

Only `_house.json` and anonymized `_example.json` files are committed. When unsure, leave it out and ask.

## Commits and PRs

- Author and committer: the repo owner identity already in `git log` (BavuuTheGreat, GitHub noreply address). Check with
  `git log -1 --format='%an|%ae'` and set `GIT_AUTHOR_NAME/EMAIL` and `GIT_COMMITTER_NAME/EMAIL` to that.
- No attribution lines: no `Co-Authored-By: Claude`, no "Generated with Claude Code", in commits, PR bodies or files.

## Rendering

Render concurrency is **1** on a 16 GB Mac (set `"concurrency": 1` in the job; higher values have crash-looped the
browser). One render at a time: the factory holds a render lock. Scratch output goes to `engine/build/` (git-ignored,
safe to delete).
