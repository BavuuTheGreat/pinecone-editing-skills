# Intake: required inputs per film type

Run this before scaffolding or writing any code. The goal is a complete `docs/brief.md`
with no guessed facts.

## How to run it

1. **Pick the film type** from the request (ask if unclear):
   A launch / promo reel · B style from a reference · C one-shape UI loop · D long-form director brief.
2. **Extract** every field below that the user already gave (in the message, attached files, links,
   or earlier conversation). Do not re-ask those.
3. **Ask for the missing REQUIRED fields**, in at most 2 rounds:
   - Choice fields (type, duration, formats, music, language, voice, effort):
     `AskUserQuestion`, up to 4 questions per call, recommended option first. The user can always
     pick "Other" to type a custom answer.
   - Free-text fields (name, URL, metric, CTA, logline, states, reference path, key names, budget):
     one numbered chat message listing only the missing ones, each with a short example. Then stop
     and wait for the reply.
4. **Optional fields** get the default in the table. List the defaults you applied in one line so the
   user can override them.
5. **Never invent** a metric, a quote, a UI screen, a URL, or a price. If the user has no real proof
   point, drop that beat and say so.
6. Write `docs/brief.md` from `brief-template.md`, show it, and **wait for an explicit OK**. This is
   gate 0. Nothing is scaffolded or built before it.

## Fields

R = required, O = optional (default shown), - = not used.

| # | Field | A | B | C | D | Ask as | Example / default |
|---|---|---|---|---|---|---|---|
| 1 | Film type | R | R | R | R | choice | A launch reel |
| 2 | Subject: product, programme or event name | R | R | R | R | text | Morphosis, Hello World '26 |
| 3 | URL to capture real UI/brand from | R | O | R | O | text | https://pinecone.mn (none: assets folder only) |
| 4 | Audience | R | O | O | R | text | 12th-grade graduates; engineers with 2+ years |
| 5 | Goal / feeling at the end (logline for D) | R | O | O | R | text | "I can reach the global market from UB" |
| 6 | Duration | R | R | R | R | choice | 15 / 20 / 30 s (C: 8-12 s; D: 30-120 s) |
| 7 | Formats | R | R | R | R | choice | 9:16 only · 9:16 + 1:1 · 9:16 + 1:1 + 16:9 |
| 8 | On-screen language | R | R | R | R | choice | Mongolian · English · both |
| 9 | Proof point: real number + source | R | O | O | O | text | 1,331 graduates since 2017 (pinecone.mn) |
| 10 | Call to action + where it points | R | O | R | O | text | "Бүртгүүлэх" · link in bio |
| 11 | Key messages / features (3 max) | R | O | - | O | text | mentors, real projects, global jobs |
| 12 | Reference: path or URL + what to take / avoid | O | R | O | R | text | ./refs/launch.mp4 · take pacing, not colours |
| 13 | UI states in order (6-12) + the real data in each | - | - | R | - | text | button → email → loader → check → card |
| 14 | Brand: colours, fonts, accent | O | O | O | O | text | Pinecone tokens (ink, paper, blue #2E55E0) |
| 15 | Assets on hand: logo, photos, footage paths | O | O | O | R | text | ./assets (default: capture from URL) |
| 16 | Music | R | R | R | R | choice | synthesize (BPM?) · supplied file with rights |
| 17 | BPM (if synthesized) | O | O | O | O | choice | 120 |
| 18 | Voiceover | O | O | - | O | choice | none · ElevenLabs (key name in .env) |
| 19 | VO script / tone | - | - | - | O | text | only if voiceover is yes |
| 20 | API keys available (names only, never values) | O | O | O | R | text | ELEVENLABS_API_KEY in .env |
| 21 | Budget (credits / ₮) | - | - | - | R | text | 50,000₮ of credits |
| 22 | Deadline and effort | O | O | O | R | choice | today/xhigh · overnight/max |
| 23 | Approver for gates | O | O | O | R | text | marketing lead |

## Question bundles (copy into AskUserQuestion)

Round 1, choices (only include the ones still missing):
- "What kind of film is this?" A launch reel (Recommended) · B match a reference · C UI loop · D long-form
- "How long?" 15 s · 20 s (Recommended) · 30 s
- "Which formats?" 9:16 only (Recommended) · 9:16 + 1:1 · all three
- "Music?" Synthesize at 120 BPM (Recommended) · I'll supply a track · Synthesize at another BPM

Round 1, free text (one chat message), e.g.:
> To build this I still need:
> 1. The URL to capture real screens from (e.g. https://pinecone.mn)
> 2. One real number with its source (e.g. "1,331 graduates since 2017"), or "none"
> 3. The CTA text and where it points (e.g. "Бүртгүүлэх" → link in bio)

Round 2: only for what round 1 left open. After round 2, use the defaults for optional fields,
write the brief, and go to gate 0. Do not keep asking.
