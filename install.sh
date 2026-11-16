#!/usr/bin/env bash
# One-shot setup for Pinecone's Claude video stack.
# Installs: CLI tools (ffmpeg, yt-dlp, node), third-party skills from their upstream
# repos (so teammates always get the maintained version), and this repo's own skills.
# Usage: ./install.sh            (installs to ~/.claude, user scope)
set -euo pipefail
cd "$(dirname "$0")"

say() { printf "\n\033[1;32m==>\033[0m %s\n" "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

say "1/4 CLI tools"
if have brew; then
  for t in ffmpeg yt-dlp node; do have "$t" || brew install "$t"; done
else
  echo "Homebrew not found. Install ffmpeg, yt-dlp and node yourself, then re-run."
fi

say "2/4 Claude Code plugins (run inside Claude Code if 'claude' CLI is missing)"
if have claude; then
  claude plugin marketplace add taoufik123-collab/claude-watch || true
  claude plugin install watch@claude-watch || true
  claude plugin marketplace add google-labs-code/stitch-skills || true
  claude plugin install stitch-build@google-labs-code-stitch-skills || true
  claude plugin marketplace add "$(pwd)" || true
  claude plugin install pinecone-video@pinecone-editing-skills || true
else
  cat <<'TXT'
In Claude Code, run:
  /plugin marketplace add taoufik123-collab/claude-watch
  /plugin install watch@claude-watch
  /plugin marketplace add google-labs-code/stitch-skills
  /plugin install stitch-build@google-labs-code-stitch-skills
  /plugin marketplace add BavuuTheGreat/pinecone-editing-skills
  /plugin install pinecone-video@pinecone-editing-skills
TXT
fi

say "3/4 Agent skills (skills.sh registry)"
if have npx; then
  npx -y skills add remotion-dev/skills --skill remotion-best-practices -g -y || true
fi

say "4/4 Connectors and built-ins (manual, one time)"
cat <<'TXT'
In claude.ai -> Settings -> Connectors, connect:
  - Higgsfield        (AI image / video / voice / lip-sync generation)
  - Google Drive      (shared footage + brand assets)
In claude.ai -> Settings -> Capabilities -> Skills, enable:
  - capcut-editing-automation  (Anthropic built-in: script -> voice -> CapCut timeline)
  - pptx                       (decks from audit results)
Optional: add GROQ_API_KEY to ~/.config/watch/.env so /watch can transcribe
videos without captions (Mongolian audio included).
TXT

say "Done. Open Claude Code and try:  /reel-audit https://www.instagram.com/pineconemongolia/reels/"
