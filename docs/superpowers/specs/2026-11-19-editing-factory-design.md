# Editing factory, phase 1: design

Date: 2026-11-19. Status: building. Owner: Editing (5) station.

## Why

Today every reel starts with a person handing footage to Claude and answering questions. The Editing manager wants the
station to run itself: footage arrives named and grouped, the system works out what kind of reel it is, proposes an edit,
waits for one "yes", edits, and puts the result in front of the reviewer. Later phases add analytics, themes that improve
from the numbers, a shooting (4) station that feeds the inbox, and publishing.

**For a five-year-old:** it is a toy factory. You put a box of video on the conveyor belt with a name tag. A robot looks in
the box and says "this is a PineQuest video, I will make it like this, okay?". When you say "okay", the robots build it and
put it on the teacher's desk to be checked.

## Goals (phase 1)

1. An **inbox**: one folder per reel, named by a person, with an optional note file.
2. A **loop** (`factory tick`) that moves every reel one step forward and is safe to run again and again.
3. **Theme detection** from the transcript, the questions asked and facts about the footage, with a confidence score and
   the evidence for it.
4. A written **proposal** per reel (theme, hook line, length, inserts, music) and an **approval gate**: nothing is edited
   until the Editing manager approves that reel.
5. An **edit hand-off**: an approved reel becomes a complete brief for the editing agent (the existing `edit-reel` skill
   and engines do the edit). A finished reel is recorded and waits for review.
6. A shared **assets** library (music, images) with licences, usable by every member.
7. A **daily review** generator: what is failing, what is working, what is needed from the manager, what was added or updated.
8. Every part explained twice: for a software engineer and for a five-year-old.

## Non-goals (phase 1)

- The shooting (4) system. It will only need to drop folders into the inbox.
- Publishing to Instagram or Facebook.
- The analytics collector and automatic theme upgrades (phases 2 and 3). Phase 1 only reserves their place in the state and the docs.
- Changing the Marketing Planner. Its code belongs to another team; phase 1 talks to it through an adapter with a local stand-in.

## Anti-goals

- A reel edited or published without the approval it needs.
- A loop that renders two reels at once (a 16 GB Mac crash-loops), or re-does finished work when it is run twice.
- Real footage, real names, account passwords or tokens in the git repo (it is public).
- A system that hides uncertainty: an unsure theme, an unheard word or a missing name must show up as a visible "needs you" item.

## Constraints found in the editing work so far

- Mongolian speech recognition: the team tool (Speechmatics at dash.pinecone.mn) only runs in a signed-in browser; local
  whisper is weak on Mongolian. Transcription is therefore an adapter; the unattended one (whisper) marks its text as low trust.
- Names are never trusted from speech. They come from the note file or stay a "needs you" item.
- One render at a time, about 7 minutes per reel.
- The agent cannot hear audio; cut points are checked with energy analysis and whisper, and reviewers still catch what those miss.

## Approaches considered

| | Approach | Trade-off |
|---|---|---|
| A | **File-based state machine + one idempotent `tick` command, agents only for judgement steps** (chosen) | Plain files anyone can read, testable without footage, survives restarts, any scheduler can run it. Less "magic": steps that need judgement are explicit hand-offs. |
| B | One long-running agent session that watches the folder and does everything | Feels the most automatic, but state lives in a conversation, a crash loses it, and nobody else can see what it is doing. |
| C | A queue service (database, workers, web UI) | The right shape at scale; far too much to run and maintain for one Mac and a few reels a day. Approach A's state files can be moved into it later. |

A is chosen because the manager asked for something organised, understandable on GitHub and able to grow: files and a
state machine are the smallest thing that is all three.

## Layout

```
factory/                      in the repo (code + docs, no footage)
  README.md                   engineer + five-year-old explanation, how to run
  factory/                    python package, standard library only
    config.py  state.py  inbox.py  transcribe.py  detect.py  propose.py
    approval.py  edit.py  review.py  tick.py  cli.py
  themes.json                 keyword and signal table per theme (the "keyword listener")
  agents/                     one role card per agent
  tests/
assets/                       shared library: MANIFEST.json, fetch_assets.py, music/ images/ (files fetched, not committed)

~/Desktop/AI-videos/factory/  on the machine (never in git); override with FACTORY_HOME
  inbox/<reel name>/          footage + optional note.txt
  state/<reel id>/reel.json   one record per reel (+ transcript.txt, proposal.md, EDIT_REQUEST.md)
  reviews/YYYY-MM-DD.md       daily reviews
  factory.lock                held while a render-heavy step runs
```

## The reel record (`reel.json`) — the contract every module shares

```json
{
  "id": "2026-11-20-pinequest-сурагч",
  "name": "2026-11-20 PineQuest Сурагч",
  "inbox_path": "/abs/path/inbox/2026-11-20 PineQuest Сурагч",
  "status": "new",
  "created": "2026-11-20T09:00:00+08:00",
  "updated": "2026-11-20T09:00:00+08:00",
  "files": [{"path": "/abs/clip.mp4", "kind": "video", "seconds": 76.2, "width": 2160, "height": 3840}],
  "note": {"name": "", "team": "", "result": "", "handle": "", "theme": "", "extra": ""},
  "transcript": {"path": "", "source": "", "trust": "", "text": ""},
  "detection": {"theme": "", "confidence": 0.0, "scores": {}, "evidence": []},
  "proposal": {"path": "", "theme": "", "hook": "", "target_seconds": 0, "inserts": [], "music": "", "open_questions": []},
  "approval": {"state": "none", "by": "", "at": "", "comment": ""},
  "edit": {"request_path": "", "job_path": "", "outputs": [], "started": "", "finished": ""},
  "review": {"state": "none", "comments": []},
  "needs": [],
  "history": [{"at": "2026-11-20T09:00:00+08:00", "from": "", "to": "new", "why": "found in inbox"}]
}
```

- `id`: lower-case slug of the folder name (Cyrillic kept, spaces and punctuation to `-`), unique; a second folder with the
  same slug gets `-2`.
- `kind`: `video`, `audio`, `image`, `other` (by extension). `seconds`/`width`/`height` from `ffprobe`, `null` if unknown.
- `note.txt`: `key: value` lines (`name`, `team`, `result`, `handle`, `theme`), anything else goes to `extra`.
- `transcript.source`: `whisper`, `speechmatics` or `manual`; `trust`: `low` (whisper) or `high`.
- `approval.state`: `none`, `pending`, `approved`, `rejected`. `review.state`: `none`, `waiting`, `changes`, `approved`.
- `needs`: plain sentences for the manager ("Name is missing: add `name:` to note.txt"). Shown in the status board and the daily review.
- Every status change appends to `history`. Records are written atomically (temp file + rename).

## Statuses and what `tick` does at each

| Status | `tick` does | Next |
|---|---|---|
| `new` | probe files; read the note; if there is no video, add a need and stay | `transcribing` |
| `transcribing` | if `transcript.txt` exists in the state folder (a person or the browser tool put it there), use it as `manual`, trust `high`; else run the configured transcriber (default: whisper if installed, else add a need and stay) | `detecting` |
| `detecting` | score themes from `themes.json`; a `theme:` line in the note wins outright | `proposed` |
| `proposed` | write `proposal.md`, set approval `pending`, list open questions (missing name, low confidence under 0.5, low-trust transcript) | waits |
| (waiting) | read the approval adapter | `approved` or `rejected` |
| `approved` | write `EDIT_REQUEST.md` (the full brief for the editing agent: files, note, theme card path, transcript, rules) | `editing` |
| `editing` | the configured editor adapter: `handoff` (default) waits until `edit.outputs` is filled by `factory done <id> <files...>`; `claude` runs `claude -p` with the brief under the render lock | `in_review` |
| `in_review` | read review adapter (phase 1: `factory review-result <id> approved|changes "<comment>"`) | `done` or `changes` |
| `changes` | write a new `EDIT_REQUEST.md` that includes the comments | `editing` |
| `rejected`, `done` | nothing | |

`tick` never throws on one bad reel: it records the error in that reel's `needs`, leaves the status, and goes on. A reel
whose inbox folder is still being copied (a file changed in the last 60 seconds) is skipped this tick.

## Adapters (how phase 1 stays honest about what is automatic)

- **Approval**: `file` (default). `factory approve <id> [comment]` / `factory reject <id> <comment>` write the decision.
  `planner` is a stub with the same three calls (`post_proposal`, `read_decision`, `post_result`) for when the Marketing
  Planner has an API.
- **Transcriber**: `whisper` (local, low trust), `manual` (drop `transcript.txt`).
- **Editor**: `handoff` (an agent session or a person picks up `EDIT_REQUEST.md`), `claude` (headless, opt-in in config).

## Theme detection ("keyword listener")

`themes.json` holds, per theme: Mongolian and English keywords with weights, question phrases, and footage signals
(count of videos, orientation, total seconds, presence of a screen recording). Score = weighted keyword hits per 100
words + question hits + footage signals, normalised so the scores sum to 1. `confidence` is the top score; `evidence` lists
the hits ("'PineQuest' x4", "question: 'ямар төсөл хийсэн'", "1 vertical video, 203 s"). Low-trust transcripts halve
keyword weights so the footage signals and the note carry more.

## Commands

```
python3 -m factory tick                 # one pass over every reel
python3 -m factory status               # the board: one line per reel + needs
python3 -m factory show <id>            # the full record and proposal
python3 -m factory approve <id> [comment] | reject <id> <comment>
python3 -m factory done <id> <output files...>
python3 -m factory review-result <id> approved|changes "<comment>"
python3 -m factory review [--date YYYY-MM-DD]   # write and print the daily review
python3 -m factory loop --every 300     # tick forever (for a terminal or a scheduler)
```

## Daily review (18:00)

`factory review` writes `reviews/<date>.md` with: **Failing** (reels with needs or errors, stuck over 24 h),
**Working** (status changes today, reels finished), **Needs you** (approvals pending, open questions, review comments),
**Added / updated** (git commits of the last day in the skills repo, grouped as skills, themes, engine, factory), and
**Tomorrow** (what the loop will do next). Scheduling it at 18:00 is a one-line scheduler entry documented in the README;
phase 1 does not install anything on the machine by itself.

## Agents (role cards in `factory/agents/`)

| Agent | Job | Reads | Writes |
|---|---|---|---|
| Intake | notice and describe new folders | inbox | reel record |
| Listener | transcript + theme detection | footage, `themes.json` | transcript, detection |
| Planner | the proposal | detection, theme card, assets manifest | `proposal.md` |
| Editor | the edit, with the `edit-reel` skill | `EDIT_REQUEST.md` | outputs |
| Checker | the theme card's checklist on the render | outputs | review notes, needs |
| Analyst (phase 2) | reel numbers, similar reels on other accounts | audits | findings |
| Librarian (phase 3) | theme and skill upgrades from the findings | findings | pull requests |
| Reporter | the daily review | every record, git log | review file |

## Later phases (reserved, not built)

2. **Analytics**: collect our own reels' numbers and the best matching reels from other accounts; weight the reels closest
   to a theme; store findings per theme. Needs account access the manager will provide.
3. **Adaptation**: the Librarian proposes theme and skill changes as pull requests with the numbers that justify them; a
   person merges.
4. **Shooting (4) station** drops folders into the inbox. **Planner API** replaces the file adapter. **Publishing** after review.

## Decided by the builder (not by the manager)

- Standard-library Python, no database, state in JSON files.
- The machine folder `~/Desktop/AI-videos/factory/` and the `FACTORY_HOME` override.
- Assets are fetched from their licensed source by a script, not committed, to keep the public repo small and licences clear.
- The editor adapter defaults to `handoff`; headless editing is opt-in until a few reels have gone through cleanly.
