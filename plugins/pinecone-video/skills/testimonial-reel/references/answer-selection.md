# Picking answers from the raw transcript

## Read the interview

The raw file has the interviewer and the student. Mark each line as Q (interviewer) or A (student):
interviewer lines are questions ("…танилцуулаач", "Яагаад…", "…юу вэ?", "…ямар зөвлөгөө…"), short
prompts ("За", "Тэгээд нөгөөдхөө нэмчихлээ") and "За баярлалаа" at the end. Students sometimes repeat
the question before answering; that repeat may stay if it reads naturally ("Гоё зүйл үү? Орчин байна.").

Map answers to slots: `intro` (name, age, background), `q1` why Pinecone, `q2` most challenging,
`q3` best thing, `q4` advice. Interviewers sometimes ask q2+q3 together; split the answer at the turn.
When a student does a second take ("intro 2 удаа"), use the clean one.

## Choose

- Keep the whole answer when it is under ~26 s. Longer: keep the part that answers the question
  directly and drop tangents. Several pieces per slot are fine (hard cut between them).
- **Every piece ends on a finished sentence.** If a student trails off ("…гэж бодоод л") and never
  completes it anywhere in the raw file, drop that piece. If that leaves the slot empty, drop the
  question (reviewers rejected an unfinished ending, 2026-11-12).
- Never include interviewer words, even a short "за".

## Write pieces

Use word times straight from the transcript; the engine snaps cuts to the quietest 40 ms:

```json
{"id": "h02", "answer": "q1", "word_start": 16.98, "word_end": 40.28, "lo": 15.7, "hi": 41.1}
```

- `word_start` / `word_end`: start of the first kept word, end of the last kept word.
- `lo`: end of the previous speech (usually the interviewer's last word). `hi`: start of the next speech.
  The cut can never cross these.
- `id`: student letter + two digits, unique in the batch.

Speechmatics word times can be ~0.5 s late at the start of an answer. After the clean render, look at
the first frame of each answer; if a word is clipped, lower `word_start` by 0.5 and re-run.
