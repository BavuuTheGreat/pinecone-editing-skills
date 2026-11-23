# Security

This repo is public. It holds editing skills, a video engine, and a local "editing factory" (`factory/`) that moves reels
from an inbox folder to review. It is not a hosted service and has no server of its own.

## What is in scope

| Part | What it does | Where it runs |
|---|---|---|
| `factory/factory/*.py` | Reads an inbox folder, keeps one `reel.json` per reel, writes edit requests, records approvals | The editing Mac, command line |
| `factory/factory/web.py` (`python3 -m factory serve`) | A board in the browser with approve / reject buttons | The editing Mac, `127.0.0.1` only |
| `factory/agents/*.md` | Role descriptions (prompts) for helper agents. Text only, no code, no secrets | Read by Claude Code |
| `assets/fetch_assets.py` | Downloads the openly licensed music and images listed in `assets/MANIFEST.json` | The editing Mac |
| Engine (`plugins/.../testimonial-reel/engine`) | Renders reels with ffmpeg and Remotion | The editing Mac |

## Threat model: the local dashboard and the factory

The factory trusts the person at the keyboard of the editing Mac. It does not try to defend against someone who already
controls that account or can write to `FACTORY_HOME`. It does try to defend against two outsiders: a web page open in the
same browser, and a hostile file name or text inside a footage folder.

What an attacker could want: to approve or reject a reel (approval starts real work on the machine), to read reel notes and
transcripts, or to make the factory read or write files outside its own folder.

Controls, each with a regression test in `factory/tests/test_security.py`:

- **Local only.** The server binds `127.0.0.1`, never `0.0.0.0`. Nothing else on the network can connect.
- **Token on every state change.** Each `serve` run makes a random token (`secrets.token_urlsafe`). Every POST must carry it
  and is compared in constant time. Without the right token the answer is 403 and nothing on disk changes. The token is in
  the board page only: it is not in `/api/reels`, `/review`, error pages or the URL.
- **Host check (DNS rebinding).** A request whose `Host` header is not `localhost`, `127.0.0.1` or `[::1]` gets 403, so a
  hostile site that points its own name at `127.0.0.1` cannot read the board page and take the token.
- **Bounded input.** A POST body over 64 KiB or with a broken `Content-Length` is refused without being read.
- **HTML escaping.** Reel names, notes, comments, hooks, evidence and the flash message are escaped before they reach the
  page, in text and in attributes.
- **Reject needs a reason.** An empty reason is refused, and an unknown decision value changes nothing.
- **Reel ids cannot leave the state folder.** An id must be one plain folder name (`\w[\w-]*`). `../..`, absolute paths and
  slashes are refused with "unknown reel" in the dashboard and on the command line.
- **`factory done` only records paths.** It checks that each file exists and stores the path. The factory never opens,
  copies, serves or runs those files, and the board shows file names only, so a wrong path cannot leak a file's contents.
- **No shell.** Every subprocess call (`ffprobe`, `ffmpeg`, `whisper-cli`, `git`, `claude`) uses an argument list, never
  `shell=True`.
- **Safe downloads.** `fetch_assets.py` accepts `https://` sources only and refuses a manifest entry whose file path would
  land outside `assets/`.

Not covered, on purpose: authentication of several users (there is one user), TLS on localhost, rate limiting.
If the approval step moves to the Marketing Planner, that adapter needs its own review: it will hold an API credential.

## Credentials

There are none in this repository, and there must never be. API keys and tokens live in the editing Mac's environment or
in a git-ignored local file. Brand files, raw footage, student names and caption files are git-ignored too (see
`.gitignore` files; examples use placeholders such as "Сурагч"). The CI secret scan below runs on every push.

## What runs in CI

`.github/workflows/ci.yml`, no secrets needed:

- **bandit**: static analysis of `factory/factory`, `assets/fetch_assets.py` and the engine Python. The job fails on medium
  severity and above. A `# nosec` comment is allowed only with a reason next to it.
- **gitleaks**: secret scan of the full git history (`gitleaks/gitleaks-action`, free for personal repositories).
- **factory tests**: unit tests, the security regression tests above, and a command-line smoke test in a throw-away
  `FACTORY_HOME`.
- **manifests**: checks that the install manifests, skill front matter and README agree (`scripts/check_manifests.py`).

Run the scanners locally: `pip install bandit && bandit -r factory/factory assets/fetch_assets.py -ll`.

## Reporting a problem

Open a private security advisory on GitHub for this repository, or contact the Pinecone Academy marketing team directly.
Please do not post details, footage or credentials in a public issue.
