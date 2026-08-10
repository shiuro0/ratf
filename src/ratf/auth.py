from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import InvalidTokenError

from .config import Settings
from .storage import MemoryStorage, Storage


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def secure_hash(value: str, secret: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def _registry_key(token_hash: str) -> str:
    return f"token_registry:{token_hash}"


def _family_key(family_id: str) -> str:
    return f"token_family:{family_id}"


def _scope_list(scope: str | list[str] | None) -> list[str]:
    if isinstance(scope, list):
        return sorted({str(x).strip() for x in scope if str(x).strip()})
    return sorted({x for x in str(scope or "").split() if x})


def stable_family_id(user_id: str, client_id: str, device_id: str, settings: Settings) -> str:
    raw = f"{user_id}|{client_id}|{device_id}"
    return "fam_" + secure_hash(raw, settings.token_hash_secret)[:32]


@dataclass
class TokenValidation:
    valid: bool
    token_id_hash: str = "unknown"
    claims: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


def _family_value(storage: Storage, family_id: str) -> dict[str, Any]:
    return storage.get_json(_family_key(family_id)) or {"token_hashes": []}


def _family_add(storage: Storage, family_id: str, token_hash: str, ttl: int) -> None:
    value = _family_value(storage, family_id)
    hashes = list(value.get("token_hashes", []))
    if token_hash not in hashes:
        hashes.append(token_hash)
    value["token_hashes"] = hashes
    value["updated_at"] = utc_now().isoformat()
    storage.set_json(_family_key(family_id), value, ttl_seconds=ttl)


def _revoke_record(storage: Storage, token_hash: str, reason: str) -> bool:
    record = storage.get_json(_registry_key(token_hash))
    if not record or not record.get("active"):
        return False
    record = dict(record)
    record["active"] = False
    record["revoked_at"] = utc_now().isoformat()
    record["revoked_reason"] = reason
    ttl = max(int(record.get("exp", 0)) - int(utc_now().timestamp()), 1)
    storage.set_json(_registry_key(token_hash), record, ttl_seconds=ttl)
    return True


def revoke_family_tokens(
    storage: Storage,
    family_id: str,
    keep_hash: str | None = None,
    reason: str = "access_token_replacement",
) -> int:
    revoked = 0
    for token_hash in _family_value(storage, family_id).get("token_hashes", []):
        if keep_hash and token_hash == keep_hash:
            continue
        revoked += int(_revoke_record(storage, token_hash, reason))
    return revoked


def _enforce_active_limit(storage: Storage, family_id: str, limit: int, keep_hash: str) -> int:
    active: list[tuple[int, str]] = []
    for token_hash in _family_value(storage, family_id).get("token_hashes", []):
        record = storage.get_json(_registry_key(token_hash))
        if record and record.get("active"):
            active.append((int(record.get("iat", 0)), token_hash))
    active.sort()
    revoked = 0
    while len(active) > max(limit, 1):
        _, token_hash = active.pop(0)
        if token_hash == keep_hash and active:
            active.append((int(utc_now().timestamp()), token_hash))
            active.sort()
            continue
        revoked += int(_revoke_record(storage, token_hash, "active_token_limit"))
    return revoked


def issue_access_token(
    *,
    user_id: str,
    role: str,
    client_id: str,
    device_id: str,
    settings: Settings,
    storage: Storage,
    token_format: str = "jwt",
    scope: str | list[str] | None = None,
    allowed_scopes: str | list[str] | None = None,
    ttl_seconds: int | None = None,
    family_id: str | None = None,
    rotate_family: bool | None = None,
    issuance_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = utc_now()
    ttl = int(ttl_seconds or settings.jwt_ttl_seconds)
    if ttl < 1 or ttl > settings.max_token_ttl_seconds:
        raise ValueError(f"ttl_seconds must be between 1 and {settings.max_token_ttl_seconds}")

    token_format = token_format.strip().lower()
    if token_format not in {"jwt", "opaque"}:
        raise ValueError("token_format must be jwt or opaque")

    allowed_source = (
        allowed_scopes
        if allowed_scopes is not None
        else (scope or "catalog:read orders:read orders:write payments:write")
    )
    allowed = set(_scope_list(allowed_source))
    requested = set(_scope_list(scope)) if scope is not None else set(allowed)
    if not requested.issubset(allowed):
        raise ValueError("requested scope exceeds the registered device policy")
    scopes = sorted(requested)

    family_id = family_id or stable_family_id(user_id, client_id, device_id, settings)
    replace_previous = settings.replace_previous_access_token if rotate_family is None else bool(rotate_family)
    exp = now + timedelta(seconds=ttl)
    jti = str(uuid.uuid4())
    device_hash = secure_hash(device_id, settings.token_hash_secret)
    claims = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": user_id,
        "role": role,
        "client_id": client_id,
        "scope": " ".join(scopes),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
        "sid": family_id,
        "cnf": {"device_hash": device_hash},
    }
    if token_format == "jwt":
        access_token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        token_hash = secure_hash(jti, settings.token_hash_secret)
    else:
        access_token = f"ratf_at_{secrets.token_urlsafe(32)}"
        token_hash = secure_hash(access_token, settings.token_hash_secret)

    registry_ttl = max(ttl, settings.registry_ttl_seconds)
    issue_ctx = issuance_context or {}
    metadata = {
        "active": True,
        "token_format": token_format,
        "token_type": "Bearer",
        "token_id_hash": token_hash,
        "jti": jti,
        "family_id": family_id,
        "sub": user_id,
        "role": role,
        "client_id": client_id,
        "scope": " ".join(scopes),
        "scopes": scopes,
        "device_id_hash": device_hash,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "issued_at": now.isoformat(),
        "expires_at": exp.isoformat(),
        "issued_ip": issue_ctx.get("issued_ip"),
        "issued_user_agent": issue_ctx.get("issued_user_agent"),
        "issued_hour_utc": issue_ctx.get("issued_hour_utc"),
        "use_count": 0,
        "last_used_at": None,
        "ttl_remaining": registry_ttl,
    }
    storage.set_json(_registry_key(token_hash), metadata, ttl_seconds=registry_ttl)
    _family_add(storage, family_id, token_hash, registry_ttl)

    revoked = revoke_family_tokens(storage, family_id, keep_hash=token_hash) if replace_previous else 0
    revoked += _enforce_active_limit(storage, family_id, settings.max_active_tokens_per_family, token_hash)
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "token_format": token_format,
        "expires_in": ttl,
        "scope": metadata["scope"],
        "family_id": family_id,
        "token_id_hash": token_hash,
        "replacement_policy_applied": replace_previous,
        "revoked_previous_tokens": revoked,
    }


def _decode_jwt(token: str, settings: Settings):
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "jti", "iss", "aud", "sub", "sid", "client_id"]},
        )
        return claims, None
    except InvalidTokenError as exc:
        return None, exc.__class__.__name__


def validate_access_token(token: str, settings: Settings, storage: Storage) -> TokenValidation:
    if token.startswith("ratf_at_"):
        token_hash = secure_hash(token, settings.token_hash_secret)
        meta = storage.get_json(_registry_key(token_hash))
        if not meta:
            return TokenValidation(False, token_hash, error="opaque_token_unknown")
        if not meta.get("active"):
            return TokenValidation(False, token_hash, metadata=meta, error="token_revoked")
        if int(utc_now().timestamp()) >= int(meta.get("exp", 0)):
            return TokenValidation(False, token_hash, metadata=meta, error="token_expired")
        return TokenValidation(True, token_hash, claims=dict(meta), metadata=meta)

    claims, error = _decode_jwt(token, settings)
    if error or claims is None:
        return TokenValidation(False, error=f"jwt_{error}")
    token_hash = secure_hash(str(claims["jti"]), settings.token_hash_secret)
    meta = storage.get_json(_registry_key(token_hash))
    if not meta:
        return TokenValidation(False, token_hash, claims=claims, error="jwt_not_registered")
    if not meta.get("active"):
        return TokenValidation(False, token_hash, claims=claims, metadata=meta, error="token_revoked")
    if int(utc_now().timestamp()) >= int(meta.get("exp", 0)):
        return TokenValidation(False, token_hash, claims=claims, metadata=meta, error="token_expired")

    comparisons = {
        "sub": meta.get("sub"),
        "client_id": meta.get("client_id"),
        "sid": meta.get("family_id"),
        "role": meta.get("role"),
        "scope": meta.get("scope"),
    }
    if any(str(claims.get(name)) != str(expected) for name, expected in comparisons.items()):
        return TokenValidation(False, token_hash, claims=claims, metadata=meta, error="registry_claim_mismatch")
    claim_device = (claims.get("cnf") or {}).get("device_hash")
    if not claim_device or not hmac.compare_digest(str(meta.get("device_id_hash", "")), str(claim_device)):
        return TokenValidation(False, token_hash, claims=claims, metadata=meta, error="registry_device_claim_mismatch")
    return TokenValidation(True, token_hash, claims=claims, metadata=meta)


def record_token_use(storage: Storage, token_hash: str, meta: dict[str, Any], ttl: int) -> None:
    updated = dict(meta)
    updated["use_count"] = int(updated.get("use_count", 0)) + 1
    updated["last_used_at"] = utc_now().isoformat()
    updated["ttl_remaining"] = max(ttl, 1)
    storage.set_json(_registry_key(token_hash), updated, ttl_seconds=max(ttl, 1))


def revoke_token(token: str, settings: Settings, storage: Storage, reason: str = "manual_revocation") -> bool:
    result = validate_access_token(token, settings, storage)
    if not result.metadata:
        return False
    return _revoke_record(storage, result.token_id_hash, reason)


def introspect_token(token: str, settings: Settings, storage: Storage) -> dict[str, Any]:
    result = validate_access_token(token, settings, storage)
    if not result.valid or not result.metadata:
        return {"active": False}
    m = result.metadata
    return {
        "active": True,
        "scope": m.get("scope", ""),
        "client_id": m.get("client_id"),
        "token_type": m.get("token_type", "Bearer"),
        "token_format": m.get("token_format"),
        "sub": m.get("sub"),
        "aud": m.get("aud"),
        "iss": m.get("iss"),
        "exp": m.get("exp"),
        "iat": m.get("iat"),
        "nbf": m.get("nbf"),
        "sid": m.get("family_id"),
        "cnf": {"device_hash": m.get("device_id_hash")},
    }


def extract_bearer_token(header: str | None) -> str | None:
    if not header:
        return None
    parts = header.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


# Compatibility helper retained for unit tests and earlier notebooks.
def create_token(user_id: str, settings: Settings, ttl_seconds: int | None = None, role: str = "user"):
    return issue_access_token(
        user_id=user_id,
        role=role,
        client_id="legacy-test-client",
        device_id="legacy-test-device",
        settings=settings,
        storage=MemoryStorage(),
        ttl_seconds=ttl_seconds,
    )


def decode_token(token: str, settings: Settings):
    return _decode_jwt(token, settings)
