from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .auth import record_token_use, validate_access_token
from .config import Settings
from .core.models import AuthenticationResult, Identity, RequestContext
from .storage import Storage


def _scopes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(sorted({str(item).strip() for item in value if str(item).strip()}))
    return tuple(sorted({item for item in str(value or "").split() if item}))


class LocalRegistryIdentityProvider:
    """Adapter for the local JWT/opaque-token issuer used by the research server."""

    def __init__(self, settings: Settings, storage: Storage):
        self.settings = settings
        self.storage = storage

    def authenticate(self, access_token: str, context: RequestContext) -> AuthenticationResult:
        result = validate_access_token(access_token, self.settings, self.storage)
        if not result.valid or not result.metadata:
            return AuthenticationResult(False, reason_code=result.error or "invalid_token")
        metadata = dict(result.metadata)
        identity = Identity(
            subject=str(metadata.get("sub", "")),
            client_id=str(metadata.get("client_id", "")),
            scopes=_scopes(metadata.get("scopes") or metadata.get("scope")),
            token_id=result.token_id_hash,
            family_id=str(metadata.get("family_id") or result.token_id_hash),
            expires_at=int(metadata["exp"]) if metadata.get("exp") is not None else None,
            metadata=metadata,
        )
        return AuthenticationResult(True, identity=identity)

    def record_use(self, identity: Identity, ttl_seconds: int) -> None:
        record_token_use(self.storage, identity.token_id, identity.metadata, ttl_seconds)


class CallbackIdentityProvider:
    """Small adapter for an application's existing token validation function."""

    def __init__(
        self,
        callback: Callable[[str, RequestContext], AuthenticationResult | Identity | dict[str, Any] | None],
        record_callback: Callable[[Identity, int], None] | None = None,
    ):
        self.callback = callback
        self.record_callback = record_callback

    def authenticate(self, access_token: str, context: RequestContext) -> AuthenticationResult:
        value = self.callback(access_token, context)
        if isinstance(value, AuthenticationResult):
            return value
        if isinstance(value, Identity):
            return AuthenticationResult(True, identity=value)
        if not value:
            return AuthenticationResult(False, reason_code="invalid_token")
        if value.get("active") is False:
            return AuthenticationResult(False, reason_code=str(value.get("reason_code", "invalid_token")))
        identity = Identity(
            subject=str(value.get("subject") or value.get("sub") or ""),
            client_id=str(value.get("client_id") or ""),
            scopes=_scopes(value.get("scopes") or value.get("scope")),
            token_id=str(value.get("token_id") or "callback"),
            family_id=str(value.get("family_id") or value.get("sid") or value.get("token_id") or "callback"),
            expires_at=int(value["exp"]) if value.get("exp") is not None else None,
            metadata=dict(value.get("metadata") or value),
        )
        return AuthenticationResult(True, identity=identity)

    def record_use(self, identity: Identity, ttl_seconds: int) -> None:
        if self.record_callback:
            self.record_callback(identity, ttl_seconds)


class OIDCIntrospectionIdentityProvider:
    """RFC 7662-style adapter for an application's OAuth/OIDC Identity Provider."""

    def __init__(
        self,
        introspection_url: str,
        client_id: str,
        client_secret: str,
        *,
        timeout_seconds: float = 3.0,
    ):
        self.introspection_url = introspection_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds

    def authenticate(self, access_token: str, context: RequestContext) -> AuthenticationResult:
        body = urlencode({"token": access_token, "token_type_hint": "access_token"}).encode()
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        request = Request(
            self.introspection_url,
            data=body,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return AuthenticationResult(False, reason_code="idp_unavailable_or_invalid_response")
        if not payload.get("active"):
            return AuthenticationResult(False, reason_code="token_inactive")
        token_id = hashlib.sha256(access_token.encode()).hexdigest()
        identity = Identity(
            subject=str(payload.get("sub", "")),
            client_id=str(payload.get("client_id") or payload.get("azp") or ""),
            scopes=_scopes(payload.get("scope")),
            token_id=token_id,
            family_id=str(payload.get("sid") or token_id),
            expires_at=int(payload["exp"]) if payload.get("exp") is not None else None,
            metadata=dict(payload),
        )
        return AuthenticationResult(True, identity=identity)

    def record_use(self, identity: Identity, ttl_seconds: int) -> None:
        return None
