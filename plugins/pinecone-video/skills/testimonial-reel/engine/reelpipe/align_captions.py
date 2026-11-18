"""Forced-align PineQuest caption lines to the speech (torchaudio MMS_FA, any language via romanization).

    .venv-align/bin/python reelpipe/align_captions.py <job.json> [--dry] [--out other.json]

Why: caption rows `[src_from, src_to, text, piece_id?]` were hand-timed from word groups and ran 0.1-0.4 s
early/late. The corrected caption TEXT is ground truth; this sets each row's from = first word start and
to = last word end, measured from the audio. Text and piece ids are never touched.

Per piece: audio span (pieces[].start/end, 0.1 s margin) -> all its caption lines joined -> words aligned -> rows.
Saves job.before-align.json next to the job (once, never overwritten), rewrites the job, prints old/new/delta.
Needs torch + torchaudio: run it with the venv python (pinequest.py --align does that for you).
The Mongolian Cyrillic -> latin romanizer is in this file; it is also importable without torch (`romanize`).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

SR = 16000
MARGIN = 0.1
MIN_DUR = 0.25      # flag lines aligned shorter than this
SHIFT = 0.5        # flag lines that moved more than this from the old time: usually text missing/extra words
KEEP_OLD = 1.0     # a line that would move more than this keeps its old time unless --force (almost always a text/audio mismatch)
LOW_SCORE = 0.35    # flag lines whose mean token probability is below this

# ---------- romanizer: Mongolian Cyrillic -> MMS_FA alphabet (a-z and ') ----------
CYR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "i", "к": "k",
       "л": "l", "м": "m", "н": "n", "о": "o", "ө": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ү": "u",
       "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i", "ь": "i", "э": "e",
       "ю": "yu", "я": "ya"}
VOWELS = set("аеёиоөуүэюяыaeiou")
# spoken forms of latin words common in tech talk (lowercase key); anything else latin is kept letter by letter
LEX = {"pinequest": "painkvest", "software": "softver", "engineer": "injiner", "python": "paiton", "unity": "yuniti",
       "java": "java", "javascript": "javaskript", "code": "kod", "app": "ep", "web": "veb", "ui": "yu ai", "ux": "yu eks",
       "bootcamp": "butkemp", "pinecone": "painkon", "api": "ei pi ai", "it": "ai ti", "ai": "ei ai",
       # as Mongolian speakers say them (episode 1: lower alignment scores on these words before this list)
       "academy": "akademi", "google": "guugl", "maps": "map", "map": "map", "higgsfield": "higsfild", "claude": "klaud", "app": "ap",
       "event": "evend", "hall": "hool", "reel": "riil", "hello": "helloo", "guys": "gais"}
LETTER = dict(zip("abcdefghijklmnopqrstuvwxyz", ["ei", "bi", "si", "di", "i", "ef", "ji", "eich", "ai", "jei", "kei", "el", "em", "en",
                                                  "ou", "pi", "kiu", "ar", "es", "ti", "yu", "vi", "dablyu", "eks", "uai", "zed"]))
ONES = ["", "neg", "hoyor", "gurav", "dorov", "tav", "zurgaa", "doloo", "naim", "yes"]
TENS = {10: "arav", 20: "hori", 30: "guch", 40: "doch", 50: "tavi", 60: "jar", 70: "dal", 80: "naya", 90: "er"}
TENS_PREFIX = {10: "arvan", 20: "horin", 30: "guchin", 40: "dochin", 50: "tavin", 60: "jaran", 70: "dalan", 80: "nayan", 90: "eren"}


def number_words(n: int) -> str:
    if n == 0:
        return "tegr"
    if n < 10:
        return ONES[n]
    if n < 100:
        t, o = n // 10 * 10, n % 10
        return TENS[t] if not o else f"{TENS_PREFIX[t]} {ONES[o]}"
    if n == 100:
        return "zuu"
    if n < 1000:
        h, r = divmod(n, 100)
        return (f"{ONES[h]} zuu" if h > 1 else "zuun") + (f" {number_words(r)}" if r else "")
    if n == 1000:
        return "myanga"
    return " ".join(number_words(int(d)) for d in str(n))  # years etc.: digit by digit


def _cyr_word(w: str) -> str:
    out = []
    for i, ch in enumerate(w):
        if ch == "е":
            out.append("ye" if i == 0 or w[i - 1] in VOWELS or w[i - 1] in "ъь" else "e")
        else:
            out.append(CYR.get(ch, ch if ch.isascii() and ch.isalpha() else ""))
    return "".join(out)


def _latin_part(p: str) -> str:
    low = p.lower()
    if low in LEX:
        return LEX[low]
    if p.isupper() and 2 <= len(p) <= 5:  # acronym: spoken letter by letter ("AI" -> "эй ай")
        return " ".join(LETTER[c] for c in low if c in LETTER)
    return low


def romanize_word(tok: str) -> str:
    """One whitespace token -> romanized string with spaces only where the spoken form is several words."""
    tok = tok.replace("’", "'")
    pieces = []
    for part in re.findall(r"\d+|[A-Za-z]+|[^\W\d_]+|'", tok):
        if part.isdigit():
            pieces.append(number_words(int(part)))
        elif re.fullmatch(r"[A-Za-z]+", part):
            pieces.append(_latin_part(part))
        elif part == "'":
            continue
        else:
            pieces.append(_cyr_word(part.lower()))
    s = " ".join(x for x in pieces if x)
    return re.sub(r"[^a-z' ]", "", s).strip()


def romanize(text: str) -> list[str]:
    """Caption text -> list of aligner words (punctuation dropped; acronyms/numbers may expand to several)."""
    words = []
    for tok in text.split():
        r = romanize_word(tok)
        words.extend(w for w in r.split(" ") if w)
    return words


def romanize_tok(tok: str) -> list[str]:
    return [w for w in romanize_word(tok).split(" ") if w]


# ---------- alignment ----------
def load_audio(src: str, a: float, b: float):
    import numpy as np
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", src, "-ac", "1", "-ar", str(SR),
                                   "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32).copy()


def piece_for(row, pieces, i=None):
    """Piece a caption row belongs to: its explicit 4th element, else the piece whose span holds the row's old start."""
    tag = f"caption row {i} {str(row[2])[:30]!r}" if i is not None else "caption row"
    if len(row) > 3 and row[3]:
        for p in pieces:
            if p["id"] == row[3]:
                return p
        raise SystemExit(f"{tag}: unknown piece id {row[3]!r} (pieces: {', '.join(p['id'] for p in pieces)})")
    for p in pieces:
        if p["start"] - 0.06 <= row[0] < p["end"]:
            return p
    raise SystemExit(f"{tag}: start {row[0]} is inside no piece; fix the time or add the piece id as the 4th element")


def align_piece(model, tokenizer, aligner, wav, lines):
    """lines: caption texts. Returns per line (start, end, score) in seconds from the start of `wav`, or None."""
    import torch
    words, owner = [], []
    for li, text in enumerate(lines):
        for tok in text.split():
            for w in romanize_tok(tok):
                words.append(w)
                owner.append(li)
    with torch.inference_mode():
        emission, _ = model(torch.from_numpy(wav)[None])
        spans = aligner(emission[0], tokenizer(words))
    ratio = len(wav) / emission.size(1) / SR
    out = [None] * len(lines)
    for w, li, sp in zip(words, owner, spans):
        s, e = sp[0].start * ratio, sp[-1].end * ratio
        score = sum(x.score for x in sp) / len(sp)
        if out[li] is None:
            out[li] = [s, e, [score]]
        else:
            out[li][1] = e
            out[li][2].append(score)
    return [None if o is None else (o[0], o[1], sum(o[2]) / len(o[2])) for o in out]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--dry", action="store_true", help="print the table, write nothing")
    ap.add_argument("--force", action="store_true", help="also apply lines that moved more than %.1f s (default: keep their old times)" % KEEP_OLD)
    ap.add_argument("--pieces", help="json [{id,start,end}] of resolved cut bounds (set by pinequest.py)")
    ap.add_argument("--out", help="write the aligned job here instead of overwriting the input")
    a = ap.parse_args()
    jp = os.path.abspath(a.job)
    base = os.path.dirname(jp)
    job = json.load(open(jp, encoding="utf8"))
    src = os.path.expanduser(job["source"])
    src = src if os.path.isabs(src) else os.path.normpath(os.path.join(base, src))
    if a.pieces:  # resolved cut bounds handed over by pinequest.py (word_start/word_end pieces are snapped to silence there)
        pieces = json.load(open(a.pieces))
    else:
        bad = [p["id"] for p in job["pieces"] if "start" not in p or "end" not in p]
        if bad:
            raise SystemExit(f"pieces {bad} have no start/end (word_start/word_end form): run through `pinequest.py <job> --align`, which resolves the cut bounds")
        pieces = [{"id": p["id"], "start": p["start"], "end": p["end"]} for p in job["pieces"]]
    try:  # python.org builds ship without CA certs: the one-time model download (~1.2 GB) needs them
        import certifi
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except ImportError:
        pass
    import torch
    from torchaudio.pipelines import MMS_FA as bundle
    torch.set_num_threads(max(1, (os.cpu_count() or 2) // 2))
    model, tokenizer, aligner = bundle.get_model(with_star=False), bundle.get_tokenizer(), bundle.get_aligner()
    rows = job["captions"]
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(piece_for(row, pieces, i)["id"], []).append(i)
    new_rows = [list(r) for r in rows]
    print(f"{'line':>4}  {'text':34s} {'old from-to':>13}  {'new from-to':>13}  {'d.from':>6} {'d.to':>6}  flags")
    flagged = 0
    for pid, idx in groups.items():
        idx.sort(key=lambda i: rows[i][0])  # spoken order = old time order (job rows are not always chronological; one real job's weren't)
        p = next(x for x in pieces if x["id"] == pid)
        t0 = max(0.0, p["start"] - MARGIN)
        t1 = p["end"] + MARGIN
        try:
            wav = load_audio(src, t0, t1)
            res = align_piece(model, tokenizer, aligner, wav, [rows[i][2] for i in idx])
        except Exception as ex:  # empty words, too few emission frames, ffmpeg trouble: keep this piece's old times, go on
            print(f"piece {pid} skipped: {type(ex).__name__}: {ex} (old times kept)")
            flagged += len(idx)
            continue
        for i, r in zip(idx, res):
            old = rows[i]
            flags = []
            if r is None:
                print(f"{i:4d}  {old[2][:34]:34s} no alignable words, unchanged")
                continue
            s, e, sc = round(t0 + r[0], 3), round(t0 + r[1], 3), r[2]
            ps, pe = s, e
            if s < p["start"] or e > p["end"]:
                flags.append("clamped-to-piece")
                s, e = max(s, p["start"]), min(e, p["end"])
                if s >= e:
                    flags.append(f"KEPT-OLD (aligner said {ps:.2f}-{pe:.2f}, outside the piece)")
                    s, e = old[0], old[1]
            if e - s < MIN_DUR:
                flags.append(f"SHORT {e - s:.2f}s")
            if abs(s - old[0]) > SHIFT or abs(e - old[1]) > SHIFT:
                flags.append("SHIFT>%.1fs (text may not match the audio)" % SHIFT)
            if sc < LOW_SCORE:
                flags.append(f"LOW-SCORE {sc:.2f}")
            placeholder = old[0] == old[1] or old[0] == 0 or old[1] == 0  # no real hand timing to protect: take the alignment
            if placeholder:
                flags.append("PLACEHOLDER-OLD: compare with the Speechmatics times; pass --force if they disagree")
            if max(abs(s - old[0]), abs(e - old[1])) > KEEP_OLD and not a.force and not placeholder:
                flags.append(f"KEPT-OLD (aligner said {s:.2f}-{e:.2f}, moved >{KEEP_OLD:.1f}s: fix the text and re-run, or --force)")
                s, e = old[0], old[1]
            flagged += bool(flags)
            new_rows[i][0], new_rows[i][1] = s, e
            print(f"{i:4d}  {old[2][:34]:34s} {old[0]:6.2f}-{old[1]:6.2f}  {s:6.2f}-{e:6.2f}  {s - old[0]:+6.2f} {e - old[1]:+6.2f}  {' '.join(flags)} (p {sc:.2f})")
    print(f"{len(rows)} lines, {flagged} flagged")
    if a.dry:
        return
    if not a.out:
        bk = os.path.join(base, "job.before-align.json")
        if not os.path.exists(bk):
            shutil.copy(jp, bk)
            print(f"saved {bk}")
        else:
            print(f"kept existing {bk} (first backup stays the hand-timed original)")
    job["captions"] = new_rows
    dst = a.out or jp
    with open(dst + ".tmp", "w", encoding="utf8") as fh:
        json.dump(job, fh, ensure_ascii=False, indent=1)
    os.replace(dst + ".tmp", dst)
    print(f"wrote {a.out or jp}")


if __name__ == "__main__":
    main()
