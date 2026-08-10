from datetime import datetime, timezone
import uuid

import requests


BASE_URL = "http://127.0.0.1:5100"
BODY = {"item": "Buku Pemrograman", "quantity": 1}


def tampilkan(judul, response):
    data = response.json()
    print(f"\n{judul}")
    print("HTTP       :", response.status_code)
    print("Keputusan  :", response.headers.get("X-RATF-Decision", data.get("decision")))
    print("Trust score:", response.headers.get("X-RATF-Score", data.get("trust_score")))
    print("Alasan     :", response.headers.get("X-RATF-Reason", data.get("reason_code")))
    print("Respons    :", data)


normal_headers = {
    "Authorization": "Bearer app-token-alice",
    "X-Client-Id": "marketplace-app",
    "X-Device-Id": "device-primary",
    "X-Request-Nonce": f"nonce_{uuid.uuid4().hex}",
    "Idempotency-Key": f"idem_{uuid.uuid4().hex}",
    "X-Experiment-Key": "local-experiment-key-32-characters-long",
    "X-Test-Source-IP": "192.168.10.10",
    "X-Test-Context-Time": datetime.now(timezone.utc).replace(hour=10).isoformat(),
    "User-Agent": "MarketplaceApp/1.0",
}

normal = requests.post(f"{BASE_URL}/api/orders", headers=normal_headers, json=BODY, timeout=5)
tampilkan("1. Request normal", normal)

changed_headers = normal_headers.copy()
changed_headers.update(
    {
        "X-Request-Nonce": f"nonce_{uuid.uuid4().hex}",
        "Idempotency-Key": f"idem_{uuid.uuid4().hex}",
        "X-Test-Source-IP": "103.10.20.30",
        "User-Agent": "AutomationClient/1.0",
    }
)
changed = requests.post(f"{BASE_URL}/api/orders", headers=changed_headers, json=BODY, timeout=5)
tampilkan("2. Token sama, tetapi IP dan aplikasi client berubah", changed)

replay = requests.post(f"{BASE_URL}/api/orders", headers=normal_headers, json=BODY, timeout=5)
tampilkan("3. Request normal dikirim ulang tanpa mengganti nonce", replay)

debug = requests.get(
    f"{BASE_URL}/app/debug/ratf",
    headers={"X-Debug-Key": "local-debug-key"},
    timeout=5,
).json()
print("\n4. State yang dapat dipakai pengembang untuk debug")
print("Storage              :", debug["storage_backend"])
print("Request allow tersimpan:", debug["context_history"].get("allowed_request_count", 0))
print("Context history      :", debug["context_history"])
print("Event terbaru        :", len(debug["recent_events"]))
print("Audit valid          :", debug["audit_integrity"]["valid"])
