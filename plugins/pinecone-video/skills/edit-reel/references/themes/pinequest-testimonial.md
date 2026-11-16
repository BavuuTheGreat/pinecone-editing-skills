# PineQuest impression (participant / judge)

One person (PineQuest participant or judge) standing at the event with a handheld mic, answering 3-5
questions. Pick it for any "PineQuest S<n> | … сэтгэгдэл" reel.

**Status:** Ready (2 reels approved in review, 2026-11-15: a III-place participant and a winner) · **Made by:** `testimonial-reel/engine/pinequest.py`
**Audit:** 7 PineQuest S5 reels (3 participant, 4 judge), 41-102 s. Organic: participant reels 1.6-8K views, judge #3 17.2K.
Judge #1 (52.1K) and the top testimonial (159K) were boosted: likes 78 and 197.
**Examples:** instagram.com/reel/DfqgqzBE85z (Hologemma), /reel/DfocUIbGLco (Kuma), /reel/DfmXpIijZkS (Naadamy), /reel/Dfg2YWhAtbO (judge #4)

## Signals
- Standing at the PineQuest venue (trophy shelf, PineQuest screen), handheld mic, interviewer off camera
- Answers about PineQuest: impression, hardest part, memory, project, future, advice

## Prompt (what the member says)

> make a PineQuest reel from `<interview.mp4>` — `<name>`, `<team>` team, `<result>`, team account `@<handle>`

Claude asks only for what is missing: name spelling, team, result (ялагч / III байр / оролцогч), team
Instagram (for project shots), judge title and company (judge reels).

## Style (measured from the reels above, plus the "more exciting" pass approved by the Editing manager)

| Part | Rule |
|---|---|
| Length | 40-60 s body + 6.2 s end card |
| Cold open (0-5 s) | One **complete sentence** (never a fragment) taken from a later answer, and that answer is then not repeated (it is the hook, no card). Prefer a quotable line: "Айвал бүү хий, хийвэл бүү ай.", "5 жилийн дараа нэг компанийн захирал болсон байх л гэж бодож байна даа.". **Calm by default** (reviewer 2026-11-16: "аймар хөдөлгөөнтэй": no impact zoom on frame 0, one fixed gentle framing held the whole hook with no punch-in ramp, headline fades in whole, no word-by-word pop; `"hook_motion": "punchy"` brings back impact + 1.14→1.22 ramp + pop). **Headline = the quote itself**, bold, auto-fit: 80 px max, shrunk (never grown) so the longest line is ≤ 80 % of the width, and always starts at y ≥ 230 so it never touches the chevron logo (reviewer 2026-11-16: "текстийг жижиг болгох, логотойгоо хэтэрхий наалдаад"; 3-line quotes with a 21-char line come out ~68 px) (`hook.lines`: `Айвал бүү хий,` / `хийвэл бүү ай.`), and no captions under the hook (drop the hook piece's caption lines, or the same words show twice). Reviewer 2026-11-15 replaced a result headline (`PineQuest S5-ийн / **ЯЛАГЧ** / NAADAMY баг`) with the quote. Use a result headline (one white pill on the key phrase, e.g. `PineQuest S5-д / **3-р байр** эзэлсэн / ДУСАЛ баг`) only when the hook line is not quotable. Top organic reels on the account (329K, 243K) all open with a headline or a face from frame 0. |
| Then | Hard cut into answer 1 (no card for the first answer, no hit, no whip; `punchy` = hit + whip) |
| Cards | `#181818` with a fine 67 px grid that drifts, question shown **whole at once** with a short fade/scale-in, no typing and no sound (reviewer 2026-11-16: "бичигдэж байгааг нь болиулаад шууд гаргаж ирэх / sound effect болиулах"; job `"card_typing": true` = typed at 22 chars/s with cursor, `"card_sfx": true` = key sounds + one transition sound per card). Hold 1.6-2.8 s by length. Wording from the published reels: "PineQuest тэмцээний үеэр хэцүү зүйл байсан уу?", "Software Engineer чиглэлээр суралцах хүсэлтэй хүмүүст зөвлөгөө", "Ямар төсөл хийсэн бэ?", "PineQuest-д орсон сэтгэгдэл", "Дараа дараагийн PineQuest-д оролцох сурагчдад зөвлөгөө" |
| Inserts | Team / project media framed 1004×564 at y 640 on the grid card (pop-in: scale 0.82 to 1, blur, slight rotate, shadow) while the voice runs on; brand cards full screen with a zoom-in. The team-result photo (e.g. "THIRD PLACE", @handle) goes on the line where they thank the team. |
| Transitions | Whip-zoom blur (5 frames out, 7 in) on every clip-to-clip cut; calm fade at cards; RGB glitch into the end card; hook has none of it (hard cut) unless `hook_motion: "punchy"` |
| Punch-ins | 2-3 per reel, only on the important lines (the hook, the key claim, the advice). More felt repetitive (review 2026-11-13). |
| Captions | GIP, 47 px, regular weight with soft shadow, centred, baseline y 1292, 2-4 words, no name line. **Times come from forced alignment** (`--align`), never from hand-timed word groups (reviewer: "always late or early") |
| Logo | Grey chevron mark top-centre (opacity 0.55) on every clip, card and insert |
| Transition sounds | **None by default** (2026-11-16). With `card_sfx: true`: one soft sound per card, a different one each time (swell, pluck, swish, low pulse), none on inserts or answers; mixed 1 dB under the bed. Only the end-card glitch stays. The music still filters down on every card. |
| Music | Original 122 BPM tech bed (`reelpipe/pq_music.py`, synthesized, safe to post): pumping chords and arp, drums drop out and the music filters down on each card, hit when the answer lands. Speech **14 dB** over the bed (`speech_over_bed_db`, the default; 11 was "a bit loud", review 2026-11-16). Every reel in a series should not share one track: set `music_style` (`{"bpm": 128, "seed": 5, "key": 3}`, a second song: major key, broken beat) and change the numbers per reel; omit it for the original bed. SFX: whoosh in/out of cards and inserts, hits, glitch. |
| End | PineQuest S5 end card (`assets/pinequest/pq_s5_end_card.mp4`, 6.2 s, its own sting) |
| Loudness | -14.5 LUFS, true peak ≤ -1 dBTP |
| Post caption | `PineQuest S5-ийн <III байр / ялагч / оролцогч>, <Баг> багийн гишүүн <Нэр>-ийн сэтгэгдэл ⭐️` + the Bootcamp CTA lines |

## Recipe

1. **Footage + assets.** Raw interview. Team Instagram: `yt-dlp` the team's reels into `<job>/media/`
   (public, no login); pick a device / product frame and a logo frame (`grabs` with a 16:9 crop for framed
   inserts). The team-result photo: crop it from the PineQuest judge or result reel if the team has one.
2. **Transcribe** with `dash.pinecone.mn/reel` twice: the full file, then an answers-only file (each answer cut,
   loudnorm -16, 1.5 s silence between). Where the two Speechmatics passes agree, that wins over whisper (whisper
   was wrong on "шөнийн 12" vs "1" the other way round too: when they disagree, ask the reviewer). Whisper large-v3
   hallucinates on these files; use it only for single words. Faint segments (-35 to -45 dB) are the interviewer's questions: use them to map answers. A faint word at the very start (one interview's "Хоёрдугаарт", -32 dB) is the question's tail, not the answer: check levels before quoting it.
3. **Pick answers** (`testimonial-reel/references/answer-selection.md`): clean second takes, every piece ends
   on a finished sentence, in the speaker's own order. Never reorder clauses or cut inside a sentence
   (reviewer: "cuts his talk in the middle"). Each piece ends ≥ 0.15 s after the last word (the whip-out runs 5 frames).
   Never drop a question because it is hard to transcribe (reviewer: "cut out one whole question"). Instead:
   whisper large-v3 on 3-4 s chunks with `-bs 5/8` after `highpass,afftdn,loudnorm` (it found "Unity дээр
   шилжүүлээд C# болгох" where Speechmatics heard "юуны дээр … шил шар"), and read tech words into the mishears.
   Cards = the interviewer's own question: transcribe the faint question segments boosted (loudnorm -16) and
   phrase the card from it ("Төсөл хийхэд хамгийн хэцүү байсан зүйл юу вэ?").
4. **Write `job.json`** from `testimonial-reel/engine/batches/pinequest/_example.json` and follow
   the comments in that file. Keep each real job in its own folder outside the repo
   (e.g. `~/Desktop/AI-videos/pinequest-jobs/<yyyy-mm>-<name>/job.json` with `media/`); real jobs are git-ignored.
5. **Align captions.** Write the `captions` rows with the corrected text (times can be rough, they only have to put each
   line inside its piece), then `python3 -I pinequest.py <job>.json --align`. It forced-aligns the text to the audio
   (torchaudio MMS_FA), sets each line's from/to to its first/last word, keeps `job.before-align.json`, and prints old/new/delta
   per line. Check every flag (`SHORT`, `LOW-SCORE`: usually wrong text or a word the speaker swallowed). Re-run after any
   text edit. The aligner needs the **spoken** text: put words that are said but should not show (fillers "нөгөө нэг",
   a stutter "жоохон жоохон", a lead-in "Ээ") in square brackets, e.g. `"[нөгөө] Хийгээд байх тусам"`: they are aligned,
   then stripped from the screen. A line that would move > 1 s keeps its old times (`KEPT-OLD`): compare the aligner's
   time with the Speechmatics word times; if Speechmatics agrees, the hand timing was wrong (2026-11-16: whole
   phrases were 1-2 s off), so re-run with the align script's `--force`. If they disagree, the text is wrong: fix it first.
   Wrong words: reviewer 2026-11-16 caught "би энэ хэсгээ" where he said "би AI-г нь". Do the answers-only Speechmatics
   pass for every answer, and whisper 2-4 s chunks with `-l en` too: English loan words ("AI", "API") come out as
   "аяыг нь" in Speechmatics and "B.A.G." / "Эй айг нь" in whisper. One-time install: `python3 scripts/setup.py --align` (~0.5 GB venv + 1.2 GB model). Optional proof:
   `--check-captions` lists caption start vs nearest speech onset; |offset| > 0.15 s is flagged.
6. `python3 -I pinequest.py <job>.json --plan`: read the timeline. Then render: `python3 -I pinequest.py <job>.json`.
7. **Check**: stills of the hook (frames 0, 15, 30, 60), every caption band, each insert, the glitch into the end card.
   Captions follow `testimonial-reel/references/captions.md`; list unsure words for the member.

## Check
- [ ] Headline small enough (longest line ≤ 80 % width) and clear of the logo
- [ ] Hook is calm: no zoom ramp, no impact flash, headline fades in, hard cut into answer 1
- [ ] Question cards show the whole question at once and make no sound
- [ ] `--align` ran after the last caption text edit; no `SHORT` / `LOW-SCORE` flag left unexplained
- [ ] Headline is the hook quote (or a result headline if the quote is weak); no duplicate captions under it
- [ ] Headline readable over the face, face not cut at the top during punch-ins
- [ ] Insert graphics don't collide with the caption line (y 1240-1310)
- [ ] No logo or print on the speaker's clothes under the captions, also during punch-ins. If there is, set `"caption_style": {"baseline": 1530}` in the job (a hoodie chest logo)
- [ ] Captions readable on white or light clothes. If not, set `"caption_style": {"shadow": "drop-shadow(0 2px 3px rgba(0,0,0,0.9)) drop-shadow(0 0 10px rgba(0,0,0,0.75))"}` (a white sweater)
- [ ] Music under the voice, not competing with it (`speech_over_bed_db` 14; raise it for quieter music)
- [ ] Read every caption line as a sentence: no lone filler lines ("би нөгөө"), no full stop mid-thought, stutters merged ("их сургуулиа… сургуульдаа" -> "их сургуульдаа"), standard spelling ("хийчихээд"), "сэтгэгдэл" not "сэтгэл"
- [ ] No interviewer voice; every answer ends on a finished sentence
- [ ] Name, team, result spelled as confirmed
- [ ] -14.5 LUFS, ≤ -1 dBTP
