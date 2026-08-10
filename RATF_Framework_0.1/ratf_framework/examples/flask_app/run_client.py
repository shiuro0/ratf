from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import requests

BASE_URL = "http://127.0.0.1:5100"
TOKEN = "app-token-alice"
BODY = {"item": "Smartphone", "quantity": 1}


def send(
    label,
    ip,
    user_agent,
    hour,
    nonce=None,
    idempotency_key=None,
    endpoint="/api/orders",
    body=None,
):
    nonce = nonce or f"nonce_{uuid.uuid4().hex}"
    idempotency_key = idempotency_key or f"idem_{uuid.uuid4().hex}"
    context_time = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0).isoformat()
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Client-Id": "marketplace-app",
        "X-Device-Id": "device-primary",
        "X-Request-Nonce": nonce,
        "Idempotency-Key": idempotency_key,
        "X-Experiment-Key": "local-experiment-key-32-characters-long",
        "X-Test-Source-IP": ip,
        "X-Test-Context-Time": context_time,
        "X-Scenario-Label": label,
        "User-Agent": user_agent,
    }
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        headers=headers,
        json=BODY if body is None else body,
        timeout=5,
    )
    result = response.json()
    print(f"\n{label}")
    print("HTTP       :", response.status_code)
    print("Keputusan  :", response.headers.get("X-RATF-Decision", result.get("decision")))
    print("Trust score:", response.headers.get("X-RATF-Score", result.get("trust_score")))
    print("Alasan     :", response.headers.get("X-RATF-Reason", result.get("reason_code")))
    print("Policy     :", response.headers.get("X-RATF-Policy", result.get("policy_name")))
    print("Respons    :", result)
    return nonce, idempotency_key


if __name__ == "__main__":
    requests.post(f"{BASE_URL}/app/login", timeout=5).raise_for_status()
    send("Normal", "192.168.10.10", "MarketplaceApp/1.0", 10)
    replay_nonce = f"nonce_{uuid.uuid4().hex}"
    replay_idem = f"idem_{uuid.uuid4().hex}"
    send("Request pertama", "192.168.10.10", "MarketplaceApp/1.0", 10, replay_nonce, replay_idem)
    send("Exact replay", "192.168.10.10", "MarketplaceApp/1.0", 10, replay_nonce, replay_idem)
    time.sleep(0.05)
    send("Konteks berbeda", "103.10.20.30", "PythonBot/3.0", 23)
    send(
        "API pembayaran penting",
        "192.168.10.10",
        "MarketplaceApp/1.0",
        10,
        endpoint="/api/payments",
        body={"amount": 250000},
    )
