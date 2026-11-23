#!/usr/bin/env python3
"""Download the assets listed in MANIFEST.json (standard library only).

  python3 assets/fetch_assets.py                  fetch every missing entry that has a source_url
  python3 assets/fetch_assets.py --force          download again, replace existing files
  python3 assets/fetch_assets.py --list           print id, title, licence, present/missing
  python3 assets/fetch_assets.py --only id [id]   fetch only these ids

After a fetch it rewrites music/CREDITS.txt with the credit line of every present track.
Exit code is 1 if any download failed.
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "MANIFEST.json")
UA = "pinecone-editing-skills-assets/1.0"
TIMEOUT = 60
MIN_BYTES = 100 * 1024
SECTIONS = ("music", "images", "sfx")


def load():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)


def entries(manifest):
    for section in SECTIONS:
        for entry in manifest.get(section, []):
            yield section, entry


def path_of(entry):
    dest = os.path.realpath(os.path.join(HERE, entry["file"]))
    if os.path.commonpath([os.path.realpath(HERE), dest]) != os.path.realpath(HERE):  # a manifest entry must never write outside assets/
        raise ValueError(f"manifest file path escapes assets/: {entry['file']!r}")
    return dest


def looks_like_audio(head, content_type):
    if content_type.lower().startswith("audio/"):
        return True
    if head.startswith(b"ID3"):
        return True
    return len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0


def ssl_context():
    """Default context; on a python without a CA bundle (python.org builds on macOS) use the system one."""
    ctx = ssl.create_default_context()
    if not os.path.exists(ssl.get_default_verify_paths().cafile or ""):
        for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
            if os.path.exists(cafile):
                return ssl.create_default_context(cafile=cafile)
    return ctx


def download(entry):
    dest = path_of(entry)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    if not entry["source_url"].lower().startswith("https://"):  # no file:// or plain http
        raise RuntimeError(f"source_url must be https: {entry['source_url']!r}")
    req = urllib.request.Request(entry["source_url"], headers={"User-Agent": UA})
    try:  # urlopen below: scheme is forced to https above, so B310 (file:/ or custom schemes) cannot happen
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl_context()) as resp:  # nosec B310
            ctype = resp.headers.get("Content-Type", "") or ""
            data = resp.read()
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"download failed: {exc}")
    if len(data) < MIN_BYTES:
        raise RuntimeError(f"only {len(data)} bytes, expected at least {MIN_BYTES}")
    if entry["file"].startswith("music/") and not looks_like_audio(data[:4], ctype):
        raise RuntimeError(f"response is not audio (Content-Type: {ctype or 'none'})")
    try:
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return len(data)


def write_credits(manifest):
    lines = [e["credit"] for _, e in entries(manifest)
             if e.get("credit") and os.path.exists(path_of(e))]
    if not lines:
        return
    out = os.path.join(HERE, "music", "CREDITS.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Fetch shared assets from MANIFEST.json")
    ap.add_argument("--force", action="store_true", help="download again even if the file exists")
    ap.add_argument("--list", action="store_true", help="list entries and whether each file is present")
    ap.add_argument("--only", nargs="+", metavar="ID", help="fetch only these ids")
    args = ap.parse_args()
    manifest = load()

    if args.list:
        for _, e in entries(manifest):
            state = "present" if os.path.exists(path_of(e)) else "missing"
            print(f"{e['id']}\t{e['title']}\t{e.get('licence', '?')}\t{state}")
        return 0

    known = {e["id"] for _, e in entries(manifest)}
    if args.only:
        unknown = [i for i in args.only if i not in known]
        if unknown:
            print("unknown id: " + ", ".join(unknown), file=sys.stderr)
            return 2

    failed = 0
    for _, e in entries(manifest):
        if args.only and e["id"] not in args.only:
            continue
        if not e.get("source_url"):
            continue
        if os.path.exists(path_of(e)) and not args.force:
            print(f"skip   {e['id']} (already present)")
            continue
        try:
            size = download(e)
            print(f"ok     {e['id']} ({size // 1024} KB)")
        except RuntimeError as exc:
            failed += 1
            print(f"FAILED {e['id']}: {exc}", file=sys.stderr)
    write_credits(manifest)
    if failed:
        print(f"{failed} download(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
