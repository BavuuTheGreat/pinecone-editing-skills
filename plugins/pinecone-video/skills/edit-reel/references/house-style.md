# House style (every theme)

Set by the Editing manager. A theme card may override a line only where it says so.

| Area | Rule |
|---|---|
| Frame | 1080×1920, 30 fps, H.264, AAC 48 kHz. Never post 16:9 with black bars (3 reels in the Oct audit did). |
| Loudness | -14.5 LUFS integrated, true peak ≤ -1 dBTP (`assemble.py finish` does this). |
| Hook | Something worth staying for in the first 3 s: a claim, a face, a number, motion. No slow fade-in. The account's top organic reels (329K, 243K, Nov 2026 check) open with a bold headline or a face from frame 0; boosted reels (likes < 0.2% of views) don't count as evidence. |
| Cuts | Hard cuts. No blur, bloom, spin or zoom transitions. Exception: the PineQuest theme uses whip-zoom and glitch transitions (Editing manager, 2026-11-13). |
| Captions | Any speech gets captions. GIP / brand-motion style, white, centred, lower third. Corrected Mongolian (rules below). |
| Music | Licensed or original only. Default bed "Funkorama" (Kevin MacLeod, CC BY 4.0, credit line in the post caption). PineQuest theme: original synthesized 122 BPM bed (`testimonial-reel/engine/reelpipe/pq_music.py`, no credit needed). |
| Brand | Pinecone mark where the card says; never cover a face or a caption. |
| End | Hard cut into the 10 s Pinecone end card (`testimonial-reel/engine/assets/end_card_9x16.mp4`). |
| Names | Every on-screen name is confirmed by a person before render. |
| Text | Mongolian Cyrillic is typeset in Remotion, never inside AI-generated images. |
| Files | `NN_<short-name>.mp4`, in `~/Desktop/ai edited reels/`. |

## Captions (Mongolian)

Use `testimonial-reel/references/captions.md`: Pinecone mishears (банканд, киноны, пайн ко… →
`Pinecone`), `12-р анги`, digits for ages, English loanwords stay English, punctuation, and the
reviewer-corrected word list. Collect unsure words as `NN 0:12 "word?"` and ask.

## Checklist (before delivery)

- [ ] 1080×1920, 30 fps, no black bars
- [ ] Hook in the first 3 s
- [ ] No off-camera voice the card says to remove (interviewer, crew)
- [ ] Every sentence ends where the speaker ends it
- [ ] Captions proofread, names confirmed
- [ ] Loudness line from `assemble.py` / `run.py`: ~-14.5 LUFS, ≤ -1 dBTP
- [ ] End card present, nothing over it
