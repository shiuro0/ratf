from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .core.models import RequestContext
from .storage import Storage


@dataclass
class ReplayResult:
    detected: bool
    reason_code: str | None = None


def check_replay(
    storage: Storage,
    settings: Settings,
    subject: str,
    context: RequestContext,
    *,
    transactional: bool = False,
) -> ReplayResult:
    # Validate required fields before consuming either identifier.
    if settings.nonce_required and not context.nonce:
        return ReplayResult(True, "nonce_missing")
    if transactional and settings.idempotency_required and not context.idempotency_key:
        return ReplayResult(True, "idempotency_key_missing")

    evidence = {
        "request_id": context.request_id,
        "fingerprint": context.request_fingerprint,
        "body_hash": context.body_hash,
        "endpoint": context.endpoint,
    }
    if context.nonce:
        key = f"nonce:{subject}:{context.nonce}"
        if not storage.claim_json(key, evidence, settings.replay_window_seconds):
            return ReplayResult(True, "nonce_reused")

    if transactional and context.idempotency_key:
        key = f"idempotency:{subject}:{context.endpoint}:{context.idempotency_key}"
        if not storage.claim_json(key, evidence, settings.replay_window_seconds):
            return ReplayResult(True, "idempotency_key_reused")

    # Fingerprints are retained as audit evidence only. Repeating a valid business
    # payload with fresh request identifiers is not automatically classified as replay.
    storage.set_json(
        f"fingerprint:{subject}:{context.request_fingerprint}",
        evidence,
        ttl_seconds=settings.replay_window_seconds,
    )
    return ReplayResult(False)
