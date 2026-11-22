"""Paths and settings. Every module takes a Config so tests can point it at a temp dir."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_HOME = "~/Desktop/AI-videos/factory"
DEFAULT_WHISPER_MODEL = "~/.cache/whisper-cpp/ggml-large-v3-q5_0.bin"
# The package lives at <repo>/factory/factory/, so the repo root is two levels up.
DEFAULT_REPO = Path(__file__).resolve().parents[2]

REEL_ID = re.compile(r"\w[\w-]*")  # what state.slugify produces
CHOICES = {"transcriber": ("whisper", "manual"), "editor": ("handoff", "claude"), "approval": ("file", "planner")}


@dataclass
class Config:
    home: Path
    transcriber: str = "whisper"
    editor: str = "handoff"
    approval: str = "file"
    settle_seconds: int = 60
    repo: Path = DEFAULT_REPO
    whisper_model: Path = field(default_factory=lambda: Path(DEFAULT_WHISPER_MODEL).expanduser())

    def __post_init__(self) -> None:
        self.home, self.repo, self.whisper_model = Path(self.home), Path(self.repo), Path(self.whisper_model)
        for key, allowed in CHOICES.items():
            if getattr(self, key) not in allowed:
                raise ValueError(f"config '{key}' must be one of {allowed}, got {getattr(self, key)!r}")

    @property
    def inbox(self) -> Path:
        return self.home / "inbox"

    @property
    def state(self) -> Path:
        return self.home / "state"

    @property
    def reviews(self) -> Path:
        return self.home / "reviews"

    @property
    def lock(self) -> Path:
        return self.home / "factory.lock"

    def reel_dir(self, reel_id: str) -> Path:
        # A reel id is a folder name: no "..", no slash, no dot. Ids from the network or the command line must stay inside state/.
        if not isinstance(reel_id, str) or not REEL_ID.fullmatch(reel_id):
            raise ValueError(f"invalid reel id: {reel_id!r}")
        return self.state / reel_id

    def ensure_dirs(self) -> None:
        for d in (self.inbox, self.state, self.reviews):
            d.mkdir(parents=True, exist_ok=True)


def load(home: str | os.PathLike | None = None) -> Config:
    """Build a Config from FACTORY_HOME (or the default) plus the optional <home>/config.json."""
    root = Path(home or os.environ.get("FACTORY_HOME") or DEFAULT_HOME).expanduser()
    values: dict = {}
    path = root / "config.json"
    if path.is_file():
        values = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"transcriber", "editor", "approval", "settle_seconds", "repo", "whisper_model"}
    values = {k: v for k, v in values.items() if k in allowed}
    for k in ("repo", "whisper_model"):
        if k in values:
            values[k] = Path(values[k]).expanduser()
    return Config(home=root, **values)
