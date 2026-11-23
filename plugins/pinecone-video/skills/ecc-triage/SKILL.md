---
name: ecc-triage
description: Read and act on the ECC Tools bot (ecc-tools) comments on a pull request of this repo. Use after every push to a PR, when someone mentions ECC or "the bot comments", or before calling a PR done. Separates useful findings from noise, fixes the useful ones, re-checks, and loops until CI is green and only noise or owner-owned items remain.
---

# ecc-triage - what to do with the bot's comments

The ECC Tools bot posts one set of audit comments per pushed commit: Security Evidence, PR Risk Taxonomy,
Reference Set Readiness, Hosted Promotion Readiness.

For a five-year-old: a robot looks at your drawing after every change and leaves sticky notes. Some notes say
"you forgot the door" (fix it). Some say "draw a unicorn" (you do not have to).

## Read

```bash
gh pr view <n> --json comments --jq '.comments[] | select(.author.login=="ecc-tools") | .body'
gh api repos/<owner>/<repo>/pulls/<n>/comments      # inline comments, if any
gh pr checks <n>
gh run list --branch <branch>
```

Only the comments for the **latest commit** matter (the commit sha is in each comment header). Wait 1-2 minutes
after a push before reading.

## Sort

| Finding | Usually | Action in this repo |
|---|---|---|
| Security Evidence `action_required` | useful | scanner evidence lives in the `security` CI job (bandit, gitleaks); add focused tests in `factory/tests/test_security.py` for the paths it names; fix real holes |
| CI/CD Recommendation (no CI, coverage lags, CLI without e2e) | useful | keep jobs for engine tests, factory tests, `factory/tests/e2e_smoke.sh`, manifests; add a test for changed logic |
| Install Manifest Integrity | useful | keep `marketplace.json`, `plugin.json`, every `skills/<folder>/SKILL.md`, README and `docs/SKILLS.md` in sync; run `python3 scripts/check_manifests.py` |
| Harness Drift | noise for a Claude-Code-only plugin | note it, no change |
| Reference Set Readiness (RAG corpora, discussion triage, salvage corpus) | noise: this repo builds no analyzer or RAG | skip |
| Hosted Promotion Readiness passed | info | nothing |
| "Check publication was denied" | owner-owned | the GitHub App needs `Checks: read and write`; tell the repo owner once |

A finding is useful when fixing it makes the code safer, better tested or easier to install. Generic boxes to tick
are noise.

## Fix, then loop

Run `loop-engineer` with one unit per useful finding. Acceptance check per unit: the bot's next comment for that
bucket passes, or the remaining signal is explained as noise, **and** CI is green. Push, wait, read again, repeat.
Never comment on the PR or change the bot's config on your own. Never weaken a check to quiet the bot. No Claude
attribution lines in commits or PR text.
