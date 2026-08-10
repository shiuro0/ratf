from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any


class AuditLogger:
    """Append-only JSONL audit logger with an HMAC hash chain.

    The chain does not make the file immutable, but it makes accidental edits and
    unsophisticated tampering detectable during experiment validation.
    """

    def __init__(self, path: str, secret: str = "local-audit-log-secret-change-me"):
        self.path = path
        self.secret = secret
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._sequence, self._last_hash = self._read_tail_state()

    def _canonical(self, entry: dict[str, Any]) -> bytes:
        return json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()

    def _sign(self, entry: dict[str, Any]) -> str:
        return hmac.new(self.secret.encode(), self._canonical(entry), hashlib.sha256).hexdigest()

    def _read_tail_state(self) -> tuple[int, str]:
        if not os.path.exists(self.path):
            return 0, "GENESIS"
        last = None
        with open(self.path, "r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    last = json.loads(line)
        if not last:
            return 0, "GENESIS"
        return int(last.get("sequence", 0)), str(last.get("entry_hash", "GENESIS"))

    def write(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._sequence += 1
            chained = {
                **entry,
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "sequence": self._sequence,
                "previous_hash": self._last_hash,
            }
            chained["entry_hash"] = self._sign(chained)
            with open(self.path, "a", encoding="utf-8") as file:
                file.write(json.dumps(chained, ensure_ascii=False, default=str) + "\n")
                file.flush()
                os.fsync(file.fileno())
            self._last_hash = chained["entry_hash"]

    def read_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as file:
            lines = file.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]

    def verify_integrity(self) -> dict[str, Any]:
        previous = "GENESIS"
        checked = 0
        errors: list[str] = []
        if not os.path.exists(self.path):
            return {"valid": True, "entries": 0, "errors": []}
        with open(self.path, "r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                checked += 1
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    errors.append(f"line {line_number}: invalid JSON")
                    continue
                observed_hash = entry.pop("entry_hash", None)
                if entry.get("previous_hash") != previous:
                    errors.append(f"line {line_number}: previous_hash mismatch")
                expected_hash = self._sign(entry)
                if not observed_hash or not hmac.compare_digest(str(observed_hash), expected_hash):
                    errors.append(f"line {line_number}: entry_hash mismatch")
                previous = str(observed_hash or previous)
        return {"valid": not errors, "entries": checked, "errors": errors}

    def clear(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with self._lock:
            with open(self.path, "w", encoding="utf-8"):
                pass
            self._sequence = 0
            self._last_hash = "GENESIS"
