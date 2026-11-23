# The agents

Each agent is a role with a card. The reel moves from left to right in this order. An agent reads some files, writes others and hands over.

| Agent | Job | Reads | Writes | Hands over to |
|---|---|---|---|---|
| [Intake](intake.md) | notice and describe new folders | inbox | reel record | Listener |
| [Listener](listener.md) | transcript and theme detection | footage, `themes.json` | transcript, detection | Planner |
| [Planner](planner.md) | the proposal | detection, theme card, assets manifest | `proposal.md` | Editor |
| [Editor](editor.md) | the edit, with the `edit-reel` skill | `EDIT_REQUEST.md` | outputs | Checker |
| [Checker](checker.md) | the theme card's checklist on the render | outputs | review notes, needs | Reporter (and the human reviewer) |
| [Analyst](analyst.md) | reel numbers, similar reels on other accounts (phase 2, not built) | audits | findings | Librarian |
| [Librarian](librarian.md) | theme and skill upgrades from the findings (phase 3, not built) | findings | pull requests | A person (the Editing manager reviews and merges) |
| [Reporter](reporter.md) | the daily review | every record, git log | review file | The Editing manager |

Phase 1 builds Intake, Listener, Planner, Editor, Checker and Reporter. Analyst and Librarian are reserved for phases 2 and 3.

Back to [the factory page](../README.md).
