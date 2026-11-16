# pinecone-editing-skills

Pinecone Academy's editing station for Claude Code. Drop raw footage in a folder, tell Claude what
reel you want, answer its questions (names, team, result) and get a finished, house-style 9:16 reel
back: cuts, typed question cards, corrected Mongolian captions, music, logo, end card, loudness.
Nobody has to open an editor.

The styles are not guesses. Each theme was measured from Pinecone's own published reels and then
tuned in review rounds with the Marketing reviewer, so the output looks like what the account posts.

> Private repo. Your GitHub account needs access, and `git` on your computer must be signed in to
> GitHub (`gh auth login`) before Claude Code can install from it.

## Install (once per computer, ~10 min)

1. Install Claude Code: https://claude.com/claude-code
2. Inside Claude Code:
   ```
   /plugin marketplace add BavuuTheGreat/pinecone-editing-skills
   /plugin install pinecone-video@pinecone-editing-skills
   ```
3. Say: `set up the editing station`. Claude runs `testimonial-reel/scripts/setup.py`, which checks
   python, numpy, node and ffmpeg, prints the install command for anything missing on your OS (Mac,
   Windows, Linux) and installs the pinned render engine. Wait for **Ready**.
4. **Brand pack** (Pinecone members only). The caption font (GIP, licensed), the Pinecone logo and the end
   cards are not in this public repo. Get `pinecone-brand-pack.zip` from the Editing manager and say:
   `install the brand pack from ~/Downloads/pinecone-brand-pack.zip` (runs `setup.py --brand <zip>`).
   Without it setup says "Not ready: brand pack".

Prefer the shell? `git clone` this repo and run `./install.sh` (Mac, Homebrew): it adds the CLI tools,
the upstream plugins below and this plugin.

## Make a reel

| You want | Say to Claude |
|---|---|
| Any reel, not sure which type | `edit a reel from ~/Downloads/<folder>`: Claude looks at the footage, suggests a theme, you pick |
| Student testimonials (one reel per student) | `make testimonial reels from ~/Downloads/<folder>` |
| PineQuest participant / judge impression | `make a PineQuest reel from <interview.mp4>: <name>, <team> team, <result>, team account @<handle>` |
| Podcast clips | `clip this episode <file>` |
| Launch teaser / motion film | `make a launch reel for <program>` |
| See every theme | `show the reel themes` |
| Apply reviewer comments | `fix <video>: <paste the comments>` |

What Claude will ask you, and why:
- **Names spelled exactly** (Cyrillic, hyphens). Speech recognition gets names wrong, so Claude never guesses one.
- **Unsure caption words.** Claude lists them instead of guessing; check them before posting.
- Theme-specific facts: team, result, event name, judge title.

Finished videos land in `~/Desktop/ai edited reels/` (testimonials: `~/Desktop/ai captioned videos/`
and `~/Downloads/ai-footages-edited-version/`). Upload them to Marketing Planner → Video review.
Paste the reviewer's comments back to Claude for the fix round.

## Themes

| Theme | Status | Made by |
|---|---|---|
| Testimonial / seated interview | Ready (review-approved) | `testimonial-reel` |
| PineQuest impression (participant / judge) | Ready (review-approved) | `testimonial-reel/engine/pinequest.py` |
| Podcast clip | Ready | `podcast-clipper` |
| Motion teaser | Ready | `motion-studio` |
| Event recap, presenter promo, creator collab, office trend | Beta (first reels go through review) | `edit-reel/scripts/assemble.py` + `brand-motion` |
| Cinematic brand film | Plan only (shot list) | `ai-video-playbook` + `motion-studio` |

Each theme's card (structure, pace, captions, music, checklist, review lessons) is in
`plugins/pinecone-video/skills/edit-reel/references/themes/`.

## Skills in this plugin

| Skill | What it does |
|---|---|
| `edit-reel` | Editing station entry point: picks the theme from the footage, asks for missing facts, hands off to the right skill, checks and delivers |
| `testimonial-reel` | Interviews → reels: answer picking, name title, typed question cards with key sounds, hard cuts, corrected captions, music, end card, reviewer fix rounds. Also hosts the PineQuest engine |
| `reel-audit` | Downloads an account's reels, contact sheets, pacing metrics, format classification, AI feasibility |
| `ai-video-playbook` | Format → shot list → film / generate / template per shot → prompts → guardrails |
| `brand-motion` | Remotion brand templates: counter, list card, kinetic title, word captions, end card |
| `podcast-clipper` | Word-level transcript → 30-60 s moments → 9:16 cuts → captions |
| `motion-studio` | Code-rendered motion films with beat-synced cuts, code-made music and a self-review loop |

### Installed from upstream by `install.sh`

| Tool | Source | Use |
|---|---|---|
| `/watch` | taoufik123-collab/claude-watch | Watch one video: frames, hook, transcript |
| `remotion-best-practices` | remotion-dev/skills | Rules for writing Remotion code |
| `stitch-build:remotion` | google-labs-code/stitch-skills | Product walkthrough videos |
| Higgsfield connector | claude.ai connectors | Image, video, dubbing, reframe, upscale |

## House rules every theme keeps

1. 1080×1920, -14.5 LUFS, true peak ≤ -1 dBTP.
2. Every answer ends on a finished sentence; no interviewer voice; never cut inside a sentence.
3. Captions are corrected by hand: no name line, punctuation added, "Pinecone" mishears fixed.
4. Music only from the theme card (Funkorama, CC BY 4.0, credit in `assets/music/LICENSE.txt`; or the synthesized PineQuest bed).
5. No synthetic face or voice of a real person. Mongolian text is typeset in code, never generated inside images.
6. A human reviewer signs off every reel before it is posted.

## Privacy

Real jobs (student names, transcripts, captions, audio) stay on the editing computer.
`.gitignore` keeps them out of git; only `_house.json` and anonymized `_example.json` files are committed.

## Repo layout

```
.claude-plugin/marketplace.json            # makes this repo a Claude plugin marketplace
plugins/pinecone-video/
  .claude-plugin/plugin.json
  skills/edit-reel/                        # router, theme cards, house style, general assembler
  skills/testimonial-reel/                 # SKILL.md, references/, scripts/setup.py
    engine/                                # run.py, new_batch.py, pinequest.py, reelpipe/, src/ (Remotion), assets/
  skills/reel-audit/  ai-video-playbook/  brand-motion/  podcast-clipper/  motion-studio/
docs/content-factory/editing-unit.md       # member guide (Mongolian)
docs/tdd/                                  # Editing rulebook and checklist
audits/2026-10-pineconemongolia/           # first reel audit
install.sh
```

## Contributing

- A review lesson goes into the theme card (or `testimonial-reel/references/`), not into one job.
- Per-video fixes go in the job / manifest, never in `engine/src` or `engine/assets`.
- TS/TSX files stay at or under 160 lines, no `any`, no `eslint-disable`. Type-check: `cd plugins/pinecone-video/skills/testimonial-reel/engine && npm ci && npx tsc --noEmit`.
- New skill or theme: add a row above and bump `version` in both manifests.

## Credits

`motion-studio` follows the approach in "How to Build a Motion Design Studio With Opus 5.5"
(time-pure rendering, springs, beat-synced cuts, self-critique loop). Music: "Funkorama" by Kevin MacLeod
(incompetech.com), CC BY 4.0.
