# Transcription (Mongolian)

Use the team's caption tool, `https://dash.pinecone.mn/reel` (Speechmatics). Whisper is weak on
Mongolian; use it only to break ties on a single word.

## With browser control (claude-in-chrome)

1. Open `dash.pinecone.mn/reel` in the user's browser (they must already be signed in; never type
   their password).
2. Click **NEW FILE**, find the file input, upload `NN.m4a` (browser upload limit 10 MB, which is why
   audio-only m4a is used), click **TRANSCRIBE**, wait ~10 s. If the upload is refused with "only files
   this session is allowed to read can be uploaded", copy the m4a into the session's scratchpad folder and
   upload that copy (or ask the user to `/add-dir` the job folder). Helpers (subagents) usually have no
   browser tools: do this step in the main session, then hand the transcript file to the helper.
3. Extract the lines with JavaScript (output is truncated near 1000 characters, so read in slices):

```js
const ins=[...document.querySelectorAll('input')].filter(i=>/^\d+:\d\d\.\d\d$/.test(i.value));
const out=[];for(let k=0;k<ins.length;k+=2){let r=ins[k].parentElement;
  while(r&&!r.contains(ins[k+1]))r=r.parentElement;
  out.push(ins[k].value+'|'+ins[k+1].value+'|'+r.innerText.replace(/\s+/g,' ').trim())}
window.__T=out; out.length
```

then `window.__T.slice(0,30).join('\n')`, `slice(30,60)` and so on. Save to the transcript file.

## Without browser control

Ask the user to upload the m4a themselves and paste the caption list, or export it from the tool.

## Tie-break with whisper (optional)

```bash
ffmpeg -ss <a> -to <b> -i <file> -ac 1 -ar 16000 seg.wav
whisper-cli -m ggml-large-v3-q5_0.bin -l mn -nt -f seg.wav      # try with and without --prompt "<candidate>"
```

Trust a candidate only when the neutral run sounds like it too.
