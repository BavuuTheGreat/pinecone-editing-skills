#!/usr/bin/env bash
# Scaffold a film folder: engine + house rules + headless browser.
# Usage: new_film.sh <folder>
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${1:?folder}"
[ -e "$DIR" ] && { echo "$DIR already exists"; exit 1; }
mkdir -p "$DIR"/{assets,refs,docs,out,audio}
cp -R "$SKILL/engine/." "$DIR/"
cp "$SKILL/references/house-rules.md" "$DIR/CLAUDE.md"
cp "$SKILL/references/review.md" "$SKILL/references/briefs.md" "$SKILL/references/intake.md" "$DIR/docs/"
cp "$SKILL/references/brief-template.md" "$DIR/docs/brief.md"
cd "$DIR"
printf '{\n  "name": "%s",\n  "private": true,\n  "type": "module"\n}\n' "$(basename "$DIR")" > package.json
printf 'node_modules\nout\n.env\n' > .gitignore
npm i -D playwright --no-audit --no-fund --silent
npx playwright install chromium >/dev/null
echo "Ready: $DIR  (preview: npx serve . or render: node render.mjs --still 1)"
