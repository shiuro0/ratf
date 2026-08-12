from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone


def request_headers(
    *,
    nonce: str | None = None,
    idempotency_key: str | None = None,
    ip: str = "192.168.10.10",
    user_agent: str = "MarketplaceApp/1.0",
    hour: int = 10,
    token: str = "app-token-alice",
) -> dict[str, str]:
    context_time = datetime.now(timezone.utc).replace(
        hour=hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Client-Id": "marketplace-app",
        "X-Device-Id": "device-primary",
        "X-Request-Nonce": nonce or f"nonce_{uuid.uuid4().hex}",
        "Idempotency-Key": idempotency_key or f"idem_{uuid.uuid4().hex}",
        "X-Experiment-Key": "local-experiment-key-32-characters-long",
        "X-Test-Source-IP": ip,
        "X-Test-Context-Time": context_time.isoformat(),
        "X-Scenario-Label": "validation",
        "User-Agent": user_agent,
    }


def authzen_payload(
    *,
    ip: str = "192.168.10.10",
    user_agent: str = "MarketplaceNode/1.0",
    device_id: str = "device-primary",
    hour: int = 10,
    scopes: list[str] | None = None,
) -> dict:
    return {
        "subject": {
            "type": "user",
            "id": "customer-node-001",
            "properties": {
                "client_id": "marketplace-node",
                "scopes": scopes or ["orders:write"],
                "family_id": "node-family-001",
                "issued_ip": "192.168.10.10",
                "issued_user_agent": "MarketplaceNode/1.0",
                "issued_hour_utc": 10,
            },
        },
        "resource": {"type": "endpoint", "id": "/orders", "properties": {"transactional": True}},
        "action": {"name": "POST", "properties": {"required_scope": "orders:write"}},
        "context": {
            "source_ip": ip,
            "user_agent": user_agent,
            "client_id": "marketplace-node",
            "device_id": device_id,
            "hour_utc": hour,
            "scenario_label": "interoperability",
        },
    }


def compact_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
