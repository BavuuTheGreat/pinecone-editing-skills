# Captions

## Source

Transcribe the **clean** render's audio (not the raw file) so times match the final video. Lines are
`m:ss.cc|m:ss.cc|text`, about 2–4 words each; keep the tool's line breaks and times.

## Corrections (do all of these)

1. **Name line out.** Remove the line(s) where the student says their name ("Намайг … гэдэг").
   Keep surrounding words on their own lines ("Сайн байна уу.", "Одоо хорин нэгэн настай.").
2. **Pinecone mishears.** Speechmatics hears Pinecone as: банканд, банкинд, банкууд, киноны, тоонд,
   ком, кино, пайн ко, "2011 онд". Write `Pinecone`, `Pinecone-д`, `Pinecone-ы`.
3. **Numbers and school.** Grades as reviewers write them: `12-р анги`, `12-оо төгсөөд`. Age in digits:
   `18 настай`.
4. **English loanwords stay English**: YouTube, settings, Gap Year, AI, IG, vibe.
5. **Punctuation.** Period at sentence end, comma between clauses, `?` only for direct questions.
   Lowercase after a comma. A sentence ends where the speaker ends it, not where the line ends.
6. **Grammar.** Mongolian case endings (Санхүүд, -д/-т, -ыг/-ийг), but never change what was said.
7. **Drop filler only when it is noise**, e.g. a stray "аягүй бол", "тэр янзаар" (reviewer requests).
8. **Unsure words.** Don't guess silently. Collect them as `NN 0:12 "word?"` and ask the user.

## Words reviewers corrected before (watch for these)

| Heard / first written | Correct |
|---|---|
| 10 дугаар ангиа | 12-р ангиа |
| 10 авсан | Gap Year авсан |
| улс байхгүй юу | байсан байхгүй юу |
| утасны сэдвийн сайн дурын | утасны settings |
| орхичихдог / барьчихдаг | больчихдог |
| олоод үзэхэд | оролдоод үзэхэд |
| байхгүй юу. Өөрийгөө | байхгүй. Өөрийгөө |
| ороод ирнэ (as advice) | ороод ир |

## Checks before rendering

The engine holds each line 0.58 s after its words, stops it at the end of its clip and before the end
card. After rendering, look at one frame per corrected line.

## Timing (review 2026-11-16: captions "always late or early")

Never time captions by hand or from Speechmatics word groups (they run about 0.1-0.5 s off, and re-split lines
get guessed times). Write the corrected text, then force-align it to the audio:
- PineQuest jobs: `python3 -I pinequest.py <job>.json --align` (see `edit-reel/references/themes/pinequest-testimonial.md`,
  Recipe step 5, for the `[spoken but hidden]` syntax and the `KEPT-OLD` / `--force` rule).
- Bootcamp batches (`run.py`, `NN.txt` caption files): the aligner is not wired in yet. Convert the lines to
  job-style rows (`[from, to, text]`), run `engine/.venv-align/bin/python engine/reelpipe/align_captions.py`, convert back.
