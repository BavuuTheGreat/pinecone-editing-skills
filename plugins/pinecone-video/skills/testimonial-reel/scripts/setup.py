"""One-time setup for the testimonial-reel skill. Safe to re-run. Works on macOS, Windows and Linux.

    python3 setup.py          (macOS / Linux)
    python3 setup.py --align  (optional: install the caption forced-alignment venv, ~0.5 GB)
    py setup.py               (Windows)

Checks python, numpy, node, ffmpeg (and yt-dlp, optional, for reel-audit); installs numpy and the pinned Remotion engine (npm ci).
It never installs system tools silently: for node/ffmpeg it prints the exact command for this OS."""
import os
import platform
import shutil
import subprocess
import sys

ENGINE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine")
OS = platform.system()  # Darwin / Windows / Linux
HINTS = {
    "node": {"Darwin": "brew install node", "Windows": "winget install OpenJS.NodeJS.LTS", "Linux": "sudo apt install nodejs npm"},
    "ffmpeg": {"Darwin": "brew install ffmpeg", "Windows": "winget install Gyan.FFmpeg", "Linux": "sudo apt install ffmpeg"},
    "yt-dlp": {"Darwin": "brew install yt-dlp", "Windows": "winget install yt-dlp.yt-dlp", "Linux": "pipx install yt-dlp"},
}


def ok(msg: str) -> None:
    print(f"  ok   {msg}")


def bad(msg: str) -> None:
    print(f"  MISSING  {msg}")


def version(cmd: list) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.strip().splitlines()[0]
    except Exception:
        return ""


def _venv_py(venv: str) -> str:
    return os.path.join(venv, "Scripts", "python.exe") if os.name == "nt" else os.path.join(venv, "bin", "python")


def _aligner_ok(py: str) -> bool:
    """The venv python can import torch and torchaudio.pipelines.MMS_FA."""
    if not os.path.exists(py):
        return False
    r = subprocess.run([py, "-c", "import torch, torchaudio; from torchaudio.pipelines import MMS_FA"], capture_output=True)
    return r.returncode == 0


def _find_python() -> list:
    """Command (argv prefix) of a python 3.10-3.12: torch wheels exist for those, not for newer ones."""
    probes = ([["py", "-3.12"], ["py", "-3.11"], ["py", "-3.10"]] if os.name == "nt"
              else [["python3.12"], ["python3.11"], ["python3.10"], ["python3"]])
    for cmd in probes:
        if not shutil.which(cmd[0]):
            continue
        try:
            v = subprocess.run([*cmd, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"], capture_output=True, text=True).stdout.strip()
            if v in ("3.10", "3.11", "3.12"):
                return cmd
        except Exception:
            pass
    return []


def install_aligner() -> int:
    """Optional: isolated venv with torch + torchaudio for caption forced alignment (reelpipe/align_captions.py).
    ~0.5 GB venv (about 1 min) + a one-time ~1.2 GB model download on the first alignment. Needs python 3.10-3.12.
    Intel Macs: torch 2.2.2 (the last build for them; torchaudio 2.2.2 has MMS_FA). Everything else: torch 2.5.1."""
    venv = os.path.join(ENGINE, ".venv-align")
    py = _venv_py(venv)
    if _aligner_ok(py):
        ok("caption aligner venv already installed")
        return 0
    intel_mac = OS == "Darwin" and platform.machine() == "x86_64"
    ver = "2.2.2" if intel_mac else "2.5.1"
    cmd = _find_python()
    if not cmd:
        bad("a python 3.10, 3.11 or 3.12 for the aligner (torch has no wheels for newer ones)  ->  install python 3.12"
            + ("  (winget install Python.Python.3.12)" if OS == "Windows" else "  (brew install python@3.12)" if OS == "Darwin" else ""))
        return 1
    if os.path.exists(venv):
        print("  ...  repairing a half-installed aligner venv")
        shutil.rmtree(venv, ignore_errors=True)
    print(f"  ...  creating {venv} with {' '.join(cmd)}, torch {ver} (~0.5 GB, ~1 min)")
    pins = [f"torch=={ver}", f"torchaudio=={ver}", "numpy<2", "certifi"]
    if subprocess.run([*cmd, "-m", "venv", venv]).returncode or subprocess.run([py, "-m", "pip", "install", "-q", *pins]).returncode \
            or not _aligner_ok(py):
        bad("aligner install failed or torch/torchaudio do not import (captions still work, just hand-timed)")
        shutil.rmtree(venv, ignore_errors=True)  # never leave a broken venv that looks installed
        return 1
    ok("caption aligner installed and importable; the model (~1.2 GB) downloads on the first --align")
    return 0


BRAND = ["GIP-Regular.woff2", "pinecone_mark.svg", "end_card_9x16.mp4", os.path.join("pinequest", "pq_s5_end_card.mp4")]


def install_brand(src: str) -> None:
    """Copy the brand-pack files (found anywhere inside a folder or .zip, matched by file name) into engine/assets."""
    import tempfile, zipfile
    if not src or not os.path.exists(src):
        bad(f"--brand: no such folder or zip: {src!r}")
        return
    tmp = None
    if zipfile.is_zipfile(src):
        tmp = tempfile.mkdtemp()
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        src = tmp
    found = {}
    for root, _, files in os.walk(src):
        for f in files:
            found.setdefault(f, os.path.join(root, f))
    for rel in BRAND:
        name = os.path.basename(rel)
        if name in found:
            dst = os.path.join(ENGINE, "assets", rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(found[name], dst)
            ok(f"brand pack: {rel}")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    if "--align" in sys.argv:
        return install_aligner()
    print(f"testimonial-reel setup ({OS})")
    missing = []

    if sys.version_info < (3, 10):
        bad(f"python 3.10+ (have {platform.python_version()})")
        missing.append("python")
    else:
        ok(f"python {platform.python_version()}")

    try:
        import numpy  # noqa: F401
        ok("numpy")
    except ImportError:
        print("  ...  installing numpy")
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--user", "numpy"])
        if r.returncode:
            bad("numpy (pip install failed)")
            missing.append("numpy")
        else:
            ok("numpy installed")

    for tool, probe in (("node", ["node", "--version"]), ("ffmpeg", ["ffmpeg", "-version"])):
        if shutil.which(tool) and (tool != "ffmpeg" or shutil.which("ffprobe")):
            ok(f"{tool} {version(probe)[:40]}")
        else:
            bad(f"{tool}  ->  install with:  {HINTS[tool].get(OS, HINTS[tool]['Linux'])}")
            missing.append(tool)

    if "node" not in missing:
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        bin_ = os.path.join(ENGINE, "node_modules", ".bin", "remotion.cmd" if os.name == "nt" else "remotion")
        if os.path.exists(bin_):
            ok("render engine already installed")
        elif npm:
            print("  ...  installing render engine (npm ci, ~1 min)")
            r = subprocess.run([npm, "ci", "--no-fund", "--no-audit"], cwd=ENGINE)
            (ok("render engine installed") if r.returncode == 0 else (bad("npm ci failed"), missing.append("engine")))
        else:
            bad("npm")
            missing.append("npm")

    # Brand pack: Pinecone-owned / licensed files kept out of the public repo. `setup.py --brand <folder or .zip>`
    # copies them into place from the pack the Editing manager shares.
    if "--brand" in sys.argv[1:]:
        i = sys.argv.index("--brand")
        src = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        install_brand(src)
    lacking = [rel for rel in BRAND if not os.path.exists(os.path.join(ENGINE, "assets", rel))]
    if lacking:
        bad(f"brand pack ({', '.join(lacking)}): ask the Editing manager for it, then run: setup.py --brand <folder or .zip>")
        missing.append("brand pack")
    else:
        ok("brand pack (caption font, logo, end cards)")

    # Optional: editing works without it; reel-audit and team-media downloads need it.
    audit = bool(shutil.which("yt-dlp"))
    if audit:
        ok(f"yt-dlp {version(['yt-dlp', '--version'])[:20]}")
    else:
        bad(f"yt-dlp (only for reel-audit / downloading reels)  ->  install with:  {HINTS['yt-dlp'].get(OS, HINTS['yt-dlp']['Linux'])}")

    if _aligner_ok(_venv_py(os.path.join(ENGINE, ".venv-align"))):
        ok("caption aligner (optional)")
    else:
        print("  --   caption aligner (optional, PineQuest forced alignment): setup.py --align  (~0.5 GB + 1.2 GB model)")

    if missing:
        print(f"\nNot ready. Install: {', '.join(missing)}. Then run setup again.")
        return 1
    print("\nReady. In Claude Code say: \"make testimonial reels from <folder>\"")
    if audit:
        print("Reel audit ready too: \"audit @<account> reels\" (needs Claude in Chrome, signed in to Instagram).")
    else:
        print("Reel audit: install yt-dlp first (command above), then run setup again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
