---
name: loop-engineer
description: The station's loop for any main goal. Use whenever someone gives a main goal, a multi-part request ("make 4 reels", "apply all reviewer comments", "ship this factory feature", "fix everything"), or says "loop until done". Splits the goal into units (reels, reviewer comments, factory features, PR bot findings), gives each unit its own acceptance checks, and loops plan, build, verify, review, fix until every unit passes with real evidence.
---

# loop-engineer - finish a goal, with proof

A main goal is finished only when **every unit** of it passes **its own acceptance checks** with **real evidence**.
"Tests pass" or "it renders" is one check, never the whole proof.

For a five-year-old: you ask for five cookies. The helper does not say "done" after baking one. It counts all five,
tastes each one, and only then says "all five are ready".

## 0. Intake (once)

1. Write the goal in one sentence plus the reason behind it.
2. Split it into **units**, the smallest pieces that can be checked alone:
   - a **reel** (one student, one participant, one episode, one clip)
   - a **reviewer comment** (one line from the Marketing reviewer on one reel)
   - a **factory feature** (one change under `factory/`)
   - an **engine change** (one change under `plugins/pinecone-video/skills/interview-reel/engine/`)
   - a **PR bot finding** (one useful ECC Tools comment, see `ecc-triage`)
3. For each unit write the acceptance checks from the table below, with the exact command or file to look at.
4. If your tool has a task or memory list, record the units there (one item per unit, status todo) so the list
   survives a long session. Otherwise keep it in the reply.

## Acceptance checks per unit type

| Unit | It is done only when all of these pass |
|---|---|
| **Reel** | the output file exists and plays (ffprobe: 1080x1920, expected duration); a still extracted at **every reviewer time** (and at each cut, the title, the end card) and looked at; loudness about **-14.5 LUFS** and true peak **<= -1 dBTP** (`ffmpeg -i out.mp4 -af loudnorm=print_format=json -f null -`); a whisper or energy check at **every cut** (no sentence cut in half, no breath or tail of the previous word); **captions checked** word by word against the corrected transcript, unsure words listed for the member; names spelled as the member wrote them |
| **Reviewer comment** | the comment is applied in the job file (never in `engine/src` or `engine/assets`); the reel is re-rendered; the still or clip at the comment's time shows the fix; all reel checks above still pass (a fix can break another cut) |
| **Factory feature** | a test that failed before and passes after; `cd factory && python3 -m unittest discover -s tests -q` is green; `bash factory/tests/e2e_smoke.sh` is green |
| **Engine change** | `cd plugins/pinecone-video/skills/interview-reel/engine && python3 -m unittest discover -s tests` is green; the matching job runs with `--plan` and prints the expected timeline (`python3 pinequest.py <job.json> --plan`, `python3 engineers.py <job> --plan`); for a visual change, a still before and after |
| **Manifests / docs** | `python3 scripts/check_manifests.py` and `python3 -m unittest discover -s scripts` are green; README and `docs/SKILLS.md` name every skill; a reader who never saw the work can follow the doc |
| **PR** | CI green (`gh run list --branch <b>`); the ECC Tools comments for the **latest commit** are triaged with `ecc-triage`; a reviewer finds nothing blocking |

## 1. The loop (per unit; independent units in parallel)

```
plan -> build -> verify -> review -> fix -> verify ... until all checks pass
```

- **Plan**: what changes, which files, which check proves it. Cause unknown? Debug first, do not guess.
- **Build**: independent units go to helpers at the same time. Each brief states the goal, the files, the unit's
  acceptance checks, what "done" looks like and what not to touch.
- **Verify**: run every acceptance check yourself or read the helper's evidence (command output, stills, numbers).
  No evidence is not verified. A helper saying "done" is a claim, not a check.
- **Review**: a second reader looks at the diff or the reel for that unit.
- **Fix**: each failed check becomes the next iteration's plan.

## 2. Stop rules

- A unit is **done** only when all its checks pass in the **same** iteration.
- After a unit changes, re-run the checks of units that share files with it.
- The same check fails **3 iterations in a row with no new information**: stop that unit as **blocked**, write what
  was tried and the exact error. Do not loop forever. Do not fake a pass.
- Needs the member or the reviewer (a spelling of a name, a taste call, an approval, credentials, anything posted
  publicly): **park** the unit as waiting on the owner, finish every other unit, ask once at the end.
- **Never weaken a check** to make it pass. Never delete a failing test without saying why.

## 3. Finish

1. Final sweep: re-run all checks of all units once more.
2. Final review of the whole change.
3. Save: commit and PR if the goal includes it. **No Claude attribution lines** (no `Co-Authored-By: Claude`, no
   "Generated with Claude Code") in commits or PR bodies.
4. Report per unit: done, blocked or waiting on the owner, with the evidence. Then what is still open.

## The 80 / 20 split

The loop does the 80 %: splitting, building, checking, fixing, re-checking, reporting. People keep the 20 %:
the goal, taste calls, spellings, approvals, credentials, anything posted outside. Ask only for those, batched, once.
