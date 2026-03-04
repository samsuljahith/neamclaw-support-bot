"""
Session storage using the local filesystem.

Default path: /tmp/sessions  (ephemeral per-Lambda-instance).
Override with SESSION_DIR env var — point this at an EFS mount path for
durable cross-invocation persistence (requires Lambda VPC + EFS setup in
the Pulumi infra).
"""
from __future__ import annotations

import json
import os
from typing import Any

_SESSION_DIR = os.environ.get("SESSION_DIR", "/tmp/sessions")
_MAX_MESSAGES = 120  # keep last 60 turns (120 messages)


def _path(key: str) -> str:
    os.makedirs(_SESSION_DIR, exist_ok=True)
    safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return os.path.join(_SESSION_DIR, f"{safe_key}.json")


class SessionManager:
    def load(self, key: str) -> list[dict[str, Any]]:
        p = _path(key)
        if not os.path.exists(p):
            return []
        try:
            with open(p) as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            return []

    def save(self, key: str, history: list[dict[str, Any]]) -> None:
        with open(_path(key), "w") as fh:
            json.dump(history[-_MAX_MESSAGES:], fh)

    def delete(self, key: str) -> None:
        p = _path(key)
        if os.path.exists(p):
            os.remove(p)

    def count(self) -> int:
        if not os.path.isdir(_SESSION_DIR):
            return 0
        return sum(1 for f in os.listdir(_SESSION_DIR) if f.endswith(".json"))
