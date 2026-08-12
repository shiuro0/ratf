from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Request

from .config import Settings
from .core.models import RequestContext


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def body_hash_from_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _body_hash(request: Request) -> str:
    raw = request.get_data(cache=True) or b""
    if request.is_json:
        try:
            raw = canonical_json_bytes(request.get_json(silent=True) or {})
        except (TypeError, ValueError):
            pass
    return hashlib.sha256(raw).hexdigest()


def experiment_headers_allowed(request: Request, settings: Settings) -> bool:
    return bool(
        settings.experiment_mode
        and request.headers.get("X-Experiment-Key")
        and request.headers.get("X-Experiment-Key") == settings.experiment_key
    )


def _source_ip(request: Request, settings: Settings, experiment_allowed: bool) -> str:
    if experiment_allowed:
        simulated = request.headers.get("X-Test-Source-IP")
        if simulated:
            return simulated.strip()
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.remote_addr or "unknown"


def _context_time(request: Request, settings: Settings, experiment_allowed: bool) -> datetime:
    value = request.headers.get("X-Test-Context-Time") if experiment_allowed else None
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)


def _user_agent(request: Request, experiment_allowed: bool) -> str:
    if experiment_allowed:
        simulated = request.headers.get("X-Test-User-Agent")
        if simulated:
            return simulated.strip()
    return request.headers.get("User-Agent", "unknown")


def extract_issuance_context(request: Request, settings: Settings) -> dict[str, Any]:
    allowed = experiment_headers_allowed(request, settings)
    now = _context_time(request, settings, allowed)
    return {
        "issued_ip": _source_ip(request, settings, allowed),
        "issued_user_agent": _user_agent(request, allowed),
        "issued_hour_utc": now.hour,
        "issued_at_context": now.isoformat(),
        "experiment_headers_accepted": allowed,
    }


def extract_context(request: Request, settings: Settings) -> RequestContext:
    experiment_allowed = experiment_headers_allowed(request, settings)
    source_ip = _source_ip(request, settings, experiment_allowed)
    body_hash = _body_hash(request)
    request_timestamp = request.headers.get("X-Request-Timestamp")
    nonce = request.headers.get("X-Request-Nonce")
    idem = request.headers.get("Idempotency-Key")
    fingerprint_source = "|".join(
        [request.method, request.path, body_hash, request_timestamp or "", nonce or "", idem or ""]
    )
    ctx_time = _context_time(request, settings, experiment_allowed)
    return RequestContext(
        request_id=request.headers.get("X-Request-Id") or str(uuid.uuid4()),
        run_id=request.headers.get("X-Run-Id", "manual"),
        scenario_label=request.headers.get("X-Scenario-Label", "manual"),
        source_ip=source_ip,
        user_agent=_user_agent(request, experiment_allowed),
        client_id=request.headers.get("X-Client-Id", "unknown-client"),
        device_id=request.headers.get("X-Device-Id", ""),
        method=request.method,
        endpoint=request.path,
        timestamp=ctx_time.isoformat(),
        request_timestamp=request_timestamp,
        hour_utc=ctx_time.hour,
        body_hash=body_hash,
        request_fingerprint=hashlib.sha256(fingerprint_source.encode()).hexdigest(),
        nonce=nonce,
        idempotency_key=idem,
        device_signature=request.headers.get("X-Device-Signature"),
        experiment_headers_accepted=experiment_allowed,
    )
