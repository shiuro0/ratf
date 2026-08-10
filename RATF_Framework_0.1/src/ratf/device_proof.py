from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import Settings
from .core.models import RequestContext
from .storage import Storage


def _key(device_id: str) -> str:
    return f"device_registry:{device_id}"


def _derive_secret(settings: Settings, device_id: str, user_id: str, client_id: str) -> str:
    material = f"{device_id}|{user_id}|{client_id}".encode()
    return hmac.new(settings.device_master_secret.encode(), material, hashlib.sha256).hexdigest()


def _secret_fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def register_device(
    storage: Storage,
    settings: Settings,
    *,
    user_id: str,
    client_id: str,
    device_name: str,
    role: str = "customer",
    allowed_scopes: str | list[str] | None = None,
    device_id: str | None = None,
) -> dict[str, Any]:
    device_id = device_id or f"dev_{uuid.uuid4().hex}"
    secret = _derive_secret(settings, device_id, user_id, client_id)
    scope_source = allowed_scopes if allowed_scopes is not None else "catalog:read orders:read orders:write payments:write"
    scopes = (
        sorted({x for x in scope_source.split() if x})
        if isinstance(scope_source, str)
        else sorted({str(x).strip() for x in scope_source if str(x).strip()})
    )
    record = {
        "active": True,
        "device_id": device_id,
        "device_secret_fingerprint": _secret_fingerprint(secret),
        "user_id": user_id,
        "client_id": client_id,
        "device_name": device_name,
        "role": role,
        "allowed_scopes": scopes,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    storage.set_json(_key(device_id), record, ttl_seconds=settings.registry_ttl_seconds)
    return {
        "device_id": device_id,
        "device_secret": secret,
        "user_id": user_id,
        "client_id": client_id,
        "role": role,
        "allowed_scopes": scopes,
    }


def get_device(storage: Storage, device_id: str) -> dict[str, Any] | None:
    value = storage.get_json(_key(device_id))
    return dict(value) if value else None


def authenticate_device(
    storage: Storage,
    settings: Settings,
    device_id: str,
    device_secret: str,
    user_id: str,
    client_id: str,
) -> bool:
    record = get_device(storage, device_id)
    if not record or not record.get("active"):
        return False
    expected = _derive_secret(settings, device_id, user_id, client_id)
    return bool(
        hmac.compare_digest(expected, device_secret)
        and hmac.compare_digest(_secret_fingerprint(expected), str(record.get("device_secret_fingerprint", "")))
        and record.get("user_id") == user_id
        and record.get("client_id") == client_id
    )


def canonical_request(context: RequestContext) -> str:
    return "\n".join(
        [
            context.method.upper(),
            context.endpoint,
            context.body_hash,
            context.request_timestamp or "",
            context.nonce or "",
            context.idempotency_key or "",
        ]
    )


def sign_request(
    secret: str,
    method: str,
    path: str,
    body_hash: str,
    timestamp: str,
    nonce: str,
    idempotency_key: str = "",
) -> str:
    canonical = "\n".join([method.upper(), path, body_hash, timestamp, nonce, idempotency_key])
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


@dataclass
class DeviceProofResult:
    valid: bool
    reason_code: str | None = None


def verify_device_proof(
    storage: Storage,
    settings: Settings,
    context: RequestContext,
    token_metadata: dict[str, Any],
) -> DeviceProofResult:
    if not settings.device_proof_required:
        return DeviceProofResult(True)
    if not context.device_id:
        return DeviceProofResult(False, "device_id_missing")
    if not context.request_timestamp:
        return DeviceProofResult(False, "request_timestamp_missing")
    if not context.device_signature:
        return DeviceProofResult(False, "device_signature_missing")

    actual_hash = hmac.new(
        settings.token_hash_secret.encode(), context.device_id.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(str(token_metadata.get("device_id_hash", "")), actual_hash):
        return DeviceProofResult(False, "token_device_binding_mismatch")

    record = get_device(storage, context.device_id)
    if not record or not record.get("active"):
        return DeviceProofResult(False, "device_not_registered")
    if record.get("client_id") != token_metadata.get("client_id") or record.get("user_id") != token_metadata.get("sub"):
        return DeviceProofResult(False, "device_owner_mismatch")

    try:
        request_time = int(context.request_timestamp)
    except (TypeError, ValueError):
        return DeviceProofResult(False, "request_timestamp_invalid")
    if abs(int(datetime.now(timezone.utc).timestamp()) - request_time) > settings.timestamp_skew_seconds:
        return DeviceProofResult(False, "request_timestamp_outside_window")

    secret = _derive_secret(settings, context.device_id, str(record["user_id"]), str(record["client_id"]))
    expected = hmac.new(secret.encode(), canonical_request(context).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, context.device_signature):
        return DeviceProofResult(False, "device_signature_invalid")
    return DeviceProofResult(True)
