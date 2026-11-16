#!/usr/bin/env bash
# Word-level transcript of a podcast via Groq Whisper (whisper-large-v3).
# Usage: transcribe.sh <video_or_audio> <out.json> [language, default mn]
# Needs GROQ_API_KEY in env or ~/.config/watch/.env (shared with /watch).
set -euo pipefail
IN="${1:?input}"; OUT="${2:?out json}"; LANG_CODE="${3:-mn}"
if [ -z "${GROQ_API_KEY:-}" ] && [ -f "$HOME/.config/watch/.env" ]; then
  GROQ_API_KEY="$(grep -E '^GROQ_API_KEY=' "$HOME/.config/watch/.env" | cut -d= -f2- | tr -d '"')"
fi
: "${GROQ_API_KEY:?Set GROQ_API_KEY (console.groq.com/keys)}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
# 64 kbps mono = ~0.5 MB/min, so up to ~50 min fits Groq's 25 MB upload limit.
ffmpeg -hide_banner -loglevel error -i "$IN" -vn -ac 1 -ar 16000 -b:a 64k "$TMP/a.m4a"
curl -sS https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -F file=@"$TMP/a.m4a" -F model=whisper-large-v3 -F language="$LANG_CODE" \
  -F response_format=verbose_json -F "timestamp_granularities[]=word" \
  -F "timestamp_granularities[]=segment" -o "$OUT"
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('words:',len(d.get('words',[])),'segments:',len(d.get('segments',[])))" "$OUT"
