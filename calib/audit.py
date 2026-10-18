"""Hash-chained audit log: every decision and appeal, immutably recorded.

Each entry commits to the previous entry's hash, so any tampering with an
earlier record breaks the chain and is detected by :meth:`AuditLog.verify`.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json


def _hash(entry: dict) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditLog:
    def __init__(self) -> None:
        self.entries: list[dict] = []

    def record(self, kind: str, payload: dict) -> dict:
        """Append an entry of ``kind`` and return it."""
        entry = {
            "seq": len(self.entries) + 1,
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "payload": payload,
            "prev": self.entries[-1]["hash"] if self.entries else "GENESIS",
        }
        entry["hash"] = _hash({k: v for k, v in entry.items() if k != "hash"})
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        """Return True iff every link in the chain is intact."""
        prev = "GENESIS"
        for i, entry in enumerate(self.entries, start=1):
            if entry["seq"] != i or entry["prev"] != prev:
                return False
            if entry["hash"] != _hash({k: v for k, v in entry.items() if k != "hash"}):
                return False
            prev = entry["hash"]
        return True

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.entries, fh, indent=2)

    @classmethod
    def load(cls, path: str) -> "AuditLog":
        log = cls()
        with open(path, encoding="utf-8") as fh:
            log.entries = json.load(fh)
        return log
