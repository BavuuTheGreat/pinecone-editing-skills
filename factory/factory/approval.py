"""Approval adapters. All share: post_proposal(reel), read_decision(reel), post_result(reel)."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from typing import Any

from factory import state
from factory.config import Config


def _older(at: object, since: object) -> bool:
    try:
        return datetime.fromisoformat(str(at)) < datetime.fromisoformat(str(since))
    except ValueError:
        return False  # no usable time on one side: nothing to compare


def refusal(reel: dict) -> str | None:
    """Why this reel cannot take a decision now, or None. Only a posted, pending proposal can be decided."""
    if (reel["status"] == "proposed" and (reel.get("approval") or {}).get("state") == "pending"
            and (reel.get("proposal") or {}).get("path")):
        return None
    return f"{reel['name']} is '{reel['status']}' with no proposal waiting, so there is nothing to decide."


class FileApproval:
    """Decision lives in <state>/<id>/approval.json, written by `factory approve|reject`."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def post_proposal(self, reel: dict) -> None:
        pass  # proposal.md in the state folder is the post; nothing to send

    def read_decision(self, reel: dict) -> dict[str, Any] | None:
        try:
            d = json.loads((self.cfg.reel_dir(reel["id"]) / "approval.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(d, dict) or d.get("state") not in ("approved", "rejected"):
            return None
        if _older(d.get("at"), (reel.get("proposal") or {}).get("at")):
            return None  # a decision made before this proposal existed is not a decision on it
        return {"state": d["state"], "by": d.get("by", ""), "at": d.get("at", ""), "comment": d.get("comment", "")}

    def post_result(self, reel: dict) -> None:
        pass  # the finished files are already listed in reel.json


class PlannerApproval:
    """Stand-in for the Marketing Planner. When its API exists it needs three HTTP calls:

    - post_proposal: POST the proposal (reel id, name, theme, hook, proposal.md text, open questions) as a pending task.
    - read_decision: GET that task; map its state to approved/rejected and copy approver, time and comment.
    - post_result: POST/PATCH the task with the finished output file paths and review state.
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def post_proposal(self, reel: dict) -> None:
        raise NotImplementedError("Marketing Planner API not available yet")

    def read_decision(self, reel: dict) -> dict[str, Any] | None:
        raise NotImplementedError("Marketing Planner API not available yet")

    def post_result(self, reel: dict) -> None:
        raise NotImplementedError("Marketing Planner API not available yet")


def get_adapter(cfg: Config) -> FileApproval | PlannerApproval:
    return PlannerApproval(cfg) if cfg.approval == "planner" else FileApproval(cfg)


def _decide(cfg: Config, reel: dict, decision: str, comment: str, by: str | None) -> None:
    folder = cfg.reel_dir(reel["id"])
    folder.mkdir(parents=True, exist_ok=True)
    data = {"state": decision, "by": by or os.environ.get("USER", "manager"), "at": state.now_iso(), "comment": comment}
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".approval-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        os.replace(tmp, folder / "approval.json")
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def approve(cfg: Config, reel: dict, comment: str = "", by: str | None = None) -> None:
    _decide(cfg, reel, "approved", comment, by)


def reject(cfg: Config, reel: dict, comment: str = "", by: str | None = None) -> None:
    _decide(cfg, reel, "rejected", comment, by)
